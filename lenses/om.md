# Object Model

Group id: `om`. Covers Sections 1, 2, and 3 of `architecture.md`: the
domain as the source of truth, naming entities, and namespaces as
swimlanes.

This group judges what the object model is: which classes exist, what
they promise, how they are shaped, and where they live. It leaves the
interface/impl split and constructor injection to `contracts`, the
context types, authorization, and tenancy to `context`, and table
classes, translation, and database roles to `storage`.

## OM-01 One object model, defined once

**Principle.** The domain has one source of truth: a standalone OM
library that every layer depends on and nothing redefines.

**Source.** Section 1, The Domain as the Source of Truth.

**Look for.** Where domain entities are declared; whether services,
workers, and apps import them from the OM package or declare their own
copies; whether the OM is packaged as its own library rather than a
module inside a service.

**Violation.** A second class with the same fields as an OM entity
living in a service, a worker, or a script; a domain noun defined only
in a wire type or a table class; the OM importable only by installing a
service.

**Severity.** high

## OM-02 Wire and table shapes are projections

**Principle.** The OM is the source of truth for entities; the wire
format and the table layout are projections derived from it, and
neither changes the OM to suit itself.

**Source.** Section 1, The Domain as the Source of Truth.

**Look for.** Fields added to an entity that exist only to satisfy a
response shape or a column; entity types imported into the network
layer as the response body itself; storage-only concerns leaking into
entity classes.

**Violation.** An entity gaining a field because a client wanted it in
JSON; an entity carrying a column-oriented attribute such as a raw
foreign key that no manager reads; a route returning an OM entity
directly instead of a view.

**Severity.** medium

## OM-03 The four mixins, with their exact fields

**Principle.** Orthogonal traits are captured by a fixed set of mixins
on a fieldless root: `Identifiable` (`id`), `Named` (`name`),
`Trackable` (`created_at`, `updated_at`, `created_by`), and
`SoftDeletable` (`deleted_at`, `deleted_by`), plus the `new_id()` and
`utcnow()` helpers in the same base module.

**Source.** Section 2, Naming Entities.

**Look for.** The base module of the OM; the fields each mixin
declares; whether entities redeclare a mixin's fields locally; whether
`new_id()` and `utcnow()` are the helpers used to construct entities.

**Violation.** A mixin missing a field or carrying an extra one; an
entity declaring its own `created_at` next to `Trackable`; a root class
that holds fields; a local `datetime.now()` or id factory used in place
of the base helpers.

**Severity.** high

## OM-04 Declaration order reads as a description

**Principle.** Mixins are composed in a fixed order: identity first,
human-facing label next, lifecycle, then cross-cutting traits. The
class signature reads as what the entity promises to be.

**Source.** Section 2, Naming Entities.

**Look for.** The base list of every concrete entity; the order of
`Identifiable`, `Named`, `Trackable`, `SoftDeletable` in it.

**Violation.** `class Warehouse(Trackable, Identifiable, ...)` or any
ordering that departs from identity, label, lifecycle, cross-cutting.

**Severity.** low

## OM-05 Inheritance expresses abstraction, not reuse

**Principle.** Each mixin is a promise about what the entity is. An
entity opts into a trait by adding the mixin and opts out by leaving it
off. Inheritance in the OM is never a way to share code.

**Source.** Section 2, Naming Entities.

**Look for.** Base classes in the OM that carry methods or behavior
rather than a trait; entity-to-entity inheritance; an entity carrying a
mixin whose promise it does not keep.

**Violation.** A `BaseOrder` with helper methods that `Order` and
`ReturnOrder` extend; an entity inheriting `SoftDeletable` although
nothing ever soft-deletes it; a mixin introduced to avoid repeating two
fields that mean different things in different entities.

**Severity.** medium

## OM-06 Append-only records carry identity only

**Principle.** A record that is never updated and never hidden (an
audit entry, a ledger line, an event) is `Identifiable` and nothing
else: no `updated_at`, no `deleted_at`.

**Source.** Section 2, Naming Entities.

**Look for.** Entities whose managers only ever create them; the mixins
those entities compose.

**Violation.** An audit or event entity composed with `Trackable` or
`SoftDeletable`; an `updated_at` on a record no code path updates.

**Severity.** low

## OM-07 The root forbids unknown fields

**Principle.** `extra="forbid"` on the root makes a misspelled field a
construction error instead of a silently ignored key, and every class
on the OM base chain inherits it.

**Source.** Section 2, Naming Entities.

**Look for.** The root's model configuration; any class on the chain
that overrides it to allow or ignore extras.

**Violation.** A root configured to ignore unknown keys; a value object
or context type that relaxes the setting so a caller's typo passes.

**Severity.** medium

## OM-08 Entities, value objects, and read models are distinct

**Principle.** An entity has an identity and is stored. A value object
is a typed piece of an entity with no identity, stored inline with its
owner. A read model is a shape a manager returns that is never written
back. The mixins tell them apart.

**Source.** Section 2, Entities, Value Objects, and Read Models.

**Look for.** Classes on the OM base chain that carry `Identifiable`;
classes returned by managers that are not entities; whether read models
compose mixins or get persisted.

