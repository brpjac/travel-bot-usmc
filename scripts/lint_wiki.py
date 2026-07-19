#!/usr/bin/env python3
"""Wiki health checks — the mechanical core shared by the /lint skill and CI.

Usage:
    python3 scripts/lint_wiki.py                 # CI mode: report to stdout, write nothing
    python3 scripts/lint_wiki.py --write-health  # skill mode: also write wiki/_health.md,
                                                 # regenerate wiki/_map.md, append log.md line
    python3 scripts/lint_wiki.py --json          # machine-readable findings

Exit codes: 0 = pass (WARNs allowed), 1 = one or more FAILs, 2 = crashed.
The semantic discrepancy scan (same number stated differently in prose) is NOT
automated — the /lint skill layers it on top of this script.
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
WIKI = REPO / "wiki"

# Built by concatenation so this file never matches its own guard.
# Twin: scripts/export_bundle.py MARKING_STRINGS — keep in sync.
MARKING_STRINGS = (
    "dow" + " community" + " only",
    "fo" + "uo",
    "cui" + "//",
)

INFRA_NO_FM = {"_map.md", "_claims.md", "_health.md", "log.md", "pending-review.md"}
REQUIRED_FM = ("title", "description", "type", "access", "status", "last_reviewed")
EXTRACT_FM = ("verbatim", "raw_file", "pages_transcribed")
FM_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)
STALE_AFTER_DAYS = 183  # ~6 months


@dataclass
class Finding:
    check: str
    level: str  # "FAIL" | "WARN"
    detail: str


def _tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=REPO, capture_output=True, text=True)
    return [f for f in out.stdout.split("\0") if f]


def _load_pages() -> tuple[dict, list[Finding]]:
    """Parse every wiki page's frontmatter+body. Returns ({rel: (fm, body)}, findings)."""
    findings, pages = [], {}
    for p in sorted(WIKI.rglob("*.md")):
        rel = p.relative_to(WIKI).as_posix()
        if p.is_symlink() or rel.startswith("sources/raw") or rel in INFRA_NO_FM:
            continue
        m = FM_RE.match(p.read_text(encoding="utf-8"))
        if not m:
            findings.append(Finding("frontmatter", "FAIL", f"no frontmatter: {rel}"))
            continue
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError as e:
            findings.append(Finding("frontmatter", "FAIL", f"bad frontmatter yaml in {rel}: {e}"))
            continue
        pages[rel] = (fm, m.group(2))
    return pages, findings


def check_distribution_guard(ctx) -> list[Finding]:
    findings = []
    tracked = ctx["tracked"]
    for f in tracked:
        if f.startswith("wiki/sources/raw/local/") or f.startswith("wiki/internal/"):
            findings.append(Finding("distribution-guard", "FAIL", f"local-only path is git-tracked: {f}"))
    for f in tracked:
        fp = REPO / f
        if not fp.is_file() or fp.suffix.lower() in (".pdf", ".png", ".zip", ".faiss", ".pkl"):
            continue
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        for s in MARKING_STRINGS:
            if s in text:
                findings.append(Finding("distribution-guard", "FAIL", f"{f}: contains marking phrase"))
    return findings


def check_claims_sync(ctx) -> list[Finding]:
    findings = []
    yml_ids = [c["id"] for c in ctx["claims"]]
    md_ids = re.findall(r"^\| (C\d{3,}) \|", (WIKI / "_claims.md").read_text(encoding="utf-8"), re.M)
    if len(yml_ids) != len(set(yml_ids)):
        findings.append(Finding("claims-sync", "FAIL", "duplicate claim ids in _claims.yml"))
    missing_md = set(yml_ids) - set(md_ids)
    extra_md = set(md_ids) - set(yml_ids)
    if missing_md:
        findings.append(Finding("claims-sync", "FAIL", f"in yml but not _claims.md: {sorted(missing_md)}"))
    if extra_md:
        findings.append(Finding("claims-sync", "FAIL", f"in _claims.md but not yml: {sorted(extra_md)}"))
    nums = [int(i[1:]) for i in yml_ids]
    if nums != sorted(nums):
        findings.append(Finding("claims-sync", "WARN", "claim ids not in ascending order in _claims.yml"))
    return findings


