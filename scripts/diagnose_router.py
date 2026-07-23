#!/usr/bin/env python3
"""Cheapest discriminating test for the empty-router-pages bug.

Symptom (eval run 2026-07-22): on gemini-3.5-flash the router returns
pages: [] for nearly every question (router accuracy 2/11), while the same
prompt on gemini-2.5-flash picks pages correctly. Answers stayed correct
because the claims table is always in the answer prompt — so the failure is
silent in production, showing up only as thinner, page-free answers.

This script sends ONE router call per (model, config) combination — a handful
of requests, not a 52-request eval — and prints what each returns.

Usage:
    GOOGLE_API_KEY=... .venv/bin/python scripts/diagnose_router.py
    GOOGLE_API_KEY=... .venv/bin/python scripts/diagnose_router.py --models gemini-2.5-flash,gemini-3.5-flash
"""

import argparse
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import bot  # noqa: E402
from google import genai  # noqa: E402
from google.genai import types  # noqa: E402

QUESTION = "My unit is drilling at a site 60 miles from our HTC. What orders type do I need and when do I submit the request?"
EXPECTED = {"orders-types/choosing-orders-type.md", "orders-types/offsite-idt.md",
            "process/orders-request-miu.md"}


def variants():
    """(name, config-kwargs, prompt-tweak) combinations to discriminate causes."""
    base = dict(temperature=0, response_mime_type="application/json",
                response_schema=bot.RouterDecision)
    return [
        ("thinking_budget=0 (current)", {**base, "thinking_config": types.ThinkingConfig(thinking_budget=0)}, None),
        ("no thinking_config", dict(base), None),
        ("thinking_budget=-1 (dynamic)", {**base, "thinking_config": types.ThinkingConfig(thinking_budget=-1)}, None),
        ("no thinking + 'choose 2-4' wording", dict(base),
         lambda p: p.replace("Choose 0-4 page paths", "Choose 2-4 page paths")
                    .replace("If nothing in the catalog fits, return an empty pages list.",
                             "Only return an empty pages list if the question is entirely unrelated to travel.")),
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="gemini-2.5-flash,gemini-3.5-flash")
    ap.add_argument("--question", default=QUESTION)
    args = ap.parse_args()

    key = os.environ.get("GOOGLE_API_KEY")
    if not key:
        print("GOOGLE_API_KEY not set")
        return 2
    client = genai.Client(api_key=key)
    catalog = bot.load_page_catalog()
    print(f"catalog rows: {len(catalog.splitlines())} | question: {args.question[:60]}...\n")

    calls = 0
    for model in [m.strip() for m in args.models.split(",") if m.strip()]:
        print(f"=== {model} ===")
        for name, cfg, tweak in variants():
            prompt = bot.ROUTER_PROMPT.format(catalog=catalog, history="",
                                              question=args.question, today="2026-07-23")
            if tweak:
                prompt = tweak(prompt)
            try:
                resp = client.models.generate_content(
                    model=model, contents=prompt,
                    config=types.GenerateContentConfig(**cfg))
                calls += 1
                d = resp.parsed
                pages = list(d.pages) if d else []
                hit = "HIT " if set(pages) & EXPECTED else "MISS"
                print(f"  {hit} {name:38} pages={pages} needs_faiss={d.needs_faiss if d else '?'}")
            except Exception as e:
                calls += 1
                print(f"  ERR  {name:38} {str(e)[:110]}")
        print()
    print(f"total API requests used: {calls}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
