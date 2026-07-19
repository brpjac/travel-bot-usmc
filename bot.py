"""
MIU Travel Regulation Bot — agent logic.

Two-call flow on Gemini 2.5 Flash (free tier):
  1. Router: reads the wiki page catalog (_map.md) and picks 0-4 pages to load,
     plus an optional FAISS fallback for deep JTR/MCRAMM text.
  2. Answer: composes the reply from the full wiki pages + the claims registry
     (+ FAISS chunks when triggered), citing claim IDs and regulation
     parentheticals.

The wiki (wiki/) is the knowledge layer; FAISS only serves verbatim deep-cuts
from the raw JTR/MCRAMM PDFs.
"""

import os
import re
from datetime import date
from pathlib import Path

import yaml
from google import genai
from google.genai import types
from pydantic import BaseModel

REPO_ROOT = Path(__file__).parent
WIKI_DIR = REPO_ROOT / "wiki"

# Router runs on flash-lite (separate free-tier quota → doubles daily question
# capacity); the answer stays on flash. Override via env for paid tiers/testing.
ROUTER_MODEL = os.environ.get("MIU_ROUTER_MODEL", "gemini-2.5-flash-lite")
ANSWER_MODEL = os.environ.get("MIU_ANSWER_MODEL", "gemini-2.5-flash")

MAX_PAGES = 4
FAISS_K = 6

# Shared claim-ID pattern (also used by scripts/eval.py). 3+ digits: C041, C1000.
CLAIM_ID_RE = re.compile(r"C\d{3,}")


class RouterDecision(BaseModel):
    pages: list[str]
    needs_faiss: bool
    faiss_query: str | None = None


# NOTE: both prompt templates go through str.format() — never add literal { }
# braces to them (e.g. JSON examples); doing so breaks every call at runtime.
ROUTER_PROMPT = """\
You are the routing step for a USMC reserve travel-regulations assistant.
Given the question (and recent conversation), pick which wiki pages to load.
Today's date: {today}.

Rules:
- Choose 0-4 page paths, EXACTLY as they appear in the catalog below.
- Prefer `topic` and `index` pages. Pick a `source_extract` page only when the
  user wants exact/verbatim regulation wording.
- Set needs_faiss=true (with a focused faiss_query) only when the question
  needs deep Joint Travel Regulations or MCRAMM (MCO 1001R.1L) text that no
  wiki page covers — e.g. an obscure JTR entitlement not in the catalog.
- If nothing in the catalog fits, return an empty pages list.

PAGE CATALOG (path | type | description):
{catalog}

{history}Question: {question}"""


SYSTEM_PROMPT = """\
You are the MIU Travel Regulation Assistant for United States Marine Corps
reserve Marines. Today's date: {today}. Answer using ONLY the wiki pages,
claims registry, and regulation excerpts provided below. Follow these rules
strictly:

1. **Less is more.** Lead with the direct answer in your first sentence. Keep
   the whole reply well under 120 words unless the Marine genuinely has
   multiple options to weigh. No filler ("It is important to note...", "Great
   question"), no restating the question, no headers for short answers.

2. **Cite naturally.** Name the source in parentheses where a fact lands, e.g.
   (MARADMIN 157/25) or (ForO 3000-52.1, Ch 5) — section/page only when it
   helps someone look it up. NEVER show internal claim IDs like C041 in the
   answer text. Cite each fact once; don't stack citations.

3. **Machine trailer (required).** After your answer, on its own final line,
   list the internal claim IDs your answer relied on:
   CLAIMS: C041, C044
   If none apply, write: CLAIMS: none
   This line is stripped before display — never reference it in prose.

4. **Do not guess.** If the provided material does not answer the question,
   say: "I don't have enough information in the loaded regulations to answer
   that. Please check with your S-1 or refer to the full JTR."

5. **Respect claim status.** A claim marked needs_review is not settled — say
   so briefly. If a claim's source string flags an old edition or a
   supersession, carry that caveat into the answer only when the number
   itself is the answer.

6. **Present options only when they exist.** If a Marine asks what they can
   do and there are real alternatives, list them tersely with what each one
   rates. Otherwise just answer.

7. **Plain language; DTS is a tool, not an orders type.** The orders types
   are IDT, Offsite IDT, AT, and ADOS. If sources conflict, newer specific
   direction (e.g. a MARADMIN) supersedes standing orders — say so.

8. **Exact dates.** For deadline math on a specific trip, give the D-offsets
   with citations, then add: "For exact dates and a calendar download, use
   the Trip Planner at the top of this page."

=== CLAIMS REGISTRY (id | claim | source | status) ===
{claims}

=== WIKI PAGES ===
{pages}
{faiss_section}
{history}Question: {question}"""


# --- Wiki loading -----------------------------------------------------------

def load_page_catalog() -> str:
    """Parse wiki/_map.md into the router's catalog: path | type | description."""
    map_file = WIKI_DIR / "_map.md"
    lines = []
    row_re = re.compile(r"^\|\s*\[([^\]]+)\]\([^)]*\)\s*\|([^|]*)\|([^|]*)\|([^|]*)\|(.*)\|\s*$")
    for line in map_file.read_text(encoding="utf-8").splitlines():
        m = row_re.match(line)
        if not m:
            continue
        path, ptype, _access, _reviewed, desc = (g.strip() for g in m.groups())
        if path.startswith("Page") or ptype in ("registry", "health", "log", "staging", "schema"):
            continue
        lines.append(f"{path} | {ptype} | {desc}")
    return "\n".join(lines)


