"""
Ingest documents into a FAISS vector store for the MIU Travel Regulation Bot.

Usage:
    python scripts/ingest.py                # Full rebuild
    python scripts/ingest.py --incremental  # Only process new/changed files

Reads PDFs and .txt files from wiki/sources/raw/, extracts text, chunks with
metadata, embeds locally with all-MiniLM-L6-v2, and saves a FAISS index to
vectorstore/. The source registry is wiki/_sources.yml; files registered with
in_faiss: false (scanned or marked documents) are skipped explicitly — their
searchable form is the wiki itself.
"""

import argparse
import hashlib
import json
import re
import sys
import pymupdf
import yaml
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

# Paths
REPO_ROOT = Path(__file__).parent.parent
RAW_DIR = REPO_ROOT / "wiki" / "sources" / "raw"
VECTORSTORE_DIR = REPO_ROOT / "vectorstore"
SOURCES_FILE = REPO_ROOT / "wiki" / "_sources.yml"
MANIFEST_FILE = VECTORSTORE_DIR / "manifest.json"

# Batching config (for memory efficiency, no rate limits with local model)
EMBED_BATCH_SIZE = 100


def load_sources_registry() -> dict:
    """Load the source registry from wiki/_sources.yml, keyed by filename."""
    if SOURCES_FILE.exists():
        with open(SOURCES_FILE) as f:
            data = yaml.safe_load(f) or {}
        return {entry["filename"]: entry for entry in data.get("sources", [])}
    return {}


def get_doc_metadata(filename: str, registry: dict) -> dict:
    """Match a filename to its FAISS chunk metadata from the registry."""
    if filename in registry:
        entry = registry[filename]
        return {
            "source_doc": entry["title"],
            "doc_type": entry.get("doc_type", "unknown"),
            "date": str(entry.get("as_of", "unknown")),
        }
    # Fallback for unknown docs
    print(f"  WARNING: '{filename}' not found in _sources.yml — using defaults")
    return {
        "source_doc": filename,
        "doc_type": "unknown",
        "date": "unknown",
    }


