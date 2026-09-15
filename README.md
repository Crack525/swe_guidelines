# Software Design and Architecture Guidelines

An opinionated guideline for building multi-tenant, service-based
systems in Python, plus the tooling that makes it checkable: a catalog
of review lenses derived from the guideline and a set of Claude Code
skills that review code through those lenses or scaffold new pieces in
the prescribed shape.

- **[`architecture.md`](architecture.md)**: the guideline. Sixteen
  sections, from the object model at the center to deployment at the
  edge. Read it once end to end; it is written to be read that way.
- **[`lenses/`](lenses/README.md)**: 137 lenses in seven groups. Each
  restates one rule as something a reviewer can check against code and
  cites the section it comes from.
- **[`skills/`](skills/)**: Claude Code skills. Seven group reviews, one
  full review that runs them in parallel, six scaffolds, an explainer,
  and a deviation recorder.

## Install the skills

The repository is a Claude Code plugin marketplace. Inside Claude Code:

```text
/plugin marketplace add baristaze/swe_guidelines
/plugin install swe-guidelines@swe-guidelines
```

Skills then appear as `/swe-guidelines:arch-review-full` and so on. To
try a checkout without installing:

```bash
claude --plugin-dir /path/to/swe_guidelines
```

Non-plugin use, version pinning, and the pointer file a project keeps
in its own `specs/` folder are in [`docs/adopting.md`](docs/adopting.md).

## The skills

| Skill                     | What it does                                                                 |
|---------------------------|------------------------------------------------------------------------------|
| `arch-review-full`        | Reviews a change through every lens group, seven reviewers in parallel, one merged report |
| `arch-review-om`          | Object model: source of truth, mixins, immutability, identifiers, namespaces |
| `arch-review-contracts`   | Interfaces, injection, roots, call direction, app container                  |
| `arch-review-context`     | OpContext, AdminContext, authorization, tenancy, provenance                  |
| `arch-review-storage`     | Storage principles, tables, translation, database roles, migrations          |
| `arch-review-async`       | Infra capabilities, queues, workers, idempotency, park versus fail           |
| `arch-review-network`     | Topology, gateway, public types, clients, realtime, push-first               |
| `arch-review-delivery`    | Apps, deployment, repo layout, client architecture, cross-cutting conventions |
| `arch-scaffold-new`       | Bootstraps a whole system by sequencing the scaffolds below                  |
| `arch-scaffold-namespace` | A new object-model swimlane, wired into the roots                            |
| `arch-scaffold-entity`    | One entity end to end: type, table, storage, manager, migration, API, tests  |
| `arch-scaffold-service`   | A web service: container, gateway, routers, wire types, ops CLI, image       |
| `arch-scaffold-worker`    | A worker role over the table-backed work queue                               |
| `arch-scaffold-app`       | A browser app, an operator console, or a CLI                                 |
| `arch-explain`            | Answers a question about the architecture with citations                     |
| `arch-deviate`            | Records a deliberate deviation as an ADR in the consuming project            |

Every review skill takes the same argument (empty for the current
branch, a path, a git range, or `all`). The seven group skills produce
the same report shape, so their reports merge cleanly; the full review
adds a per-group table. The review skills read and report; they never
edit. The scaffold skills write into the working tree and never commit.
The subagent tool the full review fans out with is called `Agent` in
Claude Code 2.1 and later.

## Develop

```bash
make check        # markdownlint, lens format and citations, vocabulary leaks, links, skill shape
make gen-skills   # regenerate the seven group review skills from the template
```

Requirements: Python 3.12 or newer, Node 22 or newer. `make lint`
fetches `markdownlint-cli2` through `npx` at a pinned version. CI runs
`make check` on every pull request.

The review skills are generated from `skills/_template/review.SKILL.md`
and the lens catalog. Edit the template or the lenses, not the
generated files. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

MIT. See [`LICENSE`](LICENSE).
