---
title: "Precedence and Currency"
description: "Which regulation wins when they conflict, how current each of our source copies is, and how to caveat stale guidance"
type: topic
access: public_release
status: active
last_reviewed: 2026-07-17
claim_ids: [C033]
source_ids: [SRC-JTR, SRC-MCRAMM, SRC-FORO-3000-52-1, SRC-MIU-MATRIX, SRC-MARADMIN-157-25]
related:
  - source-documents.md
  - ../_sources.yml
---

# Precedence and Currency

## Precedence when sources conflict

Working rule [C033 — **needs_review**: this hierarchy is unit practice, not
yet pinned to a regulation citation]:

1. A **MARADMIN** supersedes a standing order it contradicts (newer,
   more specific direction).
2. A **standing order** (MCO, ForO) governs its specific domain.
3. The **JTR** governs entitlements where more specific guidance is silent —
   it is the statutory implementation for travel allowances.
4. **Unit guidance** (the MIU matrix) tells you how MIU implements the above;
   it cannot grant what a regulation forbids.

When two sources disagree, say so explicitly and confirm with the S-1 —
don't silently pick one.

## How current our copies are

| Source | Our copy | Risk |
|---|---|---|
| JTR | **Jul 2026** | LOW — refreshed 19 Jul 2026. The JTR updates monthly; page-number citations drift between editions, so re-verify them on each refresh. |
| MCO 1001R.1L (MCRAMM) | Dec 2015 w/ Admin CH-2 | MEDIUM — the current published revision (the one ForO 3000-52.1 references); replaced our 2009 .1K copy on 19 Jul 2026. |
| ForO 3000-52.1 | Apr 2019 | MEDIUM — standing SOP; check for later changes or successor orders. |
| MARADMIN 157/25 | Mar 2025 | LOW — current program guidance; remains in effect until canceled or updated by a future MARADMIN. |
| MIU Orders-Type Matrix | Mar 2026 | LOW — recent unit guidance. |

Registry with dates: [../_sources.yml](../_sources.yml).

## What this means for answers

- JTR-sourced answers can be given at face value; page-number citations are
  edition-specific (currently ed. 07/01/2026).
- **Worked example of supersession**: our original Dec 2021 JTR copy capped
  IDT Travel Reimbursement at $500/round trip; MARADMIN 157/25 implemented
  the raise to **$750** [C041], and the refreshed JTR now states $750
  directly (par. 032304.B.1). The registry keeps the old number as retired
  claim C017 pointing to C041 — this is how the wiki resolves conflicts:
  newer authority wins, history stays auditable. See
  [../entitlements/idt-travel-reimbursement.md](../entitlements/idt-travel-reimbursement.md).
- If a Marine reports that DTS/T3 behaves differently than this wiki says,
  believe the system and flag the page for review (`/ingest` the newer
  source).
