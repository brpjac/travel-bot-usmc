"""Pure-function tests for the trip planner — the one module where a date bug
produces confidently wrong deadlines. No network, no Streamlit."""

from datetime import date

import planner
from planner import TripInputs


RULES = planner.load_rules()
CLAIMS = {c["id"]: c for c in __import__("yaml").safe_load(
    (planner.TIMELINES_FILE.parent.parent / "_claims.yml").read_text())["claims"]}


def trip(**kw) -> TripInputs:
    base = dict(departure=date(2026, 10, 1), return_date=date(2026, 10, 5),
                scope="oconus", party="individual", orders_type="at",
                commercial_air=True)
    base.update(kw)
    return TripInputs(**base)


def rule_ids(plan):
    return [d.rule_id for d in plan.deadlines]


def test_oconus_individual_air_gets_the_right_ladder():
    plan = planner.build_plan(trip(), date(2026, 7, 19), RULES, CLAIMS)
    ids = rule_ids(plan)
    assert "TL-T3-OCONUS" in ids and "TL-TOP-OCONUS" in ids
    assert "TL-T3-CONUS" not in ids and "TL-T3-CHARTER" not in ids
    assert "TL-ORDERS-OCONUS-60" in ids  # AT OCONUS -> 60-day orders lead


def test_charter_ignores_scope():
    conus = planner.build_plan(trip(scope="conus", party="charter"), date(2026, 7, 1), RULES, CLAIMS)
    oconus = planner.build_plan(trip(scope="oconus", party="charter"), date(2026, 7, 1), RULES, CLAIMS)
    for plan in (conus, oconus):
        assert "TL-T3-CHARTER" in rule_ids(plan) and "TL-TOP-CHARTER" in rule_ids(plan)
        assert "TL-T3-OCONUS" not in rule_ids(plan)


def test_no_air_means_only_orders_and_voucher():
    plan = planner.build_plan(trip(commercial_air=False, scope="conus", orders_type="ados"),
                              date(2026, 7, 19), RULES, CLAIMS)
    assert rule_ids(plan) == ["TL-ORDERS-CONUS-ADOS", "TL-VOUCHER"]


def test_deadline_dates_and_past_flags():
    # Departure 2026-10-01, today 2026-08-20: D-50 (Aug 12) past, D-45 (Aug 17) past, D-15 future
    plan = planner.build_plan(trip(), date(2026, 8, 20), RULES, CLAIMS)
    by_id = {d.rule_id: d for d in plan.deadlines}
    assert by_id["TL-T3-OCONUS"].due == date(2026, 8, 12) and by_id["TL-T3-OCONUS"].past
    assert by_id["TL-TOP-OCONUS"].due == date(2026, 8, 17) and by_id["TL-TOP-OCONUS"].past
    assert by_id["TL-ORDERS-APPROVED"].due == date(2026, 9, 16) and not by_id["TL-ORDERS-APPROVED"].past
    assert by_id["TL-TOP-OCONUS"].days_from_today == -3


def test_escalation_g35_vs_cos():
    # >15 days to departure with an exceeded T3 timeline -> G-3/5
    g35 = planner.build_plan(trip(), date(2026, 8, 20), RULES, CLAIMS)  # 42 days out
    assert g35.escalation and "G-3/5" in g35.escalation
    # <=15 days out -> Chief of Staff + cancellation warning
    cos = planner.build_plan(trip(), date(2026, 9, 25), RULES, CLAIMS)  # 6 days out
    assert cos.escalation and "Chief of Staff" in cos.escalation and "cancelled" in cos.escalation


def test_no_escalation_when_everything_is_future():
    plan = planner.build_plan(trip(departure=date(2027, 1, 15), return_date=date(2027, 1, 20)),
                              date(2026, 7, 19), RULES, CLAIMS)
    assert plan.escalation is None
    assert not any(d.past for d in plan.deadlines)


def test_voucher_business_days_over_weekend():
    # Return Fri 2026-10-02 -> +5 business days = Fri 2026-10-09
    plan = planner.build_plan(trip(return_date=date(2026, 10, 2)), date(2026, 7, 19), RULES, CLAIMS)
    voucher = next(d for d in plan.deadlines if d.rule_id == "TL-VOUCHER")
    assert voucher.due == date(2026, 10, 9)
    # Missing return date -> estimated from departure + note
    plan2 = planner.build_plan(trip(return_date=None), date(2026, 7, 19), RULES, CLAIMS)
    assert any("No return date" in n for n in plan2.notes)


def test_ics_structure():
    plan = planner.build_plan(trip(), date(2026, 7, 19), RULES, CLAIMS)
    ics = planner.to_ics(plan, trip()).decode()
    assert ics.startswith("BEGIN:VCALENDAR\r\n")
    assert "DTSTART;VALUE=DATE:20260812" in ics          # D-50 for 1 Oct departure
    assert "UID:TL-T3-OCONUS-20260812@miu-travel-bot" in ics
    assert "TRIGGER:-P1D" in ics
    assert ics.count("BEGIN:VEVENT") == len(plan.deadlines)


def test_every_rule_claim_resolves():
    for rule in RULES["rules"]:
        assert rule["claim_id"] in CLAIMS, f"{rule['id']} cites unknown {rule['claim_id']}"
        assert CLAIMS[rule["claim_id"]].get("status") == "active"
