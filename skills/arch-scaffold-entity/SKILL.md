---
name: arch-scaffold-entity
description: "Add one entity to an existing object-model namespace the way the Software Design and Architecture Guidelines prescribe: the frozen Pydantic type, the table class and migration, storage interface methods with Postgres and memory impls, manager operations, wire types and router, and tests. Stack: Python (FastAPI, Pydantic, SQLAlchemy)."
allowed-tools: Read, Grep, Glob, Write, Edit, Bash(make check), Bash(make test-unit), Bash(make openapi), Bash(uv run:*), Bash(git status:*), Bash(git diff:*)
---

# arch-scaffold-entity

Conventions: `${CLAUDE_SKILL_DIR}/../_shared/scaffold-conventions.md`.
Sections of `${CLAUDE_SKILL_DIR}/../../architecture.md`: Naming
Entities (Identifiers), The Business Layer (Shape of an Operation), The
Storage Layer (Namespace Shape, Defining ORM Classes, A Storage Impl,
Database Roles, Migrations), The Network Layer (Public Types).

## Input

`<namespace> <EntityName> [field:type ...] [--role core|activity|queue|admin] [--no-api]`

Example: `inventory Warehouse address:str timezone:str`. The role
defaults to `core`. Ask in one message for the fields not given and
for the mixins: `Named`? `Trackable`? `SoftDeletable`? The answer
"append-only" means `Identifiable` alone.

`<entity>` is the snake-case name, `<entities>` its plural, `<ns>` the
namespace, `<role>` the role, `<stamp>` the minute stamp
`YYYYMMDDHHMM` of the moment the migration is written.

## Created

| File                                                         | Holds                                                                  |
|--------------------------------------------------------------|------------------------------------------------------------------------|
| `om/src/<root>/om/<ns>/types/<entity>.py`                     | the frozen entity, mixins in house-style order                          |
| `om/src/<root>/om/<ns>/storage/tables/<entities>.py`          | the table class composing the matching mixins; the `(org_id, id)` index when the entity is a feed |
| `om/migrations/sql/<role>/<stamp>_<entities>.up.sql`          | `CREATE TABLE <role>.<entities>` with the mixin header block first    |
| `om/migrations/sql/<role>/<stamp>_<entities>.down.sql`        | the matching `DROP TABLE`                                              |
| `om/migrations/versions/<role>/<stamp>_<entities>.py`         | the wrapper: `revision = "<stamp>"`, `down_revision` = the role's current head, `run_sql(<role>, ...)` |
| `om/tests/unit/test_<entity>_storage.py`                      | the storage contract over the memory impl, with a cross-tenant negative |
| `om/tests/integration/test_<entity>_storage_postgres.py`      | the same cases over Postgres, marked `integration`                    |
| `om/tests/unit/test_<entity>_manager.py`                      | the five operations over the memory storage                            |
| `<api>/tests/test_<ns>_<entity>_api.py` (unless `--no-api`)   | the routes over the in-process app and memory container                |

`<api>` is the service whose `--namespaces` includes `<ns>`, else
`services/api`, else the API rows are skipped with a note.

## Changed

| File                                                   | Change                                                                         |
|--------------------------------------------------------|--------------------------------------------------------------------------------|
| `om/src/<root>/om/<ns>/storage/__init__.py`             | `read_<entities>(org_id, limit)`, `read_<entity>(org_id, <entity>_id)`, `write_<entity>(org_id, <entity>)` on the interface |
| `om/src/<root>/om/<ns>/storage/impl/postgres.py`        | the three methods over `_upsert` and `select`, ordered by `id`                |
| `om/src/<root>/om/<ns>/storage/impl/memory.py`          | the same three methods over the in-memory table                                |
| `om/src/<root>/om/storage/roles.py`                     | `"<entities>": DatabaseRole.<ROLE>` in the table-to-role map                   |
| `om/src/<root>/om/<ns>/manager.py`                      | `get_<entities>(ctx, limit)`, `get_<entity>`, `create_<entity>`, `update_<entity>`, `delete_<entity>` |
| `om/src/<root>/om/<ns>/impl/manager.py`                 | the five operations: authorize, verify, copy, write, return the copy           |
| `om/src/<root>/om/exceptions.py` (when a leaf is needed) | `class <Ns>Exception(PlatformException): ...` once, then leaves that multiply-inherit a shape |
| `<api>/.../types/<ns>.py` (unless `--no-api`)           | `<Entity>View`, `Add<Entity>Request`, `Update<Entity>Request`                  |
| `<api>/.../routers/<ns>.py` (unless `--no-api`)         | list (with `limit`), get, post, put, delete routes that translate and call the manager |
| `<api>/.../routers/__init__.py` (when `<ns>` is new to it) | the router added to `all_routers()`                                       |

## Procedure

1. Write the type, then the table, then storage, then manager, then
   wire types and router, in that order, so each step has its
   dependency in place.
2. Lists filter `deleted_at IS NULL` only when the entity is
   `SoftDeletable`, in both impls.
3. The router builds the entity for `create_<entity>` from the request
   with `new_id()`, `utcnow()`, and `ctx.user_id`; `update_<entity>`
   copies `updated_at`; `delete_<entity>` copies `deleted_at` and
   `deleted_by` when the entity is `SoftDeletable` and otherwise
   deletes the row through storage.
4. Run the migration check for `<role>` after the fast gate.

## Output

As `${CLAUDE_SKILL_DIR}/../_shared/scaffold-conventions.md` states.
