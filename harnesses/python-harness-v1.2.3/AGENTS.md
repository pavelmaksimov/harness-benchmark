# Python Harness catalog rules

This file is a flattened copy of every upstream `*.mdc` rule from catalog version `1.2.3` at commit `f96781a32da3481b90d24bc054d3c8e6a86fc29f`. It is mounted as the workspace `AGENTS.md` for agents that do not consume editor rule files. Apply only guidance relevant to the repository and task; task requirements and existing conventions take precedence.

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

Pair with `python-sqlalchemy`. Skip this harness when the repo creates tables from metadata only
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
- `target_metadata`: shared `MetaData` / `Base` in `project.components.base.models` when that
  module exists (`public_schema` or `Base.metadata`); otherwise the repo's existing `Base.metadata`.

## `python-base-client/python-base-client.mdc`

---
description: Outbound HTTP adapters — choose httpx AsyncApi or SyncApi, AppError mapping, retries
globs:
  - "**/utils/base_client.py"
  - "**/adapters/*.py"
alwaysApply: false
---

# Outbound HTTP adapters

Choose one implementation for `project/infrastructure/utils/base_client.py`:

- async service: copy sibling `ASYNC_CLIENT.md` (`httpx.AsyncClient`, orjson, llm_common);
- sync service: copy sibling `SYNC_CLIENT.md` (`httpx.Client`, orjson, llm_common).

Install only the implementation the developer selects; do not combine both clients in one module.
New external HTTP API → a module under `project/infrastructure/adapters/`. Subclass or compose the
selected `AsyncApi` or `SyncApi`. `layers.toml`: `base_client` is **adapters**, not presentation.

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
Container().job_store     # yes
container = Container()   # no — do not bind the proxy
```

Do not store `Container` on `self` in `__init__`.
Do not construct infrastructure clients inside a service; take them from `Container()` at the
**point of use**. Request schemas and other value objects may be created locally.

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

## Responses

Use a shared envelope (`ApiResponse` / `ApiResponseSchema[T]` from `project.components.base.schemas`,
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
Call it once at process start: API `apps/api.py` / `main.py`, bot `apps/bot.py`.
Call-site hygiene (`logger.exception`, no `extra=`) is `python-tooling`.

Levels come from `Settings()` (`python-settings`). Always `LOG_LEVEL` for root and the console handler.
`disable_existing_loggers: True`. Console is `StreamHandler` to stdout.
Formatter: `Constants.LOG_FORMAT` when present, else `%(asctime)s - %(name)s - %(levelname)s - %(message)s`.

## Library loggers

Add a named logger only when that library is in the repo, and only then add the Settings field:

| Settings field | Loggers |
|---|---|
| `FASTAPI_LOG_LEVEL` | `uvicorn`, `fastapi` |
| `TELEGRAM_LOG_LEVEL` | `telegram`, `telegram.ext`, `apscheduler` |
| `HTTP_REQUESTS_LOG_LEVEL` | `httpx`, `httpcore` |
| `SQLALCHEMY_LOG_LEVEL` | `sqlalchemy`, `sqlalchemy.engine` |
| `REDIS_LOG_LEVEL` | `redis` |

Do not add flask, werkzeug, openai, aiohttp, or requests loggers unless the repo already uses them.
Each named logger: `propagate: False`, same handlers as root.

## File handler

When `WRITE_LOGS_TO_FILE` is true: `TimedRotatingFileHandler` at repo-root `logs/app.log`
(`when="midnight"`, `backupCount=14`, `encoding="utf8"`). Create `logs/` if needed.
Append the file handler to every configured named logger and to root. Keep `logs/` out of git.

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

- **SQLAlchemy** (`python-sqlalchemy`): after metrics init,
  `register_sqlalchemy_engine_monitoring(engine, database="…")` (async engines are fine).
- **LLM** (`record_llm_request`, `record_llm_usage`, …): only if the repo already calls LLMs. Do not
  add langchain, `AuthHttpClient`, or Keycloak for this harness.

## `python-polyfactory/python-polyfactory.mdc`

---
description: Polyfactory test factories — build/create_async on the class, ORM via atransaction
globs:
  - tests/**
alwaysApply: false
---

# Polyfactory

Package: PyPI **`polyfactory`** (`uv add --dev polyfactory`). Pair with `python-tests`.
If `tests/factories.py` is missing, copy sibling `FACTORIES.md` into `tests/factories.py`
(merge; do not overwrite without asking). Include the ORM block only when `python-sqlalchemy`
is installed.

Call factories on the class in the test body. Do not wrap them in `make_*` helpers.
Do not `@register_fixture` / `register_fixture(...)`.

| Need | Call |
|---|---|
| Pydantic / schema | `ItemSchemaFactory.build(**overrides)` |
| ORM in memory | `UserFactory.build(**overrides)` |
| ORM row in DB | `await UserFactory.create_async(**overrides)` |
| Several rows | `UserFactory.batch(n, **overrides)` / `await UserFactory.create_batch_async(n, **overrides)` |

A new ORM model or request schema gets a factory class in `tests/factories.py`.
Overrides in the test beat factory defaults.

```python
from tests.factories import ItemSchemaFactory, UserFactory


