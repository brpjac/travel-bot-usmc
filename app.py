"""
MIU Travel Regulation Bot — Streamlit Frontend

Agentic wiki-navigation chatbot for reserve Marines: a router call picks pages
from the wiki knowledge layer (wiki/), an answer call composes the reply with
claim-ID and regulation citations. FAISS over the raw JTR/MCRAMM serves
verbatim deep-cuts. See bot.py for the agent logic.
"""

import csv
import os
from datetime import datetime
from pathlib import Path

import streamlit as st
import yaml
from google import genai
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

import bot

VECTORSTORE_DIR = Path(__file__).parent / "vectorstore"
LOGS_DIR = Path(__file__).parent / "logs"
WIKI_DIR = Path(__file__).parent / "wiki"

# Max conversation turns to include for context (each turn = 1 user + 1 assistant)
MAX_CONTEXT_TURNS = 3
MAX_CONTEXT_CHARS = 1500


@st.cache_resource
def load_embeddings():
    """Load the local HuggingFace embedding model (no API key needed)."""
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


@st.cache_resource
def load_vectorstore():
    """Load the FAISS vector store from disk (deep JTR/MCRAMM fallback)."""
    embeddings = load_embeddings()
    return FAISS.load_local(
        str(VECTORSTORE_DIR),
        embeddings,
        allow_dangerous_deserialization=True,
    )


@st.cache_data(ttl=300)
def load_wiki_assets():
    """Router catalog + claims table, cached briefly so wiki edits show up."""
    catalog = bot.load_page_catalog()
    claims, claims_index = bot.load_claims_table()
    return catalog, claims, claims_index


@st.cache_data(ttl=300)
def load_sources_summary():
    """Source-document list for the sidebar, from wiki/_sources.yml."""
    data = yaml.safe_load((WIKI_DIR / "_sources.yml").read_text(encoding="utf-8"))
    return [
        {"cite": s["short_cite"], "as_of": str(s.get("as_of", ""))}
        for s in data.get("sources", [])
        if not s.get("local_only")
    ]


def build_chat_history(messages: list, use_context: bool) -> str:
    """Build a capped chat history string from recent messages."""
    if not use_context or not messages:
        return ""

    recent = messages[-(MAX_CONTEXT_TURNS * 2):]

    history_parts = []
    total_chars = 0
    for msg in recent:
        role = "Marine" if msg["role"] == "user" else "Assistant"
        entry = f"{role}: {msg['content']}"
        if total_chars + len(entry) > MAX_CONTEXT_CHARS:
            break
        history_parts.append(entry)
        total_chars += len(entry)

    if not history_parts:
        return ""

    return "Recent conversation for context:\n" + "\n".join(history_parts)


def log_token_usage(question: str, call_type: str, prompt_tokens: int, response_tokens: int):
    """Append per-call token usage to the CSV log file."""
    LOGS_DIR.mkdir(exist_ok=True)
    log_file = LOGS_DIR / "token_usage.csv"
    file_exists = log_file.exists()

    with open(log_file, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "question_length", "call_type",
                             "prompt_tokens", "response_tokens", "total_tokens"])
        writer.writerow([
            datetime.now().isoformat(),
            len(question),
            call_type,
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
    st.caption("BETA — Ask about orders types, entitlements, T3/TOP deadlines, and travel procedures")

    # Check for API key
    api_key = os.environ.get("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY", "")
    if not api_key:
        st.error("Google API key not configured. Set GOOGLE_API_KEY in environment or Streamlit secrets.")
        st.stop()

    if not (WIKI_DIR / "_map.md").exists():
        st.error("Wiki not found. The wiki/ directory (with _map.md) is the knowledge layer.")
        st.stop()

    client = genai.Client(api_key=api_key)
    catalog, claims, claims_index = load_wiki_assets()

    # FAISS is a fallback, not a requirement — the wiki alone can answer.
    vectorstore = None
    if VECTORSTORE_DIR.exists():
        try:
            vectorstore = load_vectorstore()
        except Exception:
            vectorstore = None

    # Session state init
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "token_usage" not in st.session_state:
        st.session_state.token_usage = []

    # Sidebar
    with st.sidebar:
        st.header("Knowledge Layer")
        n_pages = len([l for l in catalog.splitlines() if l.strip()])
        st.caption(f"Wiki: {n_pages} pages · claims registry · source extracts")
        try:
            for s in load_sources_summary():
                st.markdown(f"- {s['cite']} _(as of {s['as_of']})_")
        except Exception:
            st.markdown("_Unable to list sources_")
        if vectorstore is None:
            st.caption("Deep JTR search: unavailable (no vectorstore)")

        st.divider()

        if st.button("New Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.token_usage = []
            st.rerun()

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
            n_queries = len([u for u in usage if u["call_type"] == "answer"])
            avg = total // n_queries if n_queries else 0

            st.metric("Session Total", f"{total:,} tokens")
            st.metric("Avg per Query", f"{avg:,} tokens")
            st.caption(f"{n_queries} queries this session (2 model calls each)")

            with st.expander("Per-call breakdown"):
                for i, u in enumerate(usage, 1):
                    st.text(
                        f"{u['call_type']:>6}: {u['prompt']:,} prompt + "
                        f"{u['response']:,} response"
                    )
        else:
            st.caption("No queries yet")

        st.divider()

        st.markdown("**Example questions:**")
        st.markdown(
            "- What type of orders do I need for an offsite IDT more than 50 miles from my HTC?\n"
            "- When must I submit my TOP request for OCONUS travel?\n"
            "- I missed the T3 window for a flight next week — what now?\n"
            "- Can I get a rental car on IDT orders?\n"
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
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Reading the wiki..."):
                history_messages = st.session_state.messages[:-1]
                chat_history = build_chat_history(history_messages, use_context)

                try:
                    result = bot.ask(
                        client, vectorstore, catalog, claims, claims_index,
                        chat_history, question,
                    )
                except Exception as e:
                    st.error(f"Model call failed: {e}")
                    st.session_state.messages.pop()
                    st.stop()

                response = result["answer"]

                # Sources: wiki pages read, claims cited, FAISS chunks used
                citations = [f"Wiki: {p}" for p in result["pages"]]
                citations += result["claim_citations"]
                citations += [f"JTR/MCRAMM search: {c}" for c in result["faiss_citations"]]

                for u in result["usage"]:
                    st.session_state.token_usage.append(u)
                    log_token_usage(question, u["call_type"], u["prompt"], u["response"])

            st.markdown(response)
            if citations:
                with st.expander("Sources"):
                    for cite in citations:
                        st.markdown(f"- {cite}")

        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "citations": citations,
        })


if __name__ == "__main__":
    main()
