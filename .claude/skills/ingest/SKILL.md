---
name: ingest
description: Ingest a new source document (MARADMIN, updated JTR, ForO, unit guidance) into the wiki - extract claims, stage or merge into registries, update topic pages, optionally re-run FAISS ingestion. Use when the user provides a new travel document or says /ingest <path>.
user_invocable: true
argument-hint: "<path to document>"
---

# Wiki ingest

The write path for the knowledge layer. Rule #1: **never invent claims** —
every extracted fact carries its exact source location.

## Workflow

1. **Identify the source.** Determine title, date, doc type, distribution
   marking. CHECK FOR DISTRIBUTION MARKINGS FIRST (unit-restricted or
   controlled-information phrases — the lint skill's guard patterns list them):
   marked documents go in `wiki/sources/raw/local/` (gitignored), never the
   committed tree; only public-release documents go in `wiki/sources/raw/`.
   When a wiki page needs to discuss a marking, paraphrase it — never
   reproduce the literal phrase, or the distribution guard will (correctly)
   fail the commit and the bundle.

2. **Read current wiki state.** `wiki/CLAUDE.md`, `wiki/_schema.md`,
   `wiki/_sources.yml`, `wiki/_claims.yml`, and the topic pages the new
   document touches.

3. **Register the source.** Add a `_sources.yml` entry (next SRC-* id,
   `filename`, `doc_type`, `as_of`, `distribution`, `local_only`, `in_faiss`,
   `scanned`). Scanned PDFs (no text layer) get `in_faiss: false` — their wiki
   transcription becomes the searchable form.

4. **Extract claims.** Every verifiable number/deadline/rule, each with a
   regulation citation (doc, chapter/paragraph, page). For scanned PDFs, read
   page images with the Read tool in 4-7 page slices, and transcribe cited
   chapters into `wiki/sources/<doc-slug>/` as `source_extract` pages
   (frontmatter per `_schema.md`: `verbatim: true`, `raw_file`,
   `pages_transcribed`). Illegible areas are marked `[illegible]`, never
   guessed.

5. **Match against the registry.** For each extracted claim:
   - **Matches an existing claim** → update `last_reviewed`/source if needed.
   - **Conflicts with an existing claim** → do NOT overwrite. Stage it in
     `wiki/pending-review.md` with both versions and sources; if the new
     source is newer and authoritative, propose supersession (old claim
     `status: retired`, `preferred_claim_id` → new ID) and ask the user.
   - **New** → assign the next C### after the highest existing ID, add to
     `_claims.yml` AND the `_claims.md` projection (keep them synchronized).

6. **Update topic pages.** Add/adjust content with inline `[C###]` cites and
   verbatim parentheticals; update `claim_ids`/`source_ids`/`related`
   frontmatter; MARADMINs that supersede standing guidance also update
   `wiki/reference/precedence-and-currency.md`.

7. **Close out.** Run `python3 scripts/generate_wiki_map.py`; if the source is
   `in_faiss: true`, run `.venv/bin/python scripts/ingest.py --incremental`;
   append one line to `wiki/log.md` (`[YYYY-MM-DD] INGEST: ...`); report what
   was added, staged, and superseded.
