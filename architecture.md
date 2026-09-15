# Software Design and Architecture Guidelines

## 1. The Domain as the Source of Truth

Good design starts with a clear domain. A domain is the set of nouns we
use to describe the product, and the relationships between them. For a
closed-loop robot development platform, the nouns might be `Robot`,
`Lab`, `Task`, `Run`, and `Artifact`. Every layer of the system refers
back to these nouns, so they must be defined in one place. That place is
our single source of truth.

The source of truth is an object model of our business domain:
handwritten, pure Python classes based on Pydantic. We ship this model
as a standalone Python library, not a web app, a service, or a CLI. Any
application can depend on it and share the same vocabulary. The library
lives in the monorepo with its consumers, so the domain evolves with the
system instead of drifting in a separate repo.

> **Principle:** The domain has one source of truth: a standalone OM
> library. Every layer depends on it; nothing redefines it.

## 2. Naming Entities

Every entity in the domain is named by a class in the object model.
Before defining entities, we define a small set of mixins that capture
orthogonal traits. Concrete entities compose the mixins they need
through multiple inheritance, in a fixed declaration order so a class
signature reads as a description of the entity.

The mixins:

``` python
class Platform(BaseModel):
    """Root of the object model. Holds no fields."""

    model_config = ConfigDict(frozen=True)


class Identifiable(Platform):
    id: UUID  # uuid_v7


class Named(Platform):
    name: str


class Trackable(Platform):
    created_at: datetime
    updated_at: datetime
    created_by: UUID  # id of the user who created it


class SoftDeletable(Platform):
    deleted_at: datetime | None = None
    deleted_by: UUID | None = None
```

A concrete entity composes the mixins it needs:

``` python
class Bench(Identifiable, Named, Trackable, SoftDeletable):
    description: str
    ssh_host: str
```

Pydantic merges the fields from every base into a single model along the
MRO. The declaration order is house style: identity first, human-facing
label next, lifecycle, then cross-cutting traits. Reading the bases left
to right tells you what the entity promises to be.

Inheritance is used here for abstraction, not code reuse. `Identifiable`
means the entity has an identity. `Trackable` means its lifecycle is
recorded. `SoftDeletable` means it can be hidden without being purged.
`Named` means it carries a human-facing label. An entity opts into a
trait by adding the mixin; it opts out by leaving it off.

> **Principle:** Inheritance expresses abstraction, not code reuse. Each
> mixin is a promise about what the entity is.

### Immutability

> **Principle:** OM entities are immutable. Updates happen by
> copy-and-write, never by mutation.

Every OM entity is immutable. Pydantic models in the base chain are
configured as frozen, so a `Bench` returned from a read is a snapshot,
not a live handle. Updates happen by copy-and-write: take the entity,
produce a modified copy (`bench.model_copy(update={...})`), and pass the
copy to a write method. This keeps shared references safe across async
tasks, makes reasoning about state simpler, and enforces the "IDs
originate top-down" rule, since no layer can quietly rewrite an entity
after it was constructed.

The same rule applies to every object built on the OM base chain,
including the sub-objects of `OpContext`, and to the generated IDL types
described in the network layer. The one deliberate exception is the
SQLAlchemy row classes under `tables/`, which must be mutable so the
session can track writes; they never leak past the storage boundary.

## 3. Namespaces as Swimlanes

The object model is split into namespaces that mirror the swimlanes of
the product. A robot or lab is a long-lived thing we define and monitor.
A task or run is something we author, execute, observe, and report on.
These concepts interact heavily, but remain separate first-class domains
rather than being buried under one another.

    platform.om.robots.*
    platform.om.runs.*

Each top-level namespace under `om` has the same internal shape:

    platform/om/robots/
        RobotManagerInterface      # manager interface at the root
        types/                     # entity classes
        impl/                      # manager implementations

The manager interface sits directly at the namespace root, so consumers
can import it with a short path. `types/` holds the entity classes.
`impl/` holds the concrete manager classes. Other supporting folders
such as `utils/` are also expected alongside these, for
namespace-specific helpers.

When a namespace grows, `types/` (or any other folder) can be
sub-sectioned. Under a run-oriented namespace, `types/` may split by
lifecycle phase:

    platform/om/runs/types/
        sources/       # what we author or request
        executions/    # what a run produces
        reports/       # what we present to users or agents

## 4. Interfaces

Every layer of this system is defined by its interfaces. A manager, a
storage, a service: each exposes a `*Interface` that lists the
operations its scope supports. An operation is an async method whose
signature is a contract.

``` python
class BenchManagerInterface:
    async def get_benches(self, ctx: OpContext) -> list[Bench]: ...
    async def get_bench(self, ctx: OpContext, bench_id: UUID) -> Bench: ...
```

The interface describes a capability. The impl decides how the
capability is delivered. That separation is what makes the impls behind
an interface mockable, stubbable, and injectable, and it is what lets a
single `*Interface` back several different impls at once.

### Multiple impls per interface

An interface usually has more than one impl, and they are
interchangeable at wiring time. Callers never know which one they are
holding.

Default impls for tests and local dev:

-   `BenchManagerMemoryOnlyImpl`: keeps state in an in-process dict.
    Exercises real behavior without infrastructure.
-   `BenchManagerVoidImpl`: a concrete impl whose writes are `pass` and
    whose reads raise `NotFound` or return empty. Useful when a test
    needs the interface wired but does not care about its behavior.

Technology-specific impls for storage:

-   `BenchStoragePostgresImpl`
-   `BenchStorageClickHouseImpl`

Swapping the impl at the storage root moves the system onto a different
engine without any caller changing.

### Composition by decoration

Because an impl depends on an interface, impls compose. Caching is a
common case:

``` python
class CacheInterface:
    async def get(self, key: str) -> bytes | None: ...
    async def set(self, key: str, value: bytes) -> None: ...


class LocalCacheImpl(CacheInterface): ...  # in-process


class CloudCacheImpl(CacheInterface): ...  # redis-like


class MixedCacheImpl(CacheInterface):
    def __init__(self, local: CacheInterface, cloud: CacheInterface):
        self._local = local
        self._cloud = cloud

    async def get(self, key):
        value = await self._local.get(key)
        if value is not None:
            return value
        value = await self._cloud.get(key)
        if value is not None:
            await self._local.set(key, value)
        return value
```

`MixedCacheImpl` takes two `CacheInterface` values and returns one. The
caller holds a `CacheInterface` and cannot tell whether the hit came
from local memory, the cloud, or a two-level composite. The same pattern
fits retry, metrics, and feature-flag wrappers: each is an impl that
holds an inner impl and forwards selectively.

### Injectability

> **Principle:** Dependencies are injected through constructors and
> typed by interface, never by impl.

Dependencies are passed into impls through the constructor and typed by
interface, never by impl. Every downstream section (storage, manager,
service) follows this rule: a root class constructs the concrete impls
in the right order and wires them together. This is what makes the swaps
and compositions above cheap; nothing has to be rewritten to switch an
impl.

## 5. OpContext

Every operation takes an `OpContext` as its first argument. The context
carries the ambient information every operation needs: who is acting, on
behalf of which tenant, with what role, and from which application.

``` python
class SecurityContext(BaseModel):
    user: User
    org: Tenant
    role: Role
    permissions: list[Permission]


class AppContext(BaseModel):
    type: AppType
    version: str  # e.g. "portal@2.14.0", useful for compatibility checks and telemetry


class OpContext(BaseModel):
    security: SecurityContext
    app: AppContext
```

`OpContext` is always populated by the gateway or app layer, which is a
thin shell around the core business logic. By the time a request reaches
a manager, the context is already fully built. Operations never reach
for ambient state through globals or thread locals. All ambient state
flows through the context, which keeps operations easy to test with a
fake context and easy to reason about across layers.

> **Principle:** All ambient state flows through `OpContext`. No
> globals, no thread locals, no hidden lookups.

## 6. Separation of Layers

The system has three layers:

-   **Network**: receives requests, shapes responses, enforces
    protocols.
-   **Business**: the Object Model. Entities, managers, and operations.
-   **Storage**: persistence. Lives under the Object Model but is
    clearly separated from it.

Each layer is a swimlane with its own language and its own
responsibilities. Upper layers depend on interfaces exposed by lower
layers, never on their internals. The infrastructure layer may be
blended into any of these where necessary, but its presence is never
allowed to leak a technology choice across a boundary.

> **Principle:** Three layers: Network, Business, Storage. Upper depends
> on lower through interfaces only. Infrastructure cross-cuts without
> leaking technology.

## 7. The Business Layer

The business layer is where the object model comes alive. Managers
expose operations through `*ManagerInterface` (Section 4). Each
operation takes `OpContext` as its first argument (Section 5) and
returns OM entities (Section 2). A manager impl holds whatever it needs
to do its work: the storage under its namespace, any peer manager whose
operations it composes, and any infrastructure capability it leans on.
All dependencies are injected through the constructor and typed by
interface. A business-layer root wires them together at boot.

Storage is the most common dependency a manager takes and is covered
next. Infrastructure (caches, buckets, topics) follows after that.

