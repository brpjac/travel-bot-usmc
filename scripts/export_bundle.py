#!/usr/bin/env python3
"""Export the wiki as a self-contained bundle for genai.mil / NIPR laptops.

Outputs (under dist/):
  miu-travel-wiki/            the folder any file-reading agent can be pointed at
  miu-travel-wiki.zip         same, zipped for transfer
  miu-travel-wiki-onefile.md  every page concatenated — the paste/upload form
                              for chat UIs with no file access

Usage:
  python3 scripts/export_bundle.py             # markdown-only bundle
  python3 scripts/export_bundle.py --with-raw  # + committed raw PDFs (never raw/local/)
  python3 scripts/export_bundle.py --full      # onefile also inlines sources/ extracts

Stdlib only. The gitignored distribution boundary (wiki/sources/raw/local/) is
NEVER exported; a marking-string guard scans the output and fails the export
on any hit.
"""

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WIKI = REPO / "wiki"
DIST = REPO / "dist"
BUNDLE = DIST / "miu-travel-wiki"
ONEFILE = DIST / "miu-travel-wiki-onefile.md"
ZIP = DIST / "miu-travel-wiki.zip"

# Never exported, under any flag.
ALWAYS_EXCLUDE = ("sources/raw/local",)
# Excluded from the default bundle.
DEFAULT_EXCLUDE = (".obsidian", "pending-review.md", "sources/raw")

# Built by concatenation so this file never contains the literal phrases and
# cannot trip its own guard (or the lint skill's git-wide grep).
MARKING_STRINGS = (
    "dow" + " community" + " only",
    "fo" + "uo",
    "cui" + "//",
)

AGENTS_HEADER = """\
# MIU Travel Wiki — Agent Entry Point

You are a USMC reserve travel-regulations assistant. **This folder is your
only knowledge source.** Do not answer from outside knowledge; when the folder
doesn't cover something, say "not in the loaded regulations — check with your
S-1."

How to work:

1. Start at `CLAUDE.md` (the master index, reproduced below) and its
   task-routing table.
2. Use `_map.md` to see every page with a description; pick 2-4 pages per
   question and read them fully.
3. Cite claim IDs from `_claims.yml` in brackets, e.g. [C020], and copy
   regulation parentheticals exactly as pages show them, e.g.
   (ForO 3000-52.1, Ch 5, p. 5-6).
4. For exact regulation wording, drill into `sources/` — verbatim transcripts
   of the cited chapters and paragraphs.
5. Claims marked `needs_review` are not settled — say so. JTR-sourced numbers
   come from the Dec 2021 edition; caveat them.

---

"""


def is_excluded(rel: str, with_raw: bool) -> bool:
    for p in ALWAYS_EXCLUDE:
        if rel == p or rel.startswith(p + "/"):
            return True
    for p in DEFAULT_EXCLUDE:
        if p == "sources/raw" and with_raw:
            continue
        if rel == p or rel.startswith(p + "/"):
            return True
    return False


def guard(root: Path) -> list[str]:
    """Scan every exported text file for distribution-marking strings."""
    hits = []
    for f in sorted(root.rglob("*")):
        if not f.is_file() or f.suffix.lower() in (".pdf", ".png", ".zip"):
            continue
        text = f.read_text(encoding="utf-8", errors="ignore").lower()
        for s in MARKING_STRINGS:
            if s in text:
                hits.append(f"{f.relative_to(root)}: contains '{s}'")
    return hits


def fm_and_body(text: str):
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    return (m.group(1), m.group(2)) if m else ("", text)


def build_onefile(full: bool) -> str:
    parts = [AGENTS_HEADER.replace(
        "the master index, reproduced below",
        "the master index, included as the first section below")]
    ordered = []
    # Root pages first, then folders in reading order.
    for name in ("CLAUDE.md", "_claims.md", "_map.md"):
        ordered.append(WIKI / name)
    for folder in ("orders-types", "entitlements", "process", "reference"):
        ordered.extend(sorted((WIKI / folder).glob("*.md")))
    if full:
        ordered.append(WIKI / "sources" / "CLAUDE.md")
        for sub in sorted((WIKI / "sources").iterdir()):
            if sub.is_dir() and sub.name != "raw":
                ordered.extend(sorted(sub.glob("*.md")))
    for f in ordered:
        if not f.is_file() or f.is_symlink():
            continue
        rel = f.relative_to(WIKI)
        _, body = fm_and_body(f.read_text(encoding="utf-8"))
        parts.append(f"\n\n<!-- ===== {rel} ===== -->\n\n{body.strip()}\n")
    return "".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-raw", action="store_true",
                    help="include committed raw PDFs (raw/local/ is never exported)")
    ap.add_argument("--full", action="store_true",
                    help="onefile also inlines sources/ extracts")
    args = ap.parse_args()

    if BUNDLE.exists():
        shutil.rmtree(BUNDLE)
    BUNDLE.mkdir(parents=True)

    copied = 0
    for f in sorted(WIKI.rglob("*")):
        if not f.is_file() or f.is_symlink():
            continue
        rel = str(f.relative_to(WIKI))
        if is_excluded(rel, args.with_raw):
            continue
        dest = BUNDLE / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dest)
        copied += 1

    # Materialize AGENTS.md as a real file: system-prompt header + master index.
    claude_md = (WIKI / "CLAUDE.md").read_text(encoding="utf-8")
    _, index_body = fm_and_body(claude_md)
    (BUNDLE / "AGENTS.md").write_text(AGENTS_HEADER + index_body, encoding="utf-8")

    # Distribution guard — fail the whole export on any hit.
    hits = guard(BUNDLE)
    if hits:
        print("DISTRIBUTION GUARD FAILED — export aborted:")
        for h in hits:
            print("  ", h)
        shutil.rmtree(BUNDLE)
        return 1

    # One-file form.
    onefile = build_onefile(args.full)
    for s in MARKING_STRINGS:
        if s in onefile.lower():
            print(f"DISTRIBUTION GUARD FAILED in onefile: '{s}' — export aborted")
            shutil.rmtree(BUNDLE)
            return 1
    ONEFILE.write_text(onefile, encoding="utf-8")

    # Zip.
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(BUNDLE.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(DIST))

    est_tokens = len(onefile) // 4
    print(f"bundle:  {BUNDLE.relative_to(REPO)}  ({copied} files + AGENTS.md)")
    print(f"zip:     {ZIP.relative_to(REPO)}  ({ZIP.stat().st_size // 1024} KB)")
    print(f"onefile: {ONEFILE.relative_to(REPO)}  ({len(onefile) // 1024} KB, ~{est_tokens:,} tokens)")
    print("distribution guard: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
