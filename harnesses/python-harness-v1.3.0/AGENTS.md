# Python Harness catalog rules

This file is a flattened copy of every upstream `*.mdc` rule from catalog version `1.3.0` at commit `86952fdb7160388f7a0fb742e45e58d5def9cac6`. It is mounted as the workspace `AGENTS.md` for agents that do not consume editor rule files. Apply only guidance relevant to the repository and task; task requirements and existing conventions take precedence.

## `python-alembic/python-alembic.mdc`

---
description: Alembic migrations — async env.py, autogenerate from ORM models, versions outside project/
globs:
  - "**/alembic.ini"
  - "**/alembic/env.py"
  - "**/alembic/versions/*.py"
  - "**/alembic/script.py.mako"
alwaysApply: false
---

# Alembic migrations

Pair with `python-sqlalchemy` and `python-db-sessions`. Skip this harness when the repo creates
tables from metadata only
(`create_all` / `create_all_tables`). CLI and autogenerate behaviour come from Alembic
(https://alembic.sqlalchemy.org/en/latest/tutorial.html); this rule owns layout.

If `alembic/` is missing and the repo should migrate: `uv add alembic`, then
`uv run alembic init -t async alembic`. Copy sibling `ENV.md` into `alembic/env.py` when that
file is still the stock template. Leave `sqlalchemy.url` unset in `alembic.ini`. Keep stock
`script.py.mako`. Default package root is `project/`.

## Commands (`uv run`)

| Need | Command |
|---|---|
| Autogenerate | `uv run alembic revision --autogenerate -m "…"` |
| Empty revision | `uv run alembic revision -m "…"` |
| Apply | `uv run alembic upgrade head` |
| Roll back one | `uv run alembic downgrade -1` |
| Current | `uv run alembic current` |
| History | `uv run alembic history` |

After every ORM model change, autogenerate, **review** the script, then `upgrade head`.
Autogenerate cannot see renames (they look like drop + add). Drop accidental `drop_table` /
`drop_column` / type rewrites before applying.

Downgrade before switching to a branch whose revisions lag.

## Layout

- Revision scripts live in `alembic/versions/`, not under `project/`.
- Do not import Alembic from application layers (`layers.toml` already bans it).
- DSN from `Settings().get_database_dsn()` (`SQLALCHEMY_DATABASE_DSN` or assembled `DB_*`),
  not from `alembic.ini`.
- Online migrations: `create_async_engine` + `connection.run_sync` (async SQLAlchemy / `asyncpg`).
- Import `project/components/**/models.py` so autogenerate sees tables. Do not rglob every `.py`.
- `target_metadata`: shared `MetaData` / `Base` in `project.base.models` when that
  module exists (`public_schema` or `Base.metadata`); otherwise the repo's existing `Base.metadata`.

## `python-base-client/python-base-client.mdc`

---
description: Outbound HTTP adapters — choose httpx AsyncApi or SyncApi, AppError mapping, retries
globs:
  - "**/infrastructure/base/http_client.py"
  - "**/adapters/*.py"
alwaysApply: false
---

# Outbound HTTP adapters

Choose one implementation for `project/infrastructure/base/http_client.py`:

- async service: copy sibling `ASYNC_CLIENT.md` (`httpx.AsyncClient`, orjson, llm_common);
- sync service: copy sibling `SYNC_CLIENT.md` (`httpx.Client`, orjson, llm_common).

Install only the implementation the developer selects; do not combine both clients in one module.
New external HTTP API → a module under `project/infrastructure/adapters/`. Subclass or compose the
selected `AsyncApi` or `SyncApi`. `layers.toml`: `http_client` is **adapters**, not presentation.

When httpx needs a level different from root, add `HTTP_REQUESTS_LOG_LEVEL` to
`SettingsValidator` and configure `httpx` and `httpcore` with it (`python-development-rules`).

`name_for_monitoring` is required (API clients suffix `_api`). When the path is dynamic, pass
`resource_for_monitoring` as a template with no IDs (`invoices/{invoice_id}`, not `invoices/123`).

## Errors

Map in `error_handling` so domain code never sees httpx exceptions (`python-exceptions`):

| Failure | Raise |
|---|---|
| 4xx | `ClientError` |
| 5xx | `ServerError` |
| Other HTTP status | `ExternalApiError` |
| Transport / timeout | `ExternalHTTPConnectionError` |

Per-adapter subclasses of those types are optional. Override `error_handling` / `process_response` /
`response_to_native` when the API needs extra mapping. HTTP status is `response.status_code`.

## Session and JSON

Reuse connections with `async with client.api.Session():` (or `with` for `SyncApi`). Decode JSON with
orjson. Do not call `raise_for_status` — status mapping lives in `error_handling`.

```python
class InvoicesClient:
    def __init__(self, token: str) -> None:
        self.api = AsyncApi(
            "https://api.example.com",
            name_for_monitoring="invoices_api",
            headers={"Authorization": f"Bearer {token}"},
        )

    async def get_invoice(self, invoice_id: str) -> dict:
        return await self.api.call_endpoint(
            f"invoices/{invoice_id}",
            resource_for_monitoring="invoices/{invoice_id}",
        )
```

## Retry

Use the decorators from `project.libs.retry` (`python-retry`) on the adapter method, not inside
`call_endpoint`. Retry only transport errors and 5xx responses; do not retry 4xx `ClientError`.
The same decorator supports sync and async functions.

```python
from project.exceptions import ExternalHTTPConnectionError, ServerError
from project.libs.retry import retry_on_exception


class InvoicesClient:
    @retry_on_exception(
        (ExternalHTTPConnectionError, ServerError),
        max_attempts=3,
        delay=1,
        backoff=2,
    )
    async def get_invoice(self, invoice_id: str) -> dict:
        return await self.api.call_endpoint(f"invoices/{invoice_id}")
```

For the sync client, keep the decorator and remove only `async` / `await`:

```python
    @retry_on_exception(
        (ExternalHTTPConnectionError, ServerError),
        max_attempts=3,
        delay=1,
        backoff=2,
    )
    def get_invoice(self, invoice_id: str) -> dict:
        return self.api.call_endpoint(f"invoices/{invoice_id}")
```

Use `retry_unless_exception` only when retrying unknown failures is intentional. List every
non-retryable application error explicitly.

## Monitoring

`call_endpoint` notifies `Callback` methods: `request_callback`, `response_callback`,
`error_callback`, `response_data_callback`. Default callbacks are `LoggingCallback` and
`TelemetryCallback` (`is_build_metrics` / `http_tracking`). Subclass `Callback` for extra
observation; do not put logs or metrics back into `call_endpoint`. Do not also wrap the selected
session with another monitored client (double-count). Use `HttpxClientWithMonitoring` only when you
need a tracked httpx client **without** this AppError mapping.

## Tests

Mock outbound calls with `httpx_responses` (`python-tests`). Do not `patch` httpx or the adapter.
Stub the adapter in use-case tests via `Container.local(...)`.

## `python-db-sessions/python-db-sessions.mdc`

---
description: Async SQLAlchemy engine, sessions, transactions, and database settings
globs:
  - "**/adapters/database.py"
  - "**/settings.py"
alwaysApply: false
---

# Database sessions

Runtime: SQLAlchemy 2 async (`asyncpg`). One adapter module owns the engine and session lifecycle.
If it is missing, copy sibling `DATABASE.md` into
`project/infrastructure/adapters/database.py` and merge its Settings contract into `settings.py`
(`python-settings`).

| Need | Call |
|---|---|
| Read | `async with asession() as session` |
| Write / commit | `async with atransaction() as session` |
| Nested write inside an open tx | `atransaction()` → savepoint |
| Join the open tx, or begin if none | `current_atransaction()` |
| Create schema in tests/e2e | `create_all_tables(metadata)` |
| After DSN / Settings override | `aengine_factory.cache_clear()` and `async_sessionmaker_factory.cache_clear()` |

`asession()` reuses the `ContextVar` session or opens and closes one.
`atransaction()` begins a transaction, or a savepoint when one is already active.
Do not call `session.commit()` / `session.close()` inside these helpers.

Cache the engine for one process-wide connection pool. Cache the sessionmaker only so it remains
bound to that engine. Never cache `AsyncSession`; `asession()` owns ContextVar reuse.

Get the DSN from `Settings().get_database_dsn()` (`SQLALCHEMY_DATABASE_DSN` or assembled `DB_*`).
Optional `DB_SCHEMA` becomes `search_path`; pass `DATABASE_PRE_PING` to the engine. If persistence
is optional, check `database_is_configured()` instead of failing at import time.

Repositories import session helpers. Services and use cases do not open sessions. A use case that
must write through several repositories wraps the calls in one `atransaction()`.

Tests use Testcontainers Postgres, schema creation through ORM metadata, and one nested transaction
with rollback per test (`python-tests` / `CONFTEST_DATABASE.md`). After a DSN override, clear the
engine and sessionmaker caches.

When `python-monitoring` is installed, register the engine after metrics initialization with
`register_sqlalchemy_engine_monitoring(engine, database="…")`.

## `python-development-rules/python-development-rules.mdc`

---
description: General Python development rules — helpers, context managers, bounded concurrency, configurable logging
alwaysApply: true
---

# Python development rules

## Module exports

Do not add `__all__` to modules by default. Keep the public surface implicit through
module names that do not start with `_`; use a leading underscore for private helpers.
Add `__all__` only when a concrete compatibility or tooling requirement calls for it.

## Context managers

Create context managers as generator functions decorated with `contextlib.contextmanager`
or `contextlib.asynccontextmanager`. Do not implement class-based context managers with
`__enter__` / `__exit__` or `__aenter__` / `__aexit__`.

## Workflow helpers

Before writing state-transition checks or retry loops, load the matching installed rule:

| Need | Use | Read before designing |
|---|---|---|
| Finite persisted lifecycle with state-dependent operations | `StateMachine` / `AsyncStateMachine` | `.cursor/rules/python-fsm/python-fsm.mdc` |
| Retry transient adapter I/O | `retry_on_exception` / `retry_unless_exception` | `.cursor/rules/python-retry/python-retry.mdc` |

Use ordinary conditionals for independent flags or a lifecycle without a meaningful
transition graph. Put retries around the smallest independently repeatable adapter operation;
writes require idempotency, and each attempt requires its own timeout. Apply the detailed rule
before implementing or reviewing either pattern, even when editing a caller rather than
`project/libs/fsm.py` or `project/libs/retry.py`.

## Bounded concurrency

Run independent asynchronous tasks concurrently whenever they can be parallelized. Create one
shared `asyncio.Semaphore` per constrained resource and reuse it across batches so concurrency is
always bounded. Define the positive limit as a descriptive `*_CONCURRENCY_LIMIT` field on
`SettingsValidator` and construct the semaphore with `Settings().<FIELD>`; never hardcode the
limit or create a separate semaphore inside each task.

Create semaphores lazily in `project/semaphores.py` using `LazyInit` from `python-di`. Name each
property after the constrained resource, not after the numeric limit:

```python
import asyncio
from functools import cached_property

from project.libs.structures import LazyInit
from project.settings import Settings


class SemaphoresContainer:
    @cached_property
    def external_api_requests(self) -> asyncio.Semaphore:
        return asyncio.Semaphore(Settings().EXTERNAL_API_CONCURRENCY_LIMIT)


Semaphores = LazyInit(SemaphoresContainer)
```

Acquire the shared semaphore only around the operation whose concurrency it limits:

```python
async with Semaphores().external_api_requests:
    response = await client.get(url)
```

Keep tasks sequential when one depends on another's result or when their shared state requires
ordering.

## Configurable logging

When a module or library needs a log level different from root, add a descriptive
`*_LOG_LEVEL` field to `SettingsValidator` and pass `Settings().<FIELD>` to its named logger
configuration. This keeps every log level configurable through environment-backed Settings.

```python
class SettingsValidator(BaseSettings):
    HTTP_LOG_LEVEL: str = "INFO"


config = {
    ...
    "loggers": {
        "httpx": {
            {
              "level": Settings().HTTP_LOG_LEVEL,
              "handlers": [],
              "propagate": True,
          }
        }
    },
    ...
}
```

The rule that owns the technology chooses the Settings field and logger names. Use the root
`Settings().LOG_LEVEL` when a separate level is unnecessary.

## `python-di/python-di.mdc`

---
description: No process globals — LazyInit, LazyService, Container
alwaysApply: true
---

# LazyInit, Container

Do not keep service instances in module globals. Create them lazily at first use.

`Container = LazyInit(Services)` lives in `project/container.py`.
Implementation: `project/libs/structures.py`.
If those types are missing, copy sibling `STRUCTURES.md` into `project/libs/structures.py`
before introducing new singletons.

Env config is `Settings = LazyInit(SettingsValidator)` in `project/settings.py` — see `python-settings`.

## Call through the proxy

```python
Container().job_store   # access dependencies through the proxy
```

Call a dependency inline when it is used once:

```python
user = await Container().user_repository.get_by_id(user_id)
```

Introduce a local dependency variable only when the same dependency is used more than once.
Keep `Container()` at the **point of use** rather than binding the proxy or storing it on `self`.
Take infrastructure clients from `Container()` instead of constructing them inside a service.
Request schemas and other value objects may be created locally.

```python
class AskUseCase:
    async def ask(self, user_id: int, question: str) -> str:
        user = await Container().repo.get(user_id)
        return await Container().chat.create_answer(user, question)
```

```python
class Services:
    def __init__(self, **overrides):
        self.__dict__.update(overrides)

    repo = LazyService("project.components.repo:Repository")
    chat = LazyService("project.components.chat:ChatService")

Container = LazyInit(Services)
```

`LazyService` accepts `module.path:ClassName` (import on first access, no cycles) or a factory
`lambda services: …`. One `Services` instance per process; each service is created once.

A client that is **not** in the container may use `@functools.cache` on a factory function.
Components still prefer `Container`.

```python
from functools import cache

@cache
def weather_client() -> WeatherClient:
    return WeatherClient(api_key=Settings().WEATHER_API_KEY.get_secret_value())
```

## Tests

- `Container.local(**kwargs)` — `ContextVar`, current async context.
- `Container.override(**kwargs)` — process singleton (needed when work runs in another thread,
  e.g. `asyncio.to_thread`).
- `Container.reset()` between tests (autouse fixture).
- `with Container.local(repo=FakeRepo()):` — no `unittest.mock.patch`.

## `python-exceptions/python-exceptions.mdc`

---
description: AppError hierarchy — where to put exceptions and how to subclass them
alwaysApply: true
---

# Exceptions

Application errors subclass `AppError` from `project/exceptions.py`. If that type is missing, add it:

```python
class AppError(Exception):
    pass
```

Do not introduce a domain or adapter error that subclasses only `Exception` or only a third-party type.

## Where

| Kind | Place |
|---|---|
| `AppError` and errors shared by several components | `project/exceptions.py` |
| Errors of one component | `project/components/{name}/exceptions.py` |
| Errors of one agent | `project/components/{name}/ai/{agent}/exceptions.py` |

A subclass may live next to the module that raises it when nothing else imports it.

Shared kinds — add when first needed:

| Kind | Use |
|---|---|
| `NotFoundError` | Missing entity |
| `AuthError` | Failed authentication / authorization |
| `ExternalApiError` | Failed call to an external HTTP API |
| `ServerError` / `ClientError` | 5xx / 4xx from that API (`ExternalApiError` subclasses) |
| `ExternalHTTPConnectionError` | Transport / timeout talking to that API |

Carry identity on the instance (`object_name`, `id`, `url`). `__str__` is the human message; `__repr__` is for logs.

```python
class NotFoundError(AppError):
    def __init__(self, object_name: str, id: object) -> None:
        self.object_name = object_name
        self.id = id

    def __str__(self) -> str:
        return f"{self.object_name}={self.id} not found"
```

## Adapters and HTTP

Adapters catch library/API errors and raise an `AppError` subclass so domain code does not import third-party exception types. The subclass may also inherit the library type when a retry decorator must still match it (`python-retry`); do not retry `NotFoundError`, `AuthError`, or 4xx `ClientError` unless listed. Outbound HTTP adapters (`python-base-client`) map 4xx → `ClientError`, 5xx → `ServerError`, other HTTP failures → `ExternalApiError`, transport/timeout → `ExternalHTTPConnectionError`.

Domain and adapters raise `AppError`. `fastapi.HTTPException` stays in `endpoints.py`.
Map these types to HTTP status codes on the app (`python-fastapi`).

## `python-fastapi/python-fastapi.mdc`

---
description: FastAPI HTTP adapter — routers, ORJSON, URL versioning, SSE disconnects
globs:
  - "**/endpoints.py"
  - "**/apps/api.py"
alwaysApply: false
---

# FastAPI HTTP adapter

Runtime: FastAPI, Starlette, `sse-starlette`, uvicorn, uvloop, httpx, orjson, Pydantic v2.
Prefer **httpx** over `requests` in application code.

Install uvloop (`uv add uvloop`) and run uvicorn with `--loop uvloop`. Do not run FastAPI on
the default asyncio loop in production or entry scripts.

Endpoints live in `project.components.{name}.endpoints`. Register routers on the app in
`project.infrastructure.apps.api`. Take services from `Container()`, not from FastAPI `Depends`
for domain objects.

```bash
uv run uvicorn project.infrastructure.apps.api:app --host 0.0.0.0 --loop uvloop
```

Call `setup_logging()` once in the app lifespan or `main.py` (`python-logging`).
When FastAPI/uvicorn needs a level different from root, add `FASTAPI_LOG_LEVEL` to
`SettingsValidator` and configure `uvicorn` and `fastapi` with it (`python-development-rules`).

## Responses

Use a shared envelope (`ApiResponse` / `ApiResponseSchema[T]` from `project.base.schemas`,
`python-structure`) as `response_model` when the OpenAPI shape matters.
Prefer `ORJSONResponse` (`response_class`) for JSON. `response_model` validation is extra cost
on large payloads.

Version **each path**, not the whole router: `/user/v1/list`. Breaking changes get a new path;
keep the old one with `deprecated=True`.

Raise `fastapi.HTTPException` only in `endpoints.py`. Domain code raises `AppError` (or a subclass).

Token-gated APIs: one `Depends` on the app (or router) that reads `Header(alias="Api-Token")` and
compares it to `Settings().API_TOKEN`.

## Exception handlers

Register handlers on the app. Log there. Endpoints do not catch-and-return error dicts.

| Raised | HTTP |
|---|---|
| `NotFoundError` | 404 |
| `AuthError` | 401 |
| `ExternalApiError` | 500 |
| `RequestValidationError` | 422 |
| `HTTPException` | as raised |
| other `Exception` | 500, generic body (no internals) |

## Client disconnect

On LLM or streaming work, cancel when the client goes away so GPU/DB work does not continue.
ASGI sends `http.disconnect`; poll `await request.receive()`. Do not use `request.is_disconnected()`
together with `BaseHTTPMiddleware` — it is unreliable. Helpers live in
`project/infrastructure/utils/disconnect.py` when that module is present.

| Case | Approach |
|---|---|
| Ordinary async endpoints | `DisconnectMiddleware` (races handler against disconnect), or `@with_cancellation` |
| SSE / `StreamingResponse` | Let the framework cancel; `sse-starlette`. Cleanup in `finally` with `anyio.CancelScope(shield=True)` (not `asyncio.shield`) |
| Granular cancel around DB / GPU | `detect_disconnect` + `cancel_on_disconnect` |
| Nested async generators | `contextlib.aclosing` or `safe_async_generator_cleanup` |

Re-raise `asyncio.CancelledError` after logging/metrics. Do not add a second manual disconnect
check inside a generator that `EventSourceResponse` already cancels.

Fire-and-forget side I/O (metrics, audit) from an endpoint: `asyncio.create_task(...)` without
await when the response does not depend on it; log failures, do not fail the request.
Wait when the write is part of the result (DB commit, payment).

## Prometheus

When `python-monitoring` is installed, register `fastapi_tracking_middleware` and `GET /prometheus`
via `fastapi_endpoint_for_prometheus`. Follow that harness; do not hand-roll a scrape endpoint.

## `python-freezegun/python-freezegun.mdc`

---
description: freezegun freeze_time in tests — stopped UTC clock, move_to/tick, no datetime patch
globs:
  - tests/**
alwaysApply: false
---

# Frozen time

Package: PyPI **`freezegun`** (`uv add --dev freezegun`). When a test depends on "now", freeze
the clock. Do not `patch` `datetime`, `date`, or `time`. Production code still calls
`datetime.now(timezone.utc)`; the test holds the clock.

Pair with `python-tests`. Freeze only tests that assert on a date, expiry, cutoff, or schedule.

## Stopped UTC instant

Put the instant in the test, not in a shared fixture. Default is a **stopped** clock
(`tick=False`). Advance with `move_to` / `tick`, not `asyncio.sleep` and not `tick=True`.

```python
from datetime import datetime, timedelta, timezone

from freezegun import freeze_time

NOW = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)


def test_still_valid():
    with freeze_time(NOW):
        assert not is_expired(issued_at=NOW, ttl=timedelta(hours=24))


@freeze_time("2012-01-14")
def test_still_valid_decorated():
    assert datetime.datetime.now() == datetime.datetime(2012, 1, 14)


def test_expired_after_ttl():
    with freeze_time(NOW) as frozen:
        token = issue_token(ttl=timedelta(hours=24))
        frozen.move_to(NOW + timedelta(hours=24, seconds=1))
        assert token.expired
```

Both forms freeze the same stopped instant. The decorator `@freeze_time(NOW)` is fine when
the clock never moves; prefer the context manager whenever the test jumps or ticks
(`frozen.move_to`).

## Async

`async def` tests use the context manager with `real_asyncio=True` so `asyncio.sleep` and
the event loop keep real monotonic time. The frozen clock still answers `datetime.now`.

```python
async def test_cutoff():
    with freeze_time(NOW, real_asyncio=True):
        ...
```

## Stay out of the way

Compute "now" inside the function under test. Freeze does not rewrite default arguments
(`def f(now=datetime.now(...))` stays at import time).

Freeze only the test that needs a fixed clock. Depend on PyPI `freezegun`.

## `python-fsm/python-fsm.mdc`

---
description: StateMachine / AsyncStateMachine — validated transitions, persist via get/set
globs: "**/libs/fsm.py"
alwaysApply: false
---

# State machines

Use `StateMachine` + `transition` for sync workflows with an explicit `Enum` of states;
`AsyncStateMachine` + `atransition` when get/set or the transition body is async.
Illegal calls raise `TransitionError`. Keep the helper in `project/libs/fsm.py`
(copy sibling `FSM.md` if missing). Domain subclasses live in the component that owns
the workflow, not in `libs/`.

Persist through `get_state` / `set_state` (or `aget_state` / `aset_state`) — memory, DB, or Redis.
Those methods are the persistence seam. Do not put adapters, sessions, or Redis clients
on the FSM class.

```python
@transition(from_states=OrderState.CREATED, to_state=OrderState.PAID)
def pay(self, amount: float) -> None:
    ...

@atransition(from_states=TaskState.PENDING, to_state=TaskState.RUNNING)
async def start(self) -> None:
    ...
```

`from_states` may be one enum member or a list. The decorator reads state, runs the method,
then writes `to_state`. Catch `TransitionError` at the use-case boundary.

## `python-logging/python-logging.mdc`

---
description: dictConfig logging — setup_logging() at process start, levels from Settings
globs: "**/logger.py"
alwaysApply: false
---

# Logging setup

Configure logging once with `logging.config.dictConfig` in `setup_logging()` (`project/logger.py`).
If that module is missing, copy sibling `LOGGER.md` into `project/logger.py`.
Call it once at process start.
Call-site hygiene (`logger.exception`, no `extra=`) is `python-tooling`.

Levels come from `Settings()` (`python-settings`). Always `LOG_LEVEL` for root and the console handler.
`disable_existing_loggers: False`. Console is `StreamHandler` to stdout.
Formatter: `Constants.LOG_FORMAT` when present, else `%(asctime)s - %(name)s - %(levelname)s - %(message)s`.

## Library loggers

The base setup does not name frameworks, clients, databases, brokers, or other integrations.
Technology-specific rules own their logger names and optional `*_LOG_LEVEL` Settings fields.
Follow `python-development-rules` when a selected module needs its own configurable level.

Helpers such as `timer` / `get_log_id` may live in `project/libs/log.py`; they are not this harness.

## `python-monitoring/python-monitoring.mdc`

---
description: Prometheus metrics via llm_common — init, FastAPI scrape, actions, httpx
alwaysApply: true
---

# Python monitoring adapter

Package: PyPI **`llm_common`** (`uv add llm_common prometheus_client`). Do not install PyPI
`pycommons` (unrelated). Metric names use **the package prefix** (today `genapp_`); do not invent
another. Do not paste private Grafana dashboard URLs. Names and labels: sibling `METRICS.md`.

## Init

Call once at process start (API / bot entry). Skip tests and local. `env` is only `dev` | `preprod` |
`prod` — never pass `test` or `local` into `build_prometheus_metrics`.

```python
from llm_common.prometheus import build_prometheus_metrics

# Skip test/local. Do not use `if env != "test" or env != "local"` (that is always true).
if env not in ("test", "local"):
    build_prometheus_metrics(project_name="project", env=prometheus_env)
```

With `python-settings`, skip when `is_autotest()` or `is_local()`. Map the remaining process env onto
`dev` | `preprod` | `prod`.

## FastAPI

```python
from llm_common.prometheus import fastapi_tracking_middleware, fastapi_endpoint_for_prometheus

app.middleware("http")(fastapi_tracking_middleware)
app.get("/prometheus")(fastapi_endpoint_for_prometheus)
```

Inbound `resource` labels must be route templates, not concrete IDs. Flask: only if the repo already
uses Flask, `flask_endpoint_for_prometheus` on `GET /prometheus`.

## Actions

`action_tracking` / `action_tracking_decorator`. Do not swallow exceptions inside the tracked block
(the helpers need the exception to record failure).

| Kind | Suffix |
|---|---|
| Telegram handlers / callbacks | `_handler` |
| Scheduled / regular jobs | `_task` |
| LLM calls | `_llm_call` |
| Agent runs | `_agent` |

Separator is `_` (`menu_handler`, `sync_task`, `summarize_llm_call`).

## Telegram (when `python-telegram` is installed)

Put `TelegramHTTPXTransportWithMonitoring` on `HTTPXRequest`. Decorate handlers with
`action_tracking_decorator("…_handler")` **inside** `processing_errors` (see that rule's decorator
order).

```python
from llm_common.clients.telegram_client import TelegramHTTPXTransportWithMonitoring
from telegram.request import HTTPXRequest

request = HTTPXRequest(httpx_kwargs={"transport": TelegramHTTPXTransportWithMonitoring()})
```

## Outbound HTTP

Named adapters that must map HTTP failures to `AppError` (`ClientError` / `ServerError` /
`ExternalApiError`) use the selected `python-base-client` implementation (`AsyncApi` or `SyncApi`
with httpx). That helper records HTTP metrics through `TelemetryCallback` (`is_build_metrics` /
`http_tracking`); do not also wrap its session in `HttpxClientWithMonitoring` (double-count). Pass
`resource_for_monitoring` as a path template with no IDs.

Use `HttpxClientWithMonitoring` when you only need a tracked httpx client without that mapping.
`name_for_monitoring` is required; API clients suffix `_api`. Override `clear_resource_path` so
`resource` has no high-cardinality IDs (`/users/123` → `/users/{user_id}`). Use
`ClientSessionWithMonitoring` only if the repo already uses aiohttp.

## Optional

- **SQLAlchemy pool** (`python-db-sessions`): after metrics init,
  `register_sqlalchemy_engine_monitoring(engine, database="…")` (async engines are fine).
- **LLM** (`record_llm_request`, `record_llm_usage`, …): only if the repo already calls LLMs. Do not
  add langchain, `AuthHttpClient`, or Keycloak for this harness.

## `python-polyfactory/python-polyfactory.mdc`

---
description: Polyfactory test factories — generated typed model data through class-level build and batch
globs:
  - tests/**
alwaysApply: false
---

# Polyfactory

Package: PyPI **`polyfactory`** (`uv add --dev polyfactory`). Pair with `python-tests`.
If `tests/factories.py` is missing, copy sibling `FACTORIES.md` into `tests/factories.py`
(merge; do not overwrite without asking).
When `python-sqlalchemy` and `python-db-sessions` are installed, read sibling
`FACTORIES_ORM.md` before creating or changing ORM factories and merge its template.

Generate all test data through Polyfactory classes. Call factories directly in the test body.
Fixtures provide environment and resources, not generated payloads or model instances.
Do not generate data in fixtures or arbitrary helper functions, wrap factories in `make_*`
helpers, or use `@register_fixture` / `register_fixture(...)`.

| Need | Call |
|---|---|
| Pydantic model | `ItemSchemaFactory.build(**overrides)` |
| Dataclass | `ItemFactory.build(**overrides)` |
| TypedDict | `ItemPayloadFactory.build(**overrides)` |
| Several values | `Factory.batch(n, **overrides)` |

A new typed model used in tests gets a factory class in `tests/factories.py`.
Overrides in the test beat factory defaults.

```python
from tests.factories import ItemSchemaFactory


def test_user():
    payload = ItemSchemaFactory.build(title="x")
```

## Pull more detail when needed

Read the sibling file only for that branch — do not load all of them by default.

| When | Read |
|---|---|
| Field defaults, `Use` / `Ignore` / `Require`, `PostGenerated`, nested factory fields | sibling `FIELDS.md` |
| `NewType` / custom type fails to generate, or many factories need the same type | sibling `CUSTOM_TYPES.md` |
| Exhaustive `Literal` / union variants with few instances | sibling `COVERAGE.md` |

## `python-redis/python-redis.mdc`

---
description: Redis async cache — prefixed keys, CacheRepository, redis_atransaction, orjson
globs:
  - "**/adapters/acache.py"
  - "**/adapters/cache.py"
  - "**/repositories.py"
alwaysApply: false
---

# Redis cache adapter

Runtime: `redis.asyncio`, orjson.

When Redis needs a level different from root, add `REDIS_LOG_LEVEL` to `SettingsValidator` and
configure `redis` with it (`python-development-rules`).

One adapter module owns the client. If it is missing, copy the adapter section from sibling
`CACHE.md` into `project/infrastructure/adapters/acache.py`. Merge its base repository section
into `project/base/repositories.py` and its Settings contract into `settings.py`.

| Need | Call |
|---|---|
| Read | `await cls.get_client().get(key)` |
| Write / delete | `async with redis_atransaction() as tr` |
| Isolated write (do not join the open pipeline) | `isolated_redis_atransaction()` |
| After host / Settings override | `redis_client.cache_clear()` |

`redis_atransaction()` reuses the `ContextVar` pipeline or opens one and `execute()`s on exit.
Do not call `pipe.execute()` by hand inside these helpers.

Connect with `Settings().REDIS_HOST` / `REDIS_PORT` / `REDIS_DB`.
If the product can run without Redis, skip cache when `redis_is_configured()` is false;
do not fail at import.

Services and use cases never import `redis` — only cache repositories do.

Every Redis key starts with the non-empty `Constants.REDIS_KEY_PREFIX`. Keep
`key_template` domain-specific and build the complete key through `CacheRepository.key()`;
use the same constant for Redis keys outside cache repositories.

## CacheRepository

The base `CacheRepository` always lives in `project/base/repositories.py`.
Subclasses live in `project/components/{name}/repositories.py`, import that base, and end in
`CacheRepository`. The Redis adapter contains only the client and transaction lifecycle.

| Attribute | Type | Rule |
|---|---|---|
| `key_template` | `ClassVar[str]` | Unprefixed domain template containing `{}` for the id (`"item:{}"`) |
| `ttl` | `ClassVar[timedelta]` | Entry lifetime |
| `get_client` | static factory | Already `redis_client`; call `cls.get_client()` |

Pass every repository key to Redis as `cls.key(...)`; this produces
`{Constants.REDIS_KEY_PREFIX}:{key_template}`.

Keys use domain types from `project/datatypes.py`. Values are Pydantic schemas.
Serialize with `orjson.dumps(data.model_dump(exclude_unset=True))`; load with
`orjson.loads` then the schema. `save` / `delete` go through `redis_atransaction()`;
`get` returns the schema or `None`.

Tests: Testcontainers Redis, `flushdb` per test (fixtures in `CACHE.md`).

## `python-retry/python-retry.mdc`

---
description: retry_on_exception / retry_unless_exception — transient I/O, sync and async
globs: "**/libs/retry.py"
alwaysApply: false
---

# Retries

Use `retry_on_exception` / `retry_unless_exception` from `project/libs/retry.py` for transient
I/O (HTTP, DB, Redis). Copy sibling `RETRY.md` if that module is missing. Both wrappers
cover sync and async via `iscoroutinefunction`. Do not add tenacity, backoff, or other
retry packages when this helper exists.

`timeout_with_retry` (`python-telegram`) is bot UX (tell the user, retry on timeout). Do not
use it for adapter I/O.

```python
@retry_on_exception((ExternalHTTPConnectionError, ServerError), max_attempts=3, backoff=2)
async def fetch_item(self, item_id: str) -> dict:
    ...

@retry_unless_exception((NotFoundError, AuthError, ClientError), max_attempts=3, backoff=2)
async def cache_get(self, key: str) -> bytes:
    ...
```

Prefer `retry_unless_exception` when the call should retry everything except listed
control-flow errors. Do not retry `AppError` types that are not transient
(`NotFoundError`, `AuthError`, 4xx `ClientError`) unless the caller lists them.
A subclass may also inherit the library exception so the decorator can still match it
(`python-exceptions`).

The helper logs a warning per retry and an error on final failure (`python-tooling`;
no `extra=`). Callers do not log the same failure again.

## `python-semver/python-semver.mdc`

---
description: SemVer 2.0 for Python libraries — public API, X.Y.Z bumps, pyproject version
alwaysApply: true
---

# Semantic Versioning (libraries)

Spec: https://semver.org/spec/v2.0.0.html (v2.0.0).

Use this rule when the repository is (or will be) a **publishable Python library**
with a declared public API. Skip it for internal apps/services that are not
versioned for external consumers.

## Public API

The package MUST declare a public API before SemVer meanings apply.

- Document what callers may import (README / API docs / `__all__`).
- Names starting with `_` are private unless documented otherwise.
- Prefer exporting the stable surface from the package root or named public modules.
- Version `1.0.0` is the first release where that public API is considered stable.
- Under `0.y.z` (initial development) anything MAY change; still use SemVer form.

## Version format

Normal version: `MAJOR.MINOR.PATCH` (non-negative integers, no leading zeroes).

| Bump | When (after `1.0.0`) |
|---|---|
| **MAJOR** | Any backward-incompatible change to the public API |
| **MINOR** | Backward-compatible addition, or deprecation of public API |
| **PATCH** | Backward-compatible bug fix only |

On MINOR bump, reset PATCH to `0`. On MAJOR bump, reset MINOR and PATCH to `0`.

Examples of **breaking** (MAJOR): remove/rename a public symbol; change a required
parameter; tighten accepted types; change return/exception contract callers rely on.

Examples of **compatible** (MINOR): add optional parameter with a default; add a
new public function/class; mark a public symbol deprecated (keep it working).

Examples of **patch**: fix incorrect behavior without changing the public contract.

### Pre-release and build

- Pre-release: `1.0.0-alpha.1`, `1.0.0-rc.1` (hyphen + dot-separated identifiers).
- Build metadata: `1.0.0+20130313144700` (plus suffix; ignored for precedence).
- Precedence: `1.0.0-alpha` < `1.0.0-alpha.1` < `1.0.0-beta` < `1.0.0-rc.1` < `1.0.0`.

PyPI / installers use **PEP 440**. Core `X.Y.Z` matches SemVer. Pre-release *syntax*
differs (`1.0.0a1` / `1.0.0rc1` in PEP 440 vs `1.0.0-alpha.1` / `1.0.0-rc.1` in
SemVer). For published wheels prefer PEP 440 spellings; keep SemVer bump rules.

## Single source of truth (Python)

One version string drives the release:

1. Prefer `[project].version` in `pyproject.toml`, **or** one dynamic source
   (e.g. `project/__version__.py` / `VERSION` file) wired via the build backend.
2. Keep package `__version__` (if present) equal to that string.
3. Do not hardcode a second conflicting version in docs, CI, or importlib hacks.
4. Git tag MAY be `v1.2.3`; the SemVer string itself is `1.2.3` (no leading `v`).

```toml
[project]
name = "example"
version = "1.2.3"
```

## Release hygiene

- Once a version is published, do **not** mutate that release; ship a new version.
- Accidental breaking change shipped as MINOR: fix compatibility in a new MINOR
  (or ship a MAJOR that documents the break). Never rewrite the bad tag’s artifacts.
- Deprecate in a MINOR first; remove in a later MAJOR.
- Link the SemVer spec from the library README so consumers know the contract.
- Changelog format is separate (e.g. Keep a Changelog via agent-setup); still bump
  by these SemVer rules.

## Agent checklist before bumping

1. Identify the public API surface touched by the change.
2. Classify: breaking / additive or deprecation / fix-only / none.
3. Choose MAJOR / MINOR / PATCH (or leave unchanged if not a release).
4. Update the single version source; sync `__version__` if it exists.
5. Mention the bump reason in the release notes / PR.

## `python-settings/python-settings.mdc`

---
description: pydantic-settings env contract — Settings().PARAM, .env, Constants
alwaysApply: true
---

# Settings

Application config is `SettingsValidator` (pydantic-settings `BaseSettings`, Pydantic v2) wrapped as
`Settings = LazyInit(SettingsValidator)` in `project/settings.py`.
If that module is missing, copy sibling `SETTINGS.md` into `project/settings.py`.
`LazyInit` comes from `python-di` (`STRUCTURES.md` → `project/libs/structures.py`).

## Env contract

Field names **are** the environment variable names (`UPPER_SNAKE`).
pydantic-settings reads process env, then `env_file` (repo-root `.env`).
Keep `env.example` in sync with required fields (no secret values). Do not commit `.env`.

```python
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from project.libs.structures import LazyInit


class SettingsValidator(BaseSettings):
    LOG_LEVEL: str = "INFO"
    API_KEY: SecretStr  # required — no default

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        extra="allow",
    )


Settings = LazyInit(SettingsValidator)
```

- Secrets: `SecretStr`; unwrap with `.get_secret_value()` at the call site.
- Closed env names: `Enum` (`Envs`).
- Derived values: `@model_validator` on `SettingsValidator`. Adapter-specific fields (DSN, …)
  stay in that adapter's contract.
- Logging (`python-logging`): `LOG_LEVEL`; `Constants.LOG_FORMAT` when the formatter is shared.
  Follow `python-development-rules` for technology-specific log-level fields.
- Read config through Settings fields, not `os.getenv` / `os.environ`.
- `extra="allow"` so undeclared host env does not fail startup.

## Call through the proxy

```python
Settings().PARAM          # yes
settings = Settings()     # no — do not bind the proxy
```

Do not pass `Settings()` as a default argument (it freezes values at import).
Do not store `Settings` on `self` in `__init__`.

## Constants vs Settings

- **Settings fields** — values that change per environment (env / `.env`).
- **`Constants`** (same module) — operational values shared across components that are not env-backed.
- Domain literals stay next to the domain code.

## Tests

- `Settings.local(**kwargs)` — `ContextVar`, current async context.
- `Settings.override(**kwargs)` — process singleton (needed when work runs in another thread,
  e.g. `asyncio.to_thread`).

## `python-sqlalchemy/python-sqlalchemy.mdc`

---
description: SQLAlchemy ORM models, shared Base and generic repositories
globs:
  - "**/models.py"
  - "**/repositories.py"
alwaysApply: false
---

# SQLAlchemy ORM

Use SQLAlchemy 2.0 `Mapped` / `mapped_column`. JSON columns use Postgres `JSONB`.

If shared ORM bases are missing, copy sibling `BASE_MODELS.md` to
`project/base/models.py`. If multiple repositories share model lookup behavior, copy
`BASE_REPOSITORIES.md` to `project/base/repositories.py`. Do not add a generic
repository for one consumer.

Session lifecycle, transactions, engine construction, DSN settings, and `DATABASE.md` belong to
`python-db-sessions`. ORM repositories use its `asession()` / `atransaction()` helpers; they do
not create a private engine or sessionmaker.

If the repo already has Alembic, follow `python-alembic`: generate a revision after every model
change and apply it. Do not add a migrator to a repo that creates tables from metadata only
(`create_all` / `create_all_tables`).

Models inherit `Base` / `TimeMixin` from `project.base.models`.
Foreign keys set `ondelete` when cascade/restrict matters. Identity and other entity keys use
domain types from `project/datatypes.py`, not bare `int` / `str`. Primary keys: `BigInteger`.
Postgres enums: `class Role(str, enum.Enum)` + `mapped_column(Enum(Role, name="role_enum"))`.
Many-to-many: `ARRAY` of ids (`Mapped[list[TagIdT]]`), not an association table.
Index columns used for filter, sort, or FK lookup.
Application rules stay in Python — no new triggers or stored procedures.

A new model also gets a `SQLAlchemyFactory` in `tests/factories.py` (`python-polyfactory`).
Follow existing `__tablename__` style in the repo.

Services and use cases never import SQLAlchemy or write SQL; only repositories do.
Design repository queries to avoid N+1 access: do not query or lazy-load related data inside
loops. Fetch related rows with a set-based query or explicit eager loading (`selectinload` /
`joinedload`), and account for the total query count on list operations.

Tests build ORM rows with `python-polyfactory`. Persisted tests additionally install
`python-db-sessions` and use its Testcontainers transaction fixture from `python-tests`.

## `python-structure/python-module-structure.mdc`

---
description: Module layout — package tree, file placement, and shared components
alwaysApply: true
---

# Module structure

Group modules by component (one domain per directory). Put new code in the matching layer;
do not mix adapters with services or use cases.
Persistence clients stay in `adapters`; persistence models and repositories stay in their
component modules.

```text
project/
  datatypes.py                        NewType domain ids and names
  infrastructure/apps/api.py          FastAPI app, router registration
  infrastructure/apps/bot.py          Telegram bot, handler registration
  infrastructure/apps/main.py         production entry
  infrastructure/adapters/            external systems (HTTP, DB, cache, queues)
  infrastructure/base/                shared infrastructure helpers
    http_client.py                    outbound HTTP helper
    telegram.py                       Telegram decorators
  infrastructure/utils/               other framework helpers, not domain
  base/                               shared modules used by every domain component
    models.py                         shared persistence model bases (when needed)
    schemas.py                        Pydantic envelopes (`ApiResponseSchema[T]`)
    repositories.py                   shared repository base (when the repo needs one)
    handlers.py                       shared Telegram handlers (when the repo has a bot)
  components/{name}/
    endpoints.py                      HTTP handlers
    handlers.py                       bot I/O
    use_cases.py                      orchestration
    service.py                        stateless domain behavior
    repositories.py                   all data access
    models.py                         persistence models
    schemas.py                        Pydantic
    enums.py                          closed value sets
    exceptions.py                     component errors
    interfaces.py                     Protocol stubs for adapters
    validation.py                     input-check helpers used by use cases
    cli.py                            CLI
    ai/{agent}/                       agent, prompts, tools, schemas, exceptions
  libs/                               reusable, no domain, no infrastructure
  exceptions.py                       AppError
  logger.py
  settings.py
  container.py
tests/
  conftest.py
  factories.py
  test_modules/                       modular tests (mocks)
  test_e2e/                           end-to-end tests (live deps)
```

Domain workflows with explicit states use `python-fsm` (`project/libs/fsm.py`).
Transient I/O retries use `python-retry` (`project/libs/retry.py`).

## Shared modules (`base`)

Put cross-component generics in `project/base/`. Domain components subclass or reuse
them; do not copy shared model bases, repository helpers, or the HTTP envelope into each
`components/{name}/`.
Keep feature-specific code in the domain component.

| File | When | Copy if missing |
|---|---|---|
| `models.py` | persistence model base | install the selected persistence rule |
| `schemas.py` | FastAPI envelope | sibling `BASE_SCHEMAS.md` → `project/base/schemas.py` (`python-fastapi`) |
| `repositories.py` | shared repository base | install the selected persistence rule |
| `handlers.py` | Telegram bot | shared handlers only (`python-telegram`); register from `apps/bot.py` |

Infrastructure-wide helpers live in `project/infrastructure/base/`.

## `python-structure/python-structure.mdc`

---
description: Layer boundaries — services, use cases, repositories, adapters, and domain types
alwaysApply: true
---

# Layer boundaries

Lower layers do not import higher ones. Domain modules do not import adapters or frameworks;
annotate expected collaborators with `Protocol` in `interfaces.py`.

- **Service** — stateless; hides a business process. Put work that other components will reuse here.
- **Use case** — I/O entry (HTTP, CLI, bot). Coordinates services; no persistence client or
  query language. Other components do not call use cases. Keep it short; names are business verbs.
  Input checks live here; shared check functions go in `validation.py`.
- **Repository** — the only data-access type; stateless. Inherit from `project.base` when a
  shared base exists. Add one only when it has a real consumer.
- **Adapter** — facade over an external system; errors and API quirks stay here so tests can stub it.
- **Container** — `LazyInit(Services)`; take dependencies with `Container().…` inside methods.

Domain annotations use types from `project/datatypes.py`, not bare `str` / `int`:

```python
UserIdT = t.NewType("UserIdT", t.Annotated[int, "User ID"])
```

Per-agent state under `ai/{agent}/` is a Pydantic model (TypedDict at minimum), one type per agent.

## Adapters

New external system → new module under `infrastructure/adapters/`. Raise `AppError` subclasses
(`python-exceptions`). Outbound HTTP APIs subclass or compose the selected `AsyncApi` / `SyncApi`
from `python-base-client` (`project/infrastructure/base/http_client.py`; copy that rule's
`ASYNC_CLIENT.md` or `SYNC_CLIENT.md` if missing). `layers.toml`: `http_client` is adapters, not
presentation. Tests stub the adapter through `Container.local(...)` (`python-tests`).

If `layers.toml` is missing, copy the `layers-linter` skill template to the
repository root (substitute the package name if it is not `project`). Keep it in
sync when adding modules. Pair with `layers-linter` and `domain-types-linter`.
Architecture imports:

```bash
uv run la-linter project
```

## `python-telegram/python-telegram.mdc`

---
description: Telegram bot adapter — python-telegram-bot handlers, polling, error decorators
globs:
  - "**/handlers.py"
  - "**/apps/bot.py"
  - "**/infrastructure/base/telegram.py"
alwaysApply: false
---

# Telegram bot adapter

Runtime: [python-telegram-bot](https://docs.python-telegram-bot.org/) (`ApplicationBuilder`, polling,
`HTTPXRequest`, `AIORateLimiter`, `concurrent_updates`). Extra: `python-telegram-bot[job-queue,rate-limiter]`.
Not aiogram.

When the bot libraries need a level different from root, add `TELEGRAM_LOG_LEVEL` to
`SettingsValidator` and configure `telegram`, `telegram.ext`, and `apscheduler` with it
(`python-development-rules`).

Handlers live in `project.components.{name}.handlers`. Shared bot-wide handlers live in
`project.base.handlers` (`python-structure`). Register them from
`project.infrastructure.apps.bot`. Decorator helpers live in `project.infrastructure.base.telegram`.
If `telegram.py` or `bot.py` is missing, copy sibling `TELEGRAM.md` into
`project/infrastructure/base/telegram.py` and `BOT.md` into `project/infrastructure/apps/bot.py`.

Token: `Settings().TELEGRAM_BOT_TOKEN` (`python-settings`, `SecretStr`). Unwrap with `.get_secret_value()` on
`ApplicationBuilder().token(...)`. Add the field to `SettingsValidator` if it is missing.

Handlers are presentation (bot I/O), like FastAPI endpoints: take collaborators via `Container()`, call use
cases. Do not import SQLAlchemy, `AsyncSession`, or Redis in handlers.

## Bot process

Use uvloop as the event loop for the bot process:

```python
with asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner:
    runner.run(run_bot_app())
```

Build with `ApplicationBuilder().token(...).request(HTTPXRequest()).rate_limiter(AIORateLimiter(max_retries=3)).concurrent_updates(True)`.
Poll with `application.updater.start_polling()`. When `python-monitoring` is installed, pass
`TelegramHTTPXTransportWithMonitoring` on `HTTPXRequest` (`httpx_kwargs={"transport": ...}`) and
decorate handlers with `action_tracking_decorator("…_handler")` **inside** `processing_errors`. Do
not add that transport or decorator unless that harness is present.

## Decorators

Centralize failures in `processing_errors`. Handlers must not swallow exceptions.

Python applies decorators **bottom-to-top**. Use this source order (the working wrap — not a reversed spec
snippet):

```python
@timeout_with_retry
@processing_errors
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await Container().example_use_case.run(update.effective_user.id)
    await update.effective_message.reply_text("Hello")


def register_example_handlers(application) -> None:
    application.add_handler(CommandHandler("start", start_handler))
```

Call stack (outer → inner): `timeout_with_retry` → `processing_errors` → handler.

| Decorator | Role |
|---|---|
| `timeout_with_retry` | Outermost. `asyncio.wait_for` around the inner stack; on timeout, tell the user and retry; re-raise after the last attempt so `processing_errors` does not treat `TimeoutError` as a generic failure. |
| `processing_errors` | Catch `AuthError` / `Exception`, log, reply. The only place handlers report failures to the user. |
| `action_tracking_decorator("…_handler")` | When `python-monitoring` is installed. Inside `processing_errors`, outside the handler (and `check_auth` if present). |
| `check_auth` | Innermost, **only** when the repo already has an auth collaborator. Raises `AuthError`. Do not add Keycloak, `auth_client`, or other SaaS auth for this harness. |

If `check_auth` exists, place it **below** `processing_errors` (closest to the handler). When
`python-monitoring` is installed, place `action_tracking_decorator("…_handler")` inside
`processing_errors` and outside the handler (and `check_auth` if present).

## `python-tests/python-tests.mdc`

---
description: Pytest — fixtures vs factories, HTTP mocks, no patch, behavior through use cases
globs:
  - tests/**
alwaysApply: false
---

# Tests

Read `tests/conftest.py` before adding helpers.
If `conftest.py` is missing the HTTP fixtures, copy sibling `CONFTEST.md` into `tests/conftest.py`
(merge; do not overwrite without asking).

## What belongs where

| Place | Holds |
|---|---|
| Test body | Scenario data, asserts, one behavior |
| `tests/conftest.py` | Session setup, HTTP mock routers, `TestClient`, `Container.reset()` |

Keep data out of fixtures: fixtures that only supply payloads make tests harder to read and change.
Duplicate literals in tests are fine.

Avoid test-only abstractions. Everything needed to understand a test should be in that test.
One test checks one behavior; a pile of asserts usually means several cases.
Assert observable outcomes (status, payload, persisted row), not object internals.

## Layout

Tests are **modular** or **e2e**. Put them in **separate directories** — never in the same folder
or the same file. Mirror `project/components/` and `project/infrastructure/` under each tree.

```text
tests/
  conftest.py                         shared fixtures
  test_modules/                       modular: mocks, no live third-party APIs
    test_components/{name}/
    test_infrastructure/
    test_libs/
  test_e2e/                           end-to-end: real GitLab, LLM, local infra
    test_components/{name}/
    test_infrastructure/
```

- **Modular** (`tests/test_modules/`): observable behavior through a use case or endpoint
  (`api_client`). Stub adapters with `Container.local(...)` and HTTP fixtures. No real network,
  credentials, or live SaaS.
- **E2E** (`tests/test_e2e/`): full cycle against real collaborators. Default CI runs
  `tests/test_modules/` only; e2e is an explicit command and needs the live stack.

```bash
uv run pytest tests/test_modules/
uv run pytest tests/test_e2e/ -n0
```

Do not use `unittest.mock.patch` — if a patch is required, invert the dependency and inject a stub.
Pair with `patch-linter` (PATCH001).
Autouse: `Container.reset()` before and after each test.
Settings overrides: `Settings.local` / `Settings.override` (`python-settings`).

## HTTP mocks

Fixtures `httpx_responses` (respx), `aiohttp_responses` (aioresponses), `requests_mock`
(requests-mock), `api_client`, and `openai_chat_completion_response` live in `CONFTEST.md`.
If the API is token-gated, `api_client` sends `Api-Token` from `Settings()`.

```python
def test_external_api(httpx_responses):
    httpx_responses.get("https://api.example.com/data").mock(
        side_effect=[httpx.Response(200, json={"result": "ok"})],
    )
```

LLM/OpenAI-style calls: mock the chat-completions URL from `Settings()` with `httpx_responses`.
JSON content is a **string** in `choices[0].message.content` — use `openai_chat_completion_response`.

## Companion harnesses

This rule stays stack-agnostic. When the repo gains a concern, install the matching catalog ID
from `python-harness` (re-run the setup skill or copy that rule dir) and apply the companion patch
below — do not invent local variants.

| Need | Catalog ID | Also copy / merge |
|---|---|---|
| Generated test data (default with automated tests) | `python-polyfactory` | `FACTORIES.md` → `tests/factories.py`; add `FACTORIES_ORM.md` only with ORM |
| Frozen clock in tests | `python-freezegun` | — |
| Postgres / ORM tests | `python-sqlalchemy` + `python-db-sessions` | sibling `CONFTEST_DATABASE.md` → `tests/conftest.py`; companion patch in this file |
| Redis cache tests | `python-redis` | Redis fixtures from `CACHE.md` → `tests/conftest.py`; companion patch in this file |

Companion patches for the installer live in sibling `COMPANION.md` (catalog repo only — not copied
to the target).

## `python-tooling/python-tooling.mdc`

---
description: Python toolchain — uv, ruff, black, isort, pre-commit, hygiene
alwaysApply: true
---

# Python tooling

Default package root is `project/` (substitute if the repo uses another name).
Tool versions and Ruff selects live in `pyproject.toml` — follow that file, do not invent a parallel config.

Package manager: **uv**. Run tools with `uv run`. Line length **120** (Ruff, Black, isort).
Ban parent-relative imports (`from ..x`). Format with Black; lint with Ruff; sort imports with isort.
Install `pre-commit` hooks; they run Black, Ruff, and `uv export` for lock-style requirements.
Async processes install and run with **uvloop** (`uv add uvloop`).

```bash
uv sync --all-groups
uv run ruff check --fix project tests
uv run black project tests
uv run isort project tests
```

## Logging

Use `logger.exception` when an exception is swallowed, converted, or followed by a fallback.
Skip a log when the exception is re-raised unchanged and the outer boundary already logs it.
Expected control-flow branches do not need exception logs. Do not pass `extra=` on log calls.
Process-wide `dictConfig` / `setup_logging()` is `python-logging`.

## Hygiene

Closed variant sets → `Enum`. Domain literals stay next to the domain code.
Operational constants shared across components live in `Constants` (`python-settings`).
Import from the concrete module; do not barrel-reexport in `__init__.py`.
Do not wrap package imports in try/except. Do not add `__future__` imports.
In async code use `asyncio.Lock()`, not `threading.Lock()`.
Async context managers: `@asynccontextmanager` from `contextlib`, not a class with `__aenter__` / `__aexit__`.
Shape tabular data with SQL or annotated lists/dicts (`TypedDict`, dataclass). Do not add Pandas or Polars.
Serialize with JSON (`orjson` where the stack already uses it), not pickle.
Persist durable state in the database or Redis, not in module globals or ad-hoc files.

## `python-workflow/python-workflow.mdc`

---
description: Repository navigation before Python code research and analysis
alwaysApply: true
---

# Python repository workflow

Before researching the repository or analyzing its code, architecture, or project structure:

1. Read `project/container.py` to identify registered dependencies and their relationships.
2. List all Python modules (`*.py`) in the repository.

Use the container and module list as the navigation map for subsequent targeted reading. If
`project/container.py` is absent, note that and continue from the module list.

## Reusable solutions

If you did not know how to complete a task and had to research the solution, preserve the
result when the task is typical and likely to recur:

1. Write the reusable procedure in an existing relevant document or a focused Markdown file.
2. Add a link to that document in the root `AGENTS.md` so the next agent can find it directly.

Do not add documentation for one-off or project-irrelevant discoveries.
