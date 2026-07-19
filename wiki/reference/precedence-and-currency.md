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
| JTR | **Dec 2021** | HIGH — the JTR updates monthly. Structure is stable; exact rates (mileage, per diem) and thresholds may have moved. Always check the current edition for numbers. **Known supersession**: the IDT-R $500 cap became $750 (see below). |
| MCO 1001R.1K (MCRAMM) | Mar 2009 | HIGH — ForO 3000-52.1 (2019) already references MCO 1001R.1L, one revision newer than our copy. |
| ForO 3000-52.1 | Apr 2019 | MEDIUM — standing SOP; check for later changes or successor orders. |
| MARADMIN 157/25 | Mar 2025 | LOW — current program guidance; remains in effect until canceled or updated by a future MARADMIN. |
| MIU Orders-Type Matrix | Mar 2026 | LOW — recent unit guidance. |

Registry with dates: [../_sources.yml](../_sources.yml).

## What this means for answers

- Any answer sourced from the JTR should carry an "as of Dec 2021" caveat when
  it involves a rate or dollar amount.
- **Live example of supersession**: our JTR copy caps IDT Travel Reimbursement
  at $500/round trip; MARADMIN 157/25 (implementing the current JTR) raised it
  to **$750** for round trips ending on or after 27 Dec 2024 [C041]. The
  registry keeps the old number as retired claim C017 pointing to C041 — the
  wiki answers with the newer authority and says why. See
  [../entitlements/idt-travel-reimbursement.md](../entitlements/idt-travel-reimbursement.md).
- If a Marine reports that DTS/T3 behaves differently than this wiki says,
  believe the system and flag the page for review (`/ingest` the newer
  source).
