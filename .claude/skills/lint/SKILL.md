---
name: lint
description: Run wiki health checks - claims sync, source parity, orphans, link integrity, distribution guard - and write the report to wiki/_health.md. Use when the user says /lint or after significant wiki changes.
user_invocable: true
---

# Wiki lint

Run the checks below and write results to `wiki/_health.md` (overwrite) and
regenerate `wiki/_map.md`. **Only those two files may be modified — never
auto-fix findings**; report them.

## Checks

1. **Claims projection sync.** Every C### in `wiki/_claims.yml` appears in
   `wiki/_claims.md` with matching claim text, status, and topic — and vice
   versa. No duplicate or missing IDs; IDs strictly increasing.

2. **Source parity (both directions).** Every file in `wiki/sources/raw/`
   (and `raw/local/`) has a `_sources.yml` entry with matching `filename`;
   every `_sources.yml` entry's file exists. Every `source_ids:` value in page
   frontmatter and every `source_ids` in claims resolves to a registered
   SRC-* id.

3. **Orphan claims.** Every claim's `topic:` page exists and lists the claim
   in its `claim_ids:` frontmatter (or cites it inline). Flag claims no page
   cites, and pages citing C### IDs that don't exist.

4. **Discrepancies.** Numbers that appear in multiple places (pages, claims,
   extracts) with different values — e.g. a deadline stated two ways.

5. **Frontmatter coverage.** Every wiki .md page (except infra fallbacks) has
   frontmatter with `title`, `description`, `type`, `access`, `status`,
   `last_reviewed`. `source_extract` pages additionally have `verbatim`,
   `raw_file`, `pages_transcribed`. Flag `last_reviewed` older than 6 months.

6. **Link integrity + map.** Every relative markdown link resolves; every
   non-index page has ≥1 inbound link (orphan pages). Then run
   `python3 scripts/generate_wiki_map.py` — nonzero exit is a finding.

7. **Extract integrity.** Every `source_extract` page's `raw_file:` path
   resolves to a real file.

8. **DISTRIBUTION GUARD (fail-hard).** Grep all git-tracked files
   (`git ls-files` output) case-insensitively for distribution-marking
   phrases using these bracket-escaped regexes (written this way so
   pattern-definition files, including this one, never match themselves):
   `[d]ow community only`, `[f]ouo`, `[c]ui//`. Run as
   `git ls-files -z | xargs -0 grep -liE '[d]ow community only|[f]ouo|[c]ui//'`.
   Also verify `git ls-files` returns nothing under
   `wiki/sources/raw/local/` or `wiki/internal/`. Any hit is a FAIL, reported
   first and loudly.

## Report format (`wiki/_health.md`)

Header with run date; one section per check with PASS/FAIL/WARN and specifics;
a summary table at top. End by appending one `[YYYY-MM-DD] LINT: ...` line to
`wiki/log.md`.
