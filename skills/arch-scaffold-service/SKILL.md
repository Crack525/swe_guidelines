---
name: arch-scaffold-service
description: "Create a web service the way the Software Design and Architecture Guidelines prescribe, either the first API process of a system or a domain or app-specific service split out of it: the app factory, container, gateway, per-namespace routers and wire types, service interfaces, health endpoints, the ops CLI entry point, the image, and tests. Stack: Python (FastAPI, Pydantic, SQLAlchemy)."
allowed-tools: Read, Grep, Glob, Write, Edit, Bash(make check), Bash(make test-unit), Bash(make openapi), Bash(uv run:*), Bash(uv sync:*), Bash(git status:*), Bash(git diff:*)
---

# arch-scaffold-service

Conventions: `${CLAUDE_SKILL_DIR}/../_shared/scaffold-conventions.md`.
Sections of `${CLAUDE_SKILL_DIR}/../../architecture.md`: 10 (How It
Starts and Where It Goes, Domain Services vs App-Specific Services,
Service Interfaces and Impls, The Gateway, Public Types, Realtime at
the Edge), 14 (Layout Conventions), 16 (Exceptions, Configuration, The
App Container).

## Input

`[service-name] [--namespaces ns1,ns2] [--app portal|admin|cli] [--realtime] [--container]`

`<service-name>` defaults to `api`. With no flags the service hosts
every existing namespace: the first API process of a system.
`--namespaces` makes a domain service hosting only those namespaces.
`--app` makes an app-specific service that composes domain operations
for one app; it sets `AppType.<APP>` on every context it builds and the
gateway rejects a request whose app header names another app.
`--realtime` adds the realtime channel; without it the service has no
socket, and the portal cannot connect to it until one is added.
`--container` adds the service to the local compose file; without it
`scripts/dev.sh` starts it on the host.

`<svc>` is the service name in snake case.

## Created

Under `services/<service-name>/`:

| File                                          | Holds                                                                                          |
|-----------------------------------------------|------------------------------------------------------------------------------------------------|
| `pyproject.toml`                              | the distribution; dependencies on `<root>-om`, `<root>-infra`, `fastapi`, `uvicorn`, `pydantic-settings`, `httpx` (dev); `[tool.uv.sources]` for the workspace members; a console entry point |
| `src/<root>/services/<svc>/__init__.py`       | empty                                                                                          |
| `src/<root>/services/<svc>/settings.py`       | one `BaseSettings` with the product prefix, including `app_type` for `--app`                    |
| `src/<root>/services/<svc>/container.py`      | `AppContainer.build(settings)` (storage, then infra, then managers), `for_tests(storage, infra)`, `start()`, `close()` |
| `src/<root>/services/<svc>/app.py`            | `create_app(container=None)`: settings, logging, trust store, tracing, then middleware in fixed order, routers under `/v1`, health routes, lifespan calling `start()` and `close()` |
| `src/<root>/services/<svc>/gateway/__init__.py` | empty                                                                                        |
| `src/<root>/services/<svc>/gateway/auth.py`   | credential parsing by prefix, `current_context` dependency, `Ctx` alias, the app-header check   |
| `src/<root>/services/<svc>/gateway/admin.py`  | the operator gate producing `AdminContext` for `/v1/admin/*`, `AdminCtx` alias                  |
| `src/<root>/services/<svc>/gateway/errors.py` | the `PlatformException` handler and the catch-all, both writing `{"error": {code, message, request_id}}` |
| `src/<root>/services/<svc>/gateway/ratelimit.py` | `rate_limited(route, limit, window)` over `CacheInterface.increment`, failing open           |
| `src/<root>/services/<svc>/gateway/idempotency.py` | the `Idempotency-Key` dependency: store the first response per tenant, replay on a retry   |
| `src/<root>/services/<svc>/gateway/observability.py` | request id middleware (accept or mint, stamp, echo, log context, span), metrics            |
| `src/<root>/services/<svc>/routers/__init__.py` | `all_routers()`                                                                              |
| `src/<root>/services/<svc>/routers/<ns>.py`   | one module per hosted namespace, translating only                                              |
| `src/<root>/services/<svc>/types/common.py`   | `View`, `RequestBody`, `ErrorBody`, `ErrorResponse`                                            |
| `src/<root>/services/<svc>/types/<ns>.py`     | views and requests per hosted namespace                                                        |
| `src/<root>/services/<svc>/services/<ns>.py` (with `--namespaces` or `--app`) | `<Ns>ServiceInterface`, the operations a sibling service may call             |
| `src/<root>/services/<svc>/impl/<ns>.py` (with `--namespaces` or `--app`) | `<Ns>ServiceImpl`, composing managers and sibling service clients; the routers delegate to it |
| `src/<root>/services/<svc>/realtime/` (with `--realtime`) | `ticket.py` (mint and redeem the single-use ticket), `socket.py` (the route, subscribe, unsubscribe, ping), `outbox.py` (the bounded per-socket outbox and drainer), `envelopes.py` |
| `src/<root>/services/<svc>/main.py`           | `serve`, `migrate`, `bootstrap`, `openapi` subcommands                                          |
| `tests/conftest.py`                           | the app over `AppContainer.for_tests(MemoryStorage(), LocalInfra(tmp))` and `httpx.AsyncClient(transport=ASGITransport(app=app))`, run inside the lifespan |
| `tests/test_health.py`                        | `/healthz` and `/readyz`                                                                        |
| `tests/test_<ns>_api.py`                      | one round trip per hosted namespace, plus the error envelope and one rate-limited route         |
| `deployment/docker/<service-name>.Dockerfile` | two stages, locked install of this package, non-root, healthcheck on `/healthz`                |

In the single-process start the routers are the impl, so
`services/<ns>.py` and `impl/<ns>.py` appear only with `--namespaces`
or `--app`, at the first split.

## Changed

| File                                    | Change                                                                          |
|-----------------------------------------|---------------------------------------------------------------------------------|
| `pyproject.toml` (root)                 | the member added to `[tool.uv.workspace] members`                                |
| `Makefile`                              | the `openapi` target emits this service's document into the apps that consume it |
| `scripts/dev.sh`                        | starts the service on its port                                                   |
| `deployment/local/docker-compose.full.yml` (with `--container`) | the service as a container                                 |
| `services/<existing>/gateway/` (when a service already exists) | moved into a workspace distribution `gateway/` that every service imports; nothing is copied |

## Procedure

1. Write the container before the app, the app before the routers.
2. A router function resolves `ctx`, builds the entity or the arguments
   from the request, calls one manager (or the service impl, at a
   split), and projects the result onto a view. When one starts
   deciding, move the decision into a manager and say so in the output.
3. An app-specific service composes managers or sibling domain service
   clients for one app only and never calls another app-specific
   service.
4. Emit the OpenAPI document with `make openapi` so the consuming apps
   regenerate their types.

## Output

As `${CLAUDE_SKILL_DIR}/../_shared/scaffold-conventions.md` states.
