---
name: arch-scaffold-new
description: Bootstrap a whole new system in the shape the Software Design and Architecture Guidelines prescribe, by sequencing the other scaffold skills. Creates the monorepo skeleton (uv workspace, om, infra, the first API process, a worker, a portal, deployment folders, Makefile, CI), then the first namespace and entity. Python and TypeScript.
allowed-tools: Read Grep Glob Write Edit Bash(make *) Bash(uv *) Bash(pnpm *) Bash(ls *) Bash(git init *) Bash(git status *) Bash(git diff *)
---

# arch-scaffold-new

Follow `${CLAUDE_SKILL_DIR}/../_shared/scaffold-conventions.md` first.
Sections that shape this skill: 14 (Monorepo Folder Structure), 13
(Deployment), and everything the sequenced skills name, all in
`${CLAUDE_SKILL_DIR}/../../architecture.md`.

## Input

`$ARGUMENTS`: `<root-package> [--first <namespace> <Entity>] [--no-portal] [--no-worker]`.
Example: `acme --first inventory Warehouse`. The root package name is
required and must not shadow a standard-library module.

## Procedure

Run these in order. Each step is the named skill's procedure, applied
in the fresh tree; stop at the first step that fails the fast gate and
report where it stopped.

1. **Skeleton.** Root `pyproject.toml` (uv workspace, `package = false`,
   test markers `integration`, `e2e`, `slow`), `ruff.toml`,
   `pyrightconfig.json`, `.python-version`, `package.json` and
   `pnpm-workspace.yaml` when a portal is wanted, `.nvmrc`, `.gitignore`,
   `.env.example`, `Makefile` with `setup`, `infra-up`, `infra-down`,
   `migrate`, `check`, `test-unit`, `test-integration`, `openapi`,
   `README.md`, `docs/architecture.md` (a one-page "as built" stub that
   links to the guideline), `docs/adr/0001-root-package.md`,
   `.github/workflows/ci.yml` running `make check`,
   `deployment/local/docker-compose.yml` (Postgres, a cache, an object
   store), `deployment/docker/entrypoint.sh`, `deployment/terraform/`
   with `modules/` and `environments/{dev,prod}` stubs.
2. **OM distribution.** `om/` with `base.py` (root class, mixins,
   `new_id`, `utcnow`, `EMPTY_UUID`), `opcontext.py` (`OpContext`,
   `AdminContext`, the role and permission tables), `exceptions.py`
   (root, shape exceptions), `storage/` (root interface, both roots,
   `roles.py`, `tables/base.py` with the mixins and sort-order bands,
   `utils/translation.py`, the Postgres base with `_upsert`, the
   memory base), `root.py` (`build_managers`), `migrations/` (Alembic
   with one chain per role), the `tenancy` namespace with `Org`,
   `User`, `Membership`, `ApiKey`, and unit tests for tenancy on write,
   the role map, and both roots.
3. **Infra distribution.** `infra/` with the root interface, the
   configured root over settings, and for each of cache, buckets,
   topics, queues, secrets: the interface, a memory or local impl, and
   the cloud impl behind a settings switch; `observability.py`;
   `trust.py`; tests over the local impls.
4. **First API process.** As `arch-scaffold-service` with no flags.
5. **Worker.** As `arch-scaffold-worker` for a `default` queue, unless
   `--no-worker`.
6. **Portal.** As `arch-scaffold-app --kind portal`, unless
   `--no-portal`.
7. **First namespace and entity.** As `arch-scaffold-namespace` and
   `arch-scaffold-entity` when `--first` was given.
8. `make setup && make check`, then `make infra-up && make migrate &&
   make test-integration` when Docker is available.

## Output

The tree two levels deep, then the file count, then the commands run
and their outcome. Nothing else.
