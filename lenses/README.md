# Lenses

A lens is one rule from `architecture.md`, restated as something a
reviewer can check against code. The review skills load one group of
lenses at a time and judge a change from that perspective only, which
keeps each review narrow enough to be thorough.

## Groups

| Group id    | File            | Covers                                                                                          |
|-------------|-----------------|-------------------------------------------------------------------------------------------------|
| `om`        | `om.md`         | Sections 1 to 3: source of truth, mixins, immutability, identifiers, namespaces, pure rules     |
| `contracts` | `contracts.md`  | Sections 4, 6, 7, 10 (Direction of Calls), 16 (App Container): interfaces, injection, wiring   |
| `context`   | `context.md`    | Sections 5, 6, 7, 8, 10, 11: OpContext, AdminContext, authorization, tenancy, provenance        |
| `storage`   | `storage.md`    | Section 8 and Identifiers: storage principles, tables, translation, roles, migrations           |
| `async`     | `async.md`      | Sections 9, 11, and 10 (idempotency, orchestration): infra, queues, workers, park vs fail       |
| `network`   | `network.md`    | Sections 10 and 12: topology, gateway, public types, clients, realtime, push-first             |
| `delivery`  | `delivery.md`   | Sections 12 to 16: apps, deployment, repo layout, client architecture, cross-cutting conventions |

A rule belongs to exactly one group. Where two groups touch the same
section, the table in each file's header says which side of the line it
takes.

## Lens format

Every lens uses the same shape, so a skill can read any group the same
way:

```markdown
## OM-01 Title of the lens

**Principle.** The rule, in one or two sentences, in the guideline's voice.

**Source.** Section 2, Immutability.

**Look for.** What to inspect: files, signatures, declarations, call sites.

**Violation.** What evidence of a breach looks like, concretely.

**Severity.** high | medium | low
```

Ids are the group prefix plus a two-digit number: `OM`, `CON`, `CTX`,
`STO`, `ASY`, `NET`, `DEL`. Severity is the default weight of a breach:
`high` breaks a boundary or a guarantee, `medium` bends a shape the
guideline relies on, `low` is a convention.

A lens restates the guideline; it never adds a rule the guideline does
not state. When the guideline changes, the lens changes with it, and
`make check` confirms every lens still cites a section that exists.
