---
name: arch-scaffold-new
description: "Bootstrap a whole new system in the shape the Software Design and Architecture Guidelines prescribe, into an empty target directory, by building the monorepo skeleton (uv workspace, om, infra, the first API process, a worker, a portal, deployment folders, Makefile, CI) and then following the other scaffold skills for the first namespace and entity. Stack: TypeScript (React, Vite) or Python."
allowed-tools: Read, Grep, Glob, Write, Edit, Bash(make setup), Bash(make check), Bash(make test-unit), Bash(make infra-up), Bash(make migrate), Bash(make test-integration), Bash(make openapi), Bash(uv init:*), Bash(uv sync:*), Bash(uv add:*), Bash(uv run:*), Bash(pnpm install:*), Bash(pnpm run:*), Bash(git init:*), Bash(git status:*), Bash(git diff:*), Bash(git rev-parse:*)
---

# arch-scaffold-new

Conventions: `${CLAUDE_SKILL_DIR}/../_shared/scaffold-conventions.md`.
Sections of `${CLAUDE_SKILL_DIR}/../../architecture.md`: 2 (Naming
Entities), 5 (OpContext, The Operator Context), 8 (Storage Root,
Defining ORM Classes, Translation, Database Roles, Migrations), 9
(InfraInterface Root), 10 (Auth: the Gateway Verifies, the Tenancy
Domain Owns), 13 (Local: Docker Compose, What a Process Refuses), 14
(Monorepo Folder Structure, Layout Conventions), 16 (Exceptions,
Configuration, Records of Decisions).

## Input

`<target-dir> <root-package> [--first <namespace> <Entity> [field:type ...]] [--no-portal] [--no-worker]`

Example: `./acme acme --first inventory Warehouse address:str`. Both
positional arguments are required; ask for them when missing.
`<target-dir>` must not exist, or must be empty; refuse otherwise, and
refuse when a `.git` directory exists in `<target-dir>` or any parent,
because `git init` never runs inside an existing repository.
`<root-package>` must not shadow a standard-library module. In this
skill `<root>` is `<root-package>`.

## Created

Everything below is under `<target-dir>/`.

Skeleton:

| File                                              | Holds                                                                                     |
|---------------------------------------------------|-------------------------------------------------------------------------------------------|
| `pyproject.toml`                                  | `[tool.uv] package = false`, `[tool.uv.workspace] members`, `[tool.uv.sources]`, pytest markers `integration`, `e2e`, `slow` |
| `ruff.toml`, `pyrightconfig.json`, `.python-version` | shared Python lint, format, and type config                                            |
| `package.json`, `pnpm-workspace.yaml`, `.nvmrc` (unless `--no-portal`) | the pnpm workspace over `apps/*` and `packages/*`                    |
| `.gitignore`, `.env.example`                      | ignores; every setting knob documented with its prefix                                    |
| `Makefile`                                        | `setup`, `infra-up`, `infra-down`, `migrate`, `check`, `test-unit`, `test-integration`, `openapi`, self-documented |
| `README.md`                                       | how to set up, run, and check                                                             |
| `docs/architecture.md`                            | a one-page "as built" stub linking to the guideline                                       |
| `docs/adr/0001-root-package.md`                   | the root package decision                                                                 |
| `docs/runbooks/README.md`                         | where runbooks go                                                                         |
| `.github/workflows/ci.yml`                        | runs `make check`, then the integration job over the compose stack                        |
| `deployment/local/docker-compose.yml`             | Postgres, a cache, a queue, an object store                                                |
| `deployment/local/docker-compose.full.yml`        | the same plus the application containers                                                  |
| `deployment/docker/entrypoint.sh`                 | the shared image entrypoint                                                               |
| `deployment/terraform/modules/`, `deployment/terraform/environments/{dev,prod}/` | module and environment stubs with `versions.tf` and `variables.tf` |
| `scripts/dev.sh`                                  | starts every application process on the host                                              |

OM distribution, under `om/`:

