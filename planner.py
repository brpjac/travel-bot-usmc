"""Deterministic trip-deadline planner — zero LLM calls.

Turns a departure date + trip shape into concrete calendar deadlines using the
claim-backed rules in wiki/reference/timelines.yml, and renders them as an
RFC 5545 .ics file for calendar import. This is the feature aimed at the
unit's late-TOP-submission problem: the bot explains deadlines, this puts
them in a Marine's calendar.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

import yaml

TIMELINES_FILE = Path(__file__).parent / "wiki" / "reference" / "timelines.yml"


@dataclass(frozen=True)
class TripInputs:
    departure: date
    return_date: date | None
    scope: Literal["conus", "oconus"]
    party: Literal["individual", "group", "charter"]
    orders_type: Literal["offsite_idt", "at", "ados"]
    commercial_air: bool


@dataclass(frozen=True)
class Deadline:
    rule_id: str
    label: str
    due: date
    claim_id: str
    source: str
    category: str
    days_from_today: int  # negative = already past
    past: bool


@dataclass(frozen=True)
class Plan:
    deadlines: list[Deadline]
    escalation: str | None
    notes: list[str]


def load_rules(path: Path | None = None) -> dict:
    return yaml.safe_load((path or TIMELINES_FILE).read_text(encoding="utf-8"))


def rule_applies(rule: dict, trip: TripInputs) -> bool:
    cond = rule.get("applies") or {}
    if "scope" in cond and trip.scope not in cond["scope"]:
        return False
    if "party" in cond and trip.party not in cond["party"]:
        return False
    if "orders_type" in cond and trip.orders_type not in cond["orders_type"]:
        return False
    if "commercial_air" in cond and trip.commercial_air != cond["commercial_air"]:
        return False
    return True


def add_business_days(start: date, n: int) -> date:
    """Add n Mon-Fri business days (federal holidays not modeled — documented)."""
    step = 1 if n >= 0 else -1
    d, remaining = start, abs(n)
    while remaining:
        d += timedelta(days=step)
        if d.weekday() < 5:
            remaining -= 1
    return d


def build_plan(trip: TripInputs, today: date, rules: dict, claims_index: dict) -> Plan:
    notes: list[str] = []
    deadlines: list[Deadline] = []

    for rule in rules.get("rules", []):
        if not rule_applies(rule, trip):
            continue
        if rule.get("anchor") == "return":
            anchor = trip.return_date or trip.departure
            if trip.return_date is None:
                notes.append(f"No return date given — '{rule['label']}' is estimated from the departure date.")
        else:
            anchor = trip.departure
        offset = rule["offset_days"]
        due = add_business_days(anchor, offset) if rule.get("business_days") else anchor + timedelta(days=offset)
        claim = claims_index.get(rule["claim_id"], {})
        deadlines.append(Deadline(
            rule_id=rule["id"],
            label=rule["label"],
            due=due,
            claim_id=rule["claim_id"],
            source=claim.get("source", ""),
            category=rule["category"],
            days_from_today=(due - today).days,
            past=due < today,
        ))

    deadlines.sort(key=lambda d: d.due)

    escalation = None
    if any(d.past and d.category in ("t3", "ticketing") for d in deadlines):
        esc = rules.get("escalation", {})
        days_to_d = (trip.departure - today).days
        if days_to_d > esc.get("g35_when_days_to_departure_gt", 15):
            escalation = (
                "A T3/TOP timeline has already been exceeded. Submission now requires an "
                "MSC G-3/5 endorsement stating operational necessity, cost acceptance, and "
                "carrier-availability risk (ForO 3000-52.1, Ch 5). Start with your S-3/S-1 today."
            )
        elif days_to_d >= 0:
            escalation = (
                "You are inside 15 days of departure with an exceeded timeline: this requires "
                "an MSC Chief of Staff endorsement, and reservations without approved orders "
                "by D-15 are cancelled (ForO 3000-52.1, Ch 5). Engage your S-3/S-1 immediately."
            )
        else:
            escalation = "Departure date is in the past — check your inputs."

    if trip.return_date and trip.return_date < trip.departure:
        notes.append("CHECK YOUR DATES: the return date is before the departure date, "
                     "so the voucher deadline below is not meaningful.")
    if trip.party == "charter":
        notes.append("Charter deadlines apply regardless of destination (the ForO has no CONUS/OCONUS charter split).")
    if not trip.commercial_air:
        notes.append("No commercial air selected — only orders and post-trip deadlines apply.")

    return Plan(deadlines=deadlines, escalation=escalation, notes=notes)


# --- ICS rendering (hand-rolled RFC 5545; all-day events, day-before alarm) ---

def _esc(text: str) -> str:
    return (text.replace("\\", "\\\\").replace(";", r"\;")
                .replace(",", r"\,").replace("\n", r"\n"))


def _fold(line: str) -> str:
    """Fold a content line to <=75 octets per RFC 5545 §3.1.

    Continuation lines start with a single space. Folds on octet boundaries
    without splitting a multi-byte UTF-8 character (labels contain non-ASCII).
    Strict parsers reject over-long lines; lenient ones accept either form.
    """
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    out, first = [], True
    while raw:
        limit = 75 if first else 74  # continuation lines carry a leading space
        chunk = raw[:limit]
        # Don't split inside a UTF-8 sequence: back off to a lead byte.
        while len(chunk) > 1 and (raw[len(chunk):len(chunk) + 1] and
                                  (raw[len(chunk)] & 0xC0) == 0x80):
            chunk = chunk[:-1]
        out.append(chunk.decode("utf-8") if first else " " + chunk.decode("utf-8"))
        raw = raw[len(chunk):]
        first = False
    return "\r\n".join(out)


def to_ics(plan: Plan, trip: TripInputs) -> bytes:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//MIU Travel Bot//planner//EN",
        "CALSCALE:GREGORIAN",
    ]
    for d in plan.deadlines:
        desc = (f"{d.source}. Departure {trip.departure.isoformat()}. "
                "Generated by MIU Travel Bot - verify with your S-1.")
        lines += [
            "BEGIN:VEVENT",
            f"UID:{d.rule_id}-{d.due:%Y%m%d}@miu-travel-bot",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{d.due:%Y%m%d}",
            f"DTEND;VALUE=DATE:{(d.due + timedelta(days=1)):%Y%m%d}",
            f"SUMMARY:{_esc('[MIU travel] ' + d.label)}",
            f"DESCRIPTION:{_esc(desc)}",
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{_esc('Due tomorrow: ' + d.label)}",
            "TRIGGER:-P1D",
            "END:VALARM",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return ("\r\n".join(_fold(l) for l in lines) + "\r\n").encode("utf-8")
