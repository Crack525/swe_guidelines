# Working in this repository

This repository holds one guideline (`architecture.md`), a lens
catalog derived from it (`lenses/`), Claude Code skills that apply the
lenses (`skills/`), and the checkers that keep the three consistent
(`scripts/`, `Makefile`).

## Layout

- `architecture.md` is the source of truth. Every rule in a lens or a
  skill restates a sentence in it; nothing adds a rule the guideline
  does not state.
- `lenses/<group>.md` holds one group of lenses in the format
  `lenses/README.md` defines. Ids are `<PREFIX>-NN`; every lens cites
  `Section N, Subsection`.
- `skills/arch-review-<group>/SKILL.md` is generated from
  `skills/_template/review.SKILL.md`; edit the template and run
  `make gen-skills`. The other skills are hand-written and share
  `skills/_shared/scaffold-conventions.md`.
- `agents/arch-reviewer.md` is the subagent `arch-review-full` fans out
  to.
- `.claude-plugin/` holds the plugin and marketplace manifests. The
  repository root is the plugin.

## Invariants

- No product, hardware, or assistant-tooling vocabulary in the
  guideline or the lenses (`scripts/check_leaks.py` lists the terms).
- No history in the guideline: it states what we do, in the present
  tense, with no rejected alternatives and no changelog phrasing.
- No em-dashes anywhere.
- Every lens cites a section and subsection that exist.
- Every skill's `name` equals its folder name and starts with `arch-`;
  every `${CLAUDE_SKILL_DIR}/...` reference resolves.
- Exactly one review skill per lens group; `arch-review-full` names all
  of them.

## Validate

```bash
make check                       # everything CI runs
claude plugin validate . --strict   # manifests, skills, agents (when claude is installed)
```

## Conventions

- Wrap prose at about 72 columns in the guideline and the lenses.
- Commit messages: a specific subject line, a short body naming the
  rule that changed and why.
- A change that removes or reverses a rule is a major release; one
  that adds or sharpens a rule is a minor release. Record it in
  `CHANGELOG.md`.
