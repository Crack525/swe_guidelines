#!/usr/bin/env python3
"""Check that every lens file follows the format in lenses/README.md and cites a real section.

Rules:
- every group listed in lenses/README.md has a file, and every file is listed;
- lens headings are `## <PREFIX>-NN Title`, ids unique and numbered 01.. in order;
- every lens has Principle, Source, Look for, Violation, Severity, in that order;
- Source names a Section that exists in architecture.md, and when it names a
  subsection after the comma, that subsection heading exists under the section;
- Severity is high, medium, or low.

Exit status is non-zero when any rule fails. Standard library only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDELINE = ROOT / "architecture.md"
LENSES = ROOT / "lenses"

FIELDS = ("Principle", "Source", "Look for", "Violation", "Severity")
SEVERITIES = {"high", "medium", "low"}
HEADING = re.compile(r"^## ([A-Z]{2,3})-(\d{2}) (.+)$")
FIELD = re.compile(r"^\*\*(Principle|Source|Look for|Violation|Severity)\.\*\*\s*(.*)$")
SOURCE = re.compile(r"^Section (\d+)(?:,\s*(.+?))?$")
TABLE_ROW = re.compile(r"^\|\s*`([a-z]+)`\s*\|\s*`([a-z]+\.md)`\s*\|")


def sections() -> dict[int, set[str]]:
    """Map section number to the set of its subsection titles."""
    out: dict[int, set[str]] = {}
    current: int | None = None
    for line in GUIDELINE.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^## (\d+)\. ", line)
        if m:
            current = int(m.group(1))
            out[current] = set()
            continue
        m = re.match(r"^### (.+)$", line)
        if m and current is not None:
            out[current].add(m.group(1).strip())
    return out


def listed_groups() -> dict[str, str]:
    groups: dict[str, str] = {}
    for line in (LENSES / "README.md").read_text(encoding="utf-8").splitlines():
        m = TABLE_ROW.match(line)
        if m:
            groups[m.group(1)] = m.group(2)
    return groups


def check_source(
    value: str, path: Path, ln: int, known: dict[int, set[str]], errors: list[str]
) -> None:
    """A source is one or more citations separated by ';', each 'Section N[, Subsection]'."""
    titles = {n: t for n, t in section_titles().items()}
    citations = [c.strip().rstrip(".") for c in value.split(";") if c.strip()]
    if not citations:
        errors.append(f"{path.name}:{ln}: empty source")
        return
    sec: int | None = None
    for citation in citations:
        sm = SOURCE.match(citation)
        if sm:
            sec = int(sm.group(1))
            sub = sm.group(2) or ""
        elif sec is not None:
            sub = citation  # a bare subsection of the previously cited section
        else:
            errors.append(f"{path.name}:{ln}: '{citation}' does not read 'Section N, Subsection'")
            continue
        sub = re.sub(r"\s*\([^)]*\)\s*$", "", sub).strip().rstrip(".")
        if sec not in known:
            errors.append(f"{path.name}:{ln}: Section {sec} does not exist")
        elif sub and sub not in known[sec] and sub != titles.get(sec):
            errors.append(f"{path.name}:{ln}: Section {sec} has no subsection '{sub}'")


def section_titles() -> dict[int, str]:
    out: dict[int, str] = {}
    for line in GUIDELINE.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^## (\d+)\. (.+)$", line)
        if m:
            out[int(m.group(1))] = m.group(2).strip()
    return out


def check_file(path: Path, known: dict[int, set[str]], errors: list[str]) -> int:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    prefix: str | None = None
    expected = 1
    count = 0
    i = 0
    while i < len(lines):
        m = HEADING.match(lines[i])
        if not m:
            i += 1
            continue
        count += 1
        pre, num, _title = m.group(1), int(m.group(2)), m.group(3)
        where = f"{path.name}:{i + 1}"
        if prefix is None:
            prefix = pre
        elif pre != prefix:
            errors.append(f"{where}: prefix {pre} differs from {prefix}")
        if num != expected:
            errors.append(f"{where}: expected id {prefix}-{expected:02d}, found {pre}-{num:02d}")
        expected = num + 1
        # collect fields until next heading
        fields: list[tuple[str, str, int]] = []
        j = i + 1
        while j < len(lines) and not HEADING.match(lines[j]):
            fm = FIELD.match(lines[j])
            if fm:
                fields.append((fm.group(1), fm.group(2).strip(), j + 1))
            elif fields and lines[j].strip() and not lines[j].startswith(("**", "-", "*")):
                # continuation of a wrapped field value
                name, value, ln = fields[-1]
                fields[-1] = (name, f"{value} {lines[j].strip()}".strip(), ln)
            j += 1
        names = [f[0] for f in fields]
        if names != list(FIELDS):
            errors.append(f"{where}: fields are {names}, expected {list(FIELDS)}")
        for name, value, ln in fields:
            if name == "Severity" and value.strip("` ") not in SEVERITIES:
                errors.append(f"{path.name}:{ln}: severity '{value}' is not high, medium, or low")
            if name == "Source":
                check_source(value, path, ln, known, errors)
            if name in ("Principle", "Look for", "Violation") and not value:
                # multi-line field: the text may start on the next line
                pass
        i = j
    if count == 0:
        errors.append(f"{path.name}: no lenses found")
    return count


def main() -> int:
    errors: list[str] = []
    known = sections()
    groups = listed_groups()
    files = {p.name: p for p in LENSES.glob("*.md") if p.name != "README.md"}
    for group, filename in groups.items():
        if filename not in files:
            errors.append(f"lenses/README.md lists {group} -> {filename}, file missing")
    for name in files:
        if name not in groups.values():
            errors.append(f"lenses/{name} is not listed in lenses/README.md")
    total = 0
    for name in sorted(files):
        total += check_file(files[name], known, errors)
    if errors:
        print("\n".join(errors))
        print(f"\n{len(errors)} problem(s) in {len(files)} lens file(s)")
        return 1
    print(f"lenses ok: {total} lenses in {len(files)} groups")
    return 0


if __name__ == "__main__":
    sys.exit(main())
