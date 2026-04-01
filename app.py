"""
MIU Travel Regulation Bot — Streamlit Frontend

RAG chatbot for reserve Marines to query JTR, MCRAMM, MARADMINs,
and unit-specific travel guidance.
"""

import csv
import os
from datetime import datetime
from pathlib import Path

import streamlit as st
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings

VECTORSTORE_DIR = Path(__file__).parent / "vectorstore"
LOGS_DIR = Path(__file__).parent / "logs"

# Max conversation turns to include for context (each turn = 1 user + 1 assistant)
MAX_CONTEXT_TURNS = 3
MAX_CONTEXT_CHARS = 1500

SYSTEM_PROMPT = """\
You are the MIU Travel Regulation Assistant, a helpful chatbot for United States Marine Corps reserve Marines \
who need guidance on travel regulations and orders.

You answer questions using ONLY the regulation text provided in the context below. Follow these rules strictly:

1. **Cite your sources.** For every claim, cite the specific order, chapter, section, and page number. \
Use the format: (Source: [document name], Section [number], Page [number]).

2. **MARADMIN precedence.** If a MARADMIN contradicts a standing order, the MARADMIN takes precedence. \
Note this explicitly and cite the MARADMIN number and date.

3. **Do not guess.** If the provided context does not contain information to answer the question, say: \
"I don't have enough information in the loaded regulations to answer that. Please check with your S-1 or refer to the full JTR."

4. **Flag expiration dates.** If a MARADMIN or order has an expiration date that may have passed, flag it: \
"Note: This MARADMIN may have expired. Verify it is still in effect."

5. **Be practical — present options as a decision tree.** When a Marine asks what they can do, \
lay out ALL their options with what each one gets them. For example: "Option 1: IDT orders (no per diem, \
no rental car). Option 2: Request CO waiver for lodging on IDT. Option 3: Request ADOS orders \
(full entitlements including rental car and per diem)." Always connect the orders type to what \
the Marine actually rates (lodging, per diem, rental car, mileage). Include deadlines, form names, \
submission requirements, and who to contact when available in the source text.

6. **Use plain language.** Explain regulation language in terms a junior Marine can understand, \
but always include the exact regulatory citation.

7. **Distance and entitlements.** When a Marine mentions two locations, consider the distance between them. \
Travel to your own HTC is IDT regardless of how far you live from it. Key distance thresholds: \
(a) 50 miles from HTC — beyond this triggers Offsite IDT/AT/ADOS orders instead of regular IDT. \
(b) 150 miles outside local commuting area — Reserve Component members performing IDT at 150+ miles \
may qualify for lodging and meals allowance (up to $500 max per round-trip, if authorized). \
(c) 400 miles one-way / 800 miles round-trip — POV travel is automatically considered advantageous \
under 400 miles one-way; exceeding 800 miles round-trip requires a Constructed Travel Worksheet. \
Always flag which threshold applies when a Marine asks about entitlements or travel mode.

8. **DTS is a tool, not an orders type.** DTS (Defense Travel System) is the system used to create and manage \
travel authorizations and vouchers. The actual orders types are IDT, Offsite IDT, AT, and ADOS. \
Never list "DTS" as a type of orders.

{chat_history_section}

Context from regulations:
{context}

Question: {question}"""


@st.cache_resource
def load_embeddings():
    """Load the local HuggingFace embedding model (no API key needed)."""
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


@st.cache_resource
def load_vectorstore():
    """Load the FAISS vector store from disk."""
    embeddings = load_embeddings()
    return FAISS.load_local(
        str(VECTORSTORE_DIR),
        embeddings,
        allow_dangerous_deserialization=True,
    )


def format_docs(docs):
    """Format retrieved documents into a single context string."""
    formatted = []
    for doc in docs:
        source = doc.metadata.get("source_doc", "Unknown")
        section = doc.metadata.get("section", "")
        page = doc.metadata.get("page", "")
        header = f"[{source}"
        if section:
            header += f", Section {section}"
        if page:
            header += f", Page {page}"
        header += "]"
        formatted.append(f"{header}\n{doc.page_content}")
    return "\n\n---\n\n".join(formatted)


def get_source_citations(docs):
    """Extract unique source citations from retrieved documents."""
    citations = []
    seen = set()
    for doc in docs:
        source = doc.metadata.get("source_doc", "Unknown")
        section = doc.metadata.get("section", "")
        page = doc.metadata.get("page", "")
        key = f"{source}|{section}|{page}"
        if key not in seen:
            seen.add(key)
            parts = [source]
            if section:
                parts.append(f"Section {section}")
            if page:
                parts.append(f"Page {page}")
            citations.append(", ".join(parts))
    return citations


def build_chat_history(messages: list, use_context: bool) -> str:
    """Build a capped chat history string from recent messages."""
    if not use_context or not messages:
        return ""

    # Take last N turns (each turn = user + assistant pair)
    recent = messages[-(MAX_CONTEXT_TURNS * 2):]

    history_parts = []
    total_chars = 0
    for msg in recent:
        role = "Marine" if msg["role"] == "user" else "Assistant"
        content = msg["content"]
        entry = f"{role}: {content}"
        if total_chars + len(entry) > MAX_CONTEXT_CHARS:
            break
        history_parts.append(entry)
        total_chars += len(entry)

    if not history_parts:
        return ""

    return "Recent conversation for context:\n" + "\n".join(history_parts)


