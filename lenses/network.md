# Network

Group id: `network`. Covers Section 10 (The Network Layer) and Section
12 (Push-First Apps) of `architecture.md`.

This group judges how the system faces its callers: how services are
cut, what the gateway does once at the edge, what crosses the wire, and
how pushes reach an open socket. It leaves service interfaces, roots,
and call direction to `contracts`; credentials, tickets, request ids,
and the operator gate to `context`; consumer-side idempotency and
long-running orchestration to `async`; and the "Apps Are Dumb" rule to
`delivery`.

## NET-01 One process first, namespace boundaries from day one

**Principle.** A system starts as one API process with one router module and one wire-types module per OM namespace behind one gateway; growth into separate services must be mechanical because routers hold no business logic.

**Source.** Section 10, How It Starts and Where It Goes.

**Look for.** The layout of `routers/` and `types/` in the API process; whether each namespace has exactly one router module and one types module; whether a router body does anything beyond resolving the context, calling a manager, and projecting a result.

**Violation.** Routers grouped by screen or by client rather than by namespace; a router that reads storage, composes several managers with decisions between them, or holds state; namespaces whose wire types are scattered across modules.

**Severity.** medium

## NET-02 Services split along namespace lines

**Principle.** A web service is the scalability unit, one per major OM namespace, running with the whole OM in-process; a service-to-service call is rare and reserved for a workflow that exceeds one manager's scope.

**Source.** Section 10, Web Services as Scalability Units.

**Look for.** How services are named and what each one wraps; whether a service composes managers locally; the number and purpose of over-the-wire calls between services.

**Violation.** A service that wraps several unrelated namespaces or a slice of one; a service that calls another service for something its own managers could do in-process; a service cut along team or client lines instead of namespace lines.

**Severity.** medium

## NET-03 Domain services and app-specific services stay distinct

**Principle.** Domain services expose one namespace to any caller; an app-specific service composes domain services for exactly one client app, stays thin, and holds only logic meaningful to that app, with the app type explicit on the context.

**Source.** Section 10, Domain Services vs App-Specific Services.

**Look for.** Which callers each service accepts; where per-app aggregation and session shaping live; whether app-aware branches read the app type from the context or guess from headers or paths.

**Violation.** Business rules inside an app-specific service; a domain service with branches keyed on which app is calling; an app-specific service used by a second app; app-specific behavior decided from anything other than the context's app type.

**Severity.** medium

## NET-04 Domain services are stateless

**Principle.** A domain service holds nothing that exists nowhere else; anything in its memory must be rebuildable from storage, cache, or queues, so a replica can be killed and replaced at any time.

**Source.** Section 10, Stateless vs Stateful Services.

**Look for.** Module-level and instance-level mutable state in service processes; in-memory maps of sessions, users, or in-flight work; anything written to memory that is not also written to a durable source.

**Violation.** A service that remembers a user's progress, a pending operation, or a session only in RAM; a process whose restart loses information; a warm cache that is the only copy of a computed result.

**Severity.** high

## NET-05 A stateful edge holds only the socket, its subscriptions, and a bounded buffer

**Principle.** A service that holds long-lived connections keeps in memory the open socket, the subscriptions the client registered, and a bounded buffer of frames waiting to be written, and nothing else.

**Source.** Section 10, Stateless vs Stateful Services; Realtime at the Edge.

**Look for.** The per-connection state kept by the socket handler; whether session data, preferences, or accumulated context live next to the socket; whether the outbound buffer has a fixed capacity.

**Violation.** Per-socket objects that accumulate user context or partial results; an unbounded outbound queue; state recovered from the socket handler instead of from storage after a reconnect.

**Severity.** high

## NET-06 The gateway is the only public surface and builds the context once

**Principle.** The gateway authenticates requests, builds the context, and routes; services never construct a context from raw headers or tokens, and by the time a service method runs the context is fully populated.

**Source.** Section 10, The Gateway.

**Look for.** Where bearer tokens and headers are parsed; whether any router, service impl, or manager reads `Authorization` or an app header itself; whether a second path to the internet bypasses the gateway.

**Violation.** A router that inspects headers to decide who is calling; a service that builds or patches a context; an endpoint reachable without passing the gateway's dependencies.

**Severity.** high

## NET-07 One error handler, one envelope

**Principle.** One handler translates `PlatformException` into `{"error": {"code", "message", "request_id"}}` with the status the exception carries, one catch-all turns anything else into a 500 in the same shape, and routers never set error status codes.

