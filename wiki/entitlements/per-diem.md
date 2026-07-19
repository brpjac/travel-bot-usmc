---
title: "Per Diem"
description: "How per diem works on travel-bearing orders: locality rates, lodging plus M&IE, the 75% travel-day rule, and the 12-hour threshold"
type: topic
access: public_release
status: active
last_reviewed: 2026-07-17
claim_ids: [C001, C013]
source_ids: [SRC-JTR]
related:
  - entitlements-matrix.md
  - lodging.md
  - ../orders-types/ados.md
---

# Per Diem

Per diem exists only on travel-bearing orders (Offsite IDT, AT, ADOS) — never
on standard IDT [C001]. See
[entitlements-matrix.md](entitlements-matrix.md) for which orders rate it.

> Computation rules below are from the current JTR copy (ed. 07/01/2026).
> Locality rates themselves change constantly — always pull the actual rate
> from the DTMO lookup, not from any static document.

## The structure

Per diem = **locality lodging rate + locality M&IE** (meals and incidental
expenses) for the duty location. Lodging is reimbursed at actual cost up to
the locality cap; M&IE is a flat daily rate. Current rates:
DTMO per diem rate lookup (defensetravel.dod.mil).

## Computation rules that surprise people (JTR, par. 020309, Table 2-20, p. 2-46)

- **12 hours or less**: per diem is not authorized at all.
- **More than 12 but less than 24 hours, no lodging**: 75% of the highest
  applicable locality M&IE rate.
- **Travel days**: 75% of the M&IE rate on the day of departure and the day of
  return; 100% on full TDY days.
- Government dining facility availability can reduce the meal portion
  (Government Meal Rate) when directed on orders.

## On AT specifically

When Government quarters and a Government dining facility are both available
at an annual training location, the training location is treated as the PDS
and **no per diem is payable** — per diem applies to TDY away from the AT
location or travel to/from it when not in commuting status (JTR, par. 032302).
Full TDY entitlements on AT/ADOS [C013] mean per diem applies when those
conditions don't strip it.

## IDT exception

The narrow 150-mile/$500 mechanism reimburses actual lodging and meal costs up
to locality caps — that's AEA-style reimbursement, not per diem. See
[idt-travel-reimbursement.md](idt-travel-reimbursement.md).
