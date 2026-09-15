---
name: arch-scaffold-entity
description: Add one entity to an existing object-model namespace the way the Software Design and Architecture Guidelines prescribe. Creates the frozen Pydantic type, the table class, the storage interface methods with Postgres and memory impls, the manager operations, the migration, the wire types and router, and the tests. Python only (Pydantic, SQLAlchemy, FastAPI).
allowed-tools: Read Grep Glob Write Edit Bash(make *) Bash(uv run *) Bash(ls *) Bash(git status *) Bash(git diff *)
---

# arch-scaffold-entity

Follow `${CLAUDE_SKILL_DIR}/../_shared/scaffold-conventions.md` first.
Sections that shape this skill: 2 (Naming Entities), 7 (The Business
Layer), 8 (The Storage Layer), 10 (Public Types) of
`${CLAUDE_SKILL_DIR}/../../architecture.md`.

## Input

`$ARGUMENTS`: `<namespace> <EntityName> [field:type ...] [--no-api]`.
Example: `inventory Warehouse address:str timezone:str`. Fields not
given are asked for in one message. The mixins are chosen from the
answer to one question: is the entity long-lived (all four mixins) or
append-only (`Identifiable` alone)?

## Files

Given `<ns>` and `<Entity>` (snake case `<entity>`, plural
`<entities>`), under `om/src/<root>/om/<ns>/`:

| File                                   | Adds                                                                 |
|----------------------------------------|----------------------------------------------------------------------|
| `types/<entity>.py`                    | the frozen entity class, mixins in house-style order                 |
| `storage/__init__.py`                  | `read_<entities>`, `read_<entity>`, `write_<entity>` on the interface |
| `storage/impl/postgres.py`             | the three methods over `_upsert` and `select`, `org_id` on every query |
| `storage/impl/memory.py`               | the same three methods over the in-memory table                      |
| `storage/tables/<entities>.py`         | the table class composing the matching mixins, role in the role map  |
| `manager.py`                           | `list_<entities>`, `get_<entity>`, `create_<entity>`, `update_<entity>`, `delete_<entity>` |
| `impl/manager.py`                      | the five operations: authorize, verify, copy, write                  |
| `om/migrations/sql/<role>/<stamp>_<entities>.up.sql` and `.down.sql`, plus the wrapper | the table |
| `om/tests/unit/test_<entity>_storage.py` | the storage contract, parametrized over both impls, with a cross-tenant negative |
| `om/tests/unit/test_<entity>_manager.py` | the five operations over the memory storage                        |

Unless `--no-api`, under the API service:

| File                     | Adds                                                              |
|--------------------------|-------------------------------------------------------------------|
| `types/<ns>.py`          | `<Entity>View`, `Add<Entity>Request`, `Update<Entity>Request`     |
| `routers/<ns>.py`        | list, get, post, put, delete routes that translate and call the manager |
| `tests/test_<ns>_api.py` | the routes over the in-process app and memory container           |

## Procedure

1. Read the namespace's existing files and copy their conventions.
2. Write the type first, then the table, then storage, then manager,
   then wire types and router, in that order, so each step has its
   dependency in place.
3. The Postgres impl filters `deleted_at IS NULL` on lists and orders
   by `id`; the memory impl does the same. The upsert refuses a row
   from another tenant.
4. The manager's `create_*` takes the whole entity from the caller; the
   router builds it from the request with `new_id()`, `utcnow()`, and
   `ctx.user_id`. `update_*` copies `updated_at`; `delete_*` copies
   `deleted_at` and `deleted_by`.
5. Register the table in the role map and write the migration pair.
6. Run the fast gate and the migration check.

## Output

The file list and command outcomes, as the conventions state.
