---
name: arch-scaffold-new
description: "Bootstrap a whole new system in the shape the Software Design and Architecture Guidelines prescribe, into an empty target directory, by building the monorepo skeleton (uv workspace, om, infra, the first API process, a worker, a portal, deployment folders, Makefile, CI) and then following the other scaffold skills for the first namespace and entity. Stack: TypeScript (React, Vite) or Python."
allowed-tools: Read, Grep, Glob, Write, Edit, Bash(make setup), Bash(make check), Bash(make test-unit), Bash(make infra-up), Bash(make migrate), Bash(make test-integration), Bash(make openapi), Bash(uv init:*), Bash(uv sync:*), Bash(uv add:*), Bash(uv run:*), Bash(pnpm install:*), Bash(pnpm run:*), Bash(git init:*), Bash(git status:*), Bash(git diff:*), Bash(git rev-parse:*)
---

# arch-scaffold-new

Conventions: `${CLAUDE_SKILL_DIR}/../_shared/scaffold-conventions.md`.
Sections of `${CLAUDE_SKILL_DIR}/../../architecture.md`: Naming
Entities, OpContext (The Operator Context), The Storage Layer (Storage
Root, Defining ORM Classes, Translation, Database Roles, Migrations),
Infrastructure (InfraInterface Root), The Network Layer (Auth: the
Gateway Verifies, the Tenancy Domain Owns), Deployment (Local: Docker
Compose, What a Process Refuses), Monorepo Folder Structure (Layout
Conventions), Cross-Cutting Conventions (Exceptions, Configuration,
Records of Decisions), Technology Choices and How to Override Them
(Versions, Overriding a Choice).

## Input

`<target-dir> <root-package> [--first <namespace> <Entity> [field:type ...]] [--no-portal] [--no-worker]`

Example: `./acme acme --first inventory Warehouse address:str`. Both
positional arguments are required; ask for them when missing.
`<target-dir>` must not exist, or must be empty, or be a fresh
repository holding nothing but `.git`, `README.md`, `LICENSE`, and
`.gitignore` (the shape a hosting service creates); refuse otherwise.
In the fresh-repository case `README.md` and `.gitignore` are replaced,
`LICENSE` is kept, and step 7 is skipped. Refuse when a `.git`
directory exists in a parent of `<target-dir>`, because `git init`
never runs inside an existing repository.
`<root-package>` must not shadow a standard-library module. In this
skill `<root>` is `<root-package>`.

## Created

Everything below is under `<target-dir>/`.

Skeleton:

