# Scaffold conventions

Every `arch-scaffold-*` skill follows these conventions. The skill's
own file says only what is specific to what it builds.

## Before writing anything

1. Find the root package. Read the root `pyproject.toml` and the first
   existing distribution under `om/`; the import root is the folder
   under `src/`. Call it `<root>` below. Never assume `platform`.
2. Find the house style. Open one existing namespace, one storage impl,
   one router, and one test, and match their naming, import order, and
   docstring habits exactly. The guideline decides the shape; the
   repository decides the spelling.
3. Read the sections of `architecture.md` the skill names, in full.
4. Confirm the target does not already exist. If it does, stop and say
   so; never overwrite.

## While writing

- Every entity is frozen and composes the mixins it needs in
  house-style order (`Identifiable`, `Named`, `Trackable`,
  `SoftDeletable`); ids come from `new_id()`, timestamps from
  `utcnow()`.
- Every operation takes `ctx: OpContext` first; every storage call
  takes `org_id: UUID` first.
- Every interface is a plain class with `...` method bodies; every impl
  subclasses it; every dependency is a constructor parameter typed by
  interface.
- Two storage impls always: relational and memory, and the same test
  module runs against both.
- Wire types are hand-written `View` and `RequestBody` subclasses;
  routers translate and never decide.
- No em-dashes, no placeholder comments left behind (`TODO`, `...` in
  prose), no dead imports.

## After writing

1. Wire the new pieces into the roots that own them: the storage root,
   the business root, the routers list, the service catalog. A piece
   that exists but is not wired is a bug.
2. Add the migration when a table was added, and the role map entry.
3. Run the repository's fast gate (`make check` or its equivalent). Fix
   what fails. Report what could not be run.
4. Print the list of files created and changed, one per line, followed
   by the commands that were run and their outcome. Nothing else.

Never commit. Scaffolding produces a working tree for a person to
review.