def file_hash(filepath: Path) -> str:
    """Compute SHA256 hash of a file for change detection."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            h.update(block)
    return h.hexdigest()


def load_manifest() -> dict:
    """Load the ingestion manifest (tracks which files have been processed)."""
    if MANIFEST_FILE.exists():
        with open(MANIFEST_FILE) as f:
            return json.load(f)
    return {}


def save_manifest(manifest: dict):
    """Save the ingestion manifest."""
    VECTORSTORE_DIR.mkdir(exist_ok=True)
    with open(MANIFEST_FILE, "w") as f:
        json.dump(manifest, f, indent=2)


# --- Section detection ---

def extract_jtr_section(text: str) -> str:
    """Extract JTR section number from text (e.g., '010201', 'A0101')."""
    # JTR uses 6-digit section numbers: chapters 01-06 plus appendices A, B
    match = re.search(r'\b(0[1-6]\d{4})\b', text)
    if match:
        return match.group(1)
    # Appendix sections (e.g., A0101, B0201)
    match = re.search(r'\b([AB]\d{4})\b', text)
    if match:
        return match.group(1)
    # Chapter-level headers
    match = re.search(r'CHAPTER\s+(\d)', text)
    if match:
        return f"Chapter {match.group(1)}"
    # Appendix headers
    match = re.search(r'APPENDIX\s+([AB])', text, re.IGNORECASE)
    if match:
        return f"Appendix {match.group(1)}"
    return ""


def extract_mcramm_section(text: str) -> str:
    """Extract MCRAMM section/chapter info from text."""
    # Chapter headers like "CHAPTER 3" or "Chapter 3"
    match = re.search(r'[Cc]hapter\s+(\d+)', text)
    if match:
        return f"Chapter {match.group(1)}"
    # Numbered paragraph at start of line: "1. " or "4. " (but not dates or list items)
    match = re.search(r'^\s*(\d{1,2})\.\s+[A-Z]', text, re.MULTILINE)
    if match:
        return f"Para {match.group(1)}"
    return ""


def extract_section(text: str, source_doc: str) -> str:
    """Extract section identifier based on document type."""
    if "JTR" in source_doc:
        return extract_jtr_section(text)
    elif "MCO" in source_doc or "MCRAMM" in source_doc:
        return extract_mcramm_section(text)
    return ""


# --- Text extraction ---

def extract_text_from_pdf(pdf_path: Path) -> list[dict]:
    """Extract text from a PDF, returning a list of {page, text} dicts."""
    doc = pymupdf.open(str(pdf_path))
    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        if text.strip():
            pages.append({
                "page": page_num + 1,
                "text": text.strip(),
            })
    doc.close()
    return pages


def extract_text_from_txt(txt_path: Path) -> list[dict]:
    """Read a .txt file as a single 'page'."""
    text = txt_path.read_text(encoding="utf-8")
    if text.strip():
        return [{"page": 1, "text": text.strip()}]
    return []


def clean_text(text: str) -> str:
    """Clean common PDF extraction artifacts."""
    # Fix excessive whitespace but preserve paragraph breaks
    text = re.sub(r'[ \t]+', ' ', text)
    # Fix broken lines within sentences (line ending without period)
    text = re.sub(r'(?<=[a-z,])\n(?=[a-z])', ' ', text)
    # Collapse 3+ newlines to 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def build_documents(file_path: Path, registry: dict) -> list[Document]:
    """Extract and process a single file into LangChain Documents."""
    filename = file_path.name
    meta = get_doc_metadata(filename, registry)

    if file_path.suffix.lower() == ".pdf":
        pages = extract_text_from_pdf(file_path)
    elif file_path.suffix.lower() == ".txt":
        pages = extract_text_from_txt(file_path)
    else:
        print(f"  Skipping unsupported file type: {filename}")
        return []

    documents = []
    last_section = ""

    for page_data in pages:
        cleaned = clean_text(page_data["text"])
        if len(cleaned) < 20:
            continue

        section = extract_section(cleaned, meta["source_doc"])
        # Carry forward: if no section detected, use the last one we saw
        if section:
            last_section = section
        else:
            section = last_section

        doc = Document(
            page_content=cleaned,
            metadata={
                **meta,
                "page": page_data["page"],
                "section": section,
                "filename": filename,
            },
        )
        documents.append(doc)

    print(f"  Extracted {len(documents)} page(s) from {filename}")
    return documents


# --- Chunking ---

def chunk_documents(documents: list[Document]) -> list[Document]:
    """Split documents into chunks, preserving metadata and prepending section context."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    chunks = []
    for doc in documents:
        splits = splitter.split_documents([doc])
        for i, chunk in enumerate(splits):
            source = chunk.metadata["source_doc"]
            section = chunk.metadata.get("section", "")
            page = chunk.metadata.get("page", "")

            prefix_parts = [f"[Source: {source}"]
            if section:
                prefix_parts.append(f"Section {section}")
            if page:
                prefix_parts.append(f"Page {page}")
            prefix = ", ".join(prefix_parts) + "]\n\n"

            chunk.page_content = prefix + chunk.page_content
            chunk.metadata["chunk_index"] = i
            chunks.append(chunk)

    return chunks


# --- Embedding & vector store ---

def get_embeddings():
    """Create the local HuggingFace embeddings instance (no API key needed)."""
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


