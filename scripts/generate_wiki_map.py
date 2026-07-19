#!/usr/bin/env python3
"""Regenerate wiki/_map.md from page frontmatter.

One table row per wiki page: path, type, access, last_reviewed, description.
Run by /lint (and after adding, moving, or removing wiki pages). Exits nonzero
if any frontmatter page is missing a description, so lint can flag it.

The bot's router also reads _map.md as its page catalog, so descriptions are
load-bearing: they are how the model decides which pages answer a question.

Usage:
    python3 scripts/generate_wiki_map.py [--root PATH]   # default: <repo>/wiki
"""
import argparse
import datetime
import glob
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Infra files without frontmatter get fixed rows so the map stays complete.
FALLBACK = {
    "_claims.md": ("registry", "public_release", "Human-readable claims view synchronized with _claims.yml"),
    "_health.md": ("health", "public_release", "Auto-generated wiki health report from /lint"),
    "log.md": ("log", "public_release", "Append-only wiki changelog"),
    "pending-review.md": ("staging", "public_release", "Staging queue for unverified/conflicting ingested claims"),
}

FM_RE = re.compile(r"^---\n(.*?)\n---", re.S)


def fm_value(fm, key):
    m = re.search(r"^%s:\s*(.*)$" % key, fm, re.M)
    return m.group(1).strip().strip('"') if m else ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.path.join(REPO, "wiki"),
                        help="Wiki root directory (default: <repo>/wiki)")
    args = parser.parse_args()
    wiki = os.path.abspath(args.root)
    map_path = os.path.join(wiki, "_map.md")

    rows = []
    missing_desc = []
    for path in sorted(glob.glob(wiki + "/**/*.md", recursive=True)):
        rel = os.path.relpath(path, wiki)
        # Skip: the map itself, symlinks (AGENTS.md), raw originals dir, editor config
        if (os.path.islink(path) or rel == "_map.md"
                or rel.startswith("sources/raw") or rel.startswith(".obsidian")):
            continue
        text = open(path, encoding="utf-8").read()
        m = FM_RE.match(text)
        if m:
            fm = m.group(1)
            ptype = fm_value(fm, "type")
            access = fm_value(fm, "access")
            reviewed = fm_value(fm, "last_reviewed")
            desc = fm_value(fm, "description")
            if not desc:
                missing_desc.append(rel)
        elif rel in FALLBACK:
            ptype, access, desc = FALLBACK[rel]
            reviewed = ""
        else:
            ptype, access, reviewed, desc = "", "", "", ""
            missing_desc.append(rel)
        rows.append((rel, ptype, access, reviewed, desc))

    lines = [
        "# Wiki Map",
        "",
        "Auto-generated page inventory. Do not edit by hand; run",
        "`python3 scripts/generate_wiki_map.py` to regenerate (done by `/lint`).",
        "Descriptions come from each page's `description:` frontmatter and double",
        "as the bot router's page catalog.",
        "",
        "Generated: %s | Pages: %d" % (datetime.date.today().isoformat(), len(rows)),
        "",
        "| Page | Type | Access | Reviewed | Description |",
        "|------|------|--------|----------|-------------|",
    ]
    for rel, ptype, access, reviewed, desc in rows:
        lines.append("| [%s](%s) | %s | %s | %s | %s |" % (rel, rel, ptype, access, reviewed, desc))
    open(map_path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("wrote %s (%d pages)" % (os.path.relpath(map_path, REPO), len(rows)))
    if missing_desc:
        print("pages missing description frontmatter:", ", ".join(missing_desc))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
