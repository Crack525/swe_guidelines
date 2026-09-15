---
name: arch-deviate
description: Record a deliberate deviation from the Software Design and Architecture Guidelines as an architecture decision record (ADR) in the current repository, naming the rule, the reason, and the consequences. Use when a review finding is accepted as intentional or when a project needs to diverge from a section.
allowed-tools: Read Grep Glob Write Bash(git log *) Bash(ls *)
---

# arch-deviate

A project that follows the guideline may still need to diverge from a
rule. The divergence is recorded, not argued about in review threads:
one ADR names the rule, the reason, and what the project accepts in
exchange. Reviews then treat the deviation as a documented exception.

## Input

`$ARGUMENTS` names the rule being deviated from, as a lens id
(`STO-02`), a section (`Section 8, Principles`), or a sentence
describing it, optionally followed by a one-line reason.

## Procedure

1. Resolve the rule: find the lens in `${CLAUDE_SKILL_DIR}/../../lenses/`
   and the section in `${CLAUDE_SKILL_DIR}/../../architecture.md`. Quote
   the principle verbatim.
2. Find the project's ADR folder: `docs/adr/` by convention; otherwise
   ask where ADRs live before writing anything. Number the new record
   as the next in sequence (`NNNN-<slug>.md`).
3. Ask for what is missing, in one message: the reason, the scope of
   the deviation (which namespace, service, or table), and whether it
   is permanent or has a condition for ending.
4. Write the ADR with the template below. Keep it under one page.
5. Print the path of the new file and the one-line summary a reviewer
   should read.

Do not commit. Do not edit the guideline or the lenses; a deviation
belongs to the project, not to the rule.

## ADR template

```markdown
# ADR NNNN: <title that names the deviation>

**Status**: accepted (<date>)

## Rule

<Lens id and section, and the principle quoted verbatim.>

## Deviation

<What the project does instead, in the present tense. Where it applies.>

## Reason

<Why the rule does not fit here. Facts, not preferences.>

## Consequences

<What the project accepts: the guarantee it gives up, the test or check
that stands in for it, the condition under which the deviation ends.>
```