**Source.** Section 10, The Gateway (Error envelope).

**Look for.** The registered exception handlers; `try`/`except` blocks in routers that map exceptions to responses; ad hoc error bodies; whether the request id is present in every error response.

**Violation.** A router raising an HTTP exception with a hand-picked status; error bodies with different shapes on different routes; a 500 that leaks a stack trace or lacks the request id; more than one mapping from domain exceptions to statuses.

**Severity.** medium

## NET-08 Rate limits are a per-route dependency on the shared counter

**Principle.** A rate limit is a per-route dependency counting in the shared cache so replicas share one budget; the subject is the credential id, the client address for unauthenticated routes, or a digest of the path token for inbound webhooks; a rejection is 429 with `Retry-After` and the error envelope; limits fail open.

**Source.** Section 10, The Gateway (Rate limits).

**Look for.** How limits are declared per route; which key identifies the subject; what happens when the cache is unreachable; the response shape on rejection.

**Violation.** Per-process counters in a multi-replica deployment; a limit keyed on a raw secret; a rejection without `Retry-After` or outside the envelope; a limit that rejects every request when the cache is down; a rate limit relied on as a security boundary.

**Severity.** medium

## NET-09 Creating requests accept an idempotency key

**Principle.** A creating `POST` accepts an `Idempotency-Key` header; the first response is stored per tenant under the key and replayed on a retry, using the same storage primitive the queue handlers use.

**Source.** Section 10, The Gateway (Edge idempotency).

**Look for.** Creating endpoints and whether they read the header; where the stored response is keyed; whether the key is scoped to the tenant.

**Violation.** A creating endpoint that produces a second record on a retried request; a key stored without the tenant in its scope; a bespoke replay mechanism for one route that differs from the shared primitive.

**Severity.** medium

## NET-10 Health, readiness, and metrics live outside the versioned API

**Principle.** `/healthz` answers liveness with the version and no I/O, `/readyz` awaits the storage healthcheck, `/metrics` exposes counters and histograms, and the API prefix is applied once where routers are mounted.

**Source.** Section 10, The Gateway (Health, Versioning).

**Look for.** The three operational endpoints and what each does; whether liveness touches a dependency; where the version prefix is declared.

**Violation.** A liveness check that queries the database; readiness that returns ok without checking storage; operational endpoints under the versioned prefix; routers that repeat the version prefix in their own paths.

**Severity.** low

## NET-11 The gateway verifies; the tenancy domain owns identity

**Principle.** The gateway verifies credentials and asks the tenancy manager for the principal behind them; organizations, identities, users, memberships, teams, credentials, sessions, and invitations are a regular namespace with types, a manager, and storage.

**Source.** Section 10, Auth: the Gateway Verifies, the Tenancy Domain Owns.

**Look for.** Where signup, invitation, role management, key rotation, and session refresh are implemented; whether the gateway holds its own user or token tables.

**Violation.** Identity logic inside gateway middleware; credential tables owned by the gateway rather than the tenancy namespace; a manager that cannot be tested without the HTTP layer.

**Severity.** medium

## NET-12 Plain intra-service traffic, operating-system trust for outbound

**Principle.** Service-to-service calls stay on the private network without TLS; managed backends that require TLS get it as a connection string; outbound TLS verification uses the operating system's trust store in every process.

**Source.** Section 10, Intra-Service Communication.

**Look for.** Certificate handling in service impls; how HTTP clients are constructed; whether a bundled certificate store is used instead of the system's.

**Violation.** Certificate rotation logic inside a service; an HTTP client pinned to a bundled CA set so a corporate proxy or private CA fails; TLS configured per component instead of once at boot.

**Severity.** low

## NET-13 Wire types are curated, immutable, and hand-written

**Principle.** Wire types are hand-written on two bases, a frozen `View` built from attributes and a `Request` that forbids unknown fields; names end in `View`, `Request`, or `Issued...View`; lists return a bare list with a clamped limit and streams page by `after_seq`; the OM never changes to match the wire.

**Source.** Section 10, Public Types.

**Look for.** The `types/` modules and their base classes; whether entities are returned directly from routers; naming of request and response classes; list endpoints and their paging parameters.

**Violation.** An OM entity serialized straight onto the wire; a view that is mutable or built by hand field by field where attributes line up; a request that silently ignores unknown keys; an OM field added or renamed to suit a client; offset paging on an append-only stream.

**Severity.** medium

## NET-14 The OpenAPI document is emitted, committed, and diffed

