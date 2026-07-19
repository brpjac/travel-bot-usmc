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

import re
from pathlib import Path

import yaml
from google import genai
from google.genai import types
from pydantic import BaseModel

REPO_ROOT = Path(__file__).parent
WIKI_DIR = REPO_ROOT / "wiki"
MODEL = "gemini-2.5-flash"

MAX_PAGES = 4
FAISS_K = 6


class RouterDecision(BaseModel):
    pages: list[str]
    needs_faiss: bool
    faiss_query: str | None = None


ROUTER_PROMPT = """\
You are the routing step for a USMC reserve travel-regulations assistant.
Given the question (and recent conversation), pick which wiki pages to load.

Rules:
- Choose 0-4 page paths, EXACTLY as they appear in the catalog below.
- Prefer `topic` and `index` pages. Pick a `source_extract` page only when the
  user wants exact/verbatim regulation wording.
- Set needs_faiss=true (with a focused faiss_query) only when the question
  needs deep Joint Travel Regulations or MCO 1001R.1K text that no wiki page
  covers — e.g. an obscure JTR entitlement not in the catalog.
- If nothing in the catalog fits, return an empty pages list.

PAGE CATALOG (path | type | description):
{catalog}

{history}Question: {question}"""


SYSTEM_PROMPT = """\
You are the MIU Travel Regulation Assistant for United States Marine Corps
reserve Marines. Answer using ONLY the wiki pages, claims registry, and
regulation excerpts provided below. Follow these rules strictly:

1. **Cite everything.** Cite registry facts by claim ID in brackets, e.g.
   [C020]. For regulation text, copy the parenthetical citations exactly as
   they appear in the wiki pages, e.g. (ForO 3000-52.1, Ch 5, p. 5-6) or
   (JTR, par. 020210, Table 2-10, p. 2-20).

2. **Do not guess.** If the provided material does not answer the question,
   say: "I don't have enough information in the loaded regulations to answer
   that. Please check with your S-1 or refer to the full JTR."

3. **Respect claim status.** A claim marked needs_review is not settled — say
   so. JTR-sourced numbers come from the Dec 2021 edition; add that caveat
   when a rate or dollar amount matters.

4. **MARADMIN precedence.** If sources conflict, newer specific direction
   (e.g. a MARADMIN) supersedes standing orders — note the conflict explicitly.

5. **Be practical — present options as a decision tree.** When a Marine asks
   what they can do, lay out ALL their options with what each one gets them,
   and connect the orders type to what the Marine actually rates (lodging, per
   diem, rental car, mileage). Include deadlines, form names, submission
   requirements, and who to contact when the sources provide them.

6. **Use plain language.** Explain regulation language in terms a junior
   Marine can understand, but always include the exact citation.

7. **DTS is a tool, not an orders type.** The orders types are IDT, Offsite
   IDT, AT, and ADOS. Never list "DTS" as a type of orders.

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
    for rel in paths[:MAX_PAGES]:
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


def route(client, catalog: str, history: str, question: str) -> tuple[RouterDecision, dict]:
    prompt = ROUTER_PROMPT.format(
        catalog=catalog,
        history=(history + "\n") if history else "",
        question=question,
    )
    resp = client.models.generate_content(
        model=MODEL,
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


def answer(client, claims: str, pages_text: str, faiss_text: str, history: str, question: str) -> tuple[str, dict]:
    faiss_section = ""
    if faiss_text:
        faiss_section = f"\n=== REGULATION EXCERPTS (vector search over raw JTR/MCRAMM) ===\n{faiss_text}\n"
    prompt = SYSTEM_PROMPT.format(
        claims=claims,
        pages=pages_text or "(no wiki pages selected)",
        faiss_section=faiss_section,
        history=(history + "\n") if history else "",
        question=question,
    )
    resp = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.1),
    )
    return resp.text or "", _usage(resp)


def cited_claims(answer_text: str, claims_index: dict) -> list[str]:
    """Pull [C###] cites out of the answer and render their registry rows."""
    out = []
    for cid in sorted(set(re.findall(r"\[(C\d{3})\]", answer_text))):
        c = claims_index.get(cid)
        if c:
            out.append(f"**{cid}** — {c['claim']} _({c['source']})_")
    return out


def ask(client, vectorstore, catalog: str, claims: str, claims_index: dict,
        history: str, question: str) -> dict:
    """Full two-call pipeline. Returns answer text, sources, and per-call usage."""
    decision, router_usage = route(client, catalog, history, question)

    pages_text, loaded_pages = read_pages(decision.pages)
    if not loaded_pages and not decision.needs_faiss:
        decision.needs_faiss = True
        decision.faiss_query = decision.faiss_query or question

    faiss_text, faiss_citations = "", []
    if decision.needs_faiss and vectorstore is not None:
        faiss_text, faiss_citations = faiss_search(vectorstore, decision.faiss_query or question)

    text, answer_usage = answer(client, claims, pages_text, faiss_text, history, question)

    return {
        "answer": text,
        "pages": loaded_pages,
        "faiss_citations": faiss_citations,
        "claim_citations": cited_claims(text, claims_index),
        "usage": [
            {"call_type": "router", **router_usage},
            {"call_type": "answer", **answer_usage},
        ],
    }
