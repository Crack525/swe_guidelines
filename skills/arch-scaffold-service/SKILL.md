---
name: arch-scaffold-service
description: Create a web service the way the Software Design and Architecture Guidelines prescribe, either the first API process of a system or a new domain or app-specific service split out of it. Creates the app factory, container, gateway (auth, errors, rate limits, request id), per-namespace routers and wire types, health endpoints, the ops CLI entry point, the Dockerfile, and tests. Python only (FastAPI, Pydantic).
allowed-tools: Read Grep Glob Write Edit Bash(make *) Bash(uv run *) Bash(ls *) Bash(git status *) Bash(git diff *)
---

# arch-scaffold-service

Follow `${CLAUDE_SKILL_DIR}/../_shared/scaffold-conventions.md` first.
Sections that shape this skill: 10 (The Network Layer), 14 (Layout
Conventions), 16 (Exceptions, Configuration, The App Container) of
`${CLAUDE_SKILL_DIR}/../../architecture.md`.

## Input

`$ARGUMENTS`: `<service-name> [--namespaces ns1,ns2] [--app portal|cli]`.

- No flags: the first API process (`services/api/`) hosting every
  existing namespace.
- `--namespaces`: a domain service hosting only those namespaces.
- `--app`: an app-specific service that composes domain operations for
  one app and carries that app's type on every context.

## Files

Under `services/<service-name>/`:

| File                                     | Holds                                                                 |
|------------------------------------------|-----------------------------------------------------------------------|
| `pyproject.toml`                         | the distribution, depending on the OM and infra distributions, and a console entry point |
| `src/<root>/services/<svc>/app.py`       | `create_app(container=None)`: settings, logging, trust store, tracing, middleware in fixed order, routers under `/v1`, health routes |
| `src/<root>/services/<svc>/container.py` | `AppContainer.build(settings)` (storage, infra, managers), `for_tests(...)`, `start()`, `close()` |
| `src/<root>/services/<svc>/settings.py`  | one `BaseSettings` with the product prefix                            |
| `src/<root>/services/<svc>/gateway/auth.py` | credential parsing by prefix, `current_context` dependency, `Ctx` alias |
| `src/<root>/services/<svc>/gateway/errors.py` | the two exception handlers and the error envelope                  |
| `src/<root>/services/<svc>/gateway/ratelimit.py` | `rate_limited(route, limit, window)` over `CacheInterface.increment` |
| `src/<root>/services/<svc>/gateway/observability.py` | request id middleware, metrics, span per request              |
| `src/<root>/services/<svc>/routers/__init__.py` | `all_routers()`                                                  |
| `src/<root>/services/<svc>/routers/<ns>.py` | one module per namespace, translating only                         |
| `src/<root>/services/<svc>/types/common.py` | `View`, `RequestBody`, `ErrorBody`, `ErrorResponse`                |
| `src/<root>/services/<svc>/types/<ns>.py` | views and requests per namespace                                     |
| `src/<root>/services/<svc>/main.py`      | `serve`, `migrate`, `bootstrap`, `openapi` subcommands                |
| `tests/conftest.py`                      | the app over `AppContainer.for_tests(MemoryStorage(), LocalInfra(tmp))` and an in-process HTTP client |
| `tests/test_health.py`, `tests/test_<ns>_api.py` | health routes, and one round trip per namespace              |
| `deployment/docker/<svc>.Dockerfile`     | two stages, locked install of this package, non-root, healthcheck     |

Changed: the root workspace members, the Makefile's `openapi` target
(the emitted document is committed next to the app that consumes it),
and the local compose file when the service must run in a container.

## Procedure

1. When a service already exists, copy its gateway package rather than
   writing a second one; the gateway is the same code in every service.
2. Write the container before the app, the app before the routers.
3. A router function resolves `ctx`, builds the entity or arguments
   from the request, calls one manager, projects to a view. When one
   starts deciding, move the decision into a manager and note it in
   the output.
4. An app-specific service (`--app`) composes managers or domain
   service clients for one app only and never calls a sibling
   app-specific service.
5. Emit the OpenAPI document and commit-ready generated types for the
   apps that consume this service, if the repository has that step.
6. Run the fast gate and the service's own tests.

## Output

The file list and command outcomes, as the conventions state.
