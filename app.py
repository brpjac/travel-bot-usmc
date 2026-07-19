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

import bot
import planner

# langchain/torch imports are deferred into load_embeddings()/load_vectorstore()
# so `import app` stays light (CI) and cold starts skip torch when FAISS is absent.

VECTORSTORE_DIR = Path(__file__).parent / "vectorstore"
LOGS_DIR = Path(__file__).parent / "logs"
WIKI_DIR = Path(__file__).parent / "wiki"

# Max conversation turns to include for context (each turn = 1 user + 1 assistant)
MAX_CONTEXT_TURNS = 3
MAX_CONTEXT_CHARS = 1500


@st.cache_resource
def load_embeddings():
    """Load the local HuggingFace embedding model (no API key needed)."""
    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


@st.cache_resource
def load_vectorstore():
    """Load the FAISS vector store from disk (deep JTR/MCRAMM fallback)."""
    from langchain_community.vectorstores import FAISS
    embeddings = load_embeddings()
    return FAISS.load_local(
        str(VECTORSTORE_DIR),
        embeddings,
        allow_dangerous_deserialization=True,
    )


def md_safe(text: str) -> str:
    """Escape $ so Streamlit's markdown doesn't LaTeX-mangle dollar amounts."""
    return text.replace("$", r"\$")


def page_title(path: str) -> str:
    """Human-readable page name from a wiki path: 'process/t3-timelines.md' -> 'T3 Timelines'."""
    stem = Path(path).stem
    if stem == "CLAUDE":
        stem = Path(path).parent.name or "index"
    words = stem.replace("-", " ").split()
    caps = {"t3", "idt", "at", "ados", "teep", "pov", "dts", "mrows", "miu", "jtr", "mcramm", "foro", "maradmin"}
    return " ".join(w.upper() if w.lower() in caps else w.capitalize() for w in words)


@st.cache_data(ttl=300)
def load_wiki_assets():
    """Router catalog + claims table, cached briefly so wiki edits show up."""
    catalog = bot.load_page_catalog()
    claims, claims_index = bot.load_claims_table()
    return catalog, claims, claims_index


DAILY_BUDGET = 200  # answers/day, under gemini-2.5-flash's free-tier RPD with headroom


@st.cache_resource
def daily_counter() -> dict:
    """Process-global {'date': 'YYYY-MM-DD', 'answers': int} across sessions."""
    return {}


@st.cache_data(ttl=300)
def load_sources_summary():
    """Source-document list for the sidebar, from wiki/_sources.yml."""
    data = yaml.safe_load((WIKI_DIR / "_sources.yml").read_text(encoding="utf-8"))
    return [
        {"cite": s["short_cite"], "as_of": str(s.get("as_of", ""))}
        for s in data.get("sources", [])
        if not s.get("local_only")
    ]


@st.cache_data(ttl=300)
def load_timeline_rules():
    return planner.load_rules()


def render_trip_planner(claims_index: dict):
    """Deterministic deadline planner — no model calls."""
    from datetime import date, timedelta

    with st.expander("🗓️ Trip Planner — turn your departure date into calendar deadlines"):
        c1, c2, c3 = st.columns(3)
        with c1:
            departure = st.date_input("Departure date", value=date.today() + timedelta(days=60))
            has_return = st.checkbox("I have a return date", value=True)
            return_date = st.date_input("Return date", value=departure + timedelta(days=4)) if has_return else None
        with c2:
            scope = st.radio("Where", ["CONUS", "OCONUS"], horizontal=True)
            party = st.radio("Party", ["Individual", "Group (2-99)", "Charter (100+)"])
        with c3:
            orders_type = st.selectbox("Orders type", ["Offsite IDT", "AT", "ADOS"])
            commercial_air = st.checkbox("Commercial air travel", value=True)

        trip = planner.TripInputs(
            departure=departure,
            return_date=return_date,
            scope=scope.lower(),
            party={"Individual": "individual", "Group (2-99)": "group", "Charter (100+)": "charter"}[party],
            orders_type={"Offsite IDT": "offsite_idt", "AT": "at", "ADOS": "ados"}[orders_type],
            commercial_air=commercial_air,
        )
        plan = planner.build_plan(trip, date.today(), load_timeline_rules(), claims_index)

        if plan.escalation:
            st.error(plan.escalation)

        rows = []
        for d in plan.deadlines:
            when = f"{abs(d.days_from_today)} days ago" if d.past else f"in {d.days_from_today} days"
            rows.append({
                "Due": d.due.strftime("%a %d %b %Y"),
                "When": ("⚠️ " if d.past else "") + when,
                "What": d.label,
                "Source": d.source,
            })
        if rows:
            st.table(rows)
            st.download_button(
                "📅 Add to calendar (.ics)",
                data=planner.to_ics(plan, trip),
                file_name=f"miu-trip-deadlines-{departure.isoformat()}.ics",
                mime="text/calendar",
            )
        for note in plan.notes:
            st.caption(note)
        st.caption("Deadlines from ForO 3000-52.1 and MIU guidance — verify with your S-1.")


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


