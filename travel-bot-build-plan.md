# MIU Travel Regulation Bot - Build Plan

## What This Is
RAG-based chatbot that answers travel policy questions for reserve Marines by referencing JTR, MCRAM, MARADMINs, and related orders. Hosted on a public URL, free to run.

## Stack
- **LLM:** Google Gemini 1.5 Flash (free tier - 15 req/min, 1M tokens/day)
- **Embeddings:** Google text-embedding-004 (free)
- **Vector store:** FAISS (local, file-based, free)
- **Framework:** LangChain (Python)
- **Frontend:** Streamlit
- **Hosting:** Streamlit Community Cloud (free, deploys from GitHub)
- **Cost:** $0

## Source Documents
- Joint Travel Regulations (JTR) - full PDF
- MCO 1001R.1K (MCRAM) - full PDF
- 2-3 additional orders TBD
- Relevant MARADMINs (added as published)

---

## Phase 1: Document Prep

**Goal:** Clean text from all source PDFs.

- Extract text from PDFs using `pymupdf` (better than PyPDF2 for DoD formatting)
- Clean OCR artifacts, fix table formatting where possible
- Tag each document with metadata: source name, date, document number
- Known issue: JTR tables (per diem rates, entitlement matrices) parse poorly from PDF. May need manual cleanup or separate handling.

## Phase 2: Chunking & Embedding

**Goal:** Documents broken into retrievable chunks in a vector store.

- Chunk size: ~600-800 tokens with ~100 token overlap
- Preserve section headers in each chunk (e.g., prepend "JTR Chapter 3, Section 0305" to every chunk from that section) so the model can cite properly
- Each chunk gets metadata: `source_doc`, `section`, `date`, `doc_type` (standing_order | maradmin)
- Embed all chunks with Google embedding model
- Store in FAISS index, save to disk

## Phase 3: RAG Pipeline

**Goal:** Question in, cited answer out.

- User question → embed → retrieve top 6-8 chunks from FAISS
- Feed retrieved chunks + question to Gemini with system prompt
- System prompt must include:
  - "Answer only from the provided regulation text"
  - "Cite the specific order, chapter, and section for every claim"
  - "If a MARADMIN contradicts a standing order, the MARADMIN takes precedence. Note this explicitly and cite the MARADMIN number and date."
  - "If you are unsure or the documents don't address the question, say so. Do not guess."
  - "If a MARADMIN has an expiration date that may have passed, flag that."

## Phase 4: Frontend

**Goal:** Simple web UI anyone in the unit can use.

- Streamlit app: text input, chat history, source citations displayed below each answer
- Show which document/section each answer came from
- Add a disclaimer banner: "This tool is for reference only. Verify answers against the source order before taking action."
- Optional: sidebar listing all loaded documents and their dates

## Phase 5: Deploy

**Goal:** Live on a public URL.

1. Push code + FAISS index to a GitHub repo (private is fine, Streamlit Cloud can access it)
2. Connect repo to Streamlit Community Cloud
3. Store Gemini API key in Streamlit secrets (not in code)
4. Share URL with unit

## Phase 6: Adding New Documents

Repeatable process for adding a MARADMIN or new order:

1. Drop PDF in `/docs` folder
2. Run ingestion script (extracts text, chunks, embeds, appends to FAISS index)
3. Push to GitHub
4. Streamlit redeploys automatically

---

## Key Risks & Mitigations

| Risk | Mitigation |
|---|---|
| JTR table data parses badly from PDF | Manual cleanup of critical tables (per diem, entitlements). Consider a separate structured lookup for rate tables. |
| Model hallucinates policy that isn't in the docs | System prompt constrains to source text only. Citations let users verify. Disclaimer banner. |
| MARADMIN supersedes standing order but model doesn't flag it | Tag doc_type in metadata, explicit system prompt instruction on precedence |
| Gemini free tier rate limits hit | Unlikely for a reserve unit. If it happens, Groq free tier is the backup. |
| Someone asks about controlled/marked content | Don't load controlled documents (CUI-type or official-use-only markings). JTR and MCRAM are publicly available. MARADMINs that reference controlled material should be excluded. |

## Estimated Build Time
- Phase 1-2: 2-3 hours (mostly PDF cleanup)
- Phase 3-4: 3-4 hours
- Phase 5: 30 minutes
- Total: ~1 day of focused work