**Violation.** A value object with an `id` and its own table; a read
model composed with `Identifiable` or written by a storage method; an
aggregate answered by inventing a table for it instead of a read model.

**Severity.** medium

## OM-09 Filters and groupings are typed value objects

**Principle.** Typed filter and grouping objects travel through manager
and storage interfaces unchanged, so an aggregation runs in SQL on one
storage impl and in memory on another while the caller writes the same
code.

**Source.** Section 2, Entities, Value Objects, and Read Models.

**Look for.** Parameters of list and aggregate methods on manager and
storage interfaces; whether filtering criteria are typed objects or
loose keyword arguments and strings.

**Violation.** A manager method taking a free-form dict or a raw SQL
fragment as a filter; a storage impl interpreting a string that another
impl interprets differently; filter shapes declared separately for the
manager and the storage.

**Severity.** low

## OM-10 Entities are immutable; updates copy and write

**Principle.** OM entities are frozen snapshots. An update takes the
entity, produces a modified copy, and passes the copy to a write
method. No layer mutates an entity after construction.

**Source.** Section 2, Immutability.

**Look for.** The root's frozen configuration; assignment to entity
attributes anywhere; the update path in managers.

**Violation.** `order.status = ...` in a manager or service; a class on
the chain that unfreezes itself; an update that reaches into a nested
value object to change it in place.

**Severity.** high

## OM-11 Everything on the base chain is frozen, rows excepted

**Principle.** Immutability applies to every object built on the OM
base chain, including context sub-objects and wire types. The one
deliberate exception is the ORM row classes, which never leave the
storage impl.

**Source.** Section 2, Immutability.

**Look for.** Value objects, read models, context types, and wire types
that subclass the root or copy its configuration; where mutable row
objects are returned from.

**Violation.** A value object or wire type declared mutable; a storage
method returning a row object to a manager; an entity constructed by
wrapping a live row.

**Severity.** high

## OM-12 Every id is uuid v7, minted above storage

**Principle.** Every id is a time-ordered `uuid_v7` produced by
`new_id()` by whoever constructs the entity, always above the storage
layer. The database never assigns an id and nothing reads an id back
after a write.

**Source.** Section 2, Identifiers.

**Look for.** Where entity ids are created; the id factory used; any
column default, sequence, or autoincrement producing ids; any write
that returns a generated id.

**Violation.** `uuid4()` used for an entity id; a table with a
server-side id default; a storage method that inserts and returns the
new id; an integer primary key on an entity table.

**Severity.** high

## OM-13 EMPTY_UUID is the system scope and the sentinel

**Principle.** `EMPTY_UUID` is the reserved scope for cross-tenant
reference data on cache and bucket calls, and the sentinel where a
required, indexed reference means "none", keeping the column `NOT NULL`
and the index simple.

**Source.** Section 2, Identifiers.

**Look for.** How platform-owned data is keyed on infra calls; nullable
reference columns that could be required; ad-hoc sentinels.

**Violation.** A second sentinel constant invented for "no project";
platform-owned data cached under a real tenant's id; a nullable
reference column where the guideline's sentinel would keep it required.

**Severity.** low

## OM-14 Namespaces mirror product swimlanes with one shape

**Principle.** The OM is split into namespaces that mirror the
swimlanes of the product, and each has the same internal shape:
`manager.py` re-exported from the package root, `types/`, `impl/`,
`storage/`, and `rules.py` when the namespace has pure rules.

**Source.** Section 3, Namespaces as Swimlanes.

**Look for.** The folder layout of each namespace; where the manager
interface is defined and whether the package root re-exports it; where
entity classes and manager impls live.

**Violation.** A namespace whose interface can only be imported from a
deep path; entity classes next to the manager impl; a namespace that is
a bag of unrelated entities; one concept buried as a sub-folder of
another swimlane.

**Severity.** medium

## OM-15 Business rules are pure functions in one module

**Principle.** The pure part of a namespace's logic (pricing, window
arithmetic, eligibility, aggregation rules) lives in a module of plain
functions that read no storage, consult no clock, and open no
settings. Manager impls and every storage impl call them; nothing
re-implements them.

**Source.** Section 3, Pure Rules.

**Look for.** Arithmetic and eligibility logic inside manager or
storage impls; the same rule implemented twice for two storage
backends; a rules module that imports storage, settings, or a clock.

**Violation.** A relational impl aggregating in SQL and an in-memory
impl aggregating with different arithmetic; a rules function calling
`utcnow()` internally instead of taking the time as an argument; a
pricing rule duplicated in a manager and a report builder.

**Severity.** medium

## OM-16 Cross-cutting namespaces are ordinary namespaces

**Principle.** Tenancy (organizations, users, memberships,
credentials) and audit (who did what, when, from which app) are
first-class swimlanes with their own types, managers, and storage, not
utilities hanging off the root.

**Source.** Section 3, Pure Rules.

**Look for.** Where identity, membership, credential, and audit types
live; whether they have a manager interface and a storage like any other
namespace.

**Violation.** User and organization classes in `base.py` or a `utils`
module; audit rows written by a helper function with no storage
interface; credential handling spread across services with no owning
namespace.

**Severity.** medium
