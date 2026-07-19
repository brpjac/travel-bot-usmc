---
title: "Sources — Index"
description: "Verbatim extracts of cited regulation text (ForO chapters, JTR paragraphs) and the raw original documents beneath them"
type: index
access: public_release
status: active
last_reviewed: 2026-07-17
related:
  - ../reference/source-documents.md
  - ../_sources.yml
---

# Sources

The descent to ground truth. Two layers:

1. **Extracts** (this folder's subdirectories) — verbatim markdown transcriptions
   of the regulation text that wiki pages cite. Use these when a topic page's
   summary isn't enough and you need exact wording.
2. **Raw originals** (`raw/`) — the actual source PDFs. The safety layer: kept
   for future builds, audit, and re-verification. `raw/local/` is gitignored
   and holds distribution-marked material that never leaves this machine.

## What's transcribed

- `foro-3000-52-1/` — ForO 3000-52.1 (TEEP/T3 SOP), transcribed chapter by
  chapter from the scanned original. The scan has no text layer, so these
  transcriptions are its ONLY searchable form:
  [basic-order.md](foro-3000-52-1/basic-order.md) ·
  [ch1 introduction](foro-3000-52-1/ch1-introduction.md) ·
  [ch2 TEEP development](foro-3000-52-1/ch2-teep-development.md) ·
  [ch3 TEEP funding](foro-3000-52-1/ch3-teep-funding.md) ·
  [ch4 non-TEEP funding](foro-3000-52-1/ch4-non-teep-funding.md) ·
  [ch5 T3 logistics (timelines)](foro-3000-52-1/ch5-t3-logistics.md) ·
  [ch6 T3 database](foro-3000-52-1/ch6-t3-database.md) ·
  [ch7 MROWS/DTS](foro-3000-52-1/ch7-mrows-dts.md)
- `jtr/` — only the JTR paragraphs that topic pages cite. The full JTR
  (1,000+ pages) is deliberately not transcribed; deep questions fall back to
  the FAISS index over the raw PDF (in the bot) or the raw PDF itself.
- `maradmin-157-25/` — [message.md](maradmin-157-25/message.md): the full
  IDT Travel Reimbursement Update ($500→$750), captured verbatim from
  marines.mil; the raw PDF is an archival capture generated from this text.
- `mcramm/` — (none yet) MCO 1001R.1K chapters get transcribed here when a
  topic page pins a MCRAMM citation.

## What's NOT here

- The MIU Orders-Type Matrix is distribution-marked; its mechanics are distilled
  into topic pages and the original lives only in `raw/local/`. No verbatim
  extract exists or should be created.

## Rules

Extracts carry `type: source_extract`, `verbatim: true`, `raw_file:`, and
`pages_transcribed:` frontmatter (see [../_schema.md](../_schema.md)). Never
edit transcribed text for style — fidelity to the original beats readability.
Transcription gaps (illegible scan areas) are marked `[illegible]` inline.
