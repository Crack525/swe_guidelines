# Adopting the guideline in a project

A project that follows the guideline needs three things: the skills,
a visible pointer to the guideline from the project's own
specification folder, and a place to record deviations. Nothing in the
project's `specs/` folder is owned by this repository; the pointer is
one short file the project writes itself.

## 1. Install the skills

Inside Claude Code, once per machine:

```text
/plugin marketplace add baristaze/swe_guidelines
/plugin install swe-guidelines@swe-guidelines
```

Skills are namespaced: `/swe-guidelines:arch-review-full`,
`/swe-guidelines:arch-scaffold-entity`, and so on. The guideline and
the lens catalog travel inside the plugin, so a skill always reads the
version it shipped with. Update with `/plugin marketplace update` and
`/plugin update swe-guidelines`.

For a team that pins versions, add the marketplace from a tag:

```text
/plugin marketplace add https://github.com/baristaze/swe_guidelines.git#v0.1.0
```

## 2. Point at the guideline from `specs/`

Create `specs/architecture.md` in the project with this content and
nothing else that belongs to the guideline:

```markdown
# Architecture

This project follows the Software Design and Architecture Guidelines:
<https://github.com/baristaze/swe_guidelines/blob/v0.1.0/architecture.md>
(pinned at `v0.1.0`).

The guideline is the source of truth for how this system is shaped.
`docs/architecture.md` describes what is implemented; `docs/adr/`
records the decisions that constrain future work, including every
deliberate deviation from the guideline.

## Deviations

| ADR  | Rule                    | Summary                                   |
|------|-------------------------|-------------------------------------------|
| 0001 | Section 14, Layout      | The root package is `acme`, not `platform` |
```

Bump the pinned tag when the project adopts a newer guideline, in a
commit that also re-runs `arch-review-full` on the main branch.

## 3. Record deviations as ADRs

`/swe-guidelines:arch-deviate STO-02 "the ledger needs one transaction
per posting"` writes an ADR in `docs/adr/` in the project's own
numbering, quoting the rule verbatim and naming what the project
accepts in exchange. Review skills treat a deviation recorded this way
as a documented exception when its ADR is cited next to the code.

## 4. Optional: vendor the text

A project that wants the guideline text in its tree without the plugin
(a reader with no Claude Code, an offline build) fetches it at a
pinned tag into a folder it does not edit:

```makefile
GUIDELINE_TAG ?= v0.1.0
GUIDELINE_URL := https://raw.githubusercontent.com/baristaze/swe_guidelines/$(GUIDELINE_TAG)

guidelines-sync:  ## fetch the pinned guideline and lenses into vendor/swe_guidelines/
	mkdir -p vendor/swe_guidelines/lenses
	curl -fsSL $(GUIDELINE_URL)/architecture.md -o vendor/swe_guidelines/architecture.md
	for g in README om contracts context storage async network delivery; do \
	  curl -fsSL $(GUIDELINE_URL)/lenses/$$g.md -o vendor/swe_guidelines/lenses/$$g.md; done
	@echo "synced $(GUIDELINE_TAG)"
```

Commit the vendored copy or ignore it; either way, `specs/` stays the
project's own.

## 5. Optional: project skills without the plugin

Clone this repository next to the project and symlink the skill
folders into `.claude/skills/`:

```bash
git clone https://github.com/baristaze/swe_guidelines ../swe_guidelines
mkdir -p .claude/skills
for s in ../swe_guidelines/skills/arch-*; do ln -s "$(cd "$s" && pwd)" ".claude/skills/$(basename "$s")"; done
```

The skills reference `${CLAUDE_SKILL_DIR}/../../architecture.md`,
which resolves through the symlink to the clone, so keep the clone at
its checkout layout. Skill discovery through symlinked folders is not a
documented Claude Code feature; the plugin route is the supported one.
