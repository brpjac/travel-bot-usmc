# Claims Registry (human view)

Human-readable projection of [_claims.yml](_claims.yml) — the canonical
machine-readable registry. Projection rule: `id`, `claim`, `source`, `status`,
`topic` must stay synchronized between the two files. Cite claims inline as
`[C001]`.

Status legend: **active** = verified against the cited source · **needs_review**
= number believed correct but citation not yet pinned (do not treat as settled)
· **retired** = superseded, kept as tombstone.

## MIU Orders Mechanics (source: MIU Orders-Type Matrix, 6 Mar 2026)

| ID | Claim | Status | Topic |
|----|-------|--------|-------|
| C001 | IDT at HTC: no per diem, no rental car, no commercial travel reimbursement | active | orders-types/idt.md |
| C002 | HTC IDT: $750 travel voucher NLT 15 days prior in DTS-R | active | entitlements/idt-travel-reimbursement.md |
| C003 | >50 mi from HTC triggers Offsite IDT / AT / ADOS instead of standard IDT | active | reference/distance-thresholds.md |
| C004 | Offsite IDT & AT CONUS: Orders Request Form 45 days prior (Correspondence Tracker) | active | process/orders-request-miu.md |
| C005 | ADOS CONUS: Orders Request NLT 2 weeks prior | active | process/orders-request-miu.md |
| C006 | OCONUS Offsite IDT & AT: 60 days prior; APACS also required | active | process/orders-request-miu.md |
| C007 | OCONUS ADOS: NLT 3 weeks prior | active | process/orders-request-miu.md |
| C008 | AT for trips >7 days; ADOS for trips <7 days | active | orders-types/choosing-orders-type.md |
| C009 | Orders prereqs: current Medical, GTCC, Primary Residence (+APACS OCONUS) | active | process/orders-request-miu.md |
| C010 | IDT lodging only at HTC; CO may authorize with written order if mission-required and duty >12 hrs | active | entitlements/lodging.md |
| C011 | ADOS is the most common orders type carrying rental-car entitlement | active | orders-types/ados.md |
| C012 | Offsite IDT: per diem yes, lodging if on orders, POV mileage yes, rental car only if mission-required + AO-approved | active | orders-types/offsite-idt.md |
| C013 | AT and ADOS carry full TDY entitlements | active | entitlements/entitlements-matrix.md |
| C014 | Active Reserve / Active Duty use DTS for all travel; DTS is a system, not an orders type | active | process/dts-and-claims.md |
| C015 | Under 50 mi needing entitlements: CO exception for IDT lodging, or ADOS orders | active | orders-types/choosing-orders-type.md |
| C016 | HTC IDT: notify MIU_Operations@usmc.mil NLT 1 week prior; Billeting Request Form via S-4 | active | process/orders-request-miu.md |

## JTR Numbers (re-verified against JTR ed. 07/01/2026 on 19 Jul 2026)

| ID | Claim | Status | Topic |
|----|-------|--------|-------|
| C017 | IDT 150+ mi (DTOD): actual expenses up to $500/round trip (ed. 12/01/2021) — **superseded by C041** ($750 for round trips ending on/after 27 Dec 2024) | retired | entitlements/idt-travel-reimbursement.md |
| C018 | POV auto-advantageous ≤400 mi one-way / ≤800 mi RT; beyond is AO case-by-case; POV-instead-of-authorized-mode limited to constructed cost (par. 020210, Table 2-10, p. 2-23, ed. 07/01/2026) | active | entitlements/pov-mileage.md |

## IDT Travel Reimbursement (source: MARADMIN 157/25, 24 Mar 2025)

| ID | Claim | Status | Topic |
|----|-------|--------|-------|
| C041 | IDT-R cap is $750/round trip for round trips ending on/after 27 Dec 2024 ($500 before) — JTR par. 032304.B.1 p. 3B-7 (ed. 07/01/2026) + MARADMIN 157/25 | active | entitlements/idt-travel-reimbursement.md |
| C042 | Eligibility: critical staffing shortfalls / command-screened / GO / IMA RSLB billets; unit 150+ mi from MCTFS primary residence (DTOD); BIC match or RA exception; no rank/MOS limits (para 3) | active | entitlements/idt-travel-reimbursement.md |
| C043 | Limit 11 round trips per Marine per FY; 22 for MOS 75XX DIFOP aviators (para 5.b) | active | entitlements/idt-travel-reimbursement.md |
| C044 | IDT-R is separate from and may NOT be combined with off-site IDT travel (para 6.g) | active | entitlements/idt-travel-reimbursement.md |
| C045 | Claims settled in DTS via monthly eligibility roster + restricted cross-org list against the FY LOA; settle NLT 31 Dec of the same calendar year (para 6.a) | active | entitlements/idt-travel-reimbursement.md |
| C046 | Commanders may not deny an IDT-R request that meets program eligibility (para 6.h) | active | entitlements/idt-travel-reimbursement.md |