### Cross-Manager Dependencies

When a manager needs another manager to do its work, the dependency is
injected through the constructor. The interface is untouched; only the
impl gains the parameter.

``` python
# platform/om/hiltesting/impl/hiltesting_manager_impl.py


class HiltestingManagerImpl(HiltestingManagerInterface):
    def __init__(
        self,
        storage: HiltestingStorageInterface,
        bench_manager: BenchManagerInterface,
    ):
        self._storage = storage
        self._bench_manager = bench_manager
```

The dependency is an implementation detail, not part of
`HiltestingManagerInterface`. The business-layer root constructs every
manager in the right order and wires dependencies between them. Callers
see only the interfaces.

## 8. The Storage Layer

The storage layer persists what the business layer gives it and returns
it on request. It does not orchestrate, it does not decide, and it never
surprises.

### Principles

-   No hidden relationships. The schema does not model links the
    business layer cannot see.
-   No transactions. We are not a bank app, and transactions do not
    scale in the shapes we care about.
-   Joins are avoided but allowed as an implementation detail. They
    never leak into the interface.
-   No trigger functions and no hidden magic. If something happens, it
    happens in our code.
-   Every ID is passed top-down. We do not create an object in the DB
    and read its ID afterwards. IDs originate in the business layer.
-   Defaults are set in the object model. Schema-level defaults are
    optional, kept as a convenience for admin and test operations where
    someone may need to write plain SQL to tweak things and schema
    defaults keep those statements short.
-   The storage layer must be swappable. Moving from a relational DB to
    a columnar DB on a different technology should only change `impl/`,
    never the interfaces or the entities.
-   No user-defined functions in the DB. Every query is written
    explicitly in their storage manager classes.

### Namespace Shape

Storage follows the same namespace pattern as the rest of the object
model, scoped under its parent entity namespace:

    platform/om/robots/storage/
        BenchStorageInterface
        impl/       # implementation of reads and writes
        tables/     # ORM classes, not exposed

The interface exposes read and write operations on domain entities.
Every operation takes `org_id` as a parameter, so tenancy is enforced at
every query:

``` python
class BenchStorageInterface:
    async def read_benches(self, org_id: UUID) -> list[Bench]: ...
    async def write_bench(self, org_id: UUID, bench: Bench) -> None: ...
```

Some scopes are strictly user-bound. A bench canvas view, where the
`x, y` positions of boxes and connections are personal to each user, is
not just tenant-scoped; it is user-scoped within a tenant. In those
cases the interface adds `user_id` on top of `org_id` explicitly:

``` python
class BenchCanvasViewStorageInterface:
    async def read_bench_view(
        self,
        org_id: UUID,
        user_id: UUID,
        bench_id: UUID,
    ) -> BenchCanvasView: ...
```

Both keys are passed, and both appear in the `WHERE` clause of every
query in the impl. `org_id` guards tenancy; `user_id` guards personal
scope within the tenant.

The interface never exposes the underlying technology. A session object
or connection pool is injected into the implementation, never referenced
in the interface. A consumer of `BenchStorageInterface` must not be able
to tell whether it is talking to SQLAlchemy, Postgres, or a columnar
store.

### Hierarchy in Parameters

Parameters follow a top-down hierarchy, from the broadest scope to the
narrowest, regardless of which layer the call lives in. A method that
takes `org_id, user_id, proj_id, bench_id, test_suite_id, test_step_id`
peels layers in sequence: tenant first, then the user inside the tenant,
then the project, then the bench, then the suite, then the step. Reading
a signature left to right tells the reader how the scope narrows. The
same ordering applies everywhere parameters appear: storage interfaces,
manager interfaces, service interfaces, and their impls.

### Storage Root

Storage implementations are assembled behind a single root, `Storage`,
which implements `StorageInterface` and lives at `platform.om.storage`:

``` python
class StorageInterface:
    def get_bench_storage(self) -> BenchStorageInterface: ...

    # one getter per entity storage
```

This root is the top-down entry point into all storage. Higher layers
receive a `StorageInterface` and ask it for the storage they need, which
keeps construction centralized and makes each entity storage trivially
mockable in tests.

`platform.om.storage` also hosts the shared building blocks used by
every concrete storage: common ORM base classes under `tables/` and
translation helpers under `utils/`. These are covered in the next
subsections.

### Defining ORM Classes

Table classes mirror the OM mixins from Section 2, so their definitions
stay focused on what is specific to the entity. The common mixins live
at `platform.om.storage.tables`, with one storage-only addition:
`org_id` rides on `IdentifiableMixin`, because every table is
tenant-scoped.

``` python
# platform/om/storage/tables/base.py


class IdentifiableMixin:
    id: Mapped[UUID]
    org_id: Mapped[UUID]  # storage-only; populated from OpContext at call time


class NamedMixin:
    name: Mapped[str]


class TrackableMixin:
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    created_by: Mapped[UUID]


class SoftDeletableMixin:
    deleted_at: Mapped[datetime | None]
    deleted_by: Mapped[UUID | None]
```

Concrete table classes live in their owning namespace's `tables/` folder
and compose the mixins their entity has, in the same house-style order
as the OM:

``` python
# platform/om/robots/storage/tables/benches.py


class Benches(IdentifiableMixin, NamedMixin, TrackableMixin, SoftDeletableMixin, Base):
    __tablename__ = "benches"
    description: Mapped[str]
    ssh_host: Mapped[str]
```

`Benches` declares only what is unique to a bench. Identity, tenancy,
name, lifecycle timestamps, and soft-delete fields come from the mixins.
Tables carry `org_id` while OM entities do not; tenancy is a storage
concern, populated by the business layer from `OpContext` at call time.

Unlike OM entities, table classes are mutable by design. The SQLAlchemy
session tracks in-place changes to produce SQL, so rows must not be
frozen. This is the one deliberate exception to the OM immutability
rule, and it is bounded: rows never leave the storage impl.

### Translation

Storage translates between the OM entity and the table row. For `Bench`
and `Benches`, field names match one-to-one, so translation is
mechanical in both directions. Two module-level helpers in
`platform.om.storage.utils` cover that case:

``` python
# platform/om/storage/utils/translation.py


def to_row(entity: BaseModel, row_type: type[R]) -> R:
    return row_type(**entity.model_dump())


def to_model(row: Any, model_type: type[M]) -> M:
    return model_type.model_validate(row, from_attributes=True)
```

A write of a `Bench` becomes `to_row(bench, Benches)`; a read becomes
`to_model(row, Bench)`. The storage impl sets `row.org_id` explicitly
since the OM entity does not carry it.

Custom translation is written only when the row and the entity diverge,
for example when a row carries a computed column or a field is
denormalized. Module-level helpers are preferred over an inheritance
base so that multi-entity storages, which touch more than one
`(entity, row)` pair, can use the same primitives without contortion.

### BenchStorageImpl

`BenchStorageImpl` implements `BenchStorageInterface` against a
SQLAlchemy session. The session is injected into the constructor and
never surfaced through the interface:

``` python
# platform/om/robots/storage/impl/bench_storage_impl.py

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform.om.benches.types.bench import Bench
from platform.om.benches.storage import BenchStorageInterface
from platform.om.benches.storage.tables.benches import Benches
from platform.om.storage.utils.translation import to_model, to_row


class BenchStorageImpl(BenchStorageInterface):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def read_benches(self, org_id: UUID) -> list[Bench]:
        stmt = select(Benches).where(Benches.org_id == org_id)
        result = await self._session.execute(stmt)
        return [to_model(row, Bench) for row in result.scalars()]

    async def write_bench(self, org_id: UUID, bench: Bench) -> None:
        row = to_row(bench, Benches)
        row.org_id = org_id
        self._session.add(row)
        await self._session.flush()
```

Every query filters by `org_id`, so tenancy is enforced at the storage
level. Writes stage on the session and flush; commit decisions belong to
the outer scope that opened the session.

### Cross-Storage Dependencies

When a scoped storage impl needs another storage to do its work, the
dependency is injected through the constructor. The interface is
untouched; only the impl gains the parameter.

``` python
# platform/om/hiltesting/storage/impl/hiltesting_storage_impl.py


class HiltestingStorageImpl(HiltestingStorageInterface):
    def __init__(
        self,
        session: AsyncSession,
        bench_storage: BenchStorageInterface,
    ):
        self._session = session
        self._bench_storage = bench_storage
```

The dependency is an implementation detail, not part of
`HiltestingStorageInterface`. `Storage`, the root that implements
`StorageInterface`, is in charge of constructing every storage impl in
the right order and wiring dependencies between them. Callers see only
the interfaces.

## 9. Infrastructure

Storage covers persistence, but managers often need more than a place to
keep rows. They need a cache to skip expensive reads, a bucket to park
large blobs, a topic to hand work off asynchronously. These are
infrastructure capabilities: cross-cutting toolkits, not a layer of
their own. Managers (and web service impls, when needed) reach for them
the same way they reach for a storage: as an interface injected through
the constructor. The three-layer model from Section 6 still holds; infra
is an add-on for concerns that the Business and Network layers cannot
satisfy on their own.

