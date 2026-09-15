---
name: arch-review-full
description: Full architecture review of code or a change against every lens group of the Software Design and Architecture Guidelines, run as seven parallel reviews (om, contracts, context, storage, async, network, delivery) and merged into one report. Use before a pull request or when a change crosses layers.
allowed-tools: Read Grep Glob Agent Bash(git diff *) Bash(git log *) Bash(git status *) Bash(git rev-parse *) Bash(git merge-base *)
---

# arch-review-full

Run every lens group over the same scope, in parallel, and merge the
seven reports into one. Each group is judged by its own reviewer so
that no perspective is diluted by another; this skill only fans out,
collects, and merges.

## Scope

`$ARGUMENTS` names what to review, exactly as the group skills read it:
empty for the current branch against the default branch, a path or
glob, a git ref or range, or `all`. Resolve it once, here, into a
concrete description (the list of files, or the range) and hand the
same description to every reviewer so the seven reports cover the same
ground.

## Procedure

1. Resolve the scope and write it down in one line.
2. Launch seven reviewers at once, one per group, each with the same
   scope line, the group name, and the absolute path of this
   repository's lens catalog and guideline
   (`${CLAUDE_SKILL_DIR}/../../lenses/` with the group's file, and
   `${CLAUDE_SKILL_DIR}/../../architecture.md`). Use the `arch-reviewer`
   agent when it is available; otherwise a general-purpose agent given
   the text of the matching `arch-review-<group>` skill. The groups:
   - `arch-review-om`
   - `arch-review-contracts`
   - `arch-review-context`
   - `arch-review-storage`
   - `arch-review-async`
   - `arch-review-network`
   - `arch-review-delivery`
3. Wait for all seven. A reviewer that fails is re-run once; if it
   fails again, its group is reported as "not reviewed" with the error.
4. Merge:
   - Concatenate all findings and sort by severity (high, medium, low),
     then by file and line.
   - When two groups flag the same `path:line`, keep both lens ids on
     one line; the fix text comes from the higher-severity one.
   - Count applied, passed, findings, and not-applicable lenses across
     groups.
5. Write the merged report below. Then, if the report has any `high`
   finding, say so in one sentence after the report. Nothing else.

Never edit, stage, or commit. This skill reads and reports.

## Report format

```markdown
# Architecture review

**Scope.** <the scope line>
**Groups.** om, contracts, context, storage, async, network, delivery
**Lenses.** <n> applied, <p> passed, <f> findings, <x> not applicable

## Findings

- **<LENS-ID>[, <LENS-ID>] <severity>** `<path>:<line>` <what breaks the rule>. Fix: <one sentence>.

## By group

| Group     | Applied | Passed | Findings | Not applicable |
|-----------|---------|--------|----------|----------------|
| om        |         |        |          |                |
| contracts |         |        |          |                |
| context   |         |        |          |                |
| storage   |         |        |          |                |
| async     |         |        |          |                |
| network   |         |        |          |                |
| delivery  |         |        |          |                |

## Passed

<LENS-ID>, ... (all groups, in id order)

## Not applicable

<LENS-ID> (<why>), ...
```