def test_user():
    user = UserFactory.build(email="b@example.com")
    payload = ItemSchemaFactory.build(title="x")


async def test_user_persisted(asession):
    user = await UserFactory.create_async(email="a@example.com")
    assert user.id is not None
```

## ORM persistence

SQLAlchemy factories persist through `atransaction()` from `python-sqlalchemy`
(`project/infrastructure/adapters/database.py`). Flush only — never `commit()` inside
the factory. Do not set `__async_session__` / `__session__` to a private sessionmaker.

Take the `asession` fixture on every test that calls `create_async` / `create_batch_async`,
even if the body does not use the session object. `build()` / `batch()` do not touch the DB.

Base factory (in `FACTORIES.md`): `__set_primary_key__ = False`,
`__set_relationships__ = False`, `__set_association_proxy__ = False`. Pass real FK ids.
Async only — no `create_sync`.

## Pull more detail when needed

Read the sibling file only for that branch — do not load all of them by default.

| When | Read |
|---|---|
| Field defaults, `Use` / `Ignore` / `Require`, `PostGenerated`, nested factory fields, FK filled from a prior create | sibling `FIELDS.md` |
| `NewType` / custom type fails to generate, or many factories need the same type | sibling `CUSTOM_TYPES.md` |
| Exhaustive `Literal` / union variants with few instances | sibling `COVERAGE.md` |

## `python-redis/python-redis.mdc`

---
description: Redis async cache — CacheRepository, redis_atransaction, orjson
globs:
  - "**/adapters/acache.py"
  - "**/adapters/cache.py"
  - "**/repositories.py"
alwaysApply: false
---

# Redis cache adapter

Runtime: `redis.asyncio`, orjson.

One adapter module owns the client. If it is missing, copy sibling `CACHE.md`
into `project/infrastructure/adapters/acache.py` (and the Settings contract into
`SettingsValidator` in `settings.py` — see `python-settings`).

| Need | Call |
|---|---|
| Read | `await cls.client().get(key)` |
| Write / delete | `async with redis_atransaction() as tr` |
| Isolated write (do not join the open pipeline) | `isolated_redis_atransaction()` |
| After host / Settings override | `redis_client.cache_clear()` |

`redis_atransaction()` reuses the `ContextVar` pipeline or opens one and `execute()`s on exit.
Do not call `pipe.execute()` by hand inside these helpers.

Connect with `Settings().REDIS_HOST` / `REDIS_PORT` / `REDIS_DB`.
If the product can run without Redis, skip cache when `redis_is_configured()` is false;
do not fail at import.

Services and use cases never import `redis` — only cache repositories do.

## CacheRepository

Subclasses live in `project/components/{name}/repositories.py`. Name ends in `CacheRepository`.
If a base class already exists (`components/base/repositories.py`), subclass that; otherwise
use `CacheRepository` from the adapter module.

| Attribute | Type | Rule |
|---|---|---|
| `key_template` | `ClassVar[str]` | Must contain `{}` for the id (`"item:{}"`) |
| `ttl` | `ClassVar[timedelta]` | Entry lifetime |
| `client` | factory | Already `redis_client`; call `cls.client()` |

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
- Logging (`python-logging`): always `LOG_LEVEL`; optional `WRITE_LOGS_TO_FILE`; `Constants.LOG_FORMAT`
  when the formatter is shared. Per-library fields only when that library is in the repo:
  `FASTAPI_LOG_LEVEL`, `TELEGRAM_LOG_LEVEL`, `HTTP_REQUESTS_LOG_LEVEL`, `SQLALCHEMY_LOG_LEVEL`,
  `REDIS_LOG_LEVEL`.
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
description: SQLAlchemy async adapter — asession, atransaction, ORM models, optional Postgres
globs:
  - "**/adapters/database.py"
  - "**/models.py"
  - "**/repositories.py"
alwaysApply: false
---

# SQLAlchemy adapter

Runtime: SQLAlchemy 2 async (`asyncpg`). JSON columns use `JSONB`.

One adapter module owns the engine and sessions. If it is missing, copy sibling `DATABASE.md`
into `project/infrastructure/adapters/database.py` (and the Settings contract into
`SettingsValidator` in `settings.py` — see `python-settings`).

| Need | Call |
|---|---|
| Read | `async with asession() as session` |
| Write / commit | `async with atransaction() as session` |
| Nested write inside an open tx | `atransaction()` → savepoint |
| Join the open tx, or begin if none | `current_atransaction()` |
| Create schema in tests/e2e | `create_all_tables(metadata)` |
| After DSN / Settings override | `aengine_factory.cache_clear()` and `async_sessionmaker_factory.cache_clear()` |

`asession()` reuses the `ContextVar` session or opens one and closes it on exit.
`atransaction()` begins, or `begin_nested()` when already in a transaction.
Do not call `session.commit()` / `session.close()` by hand inside these helpers.

`aengine_factory` is `@lru_cache` because `create_async_engine` owns a connection pool —
one engine per process. `async_sessionmaker_factory` is cached only so it stays bound to
that engine. Do not cache `AsyncSession`: `asession()` already reuses via ContextVar.

DSN from `Settings().get_database_dsn()` (`SQLALCHEMY_DATABASE_DSN` or assembled `DB_*`).
Optional `DB_SCHEMA` → `search_path`. `DATABASE_PRE_PING` on the engine.

If the product can run without Postgres, skip persistence when `database_is_configured()` is false;
do not fail at import. Side-effect writes log `logger.exception` and leave the main flow running.
Writes that are the result still go through a repository inside `atransaction()`.
A use case that must write through several repositories wraps the calls in one `atransaction()`
(or a `Repositories.transaction()` helper on the container, if the repo already has one).

If the repo already has Alembic, follow `python-alembic`: generate a revision after every model
change and apply it. Do not add a migrator to a repo that creates tables from metadata only
(`create_all` / `create_all_tables`).

## ORM models

SQLAlchemy 2.0: `Mapped` / `mapped_column`. Models inherit `Base` / `TimeMixin` from
`project.components.base.models` (`python-structure`). JSON columns use `JSONB`.
Foreign keys set `ondelete` when cascade/restrict matters. Identity and other entity keys use
domain types from `project/datatypes.py`, not bare `int` / `str`. Primary keys: `BigInteger`.
Postgres enums: `class Role(str, enum.Enum)` + `mapped_column(Enum(Role, name="role_enum"))`.
Many-to-many: `ARRAY` of ids (`Mapped[list[TagIdT]]`), not an association table.
Index columns used for filter, sort, or FK lookup.
Application rules stay in Python — no new triggers or stored procedures.

A new model also gets a `SQLAlchemyFactory` in `tests/factories.py` (`python-polyfactory`).
Follow existing `__tablename__` style in the repo.

Services and use cases never import SQLAlchemy, never create `AsyncSession`, never write SQL —
only repositories do.

Tests: Testcontainers Postgres, schema via `create_all`, then a nested transaction per test and
rollback (fixtures in `python-tests` / `CONFTEST.md`). Row data stays in the test or a factory
`build` / `create_async` (`python-polyfactory`).

When `python-monitoring` is installed, after `build_prometheus_metrics` call
`register_sqlalchemy_engine_monitoring(engine, database="…")` (async engines are fine).

## `python-structure/python-structure.mdc`

---
description: Component layout — apps, adapters, components, base generics, libs, layers
alwaysApply: true
---

# Repository structure

Group modules by component (one domain per directory). Put new code in the matching layer;
do not mix adapters with services or use cases.
SQLAlchemy stays in `adapters`, `orm` (`models.py`), and `repo` (`repositories.py`).
Redis stays in `adapters` (`acache.py`) and `repo` (`*CacheRepository` in `repositories.py`).

```text
project/
  datatypes.py                        NewType domain ids and names
  infrastructure/apps/api.py          FastAPI app, router registration
  infrastructure/apps/bot.py          Telegram bot, handler registration
  infrastructure/apps/main.py         production entry
  infrastructure/adapters/            external systems (HTTP, DB, cache, queues)
  infrastructure/utils/               framework helpers, not domain (`base_client` → adapters in layers.toml)
  components/base/                    shared generics used by every domain component
    models.py                         SQLAlchemy Base / MetaData (`public_schema`), TimeMixin
    schemas.py                        Pydantic envelopes (`ApiResponseSchema[T]`)
    repositories.py                   generic repository base (async; when the repo needs one)
    handlers.py                       shared Telegram handlers (when the repo has a bot)
  components/{name}/
    endpoints.py                      HTTP handlers
    handlers.py                       bot I/O (presentation in layers.toml)
    use_cases.py                      orchestration
    service.py                        stateless domain behavior
    repositories.py                   all data access
    models.py                         ORM
    schemas.py                        Pydantic
    enums.py                          closed value sets
    exceptions.py                     component errors
    interfaces.py                     Protocol stubs for adapters
    validation.py                     input-check helpers used by use cases
    cli.py                            CLI
    ai/{agent}/                       agent, prompts, tools, schemas, exceptions
  libs/                               reusable, no domain, no infrastructure
  exceptions.py                       AppError
  logger.py  settings.py  container.py