### Principles

-   Every infra capability is fronted by an interface with swappable
    impls. For example, a cache may have a local impl, a cloud impl, and
    a mixed impl; the caller holds a `CacheInterface` and does not know
    which.
-   Tenancy is explicit where it matters as a keying concern. Cache and
    buckets take `org_id` as a first-class parameter so a mistake cannot
    cross tenants at the key level, and user-bound variants take
    `user_id` on top, matching the Storage Layer rule. Topics take
    `OpContext` on publish because an event carries routing context
    beyond tenancy (app, user, trace); the impl pulls what it needs from
    ctx when shaping the envelope. The split is deliberate, not
    accidental.
-   Cross-tenant reference data (feature flags, schema metadata,
    firmware signatures) uses `EMPTY_UUID` as the `org_id` on cache and
    bucket calls. Impls treat it as a reserved system scope, so system
    keys and tenant keys live in disjoint namespaces and a tenant caller
    cannot read or write system data by mistake.
-   Wire-up happens in the app container at boot. Managers and service
    impls receive infra handles through their constructors, never
    through globals, thread locals, or `OpContext`.

### InfraInterface Root

Infrastructure lives under `platform.infra` and is fronted by a single
root so consumers can ask for what they need:

``` python
class InfraInterface:
    def get_cache(self, scope: CacheScope) -> CacheInterface: ...
    def get_buckets(self) -> BucketsInterface: ...
    def get_topics(self) -> TopicsInterface: ...
```

Each getter returns an interface. The concrete impl sitting behind it is
chosen by the app container and can differ across environments (local
dev, staging, production) without any manager changing.

### Cache

Cache is for fast reads against data that is expensive to fetch or
compute. A cache is scoped so that unrelated consumers do not step on
each other's keys:

``` python
class CacheScope(str, Enum):
    NETWORK_RESPONSE = "network_response"
    BUSINESS_OM_SERIALIZATION = "business_om_serialization"


class CacheInterface:
    async def get(self, org_id: UUID, key: str) -> bytes | None: ...
    async def put(self, org_id: UUID, key: str, value: bytes, ttl: timedelta) -> None: ...
    async def invalidate(self, org_id: UUID, key: str) -> None: ...
```

A manager takes the cache it needs through its constructor:

``` python
# platform/om/hiltesting/impl/hiltesting_manager_impl.py


class HiltestingManagerImpl(HiltestingManagerInterface):
    def __init__(
        self,
        storage: HiltestingStorageInterface,
        bench_manager: BenchManagerInterface,
        cache: CacheInterface,  # scoped at wire-up time
    ):
        self._storage = storage
        self._bench_manager = bench_manager
        self._cache = cache
```

`org_id` is passed explicitly on every call, so keys from different
tenants cannot collide even when they share the same logical name. A
user-bound variant (`UserCacheInterface`) can take `user_id` on top of
`org_id` when the cached value is personal to a user within a tenant.

Caching is a business-layer concern. The storage layer does not wrap
reads in a cache; a storage impl talks to its database and nothing else.
Caching decisions live in managers, where the cost/benefit of a stale
read is understood.

### Buckets

Buckets are for large blobs: run artifacts, user uploads, snapshots. The
shape is S3-like and deliberately simple:

``` python
class Buckets(str, Enum):
    RUN_ARTIFACTS = "run-artifacts"
    USER_FILE_UPLOADS = "user-file-uploads"
    BENCH_SNAPSHOTS = "bench-snapshots"


class BucketsInterface:
    async def put(self, org_id: UUID, bucket: Buckets, key: str, data: bytes) -> None: ...
    async def get(self, org_id: UUID, bucket: Buckets, key: str) -> bytes: ...
    async def list(self, org_id: UUID, bucket: Buckets, prefix: str) -> list[str]: ...
    async def delete(self, org_id: UUID, bucket: Buckets, key: str) -> None: ...
```

Keys are plain strings, but nothing prevents a manager from laying them
out as nested paths when that helps:

    test-runs/<run_id>/artifacts/report.html
    test-runs/<run_id>/logs/device-0.log
    benches/<bench_id>/snapshots/<snapshot_id>.tar.zst

Tenancy is explicit: every call takes `org_id`, and the impl prefixes
storage keys with it internally so one tenant's artifacts cannot be read
or listed by another. A user-bound variant can take `user_id` on top
when the blobs belong to a single user (uploaded avatars, per-user
exports).

### Topics

Topics are for asynchronous work and fan-out. A producer publishes an
event; one or more consumers react to it. Topic names are fixed by enum;
payload types are fixed by a payload map:

``` python
class Topics(str, Enum):
    DOCUMENT_TO_BE_VECTORIZED = "document_to_be_vectorized"
    RUN_FINISHED = "run_finished"


TOPIC_PAYLOADS: dict[Topics, type[BaseModel]] = {
    Topics.DOCUMENT_TO_BE_VECTORIZED: DocumentToBeVectorizedPayload,
    Topics.RUN_FINISHED: RunFinishedPayload,
}


class TopicsInterface:
    async def publish(self, ctx: OpContext, topic: Topics, payload: BaseModel) -> None: ...
    def subscribe(
        self,
        topic: Topics,
        consumer: str,
        handler: Callable[[OpContext, BaseModel], Awaitable[None]],
        exclusive: bool = False,
    ) -> None: ...
```

`consumer` is a logical consumer-group name, not a process. Multiple
instances of the same service can subscribe with the same `consumer`
value and the broker will load-balance messages across them: horizontal
scaling falls out automatically. Different consumers on the same topic
each get their own copy of every event, so fan-out and load-balancing
work at the same time.

`exclusive` controls how many different consumer types a topic allows,
not how many processes. With `exclusive=False`, many consumer types
subscribe and each receives every event; `RUN_FINISHED` is a natural
fit, with reporting, notifications, and analytics all reacting to the
same event. With `exclusive=True`, only one consumer type is allowed;
`DOCUMENT_TO_BE_VECTORIZED` is a good example, since exactly one
vectorization pipeline should claim each document.

### Idempotency

Delivery is at-least-once. This is the nature of a message bus: a broker
may redeliver a message if a consumer crashes before acknowledging, an
operator may replay a topic to backfill a new consumer or recover from a
bad deploy, a flaky client may publish the same request twice when its
connection blips. Handlers must be safe to run more than once with the
same payload.

The usual recipe is a producer-generated idempotency key on the payload
(typically a `uuid_v7`) combined with either a storage-level upsert
keyed on it, or a small dedupe table the handler checks before acting. A
payload base captures the convention in one place:

``` python
class TopicPayload(BaseModel):
    idempotency_key: UUID  # uuid_v7, set by the producer
    produced_at: datetime
```

Every topic payload extends `TopicPayload`, so every handler has a key
to dedupe on without thinking. This rule holds for every topic, whether
`exclusive` or not, and for every inbox or outbox queue layered on top
(see Section 10, Idempotency on the Consumer Side).

Because the producer sets `idempotency_key` at construction time, it
also serves as the observable id throughout the pipeline: producers and
consumers both log it, and anyone tracing a message end to end uses it.
That is why `publish()` returns `None`; a broker-assigned id (a Kafka
offset, an SQS `MessageId`, a JetStream seq) carries no durable meaning
across retries, replays, or broker changes, and surfacing it would leak
technology through the interface.

## 10. The Network Layer

### Web Services as Scalability Units

Web services are the network layer's scalability units. Each major OM
namespace gets its own service: `benches` has `bench-api`, `hiltesting`
has `hiltesting-api`, and so on. Splitting along namespace lines lets
each service be scaled, versioned, and deployed independently, and lets
products mix which services they expose.

Services earn their keep in three ways: they are the scalability unit of
the platform, they are the surface that apps (the products built on top)
consume, and they are the surface that external API users (CI/CD
systems, partners, anyone with a token) consume.

A service runs in its own container with the whole OM library available
to it. Within that container, the service impl can call any OM manager
or storage directly, in-process. A service-to-service call (one service
calling another over the wire) is intentionally rare: most logic is
centralized in OM managers, and a service impl almost always completes
its work by composing managers locally. A service-to-service call is
reserved for workflows that exceed a single manager's scope, for example
a hiltesting workflow that needs to reserve a bench before running a
test (see Direction of Calls).

### Domain Services vs App-Specific Services

Two kinds of web services exist, and they share the same structural
pattern:

-   **Domain services** wrap one OM namespace each and expose its
    operations to any caller. `bench-api`, `hiltesting-api`,
    `user-mgmt-api`, `docs-api`. Both external API users and the
    platform's own apps call them.
-   **App-specific services** exist for the needs of a single client
    app: `portal-web-svc`, `cli-web-svc`, `desktop-web-svc`. Each
    composes domain services to serve the exact shape its client needs,
    and holds any logic that is only meaningful for that app (session
    shape, client-specific aggregations, per-app rate limits).

App-specific services tend to be thin because most of their work is
delegating to domain services. They exist so client apps can stay dumb:
an app talks to its own backing service; that service does the
composition.

### At a Glance