| File                                   | Holds                                                                                         |
|----------------------------------------|-----------------------------------------------------------------------------------------------|
| `pyproject.toml`                       | `<root>-om`; `pydantic`, `pydantic-settings`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `uuid-utils` |
| `src/<root>/om/base.py`                | `Platform`, the four mixins, `new_id`, `utcnow`, `EMPTY_UUID`                                  |
| `src/<root>/om/opcontext.py`           | `SecurityContext`, `AppContext`, `OpContext`, `AdminContext`, `Role`, `Permission`, the role-to-permission table, `build_context` |
| `src/<root>/om/exceptions.py`          | `PlatformException` with `http_status` and `code`; `NotFound`, `Conflict`, `ValidationFailed`, `NotAuthorized`, `NotAuthenticated` |
| `src/<root>/om/root.py`                | `build_managers(storage, infra) -> Managers`                                                   |
| `src/<root>/om/storage/root.py`        | `StorageInterface` with `healthcheck` and `close`                                             |
| `src/<root>/om/storage/roles.py`       | `DatabaseRole`, the table-to-role map                                                          |
| `src/<root>/om/storage/tables/base.py` | `Base` deriving the schema from the role map, the mixins with sort-order bands, `GlobalIdentifiableMixin` |
| `src/<root>/om/storage/utils/translation.py` | `to_row`, `to_model`, `apply_row`                                                         |
| `src/<root>/om/storage/impl/pg_base.py`, `postgres.py`, `memory_base.py`, `memory.py` | the Postgres base with `_upsert` and per-statement role routing, the memory base, both roots |
| `src/<root>/om/tenancy/`               | the namespace shape with `Org`, `Identity`, `User`, `Membership`, `Session`, `ApiKey`, its manager (authenticate a credential, issue and exchange tokens), storage impls, tables |
| `migrations/alembic.ini`, `migrations/env.py`, `migrations/sql/core/`, `migrations/versions/core/` | one chain per role, the initial `core` migration |
| `tests/unit/`                          | tenancy on write, the role map, both roots, the tenant-first exceptions list                    |
| `tests/integration/`                   | the migration check and the Postgres round trip                                                |

Infra distribution, under `infra/`:

| File                                        | Holds                                                                                   |
|---------------------------------------------|-----------------------------------------------------------------------------------------|
| `pyproject.toml`                            | `<root>-infra`; `redis`, `aioboto3`, `opentelemetry-sdk`, `prometheus-client`, `truststore` |
| `src/<root>/infra/root.py`                  | `InfraInterface` with `start` and `close`                                                |
| `src/<root>/infra/{cache,buckets,topics,queues,secrets}/` | each: the interface, a memory or local impl, the cloud impl                    |
| `src/<root>/infra/observability.py`, `trust.py` | logging with the request-id filter, tracing, the OS trust store                    |
| `src/<root>/infra/impl/settings.py`, `impl/configured.py`, `impl/local.py` | settings, the configured root that picks impls and refuses unsafe combinations, the all-local root |
| `tests/`                                    | every capability over the local impls                                                    |

## Changed

Nothing; the tree is new. Every later step appends to the files above.

## Procedure

1. Write the skeleton, the OM distribution, and the infra distribution,
   then run `make setup`. The fast gate runs from step 2 on.
2. Read `${CLAUDE_SKILL_DIR}/../arch-scaffold-service/SKILL.md` and
   follow its Created, Changed, and Procedure with these arguments:
   `api --realtime` (omit `--realtime` with `--no-portal`).
3. Unless `--no-worker`, read
   `${CLAUDE_SKILL_DIR}/../arch-scaffold-worker/SKILL.md` and follow
   it with `maintenance NOOP`: a worker whose only work is the
   maintenance sweep, ready for real kinds.
4. Unless `--no-portal`, read
   `${CLAUDE_SKILL_DIR}/../arch-scaffold-app/SKILL.md` and follow it
   with `portal --kind portal`.
5. With `--first`, read
   `${CLAUDE_SKILL_DIR}/../arch-scaffold-namespace/SKILL.md` and follow
   it with `<namespace> <Entity> <field:type ...>`.
6. `make check`; then, when Docker is available, `make infra-up`,
   `make migrate`, and `make test-integration`, only against the
   compose stack of step 1: refuse when the database URL in `.env`
   is not a local address.
7. `git init` in `<target-dir>`, nothing staged.

Stop at the first step whose gate fails and report where it stopped.

## Output

As `${CLAUDE_SKILL_DIR}/../_shared/scaffold-conventions.md` states,
plus one line: the tree is uncommitted, and the first commit is the
user's.