tests/
  conftest.py  factories.py
  test_modules/                       modular tests (mocks)
  test_e2e/                           end-to-end tests (live deps)
```

`settings.py` is the pydantic-settings env contract (`python-settings`).
`logger.py` is `setup_logging()` / dictConfig (`python-logging`).
`container.py` stays at package root (libs must not import infrastructure).
Domain workflows with explicit states use `python-fsm` (`project/libs/fsm.py`).
Transient I/O retries use `python-retry` (`project/libs/retry.py`).
`endpoints.py` and `apps/api.py` belong with the FastAPI adapter;
`handlers.py` and `apps/bot.py` belong with the Telegram adapter (`python-telegram`);
`models.py` belongs with the SQLAlchemy adapter;
`repositories.py` holds SQLAlchemy and Redis cache repositories (`python-sqlalchemy`, `python-redis`).

## Shared generics (`components/base`)

Put cross-component generics in `project/components/base/`. Domain components subclass or reuse
them; do not copy `Base`, CRUD helpers, or the HTTP envelope into each `components/{name}/`.
Keep feature-specific code in the domain component.

`libs/` stays domain-free and infrastructure-free (`fsm`, `retry`, `structures`). ORM `Base` and
generic repositories live in `components/base`, not in `libs/`. `layers.toml` globs
`project.components.*` already cover `base`.

| File | When | Copy if missing |
|---|---|---|
| `models.py` | SQLAlchemy | sibling `BASE_MODELS.md` → `project/components/base/models.py` (`python-sqlalchemy`, `python-alembic`) |
| `schemas.py` | FastAPI envelope | sibling `BASE_SCHEMAS.md` → `project/components/base/schemas.py` (`python-fastapi`) |
| `repositories.py` | generic ORM/cache repo | write async `asession` / `atransaction` (`python-sqlalchemy`); Redis `CacheRepository` follows `python-redis` |
| `handlers.py` | Telegram bot | shared handlers only (`python-telegram`); register from `apps/bot.py` |

If the repo needs a generic ORM repository, inherit domain repos from it. Session helpers are
async (`asession` / `atransaction` / `current_atransaction`), not sync `Session`:

```python
class ORMRepository[T: Base]:
    _model: ClassVar[type[T]]

    @classmethod
    async def get_or_none(cls, pk: object) -> T | None:
        async with asession() as session:
            return await session.get(cls._model, pk)