``` mermaid
flowchart TD
    User[Product users]
    API[External API users<br/>CI/CD, partners]
    App[Apps<br/>CLI / Portal / Desktop]
    GW[Gateway<br/>auth + OpContext]
    AppSvc[App-specific services:<br/>portal-web-svc<br/>cli-web-svc<br/>desktop-web-svc]

    subgraph SvcContainer [" "]
      DomSvc[Domain services:<br/>bench-api<br/>hiltest-api<br/>docs-api<br/>user-mgmt-api<br/>secret-mgmt-api]
      Core[Lib: OM + Storage]
      DomSvc --> Core
    end

    User --> App
    App --> GW
    API --> GW
    GW --> AppSvc
    GW --> DomSvc
    AppSvc -->|composes| DomSvc

    style SvcContainer fill:transparent,stroke:#333
```

### Stateless vs Stateful Services

The whole point of splitting network work into web services is to scale
them horizontally, and that stays cheap only if services are treated as
ephemeral from a deployment perspective: kill one, start a fresh one
elsewhere, and the system keeps running. The test is reconstitutability.
If a process's in-memory content can be rebuilt from durable sources
(storage, cache, queues, a small registry), it counts as ephemeral
regardless of what it holds in RAM at any given moment. If the process
is the only place a piece of information exists, horizontal scaling
breaks.

Domain services are always stateless. They read from storage, write to
storage, publish events, and return. A warm cache, a preloaded index, a
cached IDL schema, a per-process rollup of an expensive computation are
all fine; they rebuild at boot. What a domain service must never do is
hold information that exists nowhere else. This rule has no exceptions,
including for cases that feel stateful on the surface like
`notification-svc` (see the case study at the end of this section).

App-specific services may be lightly stateful, but only when a client
opens a long-lived transport. A WebSocket or a gRPC stream is state by
its very nature: the kernel holds an open socket and that socket is
bound to a single process. This is the one case where a service
unavoidably holds something the rest of the system does not. The rule is
narrow: the only thing a lightly stateful app-specific service keeps in
its memory is the open connection itself. No session data, no user
preferences, no accumulated context. Those are recovered on demand from
storage, cache, or a presence store. The patterns further down in this
section (starting at Dealing with 'Stateful' Services: Inbox and Outbox
Queues) show how this rule is implemented in practice.

> **Principle:** Domain services are always stateless. App-specific
> services may hold only the open socket and its queues; never session
> data or user context.

### Service Interfaces and Impls

The network layer follows the same interface/impl pattern as managers
and storages. Each service declares its network operations through a
`ServiceInterface`; the impl handles HTTP wiring. A `ServicesInterface`
plays the role of the network-layer root:

``` python
class BenchServiceInterface:
    async def get_benches(self, ctx: OpContext) -> list[BenchView]: ...
    async def get_bench(self, ctx: OpContext, bench_id: UUID) -> BenchView: ...


class ServicesInterface:
    def get_bench_service(self) -> BenchServiceInterface: ...

    # one getter per service
```

The impl handles POST/GET routing, request and response serialization,
and translation between the public types and the OM entities.

### The Gateway

A gateway sits in front of the services. It is the only layer that talks
to the public internet. It authenticates requests, builds `OpContext`,
and routes to the right service. Services themselves never construct
`OpContext` from raw headers or tokens; by the time a service method is
called, the context is already populated.

`OpContext` is immutable. Once built by the gateway, it flows through
every downstream call unchanged. No layer adds, replaces, or mutates its
fields mid-request. If an operation needs a narrower view (for example,
an admin override or a narrowed permission set), it is passed as an
explicit argument, not by mutating `ctx`.

### Auth: Gateway vs. Dedicated Service

A recurring design choice: put auth entirely in the gateway, or keep a
dedicated `AuthService` behind it.

Recommended: the gateway verifies tokens; a dedicated `AuthService` owns
the user and tenant model, issues tokens, and handles everything that is
"about" identity. The gateway stays stateless and fast, while
`AuthService` is a regular service with its own OM namespace
(`platform.om.auth`) and storage.

Rationale: auth has business logic (signup, invite, MFA, permission
management) that belongs in the OM like any other domain. A thin gateway
can verify tokens and call into `AuthService` when it needs user detail,
but it should not own the auth domain itself. This keeps `AuthService`
testable and replaceable the same way every other service is, and avoids
turning the gateway into a smart monolith.

When the need grows beyond authentication (for example, generating,
rotating, and delivering public/private key pairs for devices, CI
runners, or partner integrations), that work does not belong in
`AuthService`. It gets its own domain service, `secret-mgmt-api`, backed
by a `platform.om.secrets` namespace and its own storage. Keeping
identity and secrets apart prevents one domain's concerns from bloating
the other, and lets them be scaled, audited, and deployed on their own
terms.

### Intra-Service Communication

All services run in the same local or virtual network.
Service-to-service calls never cross the public internet, and TLS is not
required for intra-service traffic. This simplifies the transport and
keeps service impls focused on business concerns, not certificate
rotation.

### REST + gRPC Twin

Each REST service has a gRPC companion generated from the same IDL. The
gRPC service is an auto-generated wrapper with zero business logic: it
delegates every call to the same underlying `ServiceInterface`. Protos
and scaffolding are generated, never hand-written.

REST and gRPC deploy in the same pod, each on a different port. They
never talk over the public network, and clients on the same virtual
network can pick either protocol without extra infrastructure.

### Public Types via IDL

The OM is the source of truth for entities. What a service exposes on
the wire is a selective projection of those entities, defined in an IDL
(OpenAPI or Protobuf) and generated into Python types. The IDL decides
which fields are public, which are renamed, and which are omitted. The
OM never changes to match the wire format.

Each service owns its own IDL and its own generated types. `bench-api`
owns `BenchView`, `hiltesting-api` owns `TestResultView`. Translation
between the public view and the OM entity lives in the service impl,
using the same one-to-one helper pattern as storage translation when
fields align.

Generated IDL types are immutable, like OM entities. They are wire
snapshots, not live objects. A service may hand the same view to
multiple callers; mutating one would mislead the others and would not
reach back to the OM entity behind it.

### From OM to Wire

To make the flow concrete, follow one entity end to end. `Bench` lives
in the OM; the IDL decides what the wire looks like:

``` yaml
# platform/services/bench/idl/openapi.yaml
components:
  schemas:
    BenchView:        # wire shape; curated, not auto-derived from Bench
      type: object
      properties:
        id:          { type: string, format: uuid }
        name:        { type: string }
        description: { type: string }
        ssh_host:    { type: string }
    AddBenchRequest: # input shape; no id/timestamps, server assigns them
      type: object
      properties:
        name:        { type: string }
        description: { type: string }
        ssh_host:    { type: string }
```

`BenchView` is close to `Bench` but decided separately; the IDL can
omit, rename, or add fields without the OM changing. `AddBenchRequest`
carries no identity or timestamps, because those are server-assigned.

A single build-time pass generates both transports from the same IDL:
REST router and typed request/response classes, plus a `.proto` and a
gRPC server wrapper. Both shells delegate to the same hand-written
`BenchServiceInterface` impl.

``` mermaid
flowchart LR
    OM[OM types<br/>Bench, etc.<br/>platform/om/...]
    IDL[IDL<br/>openapi.yaml<br/>services/bench/idl/]
    GR[gen_rest.py]
    GG[gen_grpc.py]

    subgraph Generated [Generated per service]
        direction TB
        RestRouter[REST router<br/>+ BenchView, AddBenchRequest]
        Proto[.proto + gRPC server wrapper]
    end

    SvcImpl[BenchServiceInterface + Impl<br/>hand-written]

    subgraph Clients [Generated clients - one per language]
        direction TB
        PyClient[platform/clients/python/<br/>bench_api_client/]
        TsClient[platform/clients/ts/<br/>bench-api-client/]
    end

    OM -. projected selectively .-> IDL
    IDL --> GR --> RestRouter
    IDL --> GG --> Proto
    RestRouter -->|delegates to| SvcImpl
    Proto -->|delegates to| SvcImpl
    IDL --> PyClient
    IDL --> TsClient

    style SvcImpl fill:#eef
    style OM fill:#efe
    style IDL fill:#fef
```

### Generated Clients Live in One Place

> **Principle:** One generated client package per language per service.
> Every consumer imports it; nobody regenerates their own.

A service is accessed in exactly one way, so its client proxy is
generated in exactly one place per language. Regenerating in every
consumer duplicates work and invites drift when someone rebases a stale
copy against a newer IDL.

    platform/clients/python/bench_api_client/   # generated once from the IDL
    platform/clients/ts/bench-api-client/       # generated once from the IDL

Consumers import the typed client they need and call only the methods
they use. When the IDL changes, CI regenerates both packages, and every
consumer picks up the new types on the next build; the import path is
the version. The same package holds both REST and gRPC under a uniform
surface, so a consumer swaps transports by changing the handle it
constructs, not its imports.

### Direction of Calls

Calls flow downward through the layers, never upward:

-   A **domain service impl** can call other domain services (through
    their `ServiceInterface`) and its own OM managers (through their
    `ManagerInterface`). It cannot call app-specific services; apps are
    consumers of the domain, not dependencies of it.
