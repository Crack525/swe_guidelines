#!/usr/bin/env python3
"""Check every skill under skills/ for a uniform shape.

Rules:
- every skills/<name>/SKILL.md has YAML frontmatter with `name` equal to the
  folder name, matching ^arch-[a-z0-9-]+$, and a non-empty `description`
  under 1024 characters;
- every `${CLAUDE_SKILL_DIR}/...` reference in a skill body resolves to a file
  or directory that exists in this repository;
- there is exactly one arch-review-<group> skill per lens group and none for
  a group that does not exist;
- arch-review-full names every group's review skill;
- allowed-tools is comma-separated, each entry `Name` or `Name(rule)`, Bash rules
  in the `Bash(cmd:*)` prefix form;
- frontmatter values containing ": " are double-quoted so strict YAML loaders accept them;
- no em-dashes.

Exit status is non-zero on any failure. Standard library only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
LENSES = ROOT / "lenses"
NAME = re.compile(r"^arch-[a-z0-9-]+$")
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
REF = re.compile(r"\$\{CLAUDE_SKILL_DIR\}/([^\s`'\")]+)")
TABLE_ROW = re.compile(r"^\|\s*`([a-z]+)`\s*\|")
TOOL = re.compile(r"^[A-Za-z]+(\([^()]*\))?$")


def frontmatter(text: str, errors: list[str], rel: str) -> dict[str, str]:
    """Parse the flat `key: value` frontmatter strictly enough for any YAML loader.

    A value that contains ": " must be a complete double-quoted string;
    otherwise a strict YAML parser refuses the file.
    """
    m = FRONTMATTER.match(text)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.startswith(" "):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            errors.append(f"{rel}: frontmatter line without a colon: {line!r}")
            continue
        key, value = key.strip(), value.strip()
        if value.startswith('"'):
            if not (value.endswith('"') and len(value) >= 2):
                errors.append(f"{rel}: unterminated quoted value for {key}")
            value = value[1:-1]
        elif ": " in value or value[:1] in ("'", "[", "{", "&", "*", "!", "|", ">", "%", "@", "`"):
            errors.append(f"{rel}: value of {key} must be double-quoted for strict YAML")
        out[key] = value
    return out


def lens_groups() -> set[str]:
    groups = set()
    for line in (LENSES / "README.md").read_text(encoding="utf-8").splitlines():
        m = TABLE_ROW.match(line)
        if m:
            groups.add(m.group(1))
    return groups


def main() -> int:
    errors: list[str] = []
    groups = lens_groups()
    review_groups: set[str] = set()
    skills = sorted(p for p in SKILLS.iterdir() if p.is_dir() and not p.name.startswith("_"))
    for folder in skills:
        skill = folder / "SKILL.md"
        rel = skill.relative_to(ROOT)
        if not skill.exists():
            errors.append(f"{folder.relative_to(ROOT)}: no SKILL.md")
            continue
        text = skill.read_text(encoding="utf-8")
        fm = frontmatter(text, errors, str(rel))
        if not fm:
            errors.append(f"{rel}: missing frontmatter")
            continue
        name = fm.get("name", "")
        if name != folder.name:
            errors.append(f"{rel}: name '{name}' differs from folder '{folder.name}'")
        if not NAME.match(name):
            errors.append(f"{rel}: name '{name}' must match {NAME.pattern}")
        desc = fm.get("description", "")
        if not desc:
            errors.append(f"{rel}: empty description")
        elif len(desc) > 1024:
            errors.append(f"{rel}: description is {len(desc)} characters, limit 1024")
        if "—" in text:
            errors.append(f"{rel}: em-dash")
        tools = fm.get("allowed-tools", "")
        if tools:
            if " " in tools and "," not in tools:
                errors.append(f"{rel}: allowed-tools must be comma-separated")
            for tool in (t.strip() for t in tools.split(",")):
                if not TOOL.match(tool):
                    errors.append(f"{rel}: allowed-tools entry {tool!r} is not Name or Name(rule)")
                if tool.startswith("Bash(") and " *" in tool:
                    errors.append(f"{rel}: use the Bash(cmd:*) prefix form, not {tool!r}")
        for ref in REF.findall(text):
            if "<" in ref:
                continue  # a placeholder such as arch-review-<group>
            target = (folder / ref).resolve()
            if not target.exists():
                errors.append(f"{rel}: reference ${{CLAUDE_SKILL_DIR}}/{ref} does not exist")
        if name.startswith("arch-review-") and name != "arch-review-full":
            group = name.removeprefix("arch-review-")
            if group not in groups:
                errors.append(f"{rel}: no lens group '{group}'")
            elif group in review_groups:
                errors.append(f"{rel}: duplicate review skill for '{group}'")
            review_groups.add(group)
            if f"lenses/{group}.md" not in text:
                errors.append(f"{rel}: does not reference lenses/{group}.md")
    for group in sorted(groups - review_groups):
        errors.append(f"skills/: no arch-review-{group} skill for lens group '{group}'")
    full = SKILLS / "arch-review-full" / "SKILL.md"
    if full.exists():
        text = full.read_text(encoding="utf-8")
        for group in sorted(groups):
            if f"arch-review-{group}" not in text:
                errors.append(f"skills/arch-review-full/SKILL.md: does not name arch-review-{group}")
    else:
        errors.append("skills/arch-review-full/SKILL.md: missing")
    if errors:
        print("\n".join(errors))
        print(f"\n{len(errors)} problem(s) in {len(skills)} skill(s)")
        return 1
    print(f"skills ok: {len(skills)} skills, {len(review_groups)} review groups")
    return 0


if __name__ == "__main__":
    sys.exit(main())