def check_source_parity(ctx) -> list[Finding]:
    findings = []
    sources = ctx["sources"]
    src_ids = {s["source_id"] for s in sources}
    for s in sources:
        sub = "local/" if s.get("local_only") else ""
        if not (WIKI / "sources/raw" / (sub + s["filename"])).exists():
            findings.append(Finding("source-parity", "FAIL", f"{s['source_id']}: file missing ({s['filename']})"))
    registered = {s["filename"] for s in sources if not s.get("local_only")}
    for f in (WIKI / "sources/raw").iterdir():
        if f.is_file() and not f.name.startswith(".") and f.name not in registered:
            findings.append(Finding("source-parity", "FAIL", f"unregistered raw file: {f.name}"))
    for rel, (fm, _) in ctx["pages"].items():
        for sid in fm.get("source_ids") or []:
            if sid not in src_ids:
                findings.append(Finding("source-parity", "FAIL", f"{rel}: unknown source id {sid}"))
    for c in ctx["claims"]:
        for sid in c.get("source_ids") or []:
            if sid not in src_ids:
                findings.append(Finding("source-parity", "FAIL", f"{c['id']}: unknown source id {sid}"))
    return findings


def check_orphan_claims(ctx) -> list[Finding]:
    findings = []
    yml_ids = {c["id"] for c in ctx["claims"]}
    for c in ctx["claims"]:
        topic = c.get("topic", "")
        if topic not in ctx["pages"]:
            findings.append(Finding("orphan-claims", "FAIL", f"{c['id']}: topic page missing: {topic}"))
            continue
        fm, body = ctx["pages"][topic]
        if c["id"] not in (fm.get("claim_ids") or []) and f"[{c['id']}]" not in body:
            findings.append(Finding("orphan-claims", "FAIL", f"{c['id']}: not cited by its topic page {topic}"))
    for rel, (fm, _) in ctx["pages"].items():
        for cid in fm.get("claim_ids") or []:
            if cid not in yml_ids:
                findings.append(Finding("orphan-claims", "FAIL", f"{rel}: cites nonexistent claim {cid}"))
    return findings


def check_frontmatter(ctx) -> list[Finding]:
    findings = []
    cutoff = date.today() - timedelta(days=STALE_AFTER_DAYS)
    for rel, (fm, _) in ctx["pages"].items():
        for k in REQUIRED_FM:
            if k not in fm:
                findings.append(Finding("frontmatter", "FAIL", f"{rel}: missing {k}"))
        if fm.get("type") == "source_extract":
            for k in EXTRACT_FM:
                if k not in fm:
                    findings.append(Finding("frontmatter", "FAIL", f"{rel}: extract missing {k}"))
        reviewed = fm.get("last_reviewed")
        if isinstance(reviewed, date) and reviewed < cutoff:
            findings.append(Finding("frontmatter", "WARN", f"{rel}: last_reviewed {reviewed} is >6 months old"))
    return findings


def check_links(ctx) -> list[Finding]:
    findings = []
    inbound = {rel: 0 for rel in ctx["pages"]}
    for rel, (fm, body) in ctx["pages"].items():
        src_dir = (WIKI / rel).parent
        for target in re.findall(r"\]\(([^)#\s]+\.md)\)", body):
            t = (src_dir / target).resolve()
            if not t.exists():
                findings.append(Finding("links", "FAIL", f"{rel}: broken link -> {target}"))
            else:
                try:
                    trel = t.relative_to(WIKI.resolve()).as_posix()
                except ValueError:
                    continue
                if trel in inbound:
                    inbound[trel] += 1
    for rel, (fm, _) in ctx["pages"].items():
        if (fm.get("type") not in ("index", "schema") and not rel.endswith("CLAUDE.md")
                and inbound.get(rel, 0) == 0):
            findings.append(Finding("links", "FAIL", f"orphan page (no inbound links): {rel}"))
    return findings


def check_extract_raw_files(ctx) -> list[Finding]:
    findings = []
    for rel, (fm, _) in ctx["pages"].items():
        if fm.get("type") == "source_extract":
            raw = ((WIKI / rel).parent / str(fm.get("raw_file", ""))).resolve()
            if not raw.exists():
                findings.append(Finding("extracts", "FAIL", f"{rel}: raw_file does not resolve"))
    return findings


def check_timelines(ctx) -> list[Finding]:
    findings = []
    tl_path = WIKI / "reference" / "timelines.yml"
    if not tl_path.exists():
        return [Finding("timelines", "WARN", "wiki/reference/timelines.yml not found")]
    data = yaml.safe_load(tl_path.read_text(encoding="utf-8")) or {}
    claims = {c["id"]: c for c in ctx["claims"]}
    for rule in data.get("rules", []):
        cid = rule.get("claim_id")
        c = claims.get(cid)
        if not c:
            findings.append(Finding("timelines", "FAIL", f"{rule.get('id')}: unknown claim {cid}"))
            continue
        if c.get("status") != "active":
            findings.append(Finding("timelines", "FAIL", f"{rule.get('id')}: claim {cid} is {c.get('status')}, not active"))
        offset = abs(int(rule.get("offset_days", 0)))
        claim_text = c.get("claim", "")
        forms = [str(offset)]
        if offset % 7 == 0:
            forms.append(f"{offset // 7} week")  # "2 weeks", "3 weeks"
        if not any(f in claim_text for f in forms):
            findings.append(Finding("timelines", "WARN",
                                    f"{rule.get('id')}: offset {offset} not found in {cid}'s claim text"))
    for key in ("g35_claim_id", "cos_claim_id", "cancel_claim_id"):
        cid = (data.get("escalation") or {}).get(key)
        if cid and cid not in claims:
            findings.append(Finding("timelines", "FAIL", f"escalation.{key}: unknown claim {cid}"))
    return findings


