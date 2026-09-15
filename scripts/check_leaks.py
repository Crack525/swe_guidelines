#!/usr/bin/env python3
"""Check the published Markdown for vocabulary that must not appear.

The guideline is generic on purpose. Product names, hardware nouns, and
assistant-tooling concepts belong to the projects that use it, never to
the guideline or the lenses. Skills may name the tooling they run on
(the review skills run inside an assistant), so they get a shorter list.

Also refuses em-dashes everywhere and changelog phrasing in the guideline.
Exit status is non-zero on any hit. Standard library only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PRODUCT_TERMS = [
    r"\brodeo\b",
    r"\brobot(s|ic|ics)?\b",
    r"\bbench(es)?\b",
    r"\blabs?\b",
    r"\bhil\b",
    r"\bfirmware\b",
    r"\bsimulat(or|ors|ion|ions|ed)\b",
    r"\bteleoperat\w*\b",
]

ASSISTANT_TERMS = [
    r"\bagents?\b",
    r"\bagentic\b",
    r"\bsub-?agents?\b",
    r"\bLLMs?\b",
    r"\bAI\b",
    r"\bprompts?\b",
    r"\bmodel provider(s)?\b",
    r"\btoken budget(s)?\b",
    r"\bcoding assistant(s)?\b",
    r"\bmachine learning\b",
    r"\bclaude\b",
]

HISTORY_TERMS = [
    r"\bused to\b",
    r"\bpreviously\b",
    r"\bformerly\b",
    r"\bwas considered\b",
    r"\bwere considered\b",
    r"\bset aside\b",
    r"\bsuperseded\b",
    r"\bdeprecated\b",
    r"\bwe changed\b",
    r"\bhas changed\b",
]

EM_DASH = "—"

# file glob -> list of pattern groups that apply
SCOPES: list[tuple[str, list[list[str]]]] = [
    ("architecture.md", [PRODUCT_TERMS, ASSISTANT_TERMS, HISTORY_TERMS]),
    ("lenses/*.md", [PRODUCT_TERMS, ASSISTANT_TERMS]),
    ("skills/*/SKILL.md", [PRODUCT_TERMS]),
    ("skills/*/*.md", [PRODUCT_TERMS]),
    ("README.md", [PRODUCT_TERMS]),
    ("CONTRIBUTING.md", [PRODUCT_TERMS]),
    ("docs/*.md", [PRODUCT_TERMS]),
]

EVERYWHERE = ["*.md", "lenses/*.md", "skills/*/*.md", "skills/*/*/*.md", "docs/*.md", ".github/**/*.md"]


def scan(path: Path, patterns: list[str], label: str, errors: list[str]) -> None:
    compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
    for ln, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        for pat in compiled:
            m = pat.search(line)
            if m:
                errors.append(f"{path.relative_to(ROOT)}:{ln}: {label} term '{m.group(0)}'")


def main() -> int:
    errors: list[str] = []
    seen: set[Path] = set()
    for glob, groups in SCOPES:
        for path in sorted(ROOT.glob(glob)):
            if not path.is_file():
                continue
            for group in groups:
                label = {
                    id(PRODUCT_TERMS): "product",
                    id(ASSISTANT_TERMS): "assistant-tooling",
                    id(HISTORY_TERMS): "history",
                }[id(group)]
                scan(path, group, label, errors)
            seen.add(path)
    for glob in EVERYWHERE:
        for path in sorted(ROOT.glob(glob)):
            if not path.is_file():
                continue
            for ln, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if EM_DASH in line:
                    errors.append(f"{path.relative_to(ROOT)}:{ln}: em-dash")
    if errors:
        print("\n".join(errors))
        print(f"\n{len(errors)} leak(s)")
        return 1
    print(f"leaks ok: {len(seen)} file(s) scanned")
    return 0


if __name__ == "__main__":
    sys.exit(main())