-   An **app-specific service impl** can call domain services, but not
    other app-specific services. Each app-specific service is bounded to
    one app; siblings stay independent so one app's needs never leak
    into another. If two apps need the same logic, it belongs in a
    domain service or in the OM.
-   An **OM manager** can call other managers and storages, but cannot
    reach back up to a `ServiceInterface`. `services.*` exists only in
    the network layer.
-   A **storage impl** can call other storages (see Cross-Storage
    Dependencies) but cannot reach up to managers or services.

Cross-service orchestration therefore lives in the service impl, not in
the OM. Running a hiltesting test, for example, needs a reserved bench.
Reserving a bench is complex enough to be a service-level operation
(availability, concurrency, notifications), which is why it lives in
`bench-api` rather than only in `BenchManager`. The hiltesting service
impl orchestrates:

``` python
# platform.services.hiltesting.impl (network layer)


class HiltestingServiceImpl(HiltestingServiceInterface):
    def __init__(
        self,
        bench_service: BenchServiceInterface,
        hiltesting_manager: HiltestingManagerInterface,
    ):
        self._bench_service = bench_service
        self._hiltesting_manager = hiltesting_manager

    async def run_test(self, ctx: OpContext, req: RunTestRequest) -> TestRunView:
        reserved_bench = await self._bench_service.reserve(ctx, req.bench_id)
        test_run = await self._hiltesting_manager.run_test(
            ctx,
            req.source_bundle,
            reserved_bench,
        )
        # translate test_run to TestRunView and return
        ...
```

The service impl holds both a service-level dependency
(`BenchServiceInterface`) and a manager-level dependency
(`HiltestingManagerInterface`), both injected through the constructor.
The OM hiltesting manager receives `reserved_bench` as a plain argument;
it has no knowledge that a service was called to produce it.

> **Principle:** Calls flow downward: services to services and managers;
> managers to managers and storage; storage to storage. Nothing reaches
> up.

### Idempotency on the Consumer Side

> **Principle:** Every queue is at-least-once. Every handler must be
> idempotent, keyed on a producer-generated idempotency key.

Delivery is at-least-once in practice, regardless of whether a queue is
backed by a broker topic or a database table. A client may retry a
request after a flaky disconnect and produce a duplicate; a handler may
do its work and then crash before marking the message processed, so the
next run sees the same input again; an operator may replay a backlog to
recover from a bad deploy. Message handlers must be safe to run more
than once with the same payload.

The recipe is independent of the implementation: every message carries a
producer-generated idempotency key (a `uuid_v7` is natural), and the
handler dedupes before doing work, either through a storage-level upsert
keyed on it or a small dedupe check. Each pipeline stage forwards the
key and applies the same check. Section 9 shows this on `TopicPayload`;
the same pattern fits a table-backed inbox row or any other shape a
logical queue takes.

### Dealing with 'Stateful' Services: Inbox and Outbox Queues

A lightly stateful app-specific service sits between two queues scoped
per user and connection: an inbox for messages the client sent, and an
outbox for messages to deliver. The stream handler shuttles bytes in
both directions only: socket to inbox, outbox to socket. A processor
consumes the inbox, does its work through domain services, and produces
onto the outbox. When the work is more than trivial, each pipeline stage
gets its own queue so stages are independently restartable and scalable.

"Queue" here is a logical concept, not necessarily a broker. For
per-user-and-connection inbox and outbox, the natural implementation is
a small set of database tables keyed by
`(user_id, connection_id, seq, status)`, not the message-bus topics from
Section 9. Topics fit a bounded number of logical streams, a handful per
domain event type. They are a poor fit for potentially millions of
short-lived queues that churn on every connect and disconnect. A
table-backed inbox and outbox is cheap to create (insert a row), cheap
to clean up (delete by `connection_id` or TTL), easy to scan per
connection, and trivial to resume after a crash by picking up from the
last acked `seq`.

Scoping per user and connection is load-bearing, not cosmetic. Ordering
matters per conversation, not globally, and backpressure should push
back on a noisy conversation without starving quiet ones. With a table,
backpressure is a row-count check against the user's own outbox, applied
locally. A single shared queue or table would couple every user into one
ordering domain and one pressure domain, which is exactly what we are
trying to avoid.

``` mermaid
flowchart LR
    Client[Client<br/>WebSocket / gRPC stream]

    subgraph AppSvc [App-specific service instance]
        direction TB
        StreamH[Stream handler<br/>shuttles bytes only]
        Proc[Processor<br/>calls domain services]
        Drain[Drainer<br/>writes to socket]
    end

    subgraph Tables [DB tables, per user+connection]
        direction TB
        Inbox[(inbox<br/>user_id, connection_id,<br/>seq, status, payload)]
        Outbox[(outbox<br/>user_id, connection_id,<br/>seq, status, payload)]
    end

    Domain[Domain services<br/>via ServiceInterface]

    Client -->|incoming| StreamH
    StreamH -->|insert| Inbox
    Inbox -->|consume| Proc
    Proc -->|call| Domain
    Proc -->|insert| Outbox
    Outbox -->|consume| Drain
    Drain -->|outgoing| Client

    style Tables fill:#fff8e6
    style Domain fill:#eef
```

### Wait-for-Response vs Fire-and-Forget

The inbox and outbox substrate does not dictate how a caller uses it.
Two patterns ride on top, and the choice is made per operation at the
client.

A CLI running a command over a gRPC stream typically pairs each outbound
request with its response by correlation id and waits synchronously for
that response. The stream is a reliable RPC with persistence: the
command is durable the moment it hits the incoming queue, so the user
can keep waiting through a network blip without losing the in-flight
work. This is the right default for short operations where the user is
at the terminal expecting an answer.

A long-running operation submitted from a portal or a desktop app is
usually fire-and-forget from the app's perspective. The app publishes
the request, returns to its event loop, and trusts a push notification
to arrive on the outbound stream later when the work completes. This is
the right default for operations measured in minutes or hours, and for
flows where the user may close the app and reopen it later to see the
result.

Services produce responses and notifications onto the outbox the same
way in both cases. The difference lives at the client: whether it holds
a pending-correlation map while it waits, or treats every inbound
message as a discrete notification to reconcile against its own durable
state.

Wait-for-response (CLI command over a gRPC stream):

``` mermaid
sequenceDiagram
    participant CLI
    participant Svc as App-specific service
    participant Dom as Domain services

    CLI->>Svc: request (corr_id=42)
    Note over CLI: blocks on corr_id=42
    Svc->>Dom: do work
    Dom-->>Svc: result
    Svc-->>CLI: response (corr_id=42)
    Note over CLI: resolves pending call 42
```

Fire-and-forget (portal submits a long-running operation):

``` mermaid
sequenceDiagram
    participant Portal
    participant Svc as App-specific service
    participant Wrk as Worker
    participant Dom as Domain services

    Portal->>Svc: request (start job)
    Svc->>Wrk: enqueue task
    Svc-->>Portal: ack (enqueued)
    Note over Portal: returns to event loop
    Wrk->>Dom: do work (minutes/hours)
    Dom-->>Wrk: result
    Wrk->>Svc: completion event
    Svc-->>Portal: push (job-completed)
    Note over Portal: reconciles against durable state
```

### Routing to the Right Process

When a producer anywhere in the system needs to push a message to a user
who happens to have an open socket, it must know which service instance
is holding that socket. A presence registry, typically a small Redis,
maps `user_id -> instance_id` and is updated on connect, disconnect, and
lease expiry. Producers look up the target and write to the outgoing
queue the target instance is draining. The registry's data lives in a
shared store, not in any one process, so the service tier stays
stateless even while individual instances hold live sockets. If an
instance dies, its entries expire, the next connect from the affected
users lands on a different instance, and the registry re-points
accordingly.

``` mermaid
flowchart LR
    Prod[Producer<br/>domain service / worker]
    Reg[(Presence registry<br/>Redis<br/>user_id -> instance_id)]

    subgraph Fleet [App-specific service fleet]
        direction TB
        I1[Instance #1<br/>holds user A socket]
        I2[Instance #2<br/>holds user B socket]
        I3[Instance #3<br/>idle]
    end

    UserA[User A]
    UserB[User B]

    Prod -->|1. lookup user A| Reg
    Reg -->|2. instance #1| Prod
    Prod -->|3. write to outbox| I1
    I1 -->|drain| UserA
    I2 -->|drain| UserB

    I1 -.->|heartbeat| Reg
    I2 -.->|heartbeat| Reg
    I3 -.->|heartbeat| Reg

    style Reg fill:#fff8e6
```

### Long-Running Orchestrations

Work that takes minutes or hours is not process state; it is a durable
record advanced by stateless workers. A twenty-minute test run lives as
a row with a status and a cursor; a worker picks it up, does a step,
updates the row, hands off. If the worker dies, another picks up at the
persisted position. The same reconstitutability rule, applied at a
longer horizon.

