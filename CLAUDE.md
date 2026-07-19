# MIU Travel Regulation Bot

Chatbot for USMC reserve Marines (MIU / MARFORRES) to query travel regulations
and get their T3/TOP requests in on time. The knowledge layer is a
**human-and-machine-readable markdown wiki** (`wiki/`) — the bot navigates it
agentically instead of doing chunk-RAG.

## Architecture

```
Marine → Streamlit (app.py)
           └─ bot.py: two Gemini 2.5 Flash calls per question
              1. Router  — reads wiki/_map.md catalog, picks 2-4 pages
              2. Answer  — full pages + claims registry → cited answer
                 └─ optional FAISS fallback: deep verbatim JTR/MCRAMM cuts
```

- **Knowledge layer:** `wiki/` — topic pages, claims registry (`_claims.yml`,
  stable C### IDs), source manifest (`_sources.yml`), verbatim extracts
  (`wiki/sources/`), raw PDFs (`wiki/sources/raw/`). Start at
  [wiki/CLAUDE.md](wiki/CLAUDE.md).
- **LLM:** Google Gemini 2.5 Flash free tier via `google-genai` SDK
  (~2 calls / 8-12k tokens per question → ~125 questions/day within free RPD).
- **FAISS fallback:** all-MiniLM-L6-v2 local embeddings over the raw JTR +
  MCRAMM only (LangChain kept solely to load the index format).
- **Frontend:** Streamlit; **hosting:** Streamlit Community Cloud.

## Project structure

```
app.py                      Streamlit UI
bot.py                      Router + answer pipeline (google-genai)
wiki/                       THE KNOWLEDGE LAYER (see wiki/CLAUDE.md)
wiki/sources/raw/           Raw source PDFs (committed, public-release only)
wiki/sources/raw/local/     GITIGNORED — distribution-marked material
scripts/ingest.py           Raw PDFs → FAISS (reads wiki/_sources.yml)
scripts/generate_wiki_map.py  Regenerates wiki/_map.md from frontmatter
scripts/export_bundle.py    NIPR/genai.mil bundle → dist/
vectorstore/                FAISS index (committed so Cloud needs no rebuild)
.claude/skills/             wiki (read) / ingest (write) / lint (validate)
```

## How to run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export GOOGLE_API_KEY="your-key-here"        # https://aistudio.google.com/apikey
.venv/bin/streamlit run app.py
```

Streamlit Cloud: set `GOOGLE_API_KEY` in dashboard secrets; deploys on push.

## Adding a new document (MARADMIN, updated JTR, unit guidance)

Use the `/ingest` skill — it drives this whole flow. Manually:

1. **Check distribution markings first.** Public-release → `wiki/sources/raw/`.
   Marked/restricted → `wiki/sources/raw/local/` (gitignored, never committed).
2. Register it in `wiki/_sources.yml` (next SRC-* id; `in_faiss: false` for
   scanned or marked docs — wiki pages/extracts become their searchable form).
3. Extract claims into `wiki/_claims.yml` + `_claims.md` (next C### id),
   update/add topic pages with `[C###]` cites and `(source, section, page)`
   parentheticals; transcribe cited chapters into `wiki/sources/<doc>/`.
4. `python3 scripts/generate_wiki_map.py`
5. If `in_faiss: true`: `.venv/bin/python scripts/ingest.py --incremental`
6. Append one line to `wiki/log.md`; run `/lint`.
7. Push — Streamlit Cloud redeploys.

## Full FAISS re-index

```bash
.venv/bin/python scripts/ingest.py
```

## NIPR / genai.mil bundle

```bash
python3 scripts/export_bundle.py            # dist/miu-travel-wiki{,.zip} + onefile.md
python3 scripts/export_bundle.py --full     # onefile also inlines verbatim extracts
python3 scripts/export_bundle.py --with-raw # + committed raw PDFs
```

`dist/miu-travel-wiki-onefile.md` (~18k tokens) pastes into any genai.mil chat;
the folder/zip form is for agents that can read files. `AGENTS.md` inside the
bundle is the self-contained system prompt. The gitignored `raw/local/` is
never exported; a distribution guard scans every export.

## Rules that keep this safe to host

- Only public-release material is committed or bundled. Marked documents live
  in `wiki/sources/raw/local/` and their mechanics are paraphrased in pages.
- Never write a literal distribution-marking phrase in a committed file
  (paraphrase it) — `/lint` check #8 and the bundle guard both fail on hits.
- Every number needs a claim ID; every claim needs a source. `needs_review`
  means not settled — the bot says so.

## Token usage logs

`logs/token_usage.csv` (local only; Cloud storage is ephemeral):
`timestamp, question_length, call_type, prompt_tokens, response_tokens, total_tokens`
— two rows per question (`router`, `answer`). The sidebar shows session totals.
