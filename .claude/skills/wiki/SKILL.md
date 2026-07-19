---
name: wiki
description: Answer a USMC travel question grounded in the wiki/ knowledge base, not from memory. Use when the user asks a travel-regulation question (/wiki or any orders/entitlements/T3 question) or wants an answer traced to sources.
user_invocable: true
argument-hint: "[question or topic]"
---

# Wiki reader

Answer questions grounded in `wiki/`, not from memory. Every claim in your
answer must trace to a wiki page, a claim ID, or a source extract.

## Getting started

1. Read `wiki/CLAUDE.md` first — the master index with the task-routing table.
2. `wiki/_map.md` is a one-read inventory of every page with descriptions.
3. Numbers live in `wiki/_claims.yml` (canonical) / `wiki/_claims.md` (human).
4. Source documents are registered in `wiki/_sources.yml`.
5. `wiki/log.md` says what changed recently.

## Crawl protocol (lazy — don't bulk-read)

Hop order: root `CLAUDE.md` → section `CLAUDE.md` → topic file → that file's
`related:` frontmatter → registries for numbers → `sources/` extracts for
verbatim regulation text → `sources/raw/` PDFs only as a last resort.

- Read cheap first: a file's first ~15 frontmatter lines tell you whether the
  full read is worth it.
- Grep-first fallback: when the routing table has no match, grep the keyword
  case-insensitively across `wiki/` and pick files via `description:` hits or
  `_map.md`.

## Rules

- Source every claim: cite claim IDs (e.g. `[C020]`) alongside the page, and
  copy regulation parentheticals verbatim, e.g. `(ForO 3000-52.1, Ch 5, p. 5-6)`.
- Money/deadline answers MUST cite a C### ID or explicitly say the registry
  lacks it.
- A claim with `status: needs_review` is not settled — say so.
- JTR-sourced numbers carry the "our copy is Dec 2021" caveat (see
  `wiki/reference/precedence-and-currency.md`).
- If the wiki doesn't cover it, say "not in the loaded regulations — check
  with your S-1"; never fill gaps from general knowledge without labeling it.