``` mermaid
sequenceDiagram
    participant Row as Durable record<br/>(status, cursor)
    participant W1 as Worker A
    participant W2 as Worker B

    W1->>Row: claim, read cursor=N
    W1->>W1: do step N
    W1->>Row: write cursor=N+1
    Note over W1: dies mid-step
    W2->>Row: claim, read cursor=N+1
    W2->>W2: do step N+1
    W2->>Row: write cursor=N+2
    Note over Row: advances regardless of<br/>which worker is alive
```

### Case Study: Notification Service

`notification-svc` delivers in-app notifications to users connected over
the realtime channel (Section 12, Push-First Apps). It is not a
cross-channel delivery service for email, SMS, or mobile push; those
belong to their own services if and when they are ever needed. At first
glance `notification-svc` feels stateful, with a backlog of pending
notifications, a set of subscriptions, and a stream of pushes to users
over time. Tracing its flow shows that none of that state lives in the
service's memory.

Subscriptions are rows. A user's subscription preferences and muted
topics are stored in the notification domain and read on demand. Pending
notifications are messages on a queue: the notification domain produces
onto an outgoing topic, and a fan-out worker consumes it. For each
target user, the worker looks up the active instance in the presence
registry and writes onto the right app-specific service's outbox. The
edge service drains the outbox into the user's held socket on the
realtime channel. If the worker dies mid-flight, the broker redelivers
and the idempotency key prevents a duplicate push.

`notification-svc` is a stateless domain service, its workers are
stateless consumers, and the only truly stateful piece in the chain is
the app-specific service at the edge holding the sockets. Every instance
at every tier can be killed and replaced without the system missing a
message, which is the shape we want for every service in the platform.

## 11. Worker Roles

A distributed system is not just web services. Anything that runs on its
own schedule, or drains a queue without a caller waiting on the other
end, is a worker role: a process that reads a task, does work, writes a
result, and optionally notifies someone. Workers sit next to web
services, not inside them.

### Workers, Not Web-Service Side Jobs

> **Principle:** Web services do not spawn background jobs or schedule
> recurring tasks. Every such need is an explicit worker role.

Web services do not spawn background jobs or schedule recurring tasks.
Every such need becomes an explicit worker role with its own container,
its own deployment, and its own place in the service catalog. This keeps
the rules from Section 10 meaningful. A stateless domain service that
fires off a background job is no longer stateless: the job outlives the
request, and the process is now the only place that remembers it is
running. A lightly stateful app-specific service that schedules
recurring work has extended its state well past the one open socket that
justified being stateful in the first place. Pulling background work out
as first-class components keeps the network tier honest and makes the
work itself observable, restartable, and scalable on its own terms.

### Shape of a Worker

A worker is a small loop: pull from a source (a topic, a table-backed
queue, a cron tick), do the work by calling OM managers and other
services through their interfaces, write the result to storage, and if
relevant produce a notification onto a topic. The same interface/impl
split as the rest of the platform applies: a `WorkerInterface` declares
the step, an impl delivers it. Handlers are idempotent by the rule from
Section 10 (Idempotency on the Consumer Side), so replays and
at-least-once delivery stay safe.

``` python
class TestResultPublisherInterface:
    async def handle(self, ctx: OpContext, msg: TestCompleted) -> None: ...


class TestResultPublisherImpl(TestResultPublisherInterface):
    def __init__(
        self,
        hiltesting_mgr: HiltestingManagerInterface,
        notify_svc: NotificationServiceInterface,
    ):
        self._hiltesting = hiltesting_mgr
        self._notify = notify_svc

    async def handle(self, ctx: OpContext, msg: TestCompleted) -> None:
        # dedupe on msg.idempotency_key, then:
        summary = await self._hiltesting.get_run_summary(ctx, msg.run_id)
        await self._notify.fan_out(ctx, summary)
```

The worker container runs the loop; the impl reads like a domain-service
impl and leans on the same managers and services a web service would.

``` mermaid
flowchart LR
    subgraph Source [Source]
        direction TB
        Topic[topic]
        Queue[(table-backed queue)]
        Cron[cron tick]
    end

    subgraph Worker [Worker container - always on]
        direction TB
        Loop["loop:<br/>pull → dedupe → handle → write → notify"]
    end

    Mgr[OM managers /<br/>domain services]
    Sto[(Storage)]
    Notif[Notification topic]

    Topic --> Loop
    Queue --> Loop
    Cron --> Loop
    Loop -->|call| Mgr
    Mgr --> Sto
    Loop -->|produce| Notif

    style Worker fill:#eef
```

### Implementation Options

Worker roles run as first-class background services: usually the same
container shape as web services, minus a public network surface.
Long-lived coding-agent or execution workers may require a more
privileged compute environment than ordinary services, including the
ability to run nested containers, browsers, local test stacks,
simulators, and hardware-facing tooling. Serverless options like AWS
Lambda were considered and set aside as the default, because the
fifteen-minute execution ceiling rules out longer runs, cold starts
defeat the warm connection pools the rest of the platform relies on, and
the Lambda runtime does not match how every other component runs on a
laptop. Kubernetes `Job` and `CronJob` fit narrow one-shot cases but
make recurring scheduled work harder to observe and evolve. Keeping
workers as always-on containers makes them indistinguishable from
services in every way that matters (deployment, observability, pooling,
local development), and leaves serverless as a case-by-case option for
truly sporadic workloads.

## 12. Apps

### Apps as Products

Apps are products that consume the system. The coding-agent CLI, web
portal, desktop app, and other user-facing clients are all apps. An app
sits at the outermost layer. It reaches the platform through the gateway
and the web services.

### Apps Are Dumb

> **Principle:** Apps are intentionally dumb. Only UI, input, and
> device-specific behavior live in the app. Business logic and
> orchestration belong on the server.

Client apps are intentionally dumb. An app renders UI, reads input, and
hands requests off to its backing app-specific web service (see section
10). The app-specific service composes across domain services; the app
just shows the result.

The only code that lives inside an app is UI rendering, local input
handling, and device-specific behavior. Business logic and cross-service
orchestration do not belong in the app.

When a piece of logic is only meaningful for one app, it moves to that
app's app-specific web service, not into the app itself. When it is
meaningful for more than one app, it moves to a domain service or to the
OM. Either way, the client app stays thin, cheap to rewrite, and easy to
replace.

### Push-First Apps

> **Principle:** Polling is a workaround for the absence of push. The
> moment any single corner of an app wants a push, the app earns a
> realtime channel.

Polling is a workaround for the absence of push. The rule: the moment
any single corner of an app wants a push, the app earns a realtime
channel. A realtime channel is one persistent, bidirectional connection
(a WebSocket, or a gRPC stream) that the client opens at startup, holds
for the session, and reads continuously. Every piece of client-bound
data flows over it.

One channel carries many message types. Command responses, push
notifications, subscription updates, and live data changes all travel as
typed envelopes on the same connection; the client inspects the envelope
type and routes each message to the right handler. Polling collapses
into "subscribe once, read forever": instead of `GET /jobs/{id}` on a
timer, the client sends one subscribe message and receives a push when
the status changes.

The rule holds because the marginal cost of another message type on an
existing channel is effectively zero, while the cost of a second
transport (a polling endpoint, a separate SSE stream, another WebSocket)
is a whole new operational surface. Once the first push need earns a
channel, every subsequent push need rides the same substrate for free.

A realtime channel makes the app-specific service lightly stateful, and
that is accepted deliberately. The only state the service holds is the
open socket and the queues scoped to it (Section 10, Dealing with
'Stateful' Services: Inbox and Outbox Queues). Everything else,
including session data, subscriptions, and accumulated context, is
recovered on demand from storage, cache, or the presence registry. The
rules that keep that trade-off bounded are in Section 10 (Stateless vs
Stateful Services and the stateful-services patterns that follow).

One channel per app, not per feature. It is tempting to open a dedicated
socket for chat, another for notifications, another for live data.
Resist. Every feature piggybacks on the single channel, which keeps
connection count low, leaves reconnect logic as one thing to get right,
and keeps the presence registry to one entry per user per connected app.

> **Principle:** One realtime channel per app, not per feature. Every
> push rides the same connection as a typed envelope.

``` mermaid
flowchart LR
    subgraph ClientApp [Client app]
        direction TB
        Router{typed envelope<br/>router}
        H1[response handler]
        H2[notification handler]
        H3[subscription handler]
        H4[live-data handler]
        Router --> H1
        Router --> H2
        Router --> H3
        Router --> H4
    end

    Channel[Realtime channel<br/>one WebSocket /<br/>gRPC stream]

    subgraph AppSvc [App-specific service]
        direction TB
        Inbox[(inbox)]
        Outbox[(outbox)]
    end

    Domain[Domain services]

    ClientApp -->|outbound:<br/>commands, subscribes| Channel
    Channel -->|inbound:<br/>typed envelopes| ClientApp
    Channel --> Inbox
    Outbox --> Channel
    AppSvc -->|composes| Domain

    style Channel fill:#fff8e6
    style ClientApp fill:#efe
    style AppSvc fill:#eef
```

## 13. Deployment

### Cloud: AWS

