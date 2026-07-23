# Wiki Changelog

Append-only. One line per modifying session: `[YYYY-MM-DD] ACTION: description`
(verbs: BUILD, ADD, UPDATE, ARCHIVE, LINT, INGEST).

[2026-07-17] BUILD: Initial wiki scaffold — schema, registries, indexes, map generator. Sources restructured into sources/raw/ with gitignored local/ distribution boundary; metadata.json merged into _sources.yml.
[2026-07-17] ADD: ForO 3000-52.1 fully transcribed into sources/foro-3000-52-1/ (basic order + 7 chapters); authored 7 process/ topic pages; claims C019-C032 verified active with page cites; added C034-C040.
[2026-07-17] ADD: JTR verification pass — par. 032303/032304 and 020210 transcribed into sources/jtr/; C017/C018 verified active with eligibility nuances; authored per-diem, pov-mileage, distance-thresholds, precedence-and-currency, source-documents.
[2026-07-17] BUILD: Skills (wiki/ingest/lint), bot rewrite to agentic wiki navigation (bot.py, google-genai), NIPR bundle exporter; lint pass clean (_health.md); README rewritten.
[2026-07-18] INGEST: MARADMIN 157/25 (IDT Travel Reimbursement Update) — archival PDF + verbatim extract; C017 ($500) retired -> C041 ($750); added C041-C046 (eligibility, 11-trip limit, DTS claims, no-combining rule, commander-may-not-deny); updated idt-travel-reimbursement, lodging, distance-thresholds, precedence, source-documents, contacts, acronyms, offsite-idt.
[2026-07-19] INGEST: JTR refreshed to ed. 07/01/2026 (par. 032304.B.1 confirms $750 — C041 gains primary JTR citation; C018 re-verified; page cites updated); MCRAMM upgraded MCO 1001R.1K (2009) -> 1001R.1L w/ Admin CH-2 (2015, the revision the ForO references); FAISS rebuilt on both.
[2026-07-19] LINT: 0 FAIL / 0 WARN across 9 checks (lint_wiki.py).
[2026-07-23] UPDATE: JTR edition-drift correction — par. 020210 re-transcribed from the loaded Jul 2026 PDF (the previous extract carried Dec 2021 text under a 2026 label). Two rules had reversed: tolls on POV-instead-of-authorized-mode are now reimbursable, and the constructed cost now includes taxi/TNC/parking/baggage via a CTW worksheet to the AO. Fixed pov-mileage.md, C018 source note, and a stale $500 IDT cap on per-diem.md.