def build_vectorstore_batched(chunks: list[Document], embeddings) -> FAISS:
    """Embed chunks in batches for memory efficiency, then build FAISS index."""
    total_batches = (len(chunks) + EMBED_BATCH_SIZE - 1) // EMBED_BATCH_SIZE
    print(f"\nEmbedding {len(chunks)} chunks in batches of {EMBED_BATCH_SIZE}...")

    vectorstore = None

    for batch_num in range(total_batches):
        start = batch_num * EMBED_BATCH_SIZE
        end = min(start + EMBED_BATCH_SIZE, len(chunks))
        batch = chunks[start:end]

        print(f"  Batch {batch_num + 1}/{total_batches} ({len(batch)} chunks)...")

        batch_store = FAISS.from_documents(batch, embeddings)
        if vectorstore is None:
            vectorstore = batch_store
        else:
            vectorstore.merge_from(batch_store)

    return vectorstore


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description="Ingest documents into FAISS vector store")
    parser.add_argument("--incremental", action="store_true",
                        help="Only process new or changed files")
    args = parser.parse_args()

    print("=== MIU Travel Bot - Document Ingestion ===\n")

    # Load source registry
    registry = load_sources_registry()
    if registry:
        print(f"Loaded registry for {len(registry)} documents from wiki/_sources.yml")
    else:
        print("WARNING: No _sources.yml found — all documents will use default metadata")

    # Find all ingestible files (non-recursive: raw/local/ is deliberately excluded)
    source_files = sorted(
        list(RAW_DIR.glob("*.pdf")) + list(RAW_DIR.glob("*.txt"))
    )
    if not source_files:
        print(f"No PDFs or .txt files found in {RAW_DIR}")
        return

    # Skip files registered as in_faiss: false (scanned/marked docs — the wiki is
    # their searchable form). Explicit, never silent.
    ingestible = []
    for f in source_files:
        entry = registry.get(f.name, {})
        if entry and not entry.get("in_faiss", True):
            print(f"  SKIP (in_faiss: false): {f.name} — searchable via wiki pages/extracts")
        else:
            ingestible.append(f)
    source_files = ingestible
    if not source_files:
        print("All files are registered in_faiss: false — nothing to ingest.")
        return

    # Incremental mode: filter to new/changed files only
    manifest = load_manifest()
    if args.incremental and manifest:
        print("Incremental mode: checking for new/changed files...")
        changed_files = []
        for f in source_files:
            current_hash = file_hash(f)
            if f.name not in manifest or manifest[f.name].get("hash") != current_hash:
                changed_files.append(f)
                print(f"  CHANGED: {f.name}")
            else:
                print(f"  unchanged: {f.name}")
        if not changed_files:
            print("\nNo changes detected. Vector store is up to date.")
            return
        source_files = changed_files
        print(f"\nProcessing {len(source_files)} changed file(s)")
    else:
        print(f"\nFull rebuild: processing {len(source_files)} files:")
        for f in source_files:
            print(f"  - {f.name}")

    # Phase 1: Extract text
    print("\n--- Phase 1: Extracting text ---")
    all_documents = []
    for file_path in source_files:
        docs = build_documents(file_path, registry)
        all_documents.extend(docs)
    print(f"\nTotal pages extracted: {len(all_documents)}")

    if not all_documents:
        print("No content extracted. Check your source files.")
        return

    # Phase 2: Chunk
    print("\n--- Phase 2: Chunking documents ---")
    chunks = chunk_documents(all_documents)
    print(f"Total chunks created: {len(chunks)}")

    if chunks:
        print(f"\nSample chunk (first 300 chars):")
        print(f"  Content: {chunks[0].page_content[:300]}...")
        print(f"  Metadata: {chunks[0].metadata}")

    # Phase 3: Embed and store
    print("\n--- Phase 3: Building vector store ---")
    embeddings = get_embeddings()

    if args.incremental and VECTORSTORE_DIR.exists() and (VECTORSTORE_DIR / "index.faiss").exists():
        # Incremental: embed new chunks and merge into existing index
        print("Loading existing vector store for merge...")
        existing_store = FAISS.load_local(
            str(VECTORSTORE_DIR), embeddings, allow_dangerous_deserialization=True
        )
        new_store = build_vectorstore_batched(chunks, embeddings)
        existing_store.merge_from(new_store)
        vectorstore = existing_store
    else:
        # Full rebuild
        vectorstore = build_vectorstore_batched(chunks, embeddings)

    # Final save
    vectorstore.save_local(str(VECTORSTORE_DIR))
    print(f"\nVector store saved to {VECTORSTORE_DIR}/")

    # Update manifest (ingested files only — in_faiss: false docs are not tracked here)
    new_manifest = manifest.copy() if args.incremental else {}
    all_files = sorted(list(RAW_DIR.glob("*.pdf")) + list(RAW_DIR.glob("*.txt")))
    for f in all_files:
        entry = registry.get(f.name, {})
        if entry and not entry.get("in_faiss", True):
            continue
        new_manifest[f.name] = {
            "hash": file_hash(f),
            "processed": True,
        }
    save_manifest(new_manifest)
    print("Manifest updated.")
    print("Done!")


if __name__ == "__main__":
    main()
