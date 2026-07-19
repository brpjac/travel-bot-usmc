---
title: "Wiki Schema"
description: "Rules for pages, frontmatter, citations, claims, and sources in the MIU travel wiki"
type: schema
access: public_release
status: active
last_reviewed: 2026-07-17
---

# Wiki Schema

Rules for every page in this wiki. Read this before adding or editing content.

## Philosophy

Markdown-first and repo-auditable. This wiki is simultaneously:
1. A human reference Marines can browse (works in Obsidian, GitHub, any editor).
2. The bot's knowledge layer (the router picks pages from `_map.md`, answers from full pages).
3. A portable bundle for genai.mil / NIPR laptops (`scripts/export_bundle.py`).

It is NOT a vector index, graph database, or memory system. Pattern credit:
Karpathy's markdown-memory concept, adapted from the FLIP operations wiki.

## Directory layout

- `orders-types/` — what each orders type is and when to use it
- `entitlements/` — what money/lodging/transport each orders type rates
- `process/` — how to actually submit: MIU workflow, T3/TOP, TEEP, DTS/MROWS
- `reference/` — cross-cutting: distance thresholds, acronyms, precedence, contacts
- `sources/` — the descent to ground truth: verbatim extracts, then raw originals
  - `sources/<doc>/` — verbatim markdown transcriptions of cited chapters/paragraphs
  - `sources/raw/` — the actual source PDFs (the safety layer for future builds)
  - `sources/raw/local/` — GITIGNORED. Distribution-marked material. Never committed,
    never auto-bundled.

Every folder has a `CLAUDE.md` index. `AGENTS.md` at the root is a symlink to
`CLAUDE.md` (materialized as a real file in exported bundles).

## Page types

| type | meaning |
|------|---------|
| `index` | folder `CLAUDE.md` files |
| `topic` | a distilled subject page (the default) |
| `source_extract` | verbatim transcription of part of a source document |
| `schema` | this file |
| `registry` | `_claims.*`, `_sources.yml` |
| `health` / `log` / `staging` | infra |

## Frontmatter (required on every page)

```yaml
---
title: "T3 Submission Timelines"
description: "D-65 through D-5 ladder plus DMO TOP/TOT deadlines for CONUS and OCONUS travel"
type: topic
access: public_release        # public_release | unit_internal (unit_internal pages live in gitignored wiki/internal/)
status: active                # active | draft | needs_review
last_reviewed: 2026-07-17
claim_ids: [C020, C021]       # registry claims this page directly relies on
source_ids: [SRC-FORO-3000-52-1]
related:
  - t3-waivers.md
  - ../process/orders-request-miu.md
---
```

`description` is mandatory — it feeds `_map.md`, which is both the human
inventory and the bot router's page catalog. Write it as "what questions does
this page answer," not "what this page is about."

`source_extract` pages additionally require:

```yaml
verbatim: true
raw_file: ../raw/ForO 3000-52.1 T3 SOP.pdf   # relative path to the original
pages_transcribed: "18-22"                    # page range of the original covered
```

## Linking

- Relative markdown links only: `[log.md](log.md)`. Never
  `[[wikilinks]]`, never bare code-span filenames — code spans are invisible to
  the Obsidian graph and unclickable for humans and agents.
- `related:` frontmatter holds graph neighbors that don't fit the body.
- Every non-index page must have at least one inbound link (`/lint` flags orphans).
- Topic pages link DOWN to their source extracts ("Full text: ..."); extracts
  link down to their `raw_file`.

## Citation convention (load-bearing — the bot copies these verbatim)

Every factual statement carries a citation:

- Registry facts: inline claim ID in brackets — `[C020]`
- Regulation text: trailing parenthetical using the source's `short_cite` from
  `_sources.yml`:
  - `(JTR, par. 032304, p. 3B-12)` — JTR uses 6-digit paragraph numbers
  - `(MCO 1001R.1L, Ch 3, para 4)`
  - `(ForO 3000-52.1, Ch 5, p. 18)` — chapter + scanned-page number
  - `(MIU Orders-Type Matrix, 6 Mar 2026)` — no internal sections; date-cited

Never invent a citation. A statement you cannot anchor gets tagged
`needs_review` in the registry, not a guessed source.

## Claims registry

`_claims.yml` is canonical; `_claims.md` is the human projection. Projection
rule: the two must stay synchronized on `id`, `claim`, `source`, `status`,
`topic`. Every verifiable number (dollar amounts, deadlines, distances) gets a
stable `C###` ID assigned sequentially after the highest existing ID. Claim
lifecycle `status`: `active` | `needs_review` | `retired`. Retired claims keep
their row (tombstones), so IDs are never reused. Optional fields:
`review_triggers` (e.g. `source_ambiguous`, `point_in_time`, `stale_source`),
`preferred_claim_id` for supersession.

## Distribution rules

- Only public-release material is committed. Marked documents (e.g. "DoW
  Community Only") live in gitignored `sources/raw/local/` — wiki pages may
  carry their procedural mechanics but never reproduce the document or its
  marking lines.
- `/lint` greps tracked files for marking strings and fails if any appear.
- Any future page that is itself unit-internal goes in gitignored
  `wiki/internal/` and ships only in the NIPR bundle.

## Maintenance

- Add content via `/ingest` (extract claims → stage or merge → registries → log).
- Validate via `/lint` (writes only `_health.md` and `_map.md`).
- Every session that modifies the wiki appends one line to `log.md`:
  `[YYYY-MM-DD] ACTION: description` (verbs: BUILD, ADD, UPDATE, ARCHIVE, LINT, INGEST).
- Freshness: pages older than 6 months by `last_reviewed` get flagged by `/lint`.
