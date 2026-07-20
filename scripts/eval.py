#!/usr/bin/env python3
"""Answer-quality regression suite: runs the REAL two-call pipeline over
evals/questions.yml and grades deterministically (no LLM judge).

Usage:
    GOOGLE_API_KEY=... python scripts/eval.py [--ids Q01,Q05] [--limit N]
        [--no-faiss] [--sleep 7] [--min-pass 0.8] [--today 2026-07-19]
        [--out evals/results-<date>.md]

Exit 0 when pass rate >= --min-pass, else 1. Reports are written to
evals/results-<date>.md (gitignored). ~2 model calls per question — mind the
free-tier RPM (default 7s sleep between questions).
"""

import argparse
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import bot  # noqa: E402

QUESTIONS_FILE = REPO / "evals" / "questions.yml"
DEFAULT_MAX_WORDS = 200


@dataclass
class QuestionResult:
    qid: str
    passed: bool
    failures: list[str] = field(default_factory=list)
    router_hit: bool | None = None
    faiss_ok: bool | None = None
    pages: list[str] = field(default_factory=list)
    cited: list[str] = field(default_factory=list)
    answer: str = ""
    skipped: bool = False  # excluded from the pass-rate denominator


def load_questions(path: Path = QUESTIONS_FILE) -> list[dict]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["questions"]


def grade(q: dict, result: dict) -> QuestionResult:
    """Pure grading function — unit-testable, no I/O."""
    # A question that exists to exercise the FAISS fallback cannot be graded
    # when FAISS isn't loaded (CI runs --no-faiss) — skip, don't fail.
    if q.get("expect_faiss") and not result.get("faiss_available", True):
        return QuestionResult(qid=q["id"], passed=True, skipped=True,
                              failures=["SKIPPED: requires FAISS, not loaded"])
    answer = result["answer"]
    low = answer.lower()
    cited = result.get("claim_ids", [])
    pages = result.get("pages", [])
    failures: list[str] = []

    for cid in q.get("expect_claims_all", []):
        if cid not in cited:
            failures.append(f"missing required claim {cid}")
    if q.get("expect_claims") and not set(q["expect_claims"]) & set(cited):
        failures.append(f"none of expected claims cited (wanted any of {q['expect_claims']}, got {cited})")
    for cid in q.get("forbid_claims", []):
        if cid in cited:
            failures.append(f"forbidden claim {cid} cited")
    if q.get("expect_no_claims") and cited:
        failures.append(f"expected no claims, got {cited}")

    for s in q.get("expect_substrings", []):
        if s.lower() not in low:
            failures.append(f"missing substring {s!r}")
    anys = q.get("expect_any_substring", [])
    if anys and not any(s.lower() in low for s in anys):
        failures.append(f"none of {anys!r} present")
    for s in q.get("forbid_substrings", []):
        if s.lower() in low:
            failures.append(f"forbidden substring {s!r} present")

    max_words = q.get("max_words", DEFAULT_MAX_WORDS)
    n_words = len(re.findall(r"\S+", answer))
    if n_words > max_words:
        failures.append(f"answer too long: {n_words} words > {max_words}")

    router_hit = None
    if "expect_pages" in q:
        expected = q["expect_pages"]
        router_hit = (not expected and not pages) or bool(set(expected) & set(pages))
        if not router_hit:
            failures.append(f"router missed pages (wanted any of {expected}, got {pages})")

    faiss_ok = None
    if "expect_faiss" in q and result.get("faiss_available", True):
        faiss_ok = result.get("faiss_used", False) == q["expect_faiss"]
        if not faiss_ok:
            failures.append(f"faiss fired={result.get('faiss_used')} wanted={q['expect_faiss']}")

    return QuestionResult(qid=q["id"], passed=not failures, failures=failures,
                         router_hit=router_hit, faiss_ok=faiss_ok,
                         pages=pages, cited=cited, answer=answer)


def run_one(client, vectorstore, catalog, claims, claims_index, q, today) -> dict:
    result = bot.ask(client, vectorstore, catalog, claims, claims_index,
                     q.get("history", ""), q["question"], today=today)
    result["faiss_used"] = bool(result["faiss_citations"])
    result["faiss_available"] = vectorstore is not None
    return result


