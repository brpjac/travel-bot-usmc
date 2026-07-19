---
title: "MIU Travel Wiki — Master Index"
description: "Start here: task-routing table and directory map for USMC reserve travel guidance (orders types, entitlements, T3/TOP, TEEP)"
type: index
access: public_release
status: active
last_reviewed: 2026-07-17
---

# MIU Travel Wiki

Travel guidance for USMC reserve Marines (Marine Innovation Unit / MARFORRES).
Distilled from the JTR, MCO 1001R.1L (MCRAMM), ForO 3000-52.1 (TEEP/T3 SOP),
MARADMIN 157/25, and MIU unit procedures. **This wiki is the knowledge layer** — for humans
browsing, for the bot answering, and for any agent pointed at this folder.

**Not authoritative.** Always verify with your S-1 and the current regulations
before making travel arrangements. See
[reference/precedence-and-currency.md](reference/precedence-and-currency.md)
for how current our source copies are.

## Start Here By Task

| A Marine asks... | Read |
|---|---|
| What orders type do I need? | [orders-types/choosing-orders-type.md](orders-types/choosing-orders-type.md) |
| What am I entitled to (per diem, lodging, rental car)? | [entitlements/entitlements-matrix.md](entitlements/entitlements-matrix.md) |
| How do I request orders at MIU? | [process/orders-request-miu.md](process/orders-request-miu.md) |
| When must I submit my travel/flight request? | [process/t3-timelines.md](process/t3-timelines.md) |
| I missed a submission deadline | [process/t3-waivers.md](process/t3-waivers.md) |
| What is T3 / TOP / TOT? | [process/t3-overview.md](process/t3-overview.md) |
| Who pays for my training event? | [process/teep-funding.md](process/teep-funding.md), [process/non-teep-funding.md](process/non-teep-funding.md) |
| How does DTS fit in? | [process/dts-and-claims.md](process/dts-and-claims.md) |
| Distance rules (50/150/400/800 miles) | [reference/distance-thresholds.md](reference/distance-thresholds.md) |
| What does an acronym mean? | [reference/acronyms.md](reference/acronyms.md) |
| Which regulation wins / how stale are our copies? | [reference/precedence-and-currency.md](reference/precedence-and-currency.md) |
| Exact regulation wording | [sources/CLAUDE.md](sources/CLAUDE.md) → verbatim extracts |

## Directory Map

- [orders-types/](orders-types/CLAUDE.md) — IDT, Offsite IDT, AT, ADOS, mobilization; how to choose
- [entitlements/](entitlements/CLAUDE.md) — what each orders type rates: per diem, lodging, POV, rental car
- [process/](process/CLAUDE.md) — MIU orders workflow, T3/TOP/TOT timelines and waivers, TEEP funding, DTS/MROWS
- [reference/](reference/CLAUDE.md) — distance thresholds, precedence, acronyms, contacts, source-document guide
- [sources/](sources/CLAUDE.md) — verbatim extracts of cited regulation text; raw originals in `sources/raw/`

## Infrastructure Files

| File | Purpose | Updated by |
|---|---|---|
| [_schema.md](_schema.md) | Page/frontmatter/citation/claims rules | by hand, rarely |
| [_claims.yml](_claims.yml) | Canonical claims registry (C### IDs — every number lives here) | /ingest |
| [_claims.md](_claims.md) | Human-readable claims view (synced with the .yml) | /ingest |
| [_sources.yml](_sources.yml) | Source-document registry (also drives scripts/ingest.py) | /ingest |
| [_map.md](_map.md) | Auto-generated page inventory (= the bot router's catalog) | scripts/generate_wiki_map.py |
| [_health.md](_health.md) | Lint report | /lint |
| [log.md](log.md) | Append-only changelog | every modifying session |
| [pending-review.md](pending-review.md) | Staging queue for unverified claims | /ingest |

## How to use this wiki (humans and agents)

1. Start from the routing table above; hop root index → folder index → topic page.
2. Follow a page's `related:` frontmatter for neighbors.
3. Look up any number in [_claims.yml](_claims.yml) by its `[C###]` ID.
4. Need exact wording? Drill from the topic page to its
   [sources/](sources/CLAUDE.md) extract, then to the raw PDF if necessary.
5. Don't bulk-read. [_map.md](_map.md) lists every page with a description —
   one read tells you where everything lives.
