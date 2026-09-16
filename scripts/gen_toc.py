#!/usr/bin/env python3
"""Generate the table of contents of architecture.md from its headings.

The table sits between `<!-- toc -->` and `<!-- /toc -->` under the
`## Contents` heading: one entry per section (`##`) with its subsections
(`###`) nested under it, each a link to the heading's anchor. Headings
inside fenced code are ignored. Anchors follow the slug rule
scripts/check_links.py uses, so every link the table emits is one that
checker accepts.

`--check` exits non-zero when the table on disk differs from what the
headings produce. Standard library only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDELINE = ROOT / "architecture.md"
START, END = "<!-- toc -->", "<!-- /toc -->"
SKIP = {"Contents"}


def slug(heading: str) -> str:
    text = re.sub(r"[`*_]", "", heading).strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"\s+", "-", text)


def headings(text: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    in_fence = False
    for line in text.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r"^(##|###) (.+)$", line)
        if m:
            out.append((len(m.group(1)), m.group(2).strip()))
    return out


def render(text: str) -> str:
    lines: list[str] = []
    seen: dict[str, int] = {}
    for level, title in headings(text):
        if level == 2 and title in SKIP:
            continue
        anchor = slug(title)
        n = seen.get(anchor, 0)
        seen[anchor] = n + 1
        if n:
            anchor = f"{anchor}-{n}"
        indent = "" if level == 2 else "  "
        lines.append(f"{indent}- [{title}](#{anchor})")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    text = GUIDELINE.read_text(encoding="utf-8")
    if START not in text or END not in text:
        print(f"architecture.md: no {START} ... {END} block")
        return 1
    head, rest = text.split(START, 1)
    _old, tail = rest.split(END, 1)
    new = f"{head}{START}\n{render(text)}\n{END}{tail}"
    if new == text:
        print("toc ok")
        return 0
    if "--check" in argv:
        print("architecture.md: table of contents is stale (run `make gen-toc`)")
        return 1
    GUIDELINE.write_text(new, encoding="utf-8")
    print("toc: regenerated")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