def render_report(results: list[QuestionResult], meta: dict) -> str:
    graded = [r for r in results if not r.skipped]
    n = len(graded) or 1
    n_pass = sum(r.passed for r in graded)
    n_skip = len(results) - len(graded)
    routed = [r for r in graded if r.router_hit is not None]
    lines = [
        f"# Eval results — {meta['date']}",
        "",
        f"Pass: **{n_pass}/{len(graded)}** ({n_pass / n:.0%}, {n_skip} skipped) · router accuracy: "
        f"{sum(r.router_hit for r in routed)}/{len(routed)} · "
        f"answer model: {meta['answer_model']} · router model: {meta['router_model']} · "
        f"pinned today: {meta['today']}",
        "",
        "| Q | Result | Failures |",
        "|---|--------|----------|",
    ]
    for r in results:
        lines.append(f"| {r.qid} | {'PASS' if r.passed else 'FAIL'} | {'; '.join(r.failures) or ''} |")
    lines += ["", "<details><summary>Answers</summary>", ""]
    for r in results:
        lines += [f"### {r.qid}", "", f"pages: {r.pages} · cited: {r.cited}", "", r.answer, ""]
    lines += ["</details>", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", help="comma-separated question ids to run")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--no-faiss", action="store_true")
    ap.add_argument("--sleep", type=float, default=7.0)
    ap.add_argument("--min-pass", type=float, default=0.8)
    ap.add_argument("--today", default=date.today().isoformat())
    ap.add_argument("--out")
    args = ap.parse_args()

    import os
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("GOOGLE_API_KEY not set")
        return 2

    from google import genai
    client = genai.Client(api_key=api_key)

    vectorstore = None
    if not args.no_faiss and (REPO / "vectorstore").exists():
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            from langchain_community.vectorstores import FAISS
            emb = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            vectorstore = FAISS.load_local(str(REPO / "vectorstore"), emb,
                                           allow_dangerous_deserialization=True)
        except Exception as e:
            print(f"note: FAISS unavailable ({e}); expect_faiss checks will be skipped")

    catalog = bot.load_page_catalog()
    claims, claims_index = bot.load_claims_table()

    questions = load_questions()
    if args.ids:
        wanted = {i.strip() for i in args.ids.split(",")}
        questions = [q for q in questions if q["id"] in wanted or q["id"].split("-")[0] in wanted]
    if args.limit:
        questions = questions[: args.limit]

    results: list[QuestionResult] = []
    for i, q in enumerate(questions):
        raw = None
        for attempt, backoff in ((1, 30), (2, 60), (3, 90), (4, 0)):
            try:
                raw = run_one(client, vectorstore, catalog, claims, claims_index, q, args.today)
                break
            except Exception as e:
                rate_limited = "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)
                if rate_limited and backoff:
                    print(f"  {q['id']}: rate-limited (attempt {attempt}), backing off {backoff}s...")
                    time.sleep(backoff)
                else:
                    raw = {"answer": f"(PIPELINE ERROR — not a content failure: {e})",
                           "claim_ids": [], "pages": [],
                           "faiss_citations": [], "faiss_used": False,
                           "faiss_available": vectorstore is not None}
                    break
        r = grade(q, raw)
        results.append(r)
        print(f"{r.qid}: {'PASS' if r.passed else 'FAIL — ' + '; '.join(r.failures)}")
        if i < len(questions) - 1:
            time.sleep(args.sleep)

    graded = [r for r in results if not r.skipped]
    n_pass = sum(r.passed for r in graded)
    rate = n_pass / len(graded) if graded else 0.0
    router_model = bot.ROUTER_MODEL
    if getattr(bot, "_router_model_broken", False):
        router_model = f"{bot.ANSWER_MODEL} (FALLBACK — {bot.ROUTER_MODEL} unavailable on this key)"
        print(f"\nWARNING: router model {bot.ROUTER_MODEL} 404'd; ran on the answer-model fallback")
    meta = {"date": date.today().isoformat(), "today": args.today,
            "router_model": router_model, "answer_model": bot.ANSWER_MODEL}
    out = Path(args.out) if args.out else REPO / "evals" / f"results-{meta['date']}.md"
    out.write_text(render_report(results, meta), encoding="utf-8")
    n_skip = len(results) - len(graded)
    print(f"\npass rate: {n_pass}/{len(graded)} ({rate:.0%}, {n_skip} skipped) — report: {out.relative_to(REPO)}")
    return 0 if rate >= args.min_pass else 1


if __name__ == "__main__":
    sys.exit(main())