def load_claims_table() -> tuple[str, dict]:
    """Compact claims table for the answer prompt + id->claim dict for citations."""
    data = yaml.safe_load((WIKI_DIR / "_claims.yml").read_text(encoding="utf-8"))
    rows, index = [], {}
    for c in data.get("claims", []):
        rows.append(f"{c['id']} | {c['claim']} | {c['source']} | {c.get('status', '')}")
        index[c["id"]] = c
    return "\n".join(rows), index


def read_pages(paths: list[str]) -> tuple[str, list[str]]:
    """Read selected wiki pages, path-validated against the wiki root."""
    blocks, loaded = [], []
    seen = set()
    deduped = [p for p in paths if not (p in seen or seen.add(p))]
    for rel in deduped[:MAX_PAGES]:
        target = (WIKI_DIR / rel).resolve()
        if not target.is_file() or WIKI_DIR.resolve() not in target.parents:
            continue
        blocks.append(f"=== {rel} ===\n{target.read_text(encoding='utf-8')}")
        loaded.append(rel)
    return "\n\n".join(blocks), loaded


# --- FAISS fallback ---------------------------------------------------------

def faiss_search(vectorstore, query: str, k: int = FAISS_K) -> tuple[str, list[str]]:
    """Retrieve deep JTR/MCRAMM chunks; returns (context, citations)."""
    docs = vectorstore.similarity_search(query, k=k)
    formatted, citations, seen = [], [], set()
    for doc in docs:
        m = doc.metadata
        source = m.get("source_doc", "Unknown")
        section = m.get("section", "")
        page = m.get("page", "")
        header = f"[{source}" + (f", Section {section}" if section else "") + (f", Page {page}" if page else "") + "]"
        formatted.append(f"{header}\n{doc.page_content}")
        key = f"{source}|{section}|{page}"
        if key not in seen:
            seen.add(key)
            citations.append(", ".join(p for p in [source, f"Section {section}" if section else "", f"Page {page}" if page else ""] if p))
    return "\n\n---\n\n".join(formatted), citations


# --- LLM calls --------------------------------------------------------------

def _usage(resp) -> dict:
    u = resp.usage_metadata
    return {
        "prompt": (u.prompt_token_count or 0) if u else 0,
        "response": (u.candidates_token_count or 0) if u else 0,
    }


def route(client, catalog: str, history: str, question: str, today: str) -> tuple[RouterDecision, dict]:
    prompt = ROUTER_PROMPT.format(
        catalog=catalog,
        history=(history + "\n") if history else "",
        question=question,
        today=today,
    )
    resp = client.models.generate_content(
        model=ROUTER_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_schema=RouterDecision,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    decision = resp.parsed or RouterDecision(pages=[], needs_faiss=True, faiss_query=question)
    return decision, _usage(resp)


def answer(client, claims: str, pages_text: str, faiss_text: str, history: str,
           question: str, today: str) -> tuple[str, dict]:
    faiss_section = ""
    if faiss_text:
        faiss_section = f"\n=== REGULATION EXCERPTS (vector search over raw JTR/MCRAMM) ===\n{faiss_text}\n"
    prompt = SYSTEM_PROMPT.format(
        claims=claims,
        pages=pages_text or "(no wiki pages selected)",
        faiss_section=faiss_section,
        history=(history + "\n") if history else "",
        question=question,
        today=today,
    )
    resp = client.models.generate_content(
        model=ANSWER_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.1),
    )
    return resp.text or "", _usage(resp)


def split_claims_trailer(text: str) -> tuple[str, list[str]]:
    """Split the machine trailer ('CLAIMS: C041, C044' / 'CLAIMS: none') off an
    answer. Returns (clean display text, claim id list). Tolerates a missing
    trailer and stray inline IDs (belt-and-suspenders sweep of the whole text)."""
    ids: list[str] = []
    lines = text.rstrip().splitlines()
    body = text.rstrip()
    for i in range(len(lines) - 1, max(len(lines) - 3, -1), -1):
        if lines[i].strip().upper().startswith("CLAIMS:"):
            ids = CLAIM_ID_RE.findall(lines[i])
            body = "\n".join(lines[:i]).rstrip()
            break
    if not ids:
        ids = CLAIM_ID_RE.findall(body)
    # Strip any bracketed IDs the model left in prose despite instructions.
    body = re.sub(r"\s*\[C\d{3,}\]", "", body)
    return body, sorted(set(ids))


def cited_claims(claim_ids: list[str], claims_index: dict) -> list[str]:
    """Render cited claims for the Sources panel — human-readable, no C### shown."""
    out = []
    for cid in claim_ids:
        c = claims_index.get(cid)
        if c:
            out.append(f"{c['claim']} _({c['source']})_")
    return out


def ask(client, vectorstore, catalog: str, claims: str, claims_index: dict,
        history: str, question: str, today: str | None = None) -> dict:
    """Full two-call pipeline. Returns clean answer text, sources, per-call usage.
    `today` is injectable so evals can pin the date."""
    today = today or date.today().isoformat()
    decision, router_usage = route(client, catalog, history, question, today)

    pages_text, loaded_pages = read_pages(decision.pages)
    if not loaded_pages and not decision.needs_faiss:
        decision.needs_faiss = True
        decision.faiss_query = decision.faiss_query or question

    faiss_text, faiss_citations = "", []
    if decision.needs_faiss and vectorstore is not None:
        faiss_text, faiss_citations = faiss_search(vectorstore, decision.faiss_query or question)

    raw_text, answer_usage = answer(client, claims, pages_text, faiss_text,
                                    history, question, today)
    text, claim_ids = split_claims_trailer(raw_text)

    return {
        "answer": text,
        "claim_ids": claim_ids,
        "pages": loaded_pages,
        "faiss_citations": faiss_citations,
        "claim_citations": cited_claims(claim_ids, claims_index),
        "usage": [
            {"call_type": "router", **router_usage},
            {"call_type": "answer", **answer_usage},
        ],
    }
