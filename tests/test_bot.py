"""Offline tests for bot.py — no API key, no network, no model calls.

Covers the pure logic that has burned us in production: the CLAIMS trailer
parser (internal claim IDs leaked into displayed answers when the model
decorated the trailer), wiki path validation, and the routing diagnostics that
make an empty page list diagnosable.
"""

import re
from types import SimpleNamespace

import pytest

import bot


# --- CLAIMS trailer -------------------------------------------------------

@pytest.mark.parametrize("raw,expected_ids", [
    ("The cap is $750.\nCLAIMS: C041", ["C041"]),
    ("The cap is $750.\n\n**CLAIMS:** C041, C044", ["C041", "C044"]),
    ("The cap is $750.\n\n- CLAIMS: C041", ["C041"]),
    ("The cap is $750.\n\n**CLAIMS:** C041\n\n", ["C041"]),
    ("The cap is $750.\n_Claims: C041_", ["C041"]),
    ("The cap is $750.\n> CLAIMS: C041", ["C041"]),
    ("Not in the loaded regulations.\n**CLAIMS:** none", []),
    ("The cap is $750 (MARADMIN 157/25).", []),
])
def test_trailer_never_leaks_and_ids_are_extracted(raw, expected_ids):
    body, ids = bot.split_claims_trailer(raw)
    assert "CLAIMS" not in body.upper(), f"trailer leaked into display text: {body!r}"
    assert ids == expected_ids


def test_trailer_survives_a_long_multi_paragraph_answer():
    raw = "Para one.\n\nPara two.\n\n- bullet\n- bullet\n\n**CLAIMS:** C020, C021"
    body, ids = bot.split_claims_trailer(raw)
    assert ids == ["C020", "C021"]
    assert body.endswith("- bullet")


def test_inline_bracketed_ids_are_stripped_from_prose():
    body, ids = bot.split_claims_trailer("Cap is $750 [C041] per the MARADMIN.\nCLAIMS: C041")
    assert "[C041]" not in body
    assert ids == ["C041"]


def test_claim_id_regex_handles_four_digits():
    assert bot.CLAIM_ID_RE.findall("C041 and C1000") == ["C041", "C1000"]


# --- page loading ---------------------------------------------------------

def test_read_pages_rejects_traversal_and_dedupes():
    text, loaded = bot.read_pages([
        "orders-types/idt.md",
        "orders-types/idt.md",          # duplicate
        "../../../etc/passwd",          # traversal
        "does-not-exist.md",
    ])
    assert loaded == ["orders-types/idt.md"]
    assert "passwd" not in text


def test_read_pages_caps_at_max_pages():
    many = ["orders-types/idt.md", "orders-types/ados.md", "orders-types/at.md",
            "orders-types/offsite-idt.md", "entitlements/lodging.md"]
    _, loaded = bot.read_pages(many)
    assert len(loaded) <= bot.MAX_PAGES


# --- routing diagnostics --------------------------------------------------

class _Usage:
    prompt_token_count = 100
    candidates_token_count = 10


def _client(router_pages):
    """Stub client: router returns the given paths, answer returns a trailer."""
    class C:
        def __init__(self):
            self.models = self

        def generate_content(self, model, contents, config):
            if getattr(config, "response_schema", None):
                return SimpleNamespace(
                    parsed=bot.RouterDecision(pages=router_pages, needs_faiss=False),
                    usage_metadata=_Usage(), text="")
            return SimpleNamespace(parsed=None, usage_metadata=_Usage(),
                                   text="answer text\nCLAIMS: none")
    return C()


@pytest.fixture(scope="module")
def wiki_assets():
    catalog = bot.load_page_catalog()
    claims, index = bot.load_claims_table()
    return catalog, claims, index


@pytest.mark.parametrize("pages,want_loaded,want_dropped", [
    ([], [], []),                                                    # model chose nothing
    (["wiki/orders-types/idt.md"], [], ["wiki/orders-types/idt.md"]),  # wrong path format
    (["orders-types/idt.md"], ["orders-types/idt.md"], []),          # good
])
def test_empty_pages_is_diagnosable(wiki_assets, pages, want_loaded, want_dropped):
    """An empty `pages` must distinguish 'model returned nothing' from
    'the paths it named did not resolve' — conflating them cost three eval runs."""
    catalog, claims, index = wiki_assets
    r = bot.ask(_client(pages), None, catalog, claims, index, "", "q?", today="2026-07-23")
    assert r["pages"] == want_loaded
    assert r["router_requested"] == pages
    assert r["router_dropped"] == want_dropped


def test_ask_reports_both_calls_usage(wiki_assets):
    catalog, claims, index = wiki_assets
    r = bot.ask(_client(["orders-types/idt.md"]), None, catalog, claims, index,
                "", "q?", today="2026-07-23")
    assert [u["call_type"] for u in r["usage"]] == ["router", "answer"]


# --- catalog / registry loading ------------------------------------------

def test_catalog_rows_are_well_formed(wiki_assets):
    catalog, _, _ = wiki_assets
    rows = [r for r in catalog.splitlines() if r.strip()]
    assert len(rows) > 20, "router catalog is suspiciously small"
    for row in rows:
        parts = [p.strip() for p in row.split("|")]
        assert len(parts) >= 3, f"malformed catalog row: {row!r}"
        assert parts[0].endswith(".md"), f"catalog path is not a page: {row!r}"
        assert parts[2], f"catalog row has an empty description (router menu): {row!r}"


def test_claims_table_matches_registry(wiki_assets):
    _, claims, index = wiki_assets
    assert len(index) > 40
    for cid, claim in index.items():
        assert re.fullmatch(r"C\d{3,}", cid)
        assert claim.get("claim") and claim.get("source")
