# MIU Travel Regulation Bot

A chatbot + trip planner that helps USMC reserve Marines (Marine Innovation
Unit / MARFORRES) navigate travel regulations and get their T3/TOP requests in
on time. Built to attack a real problem: late transportation-request
submissions (the unit was at 53% on-time when this was built).

**The knowledge layer is the product.** Instead of black-box RAG, all
regulation knowledge lives in a human-and-machine-readable markdown wiki
(`wiki/`) with a claims registry, verbatim source extracts, and the raw
source PDFs at the bottom. The chatbot is one consumer of that wiki; any
file-reading agent (including on NIPR / genai.mil) can be pointed at the same
content.

## What's in the box

```
app.py                      Streamlit UI: chat + trip planner + usage counter
bot.py                      Two-call agentic pipeline (google-genai SDK):
                              1. Router — reads wiki/_map.md, picks 2-4 pages
                              2. Answer — full pages + claims registry → cited answer
planner.py                  Deterministic deadline planner + .ics calendar export
                            (zero model calls — works with no API quota at all)
wiki/                       THE KNOWLEDGE LAYER — start at wiki/CLAUDE.md
  _claims.yml / _claims.md  Registry of every hard number, stable C### IDs
  _sources.yml              Source-document registry (drives FAISS ingestion)
  _map.md                   Auto-generated page catalog (= the router's menu)
  reference/timelines.yml   Machine-readable deadline rules (drives the planner)
  sources/                  Verbatim extracts, one hop above the raw PDFs
  sources/raw/              Public-release source PDFs (JTR, MCRAMM, ForO, MARADMIN)
vectorstore/                Committed FAISS index (deep verbatim JTR/MCRAMM search)
scripts/
  ingest.py                 Raw PDFs → FAISS (reads wiki/_sources.yml)
  generate_wiki_map.py      Rebuilds _map.md from page frontmatter (--check for CI)
  lint_wiki.py              9 mechanical health checks incl. distribution guard
  eval.py                   Answer-quality regression suite (needs API key)
  export_bundle.py          Self-contained NIPR/genai.mil bundle → dist/
evals/questions.yml         26 golden questions with deterministic grading
tests/test_planner.py       Date-math and ICS unit tests
.github/workflows/ci.yml    Lint + map + bundle guard + tests on every push;
                            manual eval job (needs GOOGLE_API_KEY repo secret)
.claude/skills/             Maintenance workflows for AI-assisted editing
                            (wiki reader / document ingest / lint)
```

## Quickstart (local)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export GOOGLE_API_KEY="..."     # free key: https://aistudio.google.com/apikey
.venv/bin/streamlit run app.py
```

The Trip Planner works immediately with no API key (it makes no model calls).
Chat requires the key.

## Hosting (Streamlit Community Cloud, free)

1. Push this tree to a GitHub repo you control.
2. At share.streamlit.io: New app → point at the repo, main file `app.py`.
3. App Settings → Secrets: add `GOOGLE_API_KEY = "..."`.
4. Every push to the repo redeploys automatically.

## Models, cost, and the quota reality

- Defaults: both calls on `gemini-2.5-flash` (`bot.py`). Override without a
  redeploy via Streamlit secrets `MIU_ROUTER_MODEL` / `MIU_ANSWER_MODEL`
  (same names work as env vars locally).
- Each question ≈ 2 requests / ~9k tokens.
- **Free tier**: Google has been cutting free quotas on deprecating model
  families (as of Jul 2026, 2.5-family ≈ 20 requests/day on new keys; current
  flagship models load-shed free traffic at peak). Treat free tier as
  demo-only capacity and verify current limits for your key.
- **Paid**: roughly half a cent per question at 2026 pricing. The in-app
  daily counter (`DAILY_BUDGET` in app.py, default 200 answers/day) doubles
  as a spend cap: a maxed-out day is well under $1.
- Resilience built in: router-model 404 → automatic fallback to the answer
  model; 503 load-shedding → one automatic retry.

## Keeping the knowledge current

The wiki is the single source of truth; everything else derives from it.

1. **New document** (MARADMIN, updated JTR, unit guidance): check its
   distribution marking FIRST. Public release → `wiki/sources/raw/`;
   marked/restricted → `wiki/sources/raw/local/` (gitignored — never
   committed; page content paraphrases mechanics only). Register it in
   `wiki/_sources.yml`, extract claims into `wiki/_claims.yml` + `_claims.md`
   (next C### ID), cite them in topic pages as `[C###]`, transcribe cited
   chapters into `wiki/sources/<doc>/`.
2. Regenerate the catalog: `python3 scripts/generate_wiki_map.py`.
3. If the doc is `in_faiss: true`: `.venv/bin/python scripts/ingest.py --incremental`.
4. Health check: `python3 scripts/lint_wiki.py --write-health` — 9 checks
   including a fail-hard distribution guard that greps every tracked file for
   marking phrases.
5. Quality check: `GOOGLE_API_KEY=... python scripts/eval.py` runs the real
   pipeline over the 26 golden questions and grades citations, numbers,
   router accuracy, and brevity deterministically. Also runnable from GitHub
   Actions (manual `eval` job; set the `GOOGLE_API_KEY` repo secret; supports
   A/B model inputs for safe upgrades).

If you use Claude Code (or a compatible agent), `.claude/skills/` contains
guided workflows for all of the above (`/ingest`, `/lint`, `/wiki`).

## The NIPR / genai.mil story

```bash
python3 scripts/export_bundle.py            # dist/miu-travel-wiki{,.zip} + onefile.md
```

Produces a self-contained markdown bundle any agent can be pointed at:
`AGENTS.md` inside it is the system prompt, `_map.md` the catalog,
`QUESTIONS.md` an answer key (generated from the eval suite) for validating
whatever agent you attach. `dist/miu-travel-wiki-onefile.md` (~19k tokens)
pastes into a chat UI with no file access. No Python, no vector store, no
API needed on the receiving side — that's the point: the wiki ports to
environments the app never could.

## Safety rails you should keep

- Only public-release material belongs in the repo or bundles. The lint
  distribution guard and the bundle exporter both fail hard on
  distribution-marking phrases; `wiki/sources/raw/local/` is the gitignored
  quarantine for anything marked.
- Every number in an answer traces to a claim ID; every claim traces to a
  source document, section, and page. `needs_review` claims are flagged as
  unsettled in answers — keep that honesty.
- The app shows a BETA banner for a reason: it is a reference aid, not an
  authoritative system. Marines verify with their S-1.

## Sources currently loaded

| Source | Edition | Notes |
|---|---|---|
| Joint Travel Regulations | Jul 2026 | Updates monthly — refresh periodically |
| MCO 1001R.1L w/ Admin CH-2 (MCRAMM) | Dec 2015 | Current published revision |
| ForO 3000-52.1 (TEEP/T3 SOP) | Apr 2019 | Fully transcribed (original is a scan) |
| MARADMIN 157/25 (IDT-R update) | Mar 2025 | $500→$750 supersession example |
| Unit orders-type guidance | Mar 2026 | Mechanics distilled into pages |

All committed sources carry Distribution Statement A (approved for public
release) or are official public messages.