TOKEN_LOG_HEADER = ["timestamp", "question_length", "call_type",
                    "prompt_tokens", "response_tokens", "total_tokens"]


def log_token_usage(question: str, call_type: str, prompt_tokens: int, response_tokens: int):
    """Append per-call token usage to the CSV log file. If an existing file has
    a stale header (pre-call_type schema), rotate it aside and start fresh."""
    LOGS_DIR.mkdir(exist_ok=True)
    log_file = LOGS_DIR / "token_usage.csv"
    file_exists = log_file.exists()

    if file_exists:
        try:
            with open(log_file, newline="") as f:
                first = f.readline().strip()
            if first and first.split(",") != TOKEN_LOG_HEADER:
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                log_file.rename(LOGS_DIR / f"token_usage-{stamp}.csv")
                file_exists = False
        except OSError:
            pass

    with open(log_file, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(TOKEN_LOG_HEADER)
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

    # Check for API key (st.secrets raises when no secrets.toml exists locally)
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        try:
            api_key = st.secrets.get("GOOGLE_API_KEY", "")
        except Exception:
            api_key = ""
    if not api_key:
        st.error("Google API key not configured. Set GOOGLE_API_KEY in environment or Streamlit secrets.")
        st.stop()

    if not (WIKI_DIR / "_map.md").exists():
        st.error("Wiki not found. The wiki/ directory (with _map.md) is the knowledge layer.")
        st.stop()

    client = genai.Client(api_key=api_key)
    catalog, claims, claims_index = load_wiki_assets()

    render_trip_planner(claims_index)

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

    # Courtesy daily budget across all sessions (process-global; resets on
    # redeploy — Google's own free-tier quota is the real enforcement).
    counter = daily_counter()
    today_key = datetime.now().strftime("%Y-%m-%d")
    if counter.get("date") != today_key:
        counter["date"] = today_key
        counter["answers"] = 0

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
            st.markdown(md_safe(message["content"]))
            if message.get("citations"):
                with st.expander("Sources"):
                    for cite in message["citations"]:
                        st.markdown(f"- {md_safe(cite)}")

    # Chat input
    if question := st.chat_input("Ask a travel regulation question..."):
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(md_safe(question))

        if counter.get("answers", 0) >= DAILY_BUDGET:
            with st.chat_message("assistant"):
                st.info(
                    "The bot's free daily budget is used up — it resets around "
                    "midnight Pacific. The Trip Planner above still works (it "
                    "makes no model calls)."
                )
            st.session_state.messages.pop()
            st.stop()

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

                counter["answers"] = counter.get("answers", 0) + 1
                response = result["answer"]

                # Sources: wiki pages read (as titles), cited facts, deep-search hits
                citations = [f"Wiki: {page_title(p)}" for p in result["pages"]]
                citations += result["claim_citations"]
                citations += [f"JTR/MCRAMM search: {c}" for c in result["faiss_citations"]]

                for u in result["usage"]:
                    st.session_state.token_usage.append(u)
                    log_token_usage(question, u["call_type"], u["prompt"], u["response"])

            st.markdown(md_safe(response))
            if citations:
                with st.expander("Sources"):
                    for cite in citations:
                        st.markdown(f"- {md_safe(cite)}")

        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "citations": citations,
        })


if __name__ == "__main__":
    main()
