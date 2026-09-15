#!/usr/bin/env python3
"""Check that every relative Markdown link and image points at a file that exists.

External links (http, https, mailto) are not fetched; CI has no reason to
depend on the network. Anchors are checked only for headings in the same
file. Exit status is non-zero on any broken link. Standard library only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#")
SKIP_DIRS = {".git", "node_modules", ".venv"}


def slug(heading: str) -> str:
    text = re.sub(r"[`*_]", "", heading).strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"\s+", "-", text)


def headings(path: Path) -> set[str]:
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^#{1,6}\s+(.+)$", line)
        if m:
            out.add(slug(m.group(1)))
    return out


def main() -> int:
    errors: list[str] = []
    files = [
        p
        for p in ROOT.rglob("*.md")
        if not any(part in SKIP_DIRS for part in p.parts)
    ]
    for path in sorted(files):
        own = headings(path)
        for ln, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for target in LINK.findall(line):
                if target.startswith(SKIP_PREFIXES[:3]):
                    continue
                if target.startswith("#"):
                    if target[1:] not in own:
                        errors.append(f"{path.relative_to(ROOT)}:{ln}: missing anchor {target}")
                    continue
                file_part, _, anchor = target.partition("#")
                resolved = (path.parent / file_part).resolve()
                if not resolved.exists():
                    errors.append(f"{path.relative_to(ROOT)}:{ln}: missing file {file_part}")
                elif anchor and resolved.suffix == ".md" and anchor not in headings(resolved):
                    errors.append(f"{path.relative_to(ROOT)}:{ln}: missing anchor #{anchor} in {file_part}")
    if errors:
        print("\n".join(errors))
        print(f"\n{len(errors)} broken link(s)")
        return 1
    print(f"links ok: {len(files)} file(s) scanned")
    return 0


if __name__ == "__main__":
    sys.exit(main())
