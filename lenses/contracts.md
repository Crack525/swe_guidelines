# Contracts

Group id: `contracts`. Covers Section 4 (Interfaces), Section 6
(Separation of Layers), Section 7 (The Business Layer), Section 10
(Service Interfaces and Impls; Direction of Calls), and Section 16 (The
App Container) of `architecture.md`.

This group judges how the pieces of the system are declared, wired, and
allowed to call each other: interfaces and their impls, constructor
injection, the roots that assemble everything at boot, and the
direction calls may flow across layers. It leaves the shape of entities
and mixins to `om`, everything about `OpContext`, authorization, and
tenancy to `context`, the internals of tables, translation, and
migrations to `storage`, the semantics of each infra capability to
`async`, and the gateway, public types, and realtime channel to
`network`.

## CON-01 Every layer is defined by an interface

**Principle.** A manager, a storage, a service: each exposes a
`*Interface` that lists the operations its scope supports. An operation
is an async method whose signature is a contract.

**Source.** Section 4, Interfaces.

**Look for.** Every manager, storage, and service class; the module a
consumer imports from; the type of every dependency a constructor
accepts.

**Violation.** A manager, storage, or service exists only as a concrete
class with no `*Interface` declared; a caller imports a concrete class
where an interface should stand; an operation is declared as a
synchronous method on an interface that describes I/O.

**Severity.** high

## CON-02 Interfaces are plain classes with empty bodies, impls subclass them

**Principle.** An interface is a plain class whose methods have `...`
bodies, and an impl subclasses it. That is enough for the type checker
to hold every impl to the signature, and it keeps the interface readable
as documentation.

**Source.** Section 4, Interfaces.

**Look for.** Interface declarations; the base list of every impl
class; method bodies inside interface classes.

**Violation.** An interface method carries logic, defaults, or side
effects; an impl does not subclass the interface it claims to
implement; an impl adds public methods the interface does not declare
and callers use them.

**Severity.** medium

## CON-03 Multiple impls, technology named last

**Principle.** An interface usually has more than one impl, and they are
interchangeable at wiring time. Names put the technology last:
`WarehouseStoragePostgresImpl`, `WarehouseStorageMemoryImpl`.

**Source.** Section 4, Multiple impls per interface.

**Look for.** Impl class names under `impl/` folders; the set of impls
behind each storage and infra interface.

**Violation.** An impl name leads with the technology or omits `Impl`;
an interface has one impl and its callers depend on details of that
impl; a technology-specific name leaks into an interface or a caller.

**Severity.** low

## CON-04 The in-memory impl is a full implementation

**Principle.** The in-memory impl is a full second implementation, not a
stub: every read, write, filter, and tenancy rule the relational impl
has, the memory impl has too, and the test suite runs both.

**Source.** Section 4, Multiple impls per interface.

**Look for.** The memory impl of every storage interface; the test
fixtures that select an impl; parametrized tests that run against both.

**Violation.** A memory impl raises `NotImplementedError` or returns
empty results for an operation the relational impl supports; a filter
or ordering rule exists only in one impl; the test suite runs storage
tests against one impl only.

**Severity.** medium

## CON-05 Decoration composes impls behind one interface

**Principle.** Because an impl depends on an interface, impls compose:
a wrapper holds an inner impl of the same interface and forwards
selectively. Decoration is an infrastructure pattern; a manager that
needs a cache takes one through its constructor rather than wrapping
its storage.

**Source.** Section 4, Composition by decoration.

**Look for.** Wrapper classes for caching, retry, metrics, and tracing;
how a manager obtains caching.

**Violation.** A wrapper exposes a different interface than the impl it
wraps; a manager wraps its storage in a caching decorator instead of
taking a `CacheInterface`; a caller can tell which layer of a composite
answered.

**Severity.** low

## CON-06 Dependencies are injected through constructors, typed by interface

**Principle.** Dependencies are passed into impls through the
constructor and typed by interface, never by impl.

**Source.** Section 4, Injectability.

**Look for.** Constructor signatures of every impl; type annotations of
stored dependencies; any construction of a dependency inside a method.

**Violation.** A constructor parameter is annotated with a concrete impl
class or `Any`; an impl instantiates its own storage, cache, or peer
manager; a dependency is fetched from a module-level global, a
registry, or a service locator at call time.

**Severity.** high

## CON-07 Tunables arrive as an options object

**Principle.** A manager that has tunables takes a small frozen options
object in its constructor, built once at boot from settings. Managers
never read environment variables.

**Source.** Section 4, Injectability.

**Look for.** Reads of environment variables or settings objects inside
manager, storage, or service impls; numeric or duration constants that
vary by environment.

**Violation.** An impl calls the environment or a settings loader
directly; a tunable is a hard-coded constant that differs between
deployments; an options object is mutable or is rebuilt per call.

**Severity.** medium

## CON-08 Cycles are broken above the managers

**Principle.** When two managers genuinely need each other, the cycle is
broken above them: extract the shared operation into the lower
namespace, or pass a narrow callable for the one operation the upper
manager needs. Reaching into another impl's private attributes after
construction is not wiring.