Cloud deployments target AWS, for both production and staging. Ordinary
stateless services and privileged long-running execution workers may use
different AWS compute substrates; the architecture should not assume
that every workload fits the same container runtime. Staging mirrors
production in shape and differs only in capacity, so a service that runs
correctly in staging is expected to run correctly in production with
nothing more than scale changes.

### Infrastructure as Code

Every cloud resource is defined in Terraform: networks, services,
databases, topics, buckets, IAM. Terraform lives in the same monorepo as
the application code, so an environment change is a pull request and a
new environment is a fresh parameter set.

> **Principle:** Every cloud resource is declared in Terraform. No
> clicks in the console, no untracked state.

### Local: Docker Compose

Local development and tests run entirely on the developer's machine
through a single `docker-compose` stack. Every technology piece the
platform depends on (Postgres, Redis, the object store, the message
broker) runs as a local container alongside the application services,
using the same images as the cloud where possible.

The one deliberate exception is for systems that are prohibitively hard
to replace faithfully. WorkOS for SSO is the canonical case: SAML and
OIDC flows cannot be stood up as a local container in any meaningful
way, so local development points at a shared development tenant on the
real service. The exception list is kept short on purpose.

> **Principle:** Every dependency runs in a local container. The only
> exceptions are SaaS pieces that cannot be faithfully emulated.

## 14. Monorepo Folder Structure

The monorepo root groups code by role: libraries, services, workers,
apps, clients, deployment, and tooling.

    [root]/
    ├── pyproject.toml                      # uv workspace root
    ├── package.json                        # pnpm workspace root
    ├── pnpm-workspace.yaml
    ├── ruff.toml                           # shared Python lint config
    ├── mypy.ini
    ├── .pre-commit-config.yaml
    ├── .python-version
    ├── .nvmrc
    ├── README.md
    │
    ├── docs/
    │   ├── architecture.md
    │   ├── adr/                            # architecture decision records
    │   └── runbooks/
    │
    ├── om/                                 # platform-om distribution
    │   ├── pyproject.toml
    │   ├── src/
    │   │   └── platform/
    │   │       └── om/
    │   │           ├── base.py             # Platform + mixins
    │   │           ├── opcontext.py
    │   │           ├── exceptions.py       # PlatformException root
    │   │           ├── benches/
    │   │           │   ├── types/
    │   │           │   ├── impl/
    │   │           │   ├── utils/
    │   │           │   └── storage/
    │   │           │       ├── impl/
    │   │           │       └── tables/
    │   │           ├── hiltesting/
    │   │           ├── auth/
    │   │           ├── users/
    │   │           ├── secrets/
    │   │           ├── notifications/
    │   │           └── storage/            # storage root + shared base classes
    │   ├── tests/
    │   │   ├── unit/
    │   │   ├── integration/
    │   │   └── conftest.py
    │   └── migrations/                     # alembic
    │       ├── alembic.ini
    │       ├── env.py
    │       └── versions/
    │
    ├── infra/                              # platform-infra distribution
    │   ├── pyproject.toml
    │   ├── src/
    │   │   └── platform/
    │   │       └── infra/
    │   │           ├── cache/
    │   │           ├── buckets/
    │   │           ├── topics/
    │   │           └── impl/
    │   └── tests/
    │
    ├── domain-services/
    │   └── bench-api/                      # platform-services-bench
    │       ├── pyproject.toml
    │       ├── Dockerfile
    │       ├── idl/
    │       │   └── openapi.yaml
    │       ├── src/
    │       │   └── platform/
    │       │       └── services/
    │       │           └── bench/
    │       │               ├── impl/
    │       │               ├── types/
    │       │               └── _generated/ # gitignored, rebuilt on demand
    │       ├── tests/
    │       ├── entrypoints/                # __main__.py for the container
    │       └── README.md
    │   # auth-api, hiltesting-api, user-mgmt-api, secret-mgmt-api,
    │   # doc-api, notification-svc
    │
    ├── app-services/
    │   ├── portal-web-svc/                 # same project shape as domain-services
    │   ├── cli-web-svc/
    │   └── desktop-web-svc/
    │
    ├── workers/
    │   └── test-result-publisher/          # same project shape, no idl/
    │   # doc-vectorizer, notification-fanout
    │
    ├── apps/
    │   ├── cli/                            # Python CLI
    │   │   ├── pyproject.toml
    │   │   ├── src/platform/apps/cli/
    │   │   └── tests/
    │   ├── portal/                         # React + TypeScript + Vite
    │   │   ├── package.json                # @platform/portal
    │   │   ├── tsconfig.json
    │   │   ├── vite.config.ts
    │   │   ├── src/
    │   │   │   ├── extensions/             # feature modules; see Section 15
    │   │   │   └── ...
    │   │   └── tests/
    │   └── desktop/                        # Tauri shell over the same Vite build
    │       ├── package.json                # @platform/desktop
    │       ├── src-tauri/
    │       └── ...
    │
    ├── clients/                            # one generated package per language per service
    │   ├── domain-services/
    │   │   ├── bench-api/
    │   │   │   ├── python/                 # platform-clients-bench-api
    │   │   │   └── ts/                     # @platform/bench-api-client
    │   │   └── ...
    │   └── app-services/
    │       ├── portal-web-svc/
    │       │   ├── python/
    │       │   └── ts/
    │       └── ...
    │
    ├── deployment/
    │   ├── terraform/
    │   │   ├── modules/
    │   │   └── environments/
    │   │       ├── staging/
    │   │       └── prod/
    │   ├── local/
    │   │   ├── docker-compose.yml          # postgres, redis, broker, object store
    │   │   ├── docker-compose.override.yml
    │   │   └── seed/
    │   ├── docker/                         # shared Dockerfile fragments and base images
    │   └── helm/                           # optional, k8s charts
    │
    ├── scripts/
    │   ├── gen_rest.py                     # IDL to REST router + types
    │   ├── gen_grpc.py                     # IDL to .proto + gRPC server wrapper
    │   ├── gen_clients.py                  # IDL to client packages, both languages
    │   ├── new_service.py                  # scaffolder
    │   └── dev.sh                          # bring up the local stack
    │
    ├── tools/                              # internal helpers shared by scripts
    │
    └── .github/
        └── workflows/
            ├── ci.yml
            ├── codegen.yml
            └── deploy.yml

### Layout Conventions

Every Python distribution uses the `src/platform/...` layout. Tests live
in a `tests/` sibling, not inside the package. The test runner exercises
the installed package, which surfaces packaging bugs before deploy and
prevents accidental imports from the source tree during development.

IDL files live in `idl/`, not inside the Python package, because they
are not Python source. Generated code lands in
`src/platform/<svc>/_generated/`, with the leading underscore signalling
"do not hand-edit." Generated code is gitignored and rebuilt as a
prerequisite of every action that depends on it; the build step is fast
enough that this is cheaper than committing a noisy diff on every IDL
change.

> **Principle:** IDL belongs in `idl/`. Generated code belongs in
> `_generated/`, gitignored, rebuilt on demand.

The OM is one distribution, `platform-om`, covering every namespace.
Splitting into per-namespace distributions adds packaging overhead
without buying real release independence, since cross-namespace
dependencies move together anyway.

> **Principle:** The OM is one distribution. Namespaces are folders
> inside it, not separate packages.

Migrations live with the OM at `om/migrations/`. Tables live in
`platform.om.<ns>.storage.tables`, and the schema timeline is owned by
the OM, not by any single service. Alembic runs against one tree.

Workers, app-specific services, and domain services share the same
project shape: `pyproject.toml`, `Dockerfile`, `src/`, `tests/`,
`entrypoints/`. They differ only in role and in which top-level folder
they sit under. Workers have no `idl/`; the rest do.

Client packages are generated, one per language per service. Python
clients are full distributions in `clients/<tier>/<service>/python/`.
TypeScript clients live in `clients/<tier>/<service>/ts/` as
`@platform/<service>-client` packages, consumed by apps via the pnpm
workspace.

`scripts/` and `tools/` are separate on purpose. `scripts/` holds
runnable entry points (codegen, scaffolders, local dev orchestration).
`tools/` holds the helper libraries those scripts share.

Workspace tooling lives at the repo root. A single `pyproject.toml`
declares `[tool.uv.workspace]` members; a single `package.json` plus
`pnpm-workspace.yaml` declares the TypeScript members. Lint, type-check,
and pre-commit config live next to them, so a developer can run any of
them from the root and get consistent behavior across every project.

## 15. Client App Architecture

### Stack

The client stack is React + TypeScript on Vite. The portal builds to a
static SPA served behind the gateway. The desktop app is the same SPA
wrapped in Tauri, which uses the OS's native webview and keeps the
binary small. The CLI is Python and lives outside this stack; the
write-once rule applies only to the non-CLI apps.

Vite is the toolchain rather than Next.js. Next.js is built around SSR,
ISR, and SSG, and opting out of all of them still leaves us paying for
its mental model and its API-routes temptation. API routes in particular
invite teams to put backend logic in the app, which directly violates
Section 12's "Apps Are Dumb" rule. Vite is a pure SPA toolchain with no
opinion on rendering strategy, because none is needed.