```

## Layers

Lower layers do not import higher ones. Domain modules do not import adapters or frameworks;
annotate expected collaborators with `Protocol` in `interfaces.py`.

- **Service** — stateless; hides a business process. Put work that other components will reuse here.
- **Use case** — I/O entry (HTTP, CLI, bot). Coordinates services; no SQL, no `AsyncSession`,
  no Redis client. Other components do not call use cases. Keep it short; names are business verbs.
  Input checks live here; shared check functions go in `validation.py`.
- **Repository** — the only data-access type; stateless. Inherit from `components.base` when a
  generic base exists. One extra repository when one transaction spans models that do not belong together.
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
from `python-base-client` (`project/infrastructure/utils/base_client.py`; copy that rule's
`ASYNC_CLIENT.md` or `SYNC_CLIENT.md` if missing). `layers.toml`: `base_client` is adapters, not
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
  - "**/utils/telegram.py"
alwaysApply: false
---

# Telegram bot adapter

Runtime: [python-telegram-bot](https://docs.python-telegram-bot.org/) (`ApplicationBuilder`, polling,
`HTTPXRequest`, `AIORateLimiter`, `concurrent_updates`). Extra: `python-telegram-bot[job-queue,rate-limiter]`.
Not aiogram.

Handlers live in `project.components.{name}.handlers`. Shared bot-wide handlers live in
`project.components.base.handlers` (`python-structure`). Register them from
`project.infrastructure.apps.bot`. Decorator helpers live in `project.infrastructure.utils.telegram`.
If `telegram.py` or `bot.py` is missing, copy sibling `TELEGRAM.md` into
`project/infrastructure/utils/telegram.py` and `BOT.md` into `project/infrastructure/apps/bot.py`.

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
    container = Container()
    await container.example_use_case.run(update.effective_user.id)
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

## Optional harnesses (install when needed)

This rule stays stack-agnostic. When the repo gains a concern, install the matching catalog ID
from `python-harness` (re-run the setup skill or copy that rule dir) and apply the companion patch
below — do not invent local variants.

| Need | Catalog ID | Also copy / merge |
|---|---|---|
| Test data factories | `python-polyfactory` | `FACTORIES.md` → `tests/factories.py`; companion patch in this file |
| Frozen clock in tests | `python-freezegun` | — |
| Postgres / ORM tests | `python-sqlalchemy` | sibling `CONFTEST_DATABASE.md` → `tests/conftest.py`; companion patch in this file |
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