**Source.** Section 4, Injectability.

**Look for.** The business root's wiring code; assignments to another
object's underscore-prefixed attributes; constructor parameters with a
`None` default that are filled in later.

**Violation.** The root sets `manager._peer = other` after construction;
a dependency is typed optional only to dodge an import cycle; two
namespaces import each other's impls.

**Severity.** high

## CON-09 Roots wire everything at boot

**Principle.** A root class constructs the concrete impls in the right
order and wires them together. The storage root, the infra root, the
business root, and the services root each expose one getter per member,
and the business root hands back one frozen object with a field per
manager.

**Source.** Section 7, The Business Layer; Section 4, Injectability.

**Look for.** The root modules of storage, infra, business, and
services; where impls are instantiated; whether the returned object is
frozen.

**Violation.** An impl is constructed outside a root; a root exposes a
concrete impl type instead of an interface; the business root returns a
mutable container or a dict; wiring is spread across request handlers.

**Severity.** medium

## CON-10 Upper layers depend on lower layers through interfaces only

**Principle.** Three layers: Network, Business, Storage. Upper layers
depend on interfaces exposed by lower layers, never on their internals.

**Source.** Section 6, Separation of Layers.

**Look for.** Import graph across the network, business, and storage
packages; what a router imports from a storage package; what a manager
imports from a storage impl.

**Violation.** A router imports a table class or a storage impl; a
manager imports from `storage/impl/` or `storage/tables/`; a service
reads a session or connection object from a storage impl.

**Severity.** high

## CON-11 Infrastructure never leaks a technology across a boundary

**Principle.** The infrastructure layer may be blended into any layer
where necessary, but its presence is never allowed to leak a technology
choice across a boundary.

**Source.** Section 6, Separation of Layers.

**Look for.** Interface signatures that mention a client library, a
driver, or a vendor type; return types of infra getters; exceptions
that escape an impl.

**Violation.** An interface method takes or returns a vendor client
object; a manager catches a driver-specific exception; a caller
branches on which backend is configured.

**Severity.** high

## CON-12 Calls flow downward, never up

**Principle.** Services call services and managers; managers call
managers and storage; storage calls storage. Nothing reaches up.
`services.*` exists only in the network layer.

**Source.** Section 10, Direction of Calls.

**Look for.** Imports of `services` from any OM or storage module;
imports of managers from any storage module; callbacks that let a lower
layer invoke an upper one.

**Violation.** A manager holds a `*ServiceInterface`; a storage impl
calls a manager; a lower layer publishes an event only to have an upper
layer complete the same operation.

**Severity.** high

## CON-13 App-specific services stay bounded to one app

**Principle.** An app-specific service impl can call domain services,
but not other app-specific services. If two apps need the same logic,
it belongs in a domain service or in the OM. A domain service cannot
call an app-specific service.

**Source.** Section 10, Direction of Calls.

**Look for.** Constructor dependencies of app-specific service impls;
any domain service that imports from an app-specific package.

**Violation.** One app-specific service holds another as a dependency;
shared logic is copied between two app-specific services; a domain
service depends on an app-specific interface.

**Severity.** medium

## CON-14 Cross-service orchestration lives in the service impl

**Principle.** Cross-service orchestration lives in the service impl,
not in the OM. The service impl holds both a service-level dependency
and a manager-level dependency, and the manager receives the result of
the other service as a plain argument.

**Source.** Section 10, Direction of Calls.

**Look for.** Operations that span two namespaces; where the sequence of
calls is written; what the manager method takes as arguments.

**Violation.** A manager calls another service to obtain an input it
could have been handed; orchestration across namespaces is written
inside the OM; a service impl passes its own dependency handle down
into a manager.

**Severity.** medium

## CON-15 A service shell translates, it does not decide

**Principle.** A router function is three lines: resolve the context,
call a manager, project the result onto a view. When a router grows a
fourth line that decides something, the decision moves into a manager.

**Source.** Section 10, Service Interfaces and Impls.

**Look for.** Router and service impl bodies; conditionals, loops, and
arithmetic inside them; direct storage access from a router.

**Violation.** A router validates business rules, computes a value, or
branches on entity state; a router composes several managers to enforce
a rule the OM should own; a router calls storage directly.

**Severity.** high

## CON-16 Every process boots through the same container in the same order

**Principle.** Settings are read; logging, the trust store, and tracing
are configured; storage is built, then infra, then the managers, in that
order. The container has `start()` and `close()`, and `close()` unwinds
in reverse. A test constructs the same container over the in-memory
storage root and the local infra root.

**Source.** Section 16, The App Container.

**Look for.** The container module of each service and worker; the order
of construction; the lifespan hooks; the test fixture that builds the
app.

**Violation.** Managers are built before storage or infra exists; a
worker assembles its dependencies by hand outside a container; `close()`
tears down in construction order or skips a member; the test suite
boots a different assembly than production.

**Severity.** medium