| File                                              | Holds                                                                                     |
|---------------------------------------------------|-------------------------------------------------------------------------------------------|
| `pyproject.toml`                                  | `[tool.uv] package = false`, `[tool.uv.workspace] members` (with a comment citing the root-package ADR by number), `[tool.uv.sources]`, pytest markers `integration`, `e2e`, `slow` |
| `ruff.toml`, `pyrightconfig.json`, `.python-version` | shared Python lint, format, and type config; `.python-version` and `requires-python` name the latest stable Python release |
| `package.json`, `pnpm-workspace.yaml`, `.nvmrc`, `tsconfig.base.json`, `eslint.config.js` (unless `--no-portal`) | the pnpm workspace over `apps/*` and `clients/*`, and the TypeScript and lint config every member extends; `.nvmrc` names the current active Node LTS release and `packageManager` the latest stable pnpm |
| `.gitignore`, `.env.example`                      | ignores; every setting knob documented with its prefix                                    |
| `Makefile`                                        | `setup`, `infra-up`, `infra-down`, `migrate` (every role, `--all`), `migrate-check` (ORM metadata against the migrated schema, per role), `check`, `test-unit`, `test-integration`, `openapi`, self-documented |
| `README.md`                                       | how to set up, run, and check                                                             |
| `docs/architecture.md`                            | a one-page "as built" stub linking to the guideline                                       |
| `specs/architecture.md`                           | the pointer to the guideline pinned at a tag or commit, with empty `Substitutions` and `Deviations` tables, as the guideline's adopting guide (`docs/adopting.md` next to it) shows |
| `docs/adr/0001-root-package.md`                   | the root package decision                                                                 |
| `docs/adr/0002-technology-choices.md`             | the stack as adopted: every technology the guideline names, and per substitution the substitute, the reason, and the rules it must still satisfy |
| `docs/runbooks/README.md`                         | where runbooks go                                                                         |
| `.github/workflows/ci.yml`, `deploy.yml`         | `ci.yml` runs `make check`, then the integration job over the compose stack (`make migrate`, `make migrate-check`, `make test-integration`), `terraform fmt -check` and `validate` per environment, and an image build; `deploy.yml` deploys the smaller environment and promotes its images to production by digest behind an approval gate |
| `deployment/local/docker-compose.yml`             | Postgres, a cache, a queue, an object store, each image tagged at its latest stable release; host ports read from `.env` with non-default values, so a second project on the same machine does not collide |
| `deployment/local/docker-compose.full.yml`        | the same plus the application containers                                                  |
| `deployment/docker/entrypoint.sh`                 | the shared image entrypoint                                                               |
| `deployment/terraform/modules/`, `deployment/terraform/environments/{dev,production}/` | one module per resource the settings name (database, cache, queue, buckets, secrets, service with rollout limits so a worker never exceeds its desired count), wired in both environments; environment names match the settings' cloud-environment set |
| `scripts/dev.sh`                                  | starts every application process on the host                                              |

OM distribution, under `om/`:

| File                                   | Holds                                                                                         |
|----------------------------------------|-----------------------------------------------------------------------------------------------|
| `pyproject.toml`                       | `<root>-om`; `pydantic`, `pydantic-settings`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `uuid-utils`, and `<root>-infra` as a workspace source (`build_managers` takes `InfraInterface`; the two distributions depend on each other and uv accepts that) |
| `src/<root>/om/base.py`                | `Platform`, the four mixins, `new_id`, `utcnow`, `EMPTY_UUID`                                  |
| `src/<root>/om/opcontext.py`           | `SecurityContext` (with `credential_id`, so a socket ticket can re-check the credential behind it), `AppContext`, `OpContext`, `AdminContext`, `build_context`; `Role`, `Permission`, `CredentialKind`, and the role-to-permission table are defined in `tenancy/types/` (the guideline puts the table in the tenancy namespace) and re-exported here, and `tenancy/manager.py` imports the context types under `TYPE_CHECKING`, which is what keeps the import graph acyclic |
| `src/<root>/om/exceptions.py`          | `PlatformException` with `http_status` and `code`; `NotFound`, `Conflict`, `ValidationFailed`, `NotAuthorized`, `NotAuthenticated` |
| `src/<root>/om/root.py`                | `build_managers(storage, infra) -> Managers`                                                   |
| `src/<root>/om/storage/root.py`        | `StorageInterface` with `healthcheck` and `close`                                             |
| `src/<root>/om/storage/roles.py`       | `DatabaseRole`, the table-to-role map                                                          |
| `src/<root>/om/events/`                | the append-only `Event(Identifiable)` with a per-tenant monotonic `seq`, its `activity`-role table, storage with an atomic `append` and `read_after(org_id, after_seq, limit)`, and a manager that records one event per entity write, because every push is also a record |
| `src/<root>/om/idempotency/`           | the edge idempotency record: `core`-role table unique on `(org_id, user_id, key)`, storage, and a manager with `begin` and `finish`, so a replayed creating request dedupes on a durable unique index like every queue handler, and the cache is only a read-through |
| `src/<root>/om/storage/migrate.py`     | `run_sql(role, file)`, the check that a SQL file names only tables of its role, the ORM-versus-schema comparison, and the migration CLI (`upgrade --role <role>` or `--all`, `check`) |
| `src/<root>/om/storage/tables/base.py` | `Base` deriving the schema from the role map, the mixins with sort-order bands, `GlobalIdentifiableMixin`, and the feed variant of the identifiable mixin whose `org_id` carries no single-column index (a feed table composes it instead of redeclaring `org_id`) |
| `src/<root>/om/storage/utils/translation.py` | `to_row`, `to_model`, `apply_row`                                                         |
| `src/<root>/om/storage/impl/pg_base.py`, `postgres.py`, `memory_base.py`, `memory.py` | the Postgres base with `_upsert` and per-statement role routing, the memory base, both roots |
| `src/<root>/om/tenancy/`               | the namespace shape with `Org`, `Identity`, `User`, `Membership`, `Session`, `ApiKey`, its manager (authenticate a credential, issue and exchange tokens, bootstrap the first org and operator and return the owner's context, authenticate an operator, one service context per live tenant for sweeps, issue and atomically redeem the socket ticket, and for every trait an entity composes the operation that exercises it: update a member's role, remove a member, update a user, revoke a session, delete an org on the operator plane), storage impls, tables. An entity composes only the mixins a manager operation exercises |
| `migrations/alembic.ini`, `migrations/env.py`, `migrations/sql/core/`, `migrations/versions/core/` | one chain per role, the initial `core` migration |
| `tests/contracts/`                     | the storage contract cases as plain modules, parameterised by a storage fixture, so the unit suite runs them over memory and the integration suite over Postgres (pytest `--import-mode=importlib`, since two distributions each have a `tests/`) |
| `tests/unit/`                          | tenancy on write, the role map, both roots, the tenant-first exceptions list, the import direction (nothing under the OM or infra imports a service or a worker), the contract cases over memory |
| `tests/integration/`                   | the migration check (ORM metadata against the migrated schema, per role) and the contract cases over Postgres |