**Principle.** The running app emits the OpenAPI document; it is committed, and CI regenerates it and fails on a diff, so a change to the API surface shows in the document in the same pull request.

**Source.** Section 10, From OM to Wire.

**Look for.** The committed document and the make target that regenerates it; the CI job that compares; whether the document is authored by hand anywhere.

**Violation.** A view changed without the committed document changing; a hand-maintained schema file next to the code; no CI check on the document.

**Severity.** medium

## NET-15 One client per language per service

**Principle.** Each language gets one client for a service: generated types in one file, a curated facade re-exporting the names feature code uses, and one small hand-written transport client that knows the error envelope and the request id.

**Source.** Section 10, Clients Live in One Place.

**Look for.** Where types are generated; whether feature code imports generated paths directly; how many places call the transport; whether a consumer built its own client.

**Violation.** Two clients for the same service in one language; feature code importing the generated schema module; raw HTTP calls scattered through features; a client that does not parse the error envelope.

**Severity.** medium

## NET-16 Pushes travel on the bus and are filtered at the socket

**Principle.** Every process holding sockets subscribes to the topics its clients care about; a producer publishes once; each socket handler filters by tenant and by the client's subscriptions. A presence store replaces the broadcast only when the fleet grows past it.

**Source.** Section 10, Realtime at the Edge.

**Look for.** How a push reaches the process with the right socket; whether producers look anything up before publishing; the filtering in socket handlers.

**Violation.** A producer that must know which replica holds a user; a registry kept in sync by hand in a small fleet; a socket handler that forwards events from other tenants or ignores the client's subscriptions.

**Severity.** high

## NET-17 The socket is a hint; storage is the truth

**Principle.** Each socket has one bounded in-memory outbox drained by a task; when it is full the oldest frame is dropped and logged; every push is also a record, and a reconnecting client asks for everything after the last sequence it saw.

**Source.** Section 10, Realtime at the Edge.

**Look for.** The outbox capacity and overflow behavior; whether every pushed event has a durable record; the reconnect path and its `after_seq` parameter.

**Violation.** A push that exists only as a frame; an outbox that grows without bound or blocks the producer; a client that cannot recover missed events after a reconnect.

**Severity.** high

## NET-18 Inbound socket traffic is subscribe, unsubscribe, and ping

**Principle.** Commands travel over REST, where they get the error envelope, the rate limit, and the idempotency key; the socket carries only subscription management and keepalives inbound.

**Source.** Section 10, Realtime at the Edge.

**Look for.** The set of inbound message types the socket handler accepts; whether any mutation is performed from a socket frame.

**Violation.** A create or update issued over the socket; a socket message type that bypasses authorization or rate limiting a REST route would apply.

**Severity.** medium

## NET-19 Waiting is the client's choice; the server answers the same way

**Principle.** The choice between waiting and not waiting is made per operation at the client; a long operation returns an acknowledgement with an id and completes with a push, and the server produces responses and notifications the same way in both cases.

**Source.** Section 10, Wait-for-Response vs Fire-and-Forget.

**Look for.** Endpoints that start long work and what they return; whether a request blocks for minutes; how a CLI follows an operation to completion.

**Violation.** A request that holds the connection for the duration of a long task; two server code paths for the same operation depending on the caller's patience; a portal that polls a status endpoint on a timer.

**Severity.** medium

## NET-20 One realtime channel per app, typed envelopes routed by type

**Principle.** The moment any corner of an app wants a push, the app earns one persistent bidirectional channel; every push rides it as a typed envelope routed by type, and a new kind of push is a new envelope type, not a new connection.

**Source.** Section 12, Push-First Apps.

**Look for.** The number of sockets or streams an app opens; how envelopes are discriminated; whether a feature added its own transport for updates.

**Violation.** A second WebSocket or SSE stream for one feature; a polling endpoint next to an open channel; envelopes without a type field or routed by ad hoc inspection.

**Severity.** high

## NET-21 The channel degrades and its timeouts are pinned

**Principle.** The client reconnects with exponential backoff, and after more than one failed cycle shows a banner and polls slowly until the socket returns; the ping interval and the load balancer idle timeout live in one shared file that both a server test and a client test assert against.

**Source.** Section 12, Push-First Apps.

**Look for.** The reconnect logic and its backoff; the fallback behavior when the socket stays down; where keepalive and idle timeout values are defined and which tests read them.

**Violation.** Immediate tight reconnect loops; a client that shows stale data silently when the socket is gone; a ping interval and an idle timeout defined in two places that can drift in separate changes.

**Severity.** medium