## T3 / TEEP (source: ForO 3000-52.1; verified against the scan, 17 Jul 2026)

| ID | Claim | Status | Topic |
|----|-------|--------|-------|
| C019 | T3 is the only method of reserving commercial transportation for reservists outside DTS (Ch 1 p. 1-1; Ch 6 p. 6-1) | active | process/t3-overview.md |
| C020 | D-65: group charter T3 request to final approver (Ch 5, 3.i(1), p. 5-6) | active | process/t3-timelines.md |
| C021 | D-60: group charter TOP request to DMO (Ch 5, 3.i(2), p. 5-6) | active | process/t3-timelines.md |
| C022 | D-50: OCONUS commercial air T3 request to final approver (Ch 5, 3.i(3), p. 5-6) | active | process/t3-timelines.md |
| C023 | D-45: OCONUS commercial air TOP to DMO with approved/authenticated orders (Ch 5, 3.i(4), p. 5-6) | active | process/t3-timelines.md |
| C024 | D-35: CONUS commercial air/bus TOP to MARFORRES/MSC T3 Manager (Ch 5, 3.i(5), p. 5-6) | active | process/t3-timelines.md |
| C025 | D-30: CONUS commercial air/bus TOP to DMO with authenticated orders (Ch 5, 3.i(6), p. 5-6) | active | process/t3-timelines.md |
| C026 | D-10: GTCC IBA activated + authenticated orders attached or DMO cancels; ticketing begins (Ch 5, 3.i(7)-(8), p. 5-6) | active | process/t3-timelines.md |
| C027 | D-5: DMO ticketing complete (Ch 5, 3.i(9), p. 5-6) | active | process/t3-timelines.md |
| C028 | Late T3: G-3/5 endorsement up to D-16; MSC Chief of Staff within 15 days of execution (Ch 5, 3.j, p. 5-6) | active | process/t3-waivers.md |
| C029 | Adjudication email must state operational necessity, cost acceptance, carrier-availability risk acceptance (Ch 5, 3.j, p. 5-6) | active | process/t3-waivers.md |
| C030 | TEEP funding lines: RPMC 1108 (ADOS 2732, Reserve Travel 2731), O&MMCR 1107 (EXSPT, TAD, TOT, PEM), JEP 0100 (CTP, SIF), IRT, AC ADOS, extended/split/additional AT (Ch 3) | active | process/teep-funding.md |
| C031 | Non-TEEP funding: OCO 1106, schools 1108 (RPT/CDT), other non-TEEP RPMC PIDs, O&MMCR 1107 (Ch 4) | active | process/non-teep-funding.md |
| C032 | DMO deadlines: CONUS TOP 30 / OCONUS TOP 45 (ladder); TOT CONUS 30 / OCONUS 60 / SPP 7 (Ch 5, 3.i and 2.c) | active | process/t3-timelines.md |
| C034 | Orders not approved by D-15 → reservations cancelled, resubmit with MSC CoS waiver; any submission inside 15 days needs CoS waiver (Ch 5, 3.f(5), p. 5-5) | active | process/t3-timelines.md |
| C035 | TOT deadlines to DMO: OCONUS 60, CONUS 30, Small Package Program 7 days (Ch 5, 2.c, p. 5-1) | active | process/t3-timelines.md |
| C036 | Reservations 5-10 days after TOP receipt; ticketing within 10 days of travel on CBA; IBA active NLT 10 days out (Ch 5, 3.g, p. 5-5) | active | process/t3-timelines.md |
| C037 | DD 1351-2 or DTS voucher NLT 5 working days after completing travel (Ch 7, 2.c/3.b, p. 7-2) | active | process/mrows-dts-orders.md |
| C038 | Standard AT 14+1=15 days; extended ≤29 (COMMARFORRES G-3/5); split ≤15 total, once, MSC G3; additional AT: both ≤30 days (Ch 3, para 7, p. 3-5) | active | process/teep-funding.md |
| C039 | Offsite IDT travel funds (PID 2) require the offsite drill to directly support an approved TEEP funded event (Ch 3, 2.b(5), p. 3-2) | active | process/teep-funding.md |
| C040 | No self-booking: travel only through the servicing Travel Management Company (Ch 5, 3.d(1), p. 5-3) | active | process/t3-overview.md |

## Precedence

| ID | Claim | Status | Topic |
|----|-------|--------|-------|
| C033 | MARADMIN supersedes a standing order it contradicts; JTR governs where specific guidance is silent | needs_review | reference/precedence-and-currency.md |
