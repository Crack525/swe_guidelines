---
name: arch-scaffold-namespace
description: Create a new object-model namespace (swimlane) with the shape the Software Design and Architecture Guidelines prescribe: manager interface at the root, types, impl, storage with Postgres and memory impls, tables, rules module, wiring into the storage and business roots, and tests. Python only.
allowed-tools: Read Grep Glob Write Edit Bash(make *) Bash(uv run *) Bash(ls *) Bash(git status *) Bash(git diff *)
---

# arch-scaffold-namespace

Follow `${CLAUDE_SKILL_DIR}/../_shared/scaffold-conventions.md` first.
Sections that shape this skill: 3 (Namespaces as Swimlanes), 4
(Interfaces), 7 (The Business Layer), 8 (Storage Root, Database Roles)
of `${CLAUDE_SKILL_DIR}/../../architecture.md`.

## Input

`$ARGUMENTS`: `<namespace> [FirstEntity] [--role core|activity|queue|admin]`.
Example: `inventory Warehouse`. The role defaults to `core`. When a
first entity is named, this skill ends by invoking the same steps as
`arch-scaffold-entity` for it; when none is named, the namespace is
created empty and ready.

## Files

Under `om/src/<root>/om/<ns>/`:

| File                       | Holds                                                        |
|----------------------------|--------------------------------------------------------------|
| `__init__.py`              | `from .manager import <Ns>ManagerInterface`                  |
| `manager.py`               | the manager interface, empty apart from a docstring          |
| `types/__init__.py`        | empty; one module per entity is added later                  |
| `impl/__init__.py`         | empty                                                        |
| `impl/manager.py`          | `<Ns>ManagerImpl(<Ns>ManagerInterface)` taking the storage   |
| `rules.py`                 | a docstring stating the pure-function contract, no code yet  |
| `storage/__init__.py`      | `<Ns>StorageInterface`, empty apart from a docstring         |
| `storage/impl/postgres.py` | `<Ns>StoragePostgresImpl(PgStorageBase, <Ns>StorageInterface)` |
| `storage/impl/memory.py`   | `<Ns>StorageMemoryImpl(MemoryStorageBase, <Ns>StorageInterface)` |
| `storage/tables/__init__.py` | empty; one module per table is added later                 |

Changed:

| File                              | Change                                                       |
|-----------------------------------|--------------------------------------------------------------|
| `om/.../storage/root.py`          | `get_<ns>_storage()` on `StorageInterface`                   |
| `om/.../storage/impl/postgres.py` | constructs the Postgres impl and returns it from the getter  |
| `om/.../storage/impl/memory.py`   | constructs the memory impl and returns it from the getter    |
| `om/.../root.py`                  | constructs `<Ns>ManagerImpl` and adds a field to `Managers`  |
| `om/.../exceptions.py`            | `<Ns>Exception(PlatformException)` with `code = "<ns>_error"` |
| `om/tests/unit/test_roots.py` (or the existing root test) | the new getter and manager field are present |

## Procedure

1. Read one existing namespace end to end and mirror its file names,
   base classes, and import style.
2. Create the files in the table, then wire the roots.
3. When a first entity was named, continue exactly as
   `arch-scaffold-entity` does for it.
4. Run the fast gate.

## Output

The file list and command outcomes, as the conventions state.