> **Principle:** One React + TypeScript codebase for portal and desktop.
> The CLI stays Python. Mobile is deferred.

### No SSR

Rendering happens in the client only. There is no server-side rendering,
no incremental static regeneration, no edge rendering. The deployed
artifact is a static bundle that hydrates against backing services and
the realtime channel.

SSR would split "what the app does" across two runtimes, force dual
data-fetching paths, add operational surface for no return on an
enterprise B2B app, and break the bidirectional realtime channel
(sockets do not live on a server-rendered page). The gateway and the
realtime channel are the only network surfaces the bundle talks to.

> **Principle:** No server-side rendering. The app is a static bundle
> that talks to backing services and the realtime channel.

### One Codebase, Two Builds

The portal and the desktop app share the same source tree, the same
routes, the same components, and the same state. The web build is
`vite build`; the desktop build is `tauri build` over the same Vite
output. Anything platform-specific (filesystem access, native menus,
OS-level shortcuts) lives behind a small capability interface, with a
web impl that no-ops or falls back to web equivalents and a Tauri impl
that calls into Rust commands.

If mobile becomes a real need, the right call is React Native + React
Native Web with a shared component layer and explicit discipline about
which primitives are RN-compatible. Deferring that decision until it is
real keeps the current stack honest.

### State and Data

State splits along server-state vs client-state. Server state, the
things the backing services own, lives in TanStack Query: queries,
mutations, caching, invalidation, optimistic updates, retries. Client
state, the things only the UI knows about, lives in Zustand: selection,
modal flags, transient view configuration, anything that does not need
to be persisted by a service.

Redux is not used. Zustand replaces it for client state with less
ceremony, and TanStack Query replaces it for server state with a model
purpose-built for fetching, not for in-memory event sourcing. The two
together are the entire state stack.

Realtime envelopes push into both. A status update on the realtime
channel becomes an invalidation or a direct cache write in TanStack
Query, so the UI reacts the same way it would to a fresh fetch. A purely
UI-side push (presence ping, transient notification) becomes a Zustand
store entry. The envelope router from Section 12 dispatches into these
handlers, never directly into components.

> **Principle:** Zustand for client state, TanStack Query for server
> state. No Redux.

### Views, View-Models, Stores

Component code follows a hook-based MVVM split. The Model is generated
client types (Section 10), Zustand stores, and the TanStack Query cache.
The View-Model is custom hooks that combine queries, mutations, store
reads, and local logic into one ergonomic surface per view. The View is
functional React components that consume those hooks and render JSX,
with no fetches, mutations, or business decisions inside a component
file.

A view-model hook is the unit of testability. Components stay
declarative and shallow; tests target hooks where the data shape and
behavior actually live.

> **Principle:** Components render. View-model hooks decide. Stores and
> queries hold.

### Realtime: One Channel per App

The push-first rule from Section 12 holds without exception. Every push
the app receives, status updates, chat messages, presence changes,
notifications, rides the same WebSocket as a typed envelope. A second
channel for chat would double the connection lifecycle, the reconnect
logic, the presence-registry entries, and the ordering and backpressure
reasoning, in exchange for nothing the multiplex cannot already do. If
chat latency ever becomes a real concern, the fix is a faster broker
path, not a second socket.

> **Principle:** One realtime channel per app. Chat is an envelope type,
> not a separate channel.

### Feature Modules

Vendor-specific widgets, test-type-specific report tiles, and
persona-specific dashboard cards are the obvious extension surface for a
HIL testing product. A full plugin runtime (dynamic loading, module
federation, third-party distribution) is over-engineering for an
enterprise app of this shape. A small set of typed, build-time extension
points is right-sized.

The pattern: each extension point is a TypeScript interface
(`BenchWidget`, `ReportTile`, `DashboardCard`) defined in a shared
`@platform/extensions-api` package. Each extension is a module under
`apps/portal/src/extensions/...` that exports an object conforming to
its interface. A registry collects them at build time by convention (a
single index file re-exports everything). The shell looks up extensions
by id or by a match predicate, lazy-loads the module via dynamic import,
and gates visibility behind a feature flag (Section 16). When a feature
module is dropped, the registry shrinks and the shell carries on.

This is a plugin contract, not a plugin runtime. It gives us isolation
between feature modules and a clean place for vendor-specific code
without the operational weight of true dynamic loading.

> **Principle:** Extension points are typed contracts, registered at
> build time and lazy-loaded at runtime. No dynamic plugin runtime.

### The CLI Is Different

The CLI is a Python app. Its UI is the terminal, its state lives in the
process, and its realtime channel is a gRPC stream against `cli-web-svc`
(Section 10, Wait-for-Response vs Fire-and-Forget). Most of this section
does not apply to it. What does apply: dumb client, business logic on
the backend, push-first for long-running operations. Short commands wait
on correlation ids; long-running operations submit and listen for
completion envelopes.

## 16. Misc

A short set of conventions that apply across the system and did not fit
cleanly into any single earlier section.

### UUID v4 vs v7

Every id in the system is `uuid_v7`, not `uuid_v4`. Both are 128 bits
and globally unique in practice, but v7 prefixes its bits with a 48-bit
millisecond timestamp and fills the rest with randomness. That choice
earns its keep on every write and every range query.

Inserts into a B-tree index on a v7 id land at the tail of the tree
because the timestamp prefix orders lexicographically by insertion time.
Inserts on a v4 id scatter across the index, fragment pages, and
multiply write IO under load. Every OM entity lives in a relational DB
with its id as the primary key, so the difference is not hypothetical;
it shows up on every insert.

A cursor-based list of entities by creation time collapses to a single
range scan on the id column; v4 would need a compound cursor built from
`created_at` and id to break ties. Anyone reading a log line can also
eyeball roughly when the record was created from the id alone, which is
cheap triage.

> **Principle:** Every id is `uuid_v7`. Time-ordered inserts,
> time-ordered scans, and time-readable logs fall out of one choice.

### Exceptions

Every namespace has its own base exception rooted at
`PlatformException`. The root is a plain `Exception` subclass; each
namespace defines its own base under it, and concrete exceptions inherit
from the namespace base:

``` python
class PlatformException(Exception):
    """Root of every exception raised inside the platform."""


class BenchesException(PlatformException): ...


class HiltestingException(PlatformException): ...


class UserManagementException(PlatformException): ...


class BenchNotFound(BenchesException): ...


class BenchAlreadyReserved(BenchesException): ...
```

The shape has two uses. A caller at a boundary (gateway handler, worker
loop, test harness) catches `PlatformException` and knows the failure is
domain-originated and not a runtime crash. Translation to HTTP codes or
gRPC statuses happens at that boundary, not inside managers. Managers
raise domain exceptions and let the service impl decide how to present
them.

### Logs

Logging uses Python's standard `logging` module. It is the platform-wide
paradigm, not a FastAPI or framework-specific choice; every library in
our stack (FastAPI, uvicorn, SQLAlchemy, the HTTP client, workers)
either uses it or integrates with it. We do not bring in a competing
library.

Every module gets its logger with `logging.getLogger(__name__)`, so the
logger hierarchy mirrors the OM namespace tree. Formatting, level, and
sink are configured once at the app container's boot and never
overridden per module. Logs are JSON in cloud environments and
human-readable locally, switched by an env flag. Fields from `OpContext`
(org_id, user_id, app type, request id, idempotency key where present)
are attached through a logging filter installed at the same entry point
that builds the context, so operations never need to remember to include
them.

> **Principle:** Python's `logging` is the platform logger. Every module
> uses it; no module replaces it.

### Event and Metric Telemetry

Python does not have a built-in metrics or tracing framework the way it
has `logging`. The de facto standard is OpenTelemetry (OTel), a CNCF
project with a stable API, an official Python SDK, and
auto-instrumentation libraries for every major component in our stack.

We use OpenTelemetry directly, without a Platform wrapper. OTel is
itself the abstraction: metrics are counters, histograms, and gauges;
traces are spans; both are independent of the backend we ship data to
(Prometheus, Grafana, Datadog, Honeycomb, anything speaking OTLP).
Swapping backends is an exporter config change, not a code change.
Wrapping OTel in our own interface would re-teach the same concepts
under different names and buy nothing in return.

> **Principle:** Use OpenTelemetry directly for metrics and traces. The
> backend is a config detail; the API is stable.

### Feature Flags

There is no standard-library equivalent for feature flags in Python, so
we adopt a vendor SDK and use it directly. LaunchDarkly is the default
for commercial hosting; Unleash is the default when we want a
self-hosted OSS option. Both expose the same shape
(`client.variation(flag, context, default)`), both publish official
Python SDKs, and both handle local evaluation with offline fallbacks for
tests.

We do not wrap the SDK in a `PlatformFeatureFlagsInterface`. Feature
flags are one of the rare cases where the vendor SDK is itself the seam:
the client object is injectable, offline mode makes tests trivial, and a
migration between vendors is find-and-replace on one call site shape.
Adding a layer on top would hide a familiar API behind a custom one and
buy no portability we do not already have.

> **Principle:** Use a feature-flag vendor SDK directly. No Platform
> wrapper.