Infra distribution, under `infra/`:

| File                                        | Holds                                                                                   |
|---------------------------------------------|-----------------------------------------------------------------------------------------|
| `pyproject.toml`                            | `<root>-infra`; `redis`, `aioboto3`, `opentelemetry-sdk`, `prometheus-client`, `truststore`, and `<root>-om` as a workspace source (payloads extend `Platform`) |
| `src/<root>/infra/root.py`                  | `InfraInterface` with `start` and `close`                                                |
| `src/<root>/infra/{cache,buckets,topics,queues,secrets}/` | each: the interface (with `start()` and `close()`, returning `None` where an impl holds nothing), a memory or local impl that behaves like the hosted one (a queue twin does not deduplicate), the cloud impl translating driver errors into a platform exception and counting outcomes; `topics/` defines `Topics.WORK_AVAILABLE` and `Topics.ENTITY_CHANGED` (entity name, id, action) with their payloads, the two every later step produces or routes |
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
   `api --realtime --container` (omit `--realtime` with `--no-portal`).
3. Unless `--no-worker`, read
   `${CLAUDE_SKILL_DIR}/../arch-scaffold-worker/SKILL.md` and follow
   it with `maintenance NOOP --container`: a worker whose only work is
   the maintenance sweep, ready for real kinds.
4. Unless `--no-portal`, read
   `${CLAUDE_SKILL_DIR}/../arch-scaffold-app/SKILL.md` and follow it
   with `portal --kind portal`.
5. With `--first`, read
   `${CLAUDE_SKILL_DIR}/../arch-scaffold-namespace/SKILL.md` and follow
   it with `<namespace> <Entity> <field:type ...>`.
6. `make check`; then, when Docker is available, `make infra-up`,
   `make migrate`, and `make test-integration`, only against the
   compose stack of step 1: refuse when the effective database URL
   (the environment, `.env`, or the settings default) is not a local
   address.
7. `git init` in `<target-dir>`, nothing staged (skipped when the
   target was a fresh repository).

Stop at the first step whose gate fails and report where it stopped.

## Output

As `${CLAUDE_SKILL_DIR}/../_shared/scaffold-conventions.md` states,
plus one line: the tree is uncommitted, and the first commit is the
user's.