def log_token_usage(question: str, prompt_tokens: int, response_tokens: int):
    """Append token usage to CSV log file."""
    LOGS_DIR.mkdir(exist_ok=True)
    log_file = LOGS_DIR / "token_usage.csv"
    file_exists = log_file.exists()

    with open(log_file, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "question_length", "prompt_tokens", "response_tokens", "total_tokens"])
        writer.writerow([
            datetime.now().isoformat(),
            len(question),
            prompt_tokens,
            response_tokens,
            prompt_tokens + response_tokens,
        ])


def main():
    st.set_page_config(
        page_title="MIU Travel Regulation Bot",
        page_icon="🌐",
        layout="wide",
    )

    # Disclaimer banner
    st.warning(
        "**BETA — This tool is for reference only.** "
        "Answers may contain errors. Verify against the source order before taking action. "
        "This is not an official DoD or USMC system.",
        icon="⚠️",
    )

    st.title("MIU Travel Regulation Bot")
    st.caption("BETA — Ask questions about JTR, MCRAMM, and unit travel procedures")

    # Check for API key
    api_key = os.environ.get("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY", "")
    if not api_key:
        st.error("Google API key not configured. Set GOOGLE_API_KEY in environment or Streamlit secrets.")
        st.stop()

    # Check for vector store
    if not VECTORSTORE_DIR.exists():
        st.error("Vector store not found. Run `python scripts/ingest.py` first.")
        st.stop()

    # Load vector store
    vectorstore = load_vectorstore()
    if vectorstore is None:
        st.error("Failed to load vector store.")
        st.stop()

    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 8},
    )

    # LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0.1,
    )

    prompt = ChatPromptTemplate.from_template(SYSTEM_PROMPT)

    # Session state init
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "token_usage" not in st.session_state:
        st.session_state.token_usage = []

    # Sidebar
    with st.sidebar:
        st.header("Loaded Documents")
        try:
            docs_dir = Path(__file__).parent / "docs"
            for f in sorted(list(docs_dir.glob("*.pdf")) + list(docs_dir.glob("*.txt"))):
                if f.name != "metadata.json":
                    st.markdown(f"- {f.stem}")
        except Exception:
            st.markdown("_Unable to list documents_")

        st.divider()

        # New Chat button
        if st.button("New Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.token_usage = []
            st.rerun()

        # Conversation context toggle
        use_context = st.toggle("Use conversation context", value=True)
        st.caption(
            "This bot remembers your last 3 questions for follow-ups. "
            "For best results on a new topic, click **New Chat**."
        )

        st.divider()

        # Token usage display
        st.subheader("Token Usage")
        usage = st.session_state.token_usage
        if usage:
            total_prompt = sum(u["prompt"] for u in usage)
            total_response = sum(u["response"] for u in usage)
            total = total_prompt + total_response
            avg = total // len(usage) if usage else 0

            st.metric("Session Total", f"{total:,} tokens")
            st.metric("Avg per Query", f"{avg:,} tokens")
            st.caption(f"{len(usage)} queries this session")

            with st.expander("Per-query breakdown"):
                for i, u in enumerate(usage, 1):
                    st.text(
                        f"Q{i}: {u['prompt']:,} prompt + {u['response']:,} response "
                        f"= {u['prompt'] + u['response']:,} total"
                    )
        else:
            st.caption("No queries yet")

        st.divider()

        st.markdown("**Example questions:**")
        st.markdown(
            "- What type of orders do I need for an offsite IDT more than 50 miles from my HTC?\n"
            "- How far in advance do I need to submit orders for OCONUS travel?\n"
            "- What is the per diem rate policy for TDY travel?\n"
            "- What are my responsibilities as a traveler under the JTR?\n"
            "- When should I use AT orders vs ADOS orders?"
        )

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("citations"):
                with st.expander("Sources"):
                    for cite in message["citations"]:
                        st.markdown(f"- {cite}")

    # Chat input
    if question := st.chat_input("Ask a travel regulation question..."):
        # Show user message
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Searching regulations..."):
                # Retrieve relevant chunks
                retrieved_docs = retriever.invoke(question)
                context = format_docs(retrieved_docs)
                citations = get_source_citations(retrieved_docs)

                # Build chat history (from messages BEFORE the current question)
                history_messages = st.session_state.messages[:-1]  # exclude current question
                chat_history = build_chat_history(history_messages, use_context)
                chat_history_section = ""
                if chat_history:
                    chat_history_section = chat_history + "\n"

                # Build chain and run — get full response object for token counts
                chain = prompt | llm
                result = chain.invoke({
                    "context": context,
                    "question": question,
                    "chat_history_section": chat_history_section,
                })

                response = result.content

                # Extract token usage
                prompt_tokens = 0
                response_tokens = 0
                if hasattr(result, "usage_metadata") and result.usage_metadata:
                    prompt_tokens = getattr(result.usage_metadata, "input_tokens", 0)
                    response_tokens = getattr(result.usage_metadata, "output_tokens", 0)
                elif hasattr(result, "response_metadata"):
                    meta = result.response_metadata or {}
                    usage = meta.get("usage_metadata", {})
                    prompt_tokens = usage.get("prompt_token_count", 0)
                    response_tokens = usage.get("candidates_token_count", 0)

                # Track token usage
                st.session_state.token_usage.append({
                    "prompt": prompt_tokens,
                    "response": response_tokens,
                })
                log_token_usage(question, prompt_tokens, response_tokens)

            st.markdown(response)
            with st.expander("Sources"):
                for cite in citations:
                    st.markdown(f"- {cite}")

        # Save to history
        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "citations": citations,
        })


if __name__ == "__main__":
    main()
