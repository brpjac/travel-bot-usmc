---
title: "MROWS and DTS Orders"
description: "Writing orders that fund correctly: TEEP event numbers, SICs, the PID table, order sequencing with T3, and the 5-day voucher rule"
type: topic
access: public_release
status: active
last_reviewed: 2026-07-17
claim_ids: [C037]
source_ids: [SRC-FORO-3000-52-1]
related:
  - dts-and-claims.md
  - t3-overview.md
  - teep-funding.md
  - ../sources/foro-3000-52-1/ch7-mrows-dts.md
---

# MROWS and DTS Orders

Orders written wrong lose training time and money. The rules: ForO 3000-52.1,
Ch 7 (verbatim:
[../sources/foro-3000-52-1/ch7-mrows-dts.md](../sources/foro-3000-52-1/ch7-mrows-dts.md)).

## MROWS — the reserve orders system

TEEP-funded MROWS orders must contain:

1. The **TEEP Event Number** — 7-place identifier (e.g. AFRICAN LION =
   F23-7870), from the T3 database or your ops section.
2. The **SIC** — 3-place code (e.g. AFRICAN LION = DZ0).
3. The correct **PID**:

| PID | Funds |
|---|---|
| 1 | AT travel and per diem |
| 2 | Offsite IDT travel and per diem |
| 3 | ADOS pay/allowances, travel, per diem |
| SIF | CJCS conference travel/per diem (with PID 3 for P&A) |
| CTP / CTA | CJCS exercise airline ticket only (CTP on AT, CTA on ADOS; no per diem) |
| IRT | IRT project support |

(ForO 3000-52.1, Ch 7, p. 7-1)

## Sequencing with T3

MROWS orders must reach **"Pending Fund Approval"** before the unit submits
the TEEP request, and the travel manifest must include the 7-digit MROWS
tracking number — missing tracking numbers get the TEEP request denied. A copy
of authenticated orders must be attached to the TOP request before ticketing.
(Ch 7, para 2.b, p. 7-2.) The downstream deadlines live in
[t3-timelines.md](t3-timelines.md).

## DTS

DTS is the primary system for AD/AR TAD and for reservists on DTS-supported
MROWS order types. TEEP TAD and IRT TAD flow: TEEP request approved in T3 → a
Financial Information Pointer (FIP) is created → used to build the LOA in DTS.
(Ch 7, para 3, p. 7-2.)

## After travel: the 5-day rule [C037]

**DD Form 1351-2 (travel claim) or DTS voucher must be submitted no later than
5 working days after completion of travel** to your administrative support
section. (Ch 7, paras 2.c and 3.b, p. 7-2.) Don't sit on it — unliquidated
orders are how GTCC delinquencies start.
