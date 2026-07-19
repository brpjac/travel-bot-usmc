---
name: lint
description: Run wiki health checks - mechanical checks via scripts/lint_wiki.py plus a semantic discrepancy scan - and write the report to wiki/_health.md. Use when the user says /lint or after significant wiki changes.
user_invocable: true
---

# Wiki lint

Two layers: the mechanical checks live in `scripts/lint_wiki.py` (single
source of truth, also run by CI); this skill adds the judgment layer on top.
**Never auto-fix findings** — report them. Only `wiki/_health.md` and
`wiki/_map.md` may be modified (the script handles both), plus the `log.md`
line.

## Steps

1. **Run the mechanical checks**: `python3 scripts/lint_wiki.py --write-health`
   — distribution guard (fail-hard, reported first), claims yml/md sync,
   source parity, orphan claims, frontmatter coverage (+6-month freshness),
   link integrity + orphan pages, extract raw_file resolution, timelines.yml
   claim cross-check, map currency. It writes `_health.md`, regenerates
   `_map.md`, and appends the LINT line to `log.md`. Nonzero exit = FAILs.

2. **Semantic discrepancy scan** (not automatable): read the topic pages and
   registries for the same fact stated two ways — a deadline or dollar amount
   that differs between a page, its claim, an extract, or `timelines.yml`
   labels. Also spot-check that `needs_review` claims are still hedged where
   pages cite them. Append any findings to the `## Findings` section of
   `wiki/_health.md` marked `SEMANTIC`.

3. **Report** the summary table to the user, FAILs first.

## Notes

- The distribution guard greps git-tracked files for marking phrases. When
  writing patterns for it anywhere (docs, scripts), keep them self-non-matching:
  bracket-escaped regex form (`[d]ow community only`, `[f]ouo`, `[c]ui//`) in
  prose/skills, string-concatenation form in Python (see
  `scripts/lint_wiki.py` / `scripts/export_bundle.py` — twins, keep in sync).
- `wiki/sources/raw/local/` and `wiki/internal/` must never appear in
  `git ls-files`; the script asserts this.
