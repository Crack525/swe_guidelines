# Changelog

All notable changes to this repository are listed here. Releases are
tagged `vMAJOR.MINOR.PATCH`; see `CONTRIBUTING.md` for what bumps
which number.

## Unreleased

### Added

- `architecture.md`: the Software Design and Architecture Guidelines.
- `architecture.md`: "Technology Choices and How to Override Them",
  a section that says why the guideline names technologies and how a
  project records substitutions in one ADR; lens `DEL-25`;
  `docs/adopting.md` step 3; `arch-scaffold-new` writes
  `docs/adr/0002-technology-choices.md`. Minor.
- `architecture.md`: "Next: An End-to-End Reference Implementation",
  a closing pointer to Tadas (<https://github.com/baristaze/tadas>), a
  to-do app for teams that applies the guideline end to end; linked
  from the introduction. Patch.
- `scripts/check_links.py` checks a link whose text wraps across
  lines; before, a line break hid the anchor from the checker.
- `architecture.md`: a generated table of contents (`make gen-toc`,
  checked by `make toc`) and named anchor links at every
  cross-reference and at the first mention of a concept defined later.
- `skills/arch-new-aspect`: incorporates a new aspect into the
  guideline and cascades it through lenses, skills, docs, README, and
  this changelog.
- `lenses/`: 138 review lenses in seven groups, each citing its
  section by title.
- Skills: `arch-review-<group>` for each group, `arch-review-full`,
  `arch-scaffold-new`, `arch-scaffold-namespace`,
  `arch-scaffold-entity`, `arch-scaffold-service`,
  `arch-scaffold-worker`, `arch-scaffold-app`, `arch-explain`,
  `arch-deviate`.
- `agents/arch-reviewer.md`: the subagent the full review fans out to.
- Plugin and marketplace manifests under `.claude-plugin/`.
- Checkers: markdownlint, lens format and citations, vocabulary leaks,
  links, skill shape, generated-skill freshness; `make check` runs them
  and CI runs `make check`.
- `docs/adopting.md`: how a project adopts the guideline and the
  skills.

### Changed

- Scaffold skills sharpened from their first end-to-end run and the
  full review of what they produced: `arch-scaffold-new` accepts a
  fresh repository as its target, writes `specs/architecture.md`, the
  `events` and `idempotency` namespaces, the migration module, the
  contract-test layout, the Terraform modules and the deploy workflow,
  and states the om/infra workspace dependency and where the role table
  lives; `arch-scaffold-service` declares service interfaces from the
  single-process start, a durable edge idempotency, a server span, a
  boot helper, rate limits from settings, and the `after_seq` replay
  route; `arch-scaffold-worker` gains a container, a `health`
  subcommand, `rules.py`, bounded lease renewal, conditional writes,
  and a per-tenant sweep; `arch-scaffold-app` moves the client package
  to `clients/`, adds the sign-in screen, the lint config, and the
  sequence-gap replay; `arch-scaffold-entity` composes the feed mixin
  variant instead of redeclaring `org_id` and reads the current entity
  before an update. Patch.
- Sections are unnumbered. Every reference in the repository names a
  section by title; `scripts/check_lenses.py` refuses a number. The
  two `Principles` subsections are `Storage Principles` and
  `Infrastructure Principles` so every anchor is unique.
- Every tree diagram in the guideline is a fenced `text` block.
- Root snippets (`StorageInterface`, `ServicesInterface`,
  `InfraInterface`, `Queues`) show two entries and a `# ...` line.