def check_map_current(ctx) -> list[Finding]:
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "generate_wiki_map.py"), "--check"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return [Finding("map", "FAIL", (r.stdout + r.stderr).strip()[:400])]
    return []


CHECKS = [
    ("distribution-guard", check_distribution_guard),
    ("claims-sync", check_claims_sync),
    ("source-parity", check_source_parity),
    ("orphan-claims", check_orphan_claims),
    ("frontmatter", check_frontmatter),
    ("links", check_links),
    ("extracts", check_extract_raw_files),
    ("timelines", check_timelines),
    ("map", check_map_current),
]


def render_health_md(findings: list[Finding], stats: dict) -> str:
    by_check: dict[str, list[Finding]] = {}
    for f in findings:
        by_check.setdefault(f.check, []).append(f)
    lines = [
        "# Wiki Health", "",
        "Auto-generated by `scripts/lint_wiki.py --write-health`. Do not edit by hand.",
        "", f"**Run: {date.today().isoformat()}**", "",
        "| Check | Result |", "|---|---|",
    ]
    for name, _ in CHECKS:
        fs = by_check.get(name, [])
        fails = [f for f in fs if f.level == "FAIL"]
        warns = [f for f in fs if f.level == "WARN"]
        if fails:
            lines.append(f"| {name} | FAIL — {len(fails)} finding(s) |")
        elif warns:
            lines.append(f"| {name} | WARN — {len(warns)} finding(s) |")
        else:
            lines.append(f"| {name} | PASS |")
    lines += ["", f"Pages: {stats['pages']} · Claims: {stats['claims']} · Sources: {stats['sources']}", ""]
    if findings:
        lines.append("## Findings")
        for f in findings:
            lines.append(f"- **{f.level}** [{f.check}] {f.detail}")
        lines.append("")
    lines.append("_Semantic discrepancy scan (same number stated two ways in prose) is not"
                 " automated — run `/lint` for the full pass._")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-health", action="store_true",
                    help="write wiki/_health.md, regenerate _map.md, append log.md line")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    pages, findings = _load_pages()
    ctx = {
        "pages": pages,
        "claims": yaml.safe_load((WIKI / "_claims.yml").read_text(encoding="utf-8"))["claims"],
        "sources": yaml.safe_load((WIKI / "_sources.yml").read_text(encoding="utf-8"))["sources"],
        "tracked": _tracked_files(),
    }
    for name, fn in CHECKS:
        try:
            findings.extend(fn(ctx))
        except Exception as e:  # a crashed check is itself a failure
            findings.append(Finding(name, "FAIL", f"check crashed: {e}"))

    stats = {"pages": len(pages), "claims": len(ctx["claims"]), "sources": len(ctx["sources"])}
    fails = [f for f in findings if f.level == "FAIL"]

    if args.json:
        print(json.dumps({"stats": stats, "findings": [asdict(f) for f in findings]}, indent=2))
    else:
        guard_fails = [f for f in fails if f.check == "distribution-guard"]
        for f in guard_fails:
            print(f"DISTRIBUTION GUARD FAILED: {f.detail}")
        for f in findings:
            if f not in guard_fails:
                print(f"{f.level:4} [{f.check}] {f.detail}")
        print(f"\npages: {stats['pages']} | claims: {stats['claims']} | sources: {stats['sources']} | "
              f"FAIL: {len(fails)} | WARN: {len(findings) - len(fails)}")
        if not findings:
            print("ALL CHECKS PASS")

    if args.write_health:
        subprocess.run([sys.executable, str(REPO / "scripts" / "generate_wiki_map.py")],
                       capture_output=True)
        (WIKI / "_health.md").write_text(render_health_md(findings, stats), encoding="utf-8")
        with open(WIKI / "log.md", "a", encoding="utf-8") as f:
            f.write(f"[{date.today().isoformat()}] LINT: {len(fails)} FAIL / "
                    f"{len(findings) - len(fails)} WARN across {len(CHECKS)} checks (lint_wiki.py).\n")

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
