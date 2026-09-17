# -*- coding: utf-8 -*-
"""Baron Munchausen (пакет mnemos): MCP-сервер-скелет (JSON-RPC 2.0 поверх stdlib http.server).

fastmcp/mcp недоступны в системном python — интерфейс MCP реализован вручную
по спецификации Model Context Protocol (JSON-RPC 2.0 over HTTP):

  POST /  с телом {"jsonrpc":"2.0","id":1,"method":"initialize",...}
  методы: initialize, notifications/initialized, ping, tools/list, tools/call

Ядро (всегда):
  memory_add(claim, source, evidence, context, kind, links) -> узел
  memory_verify(node_id) -> вердикт П1-П6 (verdict, score, notes);
      проход «pass» ПОДКРЕПЛЯЕТ узел (вес растёт — проверенная память крепче)
  memory_search(query, top_k) -> топ-k узлов по подстроке
  memory_rewrite(node_id, new_claim, source, reason) -> переписывание узла
      новым фактом (старое утверждение остаётся в revisions — пластичность)
  memory_counter_take(counter, agent) -> следующий номер из узла-счётчика
      (чтение и увеличение под одним замком графа; mnemos/counter.py)
  memory_counter_reserve(counter, number, agent) -> записать номер, занятый
      мимо счётчика, и подвинуть next — тем же замком
  memory_reinforce(node_id, delta) -> подкрепление веса вручную
  memory_link(parent_id, claim, ...) -> новый узел-ребёнок внутри родителя
      («граф в узле», структурная рекурсия; глубина ограничена MAX_DEPTH)

Плагины (контекст-модуль — отдельный подключаемый/отключаемый плагин,
правило проекта; см. mnemos/plugins.py):
  context_engine (ВКЛЮЧЁН по умолчанию) — context_compact, context_prefix,
      context_defragment; выключен — инструментов нет в tools/list и tools/call.
  gates — слой гейтов Г1-Г5 при выгрузке сводок (capability, без инструментов).

Конфигурация: env MNEMOS_PLUGINS="context_engine,gates" | plugins.json
{"enabled": [...]} | аргумент --plugins | параметр plugins при встраивании.

Запуск:  py -3.12 -m mnemos --port 8765 --store nodes.json
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import signal
import threading
import time
import traceback
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

import re

from . import grounding, privacy, pulse as pulse_mod, sync_queue, thread as thread_mod, trace
from . import i18n
from .budget import ensure_router_tag
from .gates import run_read_gates, run_write_gates
from . import archive as archive_mod
from . import counter as counter_mod
from . import sandbox as sandbox_mod
from .model import DEFAULT_HALF_LIFE_HOURS, MemoryNode, make_node
from .plugins import PluginManager, resolve_enabled_plugins
from .store import WEAK_LIMIT, Store, blank_target, resolve_store_path
from .truth_gate import check_and_update

# Г4 сверяет новый claim со всем стором (линейно): 43 мс на 3121 узле
# (замер 01.09). Потолок скана — чтобы запись не деградировала при росте
# графа; сверяются самые свежие узлы, факт усечения виден в ответе.
GATE_MAX_SCAN = 5000

_RE_NODE_ID = re.compile(r"\bmn_[0-9a-f]{6,}\b")


class GateRejected(ValueError):
    """Запись отклонена гейтами Г1-Г5 (не баг сервера, а решение памяти)."""


def _first_node_id(text: str) -> Optional[str]:
    """id узла, на который сослался гейт (для подкрепления оригинала)."""
    m = _RE_NODE_ID.search(str(text or ""))
    return m.group(0) if m else None


def _as_float(value: Any) -> Optional[float]:
    """float или None — без падения на мусорном вводе от клиента."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> Optional[int]:
    """int или None — как _as_float, для целочисленных параметров."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

PROTOCOL_VERSION = "2025-03-26"
# Имя, под которым продукт видит пользователь. Внутреннее имя пакета
# осталось mnemos; наружу — Baron Munchausen. Старое имя доступно как
# LEGACY_SERVER_NAME и отдаётся в /health полем "legacy_name", чтобы уже
# написанные проверки клиентов не сломались.
SERVER_NAME = "baron-munchausen"
PRODUCT_NAME = "Baron Munchausen"
LEGACY_SERVER_NAME = "shinemnemos"
log = logging.getLogger("mnemos.server")
# Медленный вызов инструмента (wave2, фронт 6): выше порога — WARNING с
# разбивкой по фазам, чтобы по логу было видно, куда ушло время.
SLOW_MS = float(os.environ.get("MNEMOS_SLOW_MS", "200"))
STARTED_AT = time.time()


class JsonLogFormatter(logging.Formatter):
    """Одна строка JSON на запись: ts, level, logger, msg + поля из extra."""

    _SKIP = {"name", "msg", "args", "levelname", "levelno", "pathname", "filename", "module",
             "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created", "msecs",
             "relativeCreated", "thread", "threadName", "processName", "process", "message",
             "taskName", "asctime"}

    def format(self, record: logging.LogRecord) -> str:
        out: Dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
            + f".{int(record.msecs):03d}Z",
            "level": record.levelname, "logger": record.name, "msg": record.getMessage(),
        }
        for k, v in record.__dict__.items():
            if k not in self._SKIP and not k.startswith("_"):
                out[k] = v
        if record.exc_info:
            out["traceback"] = self.formatException(record.exc_info)
        return json.dumps(out, ensure_ascii=False, default=str)


def configure_logging(level: Optional[str] = None) -> None:
    """Структурный лог в stderr (LaunchAgent/systemd собирают его в файл).
    Уровень — MNEMOS_LOG_LEVEL (INFO по умолчанию)."""
    lvl = (level or os.environ.get("MNEMOS_LOG_LEVEL") or "INFO").upper()
    root = logging.getLogger("mnemos")
    root.setLevel(getattr(logging, lvl, logging.INFO))
    if not any(isinstance(h, logging.StreamHandler) and getattr(h, "_mnemos_json", False)
               for h in root.handlers):
        h = logging.StreamHandler()
        h.setFormatter(JsonLogFormatter())
        h._mnemos_json = True  # type: ignore[attr-defined]
        root.addHandler(h)
    root.propagate = False
# Ф1 02.09: бюджет system-prompt из памяти по умолчанию (план Ильи: <= 1200 токенов)
PROMPT_DEFAULT_TOKENS = 1200
SERVER_VERSION = "0.6.1"  # 10.09: memory_counter_reserve — вторая точка выдачи номеров под тем же замком
# 0.5.0 (wave2 05.09): журнал стора, checkpoint, batch add, паспорт агента

# Grounded по умолчанию (приказ Ильи 03.09). Проход через граф — не опция, а
# режим работы: сервер стартует с ним ВКЛЮЧЁННЫМ у всех пользователей, и без
# пред-прохода (memory_ground_prepare) ответ агента помечается ungrounded.
# Выключается осознанно — env MNEMOS_GROUND_BY_DEFAULT=0 или
# `python -m mnemos --no-ground-by-default`.
GROUND_BY_DEFAULT = True
GROUND_ENV = "MNEMOS_GROUND_BY_DEFAULT"
# Потолок длины строк-идентификаторов протокола (session_id, agent): они едут
# в журнал как есть, поэтому ограничиваются на входе.
MAX_ID_LEN = 200
# wave2: батч memory_add и выдержка memory_checkpoint
MAX_BATCH_ITEMS = 50
CHECKPOINT_TOP_K = 8
# правило: тег архива. Узел с ним остаётся в памяти и находится явным
# memory_search, но в выдержку memory_checkpoint не поднимается.
ARCHIVED_TAG = "status:archived"

#: правило: нить, в которую memory_archive складывает сводки дня, если
#: вызывающий не назвал свою. Отдельная от нити продукта: сводка циклов
#: бота — это не запись сессии дирижёра.
ARCHIVE_DEFAULT_SLUG = "bot"

# TS.1 (фаза S): узлы песочницы — карантин. Нить thread:sandbox и всё,
# помеченное state:trip, живут в памяти и находятся явным memory_search, но
# в выдержку начала сессии основной нити не поднимаются и в выгрузку Obsidian
# не уезжают: трип порождает предположения при ослабленных гейтах, и пускать
# их в общий граф до трезвой фазы нельзя (R4 §3 Л1, §4.2).


def _cut_hidden(search: Any) -> Any:
    """Убрать карантинные узлы из выдачи `search_budget` и пересчитать count.

    Один помощник на все входы в `graph_first` и в сборку промпта: их три
    (`memory_checkpoint`, `memory_ground_prepare`, `memory_answer`) плюс
    `memory_prompt`, и заплатка на каждом входе по отдельности — ровно тот
    способ, которым дыра и появилась.
    """
    if not isinstance(search, dict):
        return search
    kept = [r for r in (search.get("results") or []) if not _hidden_from_thread(r)]
    search["results"] = kept
    search["count"] = len(kept)
    return search


def _hidden_from_thread(node: Any) -> bool:
    """Узел не поднимается в выдержку начала сессии основной нити."""
    tags = node.get("tags") or [] if hasattr(node, "get") else []
    if ARCHIVED_TAG in tags:
        return True
    return sandbox_mod.is_quarantined(node)


# фаза 2 (нить проекта): записей сессий в thread-блоке checkpoint
THREAD_SESSIONS_DEFAULT = 3
THREAD_SESSIONS_MAX = 20
# memory_rewrite(kind=…): те же виды, что в memory_add (hub — только офлайн)
# T2.11: сколько последних записей prepare смотреть, чтобы найти открытые сессии нити.
THREAD_ACTIVE_JOURNAL_TAIL = 400
REWRITE_KINDS = ("fact", "hypothesis", "refuted", "outdated", "rule", "api", "task", "result",
                 "digest", "cost", "incident")
# правило: очередь изменённых узлов для событийного экспорта в Obsidian.
# MNEMOS_SYNC_QUEUE=0 выключает её — витрина тогда живёт только таймером.
SYNC_QUEUE_ENV = "MNEMOS_SYNC_QUEUE"

_TRUE_WORDS = ("1", "true", "yes", "on", "да")
_FALSE_WORDS = ("0", "false", "no", "off", "нет")


def _env_flag(name: str, default: bool, env: Optional[Dict[str, str]] = None) -> bool:
    """Булев флаг из окружения. Мусор — ошибка старта, а не тихий дефолт.

    Опечатка в MNEMOS_GROUND_BY_DEFAULT=flase не должна молча оставлять
    политику в состоянии, которого администратор не выбирал: он узнает об
    этом не из логов, а из ответов агента, которые «почему-то ungrounded».
    """
    env = os.environ if env is None else env
    raw = env.get(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value == "":
        # Пустое значение — это «не задано», а НЕ «выключить». Юнит со строкой
        # `Environment=MNEMOS_GROUND_BY_DEFAULT=` не должен молча снимать
        # обязательный проход через граф: выключение делается словом.
        return default
    if value in _TRUE_WORDS:
        return True
    if value in _FALSE_WORDS:
        return False
    raise ValueError(
        f"{name}={raw!r}: expected one of {_TRUE_WORDS + _FALSE_WORDS}"
    )


# фикс аудита 26.08: лимит HTTP-тела — защита от DoS (B5): клиент с
# Content-Length: 10GB не должен заставить сервер читать 10 ГБ в память.
# wave2 (фронт 7): 2 МБ — батч из 50 узлов по 16 КБ влезает с запасом.
MAX_BODY_BYTES = 2 * 1024 * 1024
# Лимиты размера узла и запроса (wave2, фронт 7). Узел — факт, а не документ:
# claim/context/source до 16 КБ, evidence до 100 строк по 4 КБ, вопрос до 4 КБ,
# сверяемый ответ до 100 КБ (потолок утверждений MAX_CLAIMS всё равно 24).
MAX_CLAIM_CHARS = 16_000
MAX_FIELD_CHARS = 16_000
MAX_LIST_ITEMS = 100
MAX_EVIDENCE_ITEM_CHARS = 4_000
MAX_QUERY_CHARS = 8_000
MAX_ANSWER_CHARS = 100_000
# Лимит частоты для неразрешённых источников (wave2, фронт 7): запросы с чужим
# Origin, не-JSON, битым JSON или превышенным телом считаются по адресу
# клиента; свыше RATE_LIMIT_REJECTS за минуту — 429 без обработки. Обычный
# локальный клиент (без Origin, валидный JSON) счётчик не трогает.
RATE_LIMIT_REJECTS = int(os.environ.get("MNEMOS_RATE_LIMIT_REJECTS", "60"))
RATE_LIMIT_WINDOW = 60.0


def _text_limit(value: Any, limit: int, what: str) -> None:
    if isinstance(value, str) and len(value) > limit:
        raise ValueError(f"{what}: length {len(value)} — the cap is {limit} characters")


def _list_limit(value: Any, what: str, item_limit: Optional[int] = None) -> None:
    if isinstance(value, (list, tuple)):
        if len(value) > MAX_LIST_ITEMS:
            raise ValueError(f"{what}: {len(value)} items — the cap is {MAX_LIST_ITEMS}")
        if item_limit:
            for e in value:
                if isinstance(e, str) and len(e) > item_limit:
                    raise ValueError(f"{what}: an item of length {len(e)} — the cap is {item_limit} characters")


class RateLimiter:
    """Скользящее окно по ключу (адрес клиента): hit() -> можно ли ещё."""

    MAX_KEYS = 10_000

    def __init__(self) -> None:
        self._hits: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window: float = RATE_LIMIT_WINDOW) -> bool:
        now = time.monotonic()
        with self._lock:
            if len(self._hits) > self.MAX_KEYS:
                self._hits.clear()
            q = [t for t in self._hits.get(key, []) if now - t < window]
            q.append(now)
            self._hits[key] = q
            return len(q) <= limit

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

# JSON-RPC коды ошибок
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
NODE_NOT_FOUND = -32002  # свой код: узел не найден

# R12-6: поле text ответа memory_prompt было побайтным дублем prompt.
# Одна версия отдаёт вместо него это предупреждение — потом уйдёт и оно.
def prompt_text_deprecated(lang: Optional[str] = None) -> str:
    return i18n.pick(
        "the text field is gone: it was a byte-for-byte duplicate of prompt. "
        "Read prompt.",
        "поле text убрано: оно было побайтным дублем prompt. Читай prompt.",
        lang,
    )

def build_tools(lang: Optional[str] = None) -> List[Dict[str, Any]]:
    """MCP-схемы инструментов на языке поверхности.

    English по умолчанию, русский — при BARON_LANG=ru. Язык читается в момент
    вызова, поэтому `tools/list` отдаёт то, что просит окружение сессии, а не
    то, что было при импорте модуля. Имена инструментов, ключи схем, enum'ы и
    коды ошибок не переводятся никогда — это контракт.
    """

    def P(en: str, ru: str) -> str:
        return i18n.pick(en, ru, lang)

    audience_desc = P(
        "правил проекта: audience=public returns ONLY nodes tagged visibility:public — "
        "everything else (including anything unlabelled) is cut off. Required "
        "for any output leaving the machine",
        "правил проекта: audience=public отдаёт ТОЛЬКО узлы с тегом "
        "visibility:public — всё остальное (в том числе всё без метки) "
        "отрезается. Обязателен для любого вывода наружу машины",
    )
    counter_desc = P(
        "Counter name; the node is looked up by tag counter:<name> "
        "(e.g. next_decision). A full tag is accepted too",
        "Имя счётчика; узел ищется по тегу counter:<имя> "
        "(например next_decision). Полный тег тоже принимается",
    )

    return [
    {
        "name": "memory_add",
        "description": P(
            "Add a memory node. Creates the node, runs truth-gate P1-P6 and "
            "returns it with the truth_check verdict. Project thread "
            "(docs/product/THREAD.md, v1): an item tagged thread:<slug> + "
            "thread_head is the thread head (claim '[THREAD:<slug>] last step: … | "
            "next step: … | updated: <date> <agent>/<session_id>'), kind is always "
            "rule, no ttl; if an active head already exists it is REWRITTEN "
            "(rewritten: true, same id) instead of duplicated; a claim prefixed "
            "with [THREAD:<slug>] counts as a head even without the tag. "
            "thread_head and session require the agent/session_id passport.",
            "Добавить узел памяти. Создаёт узел, прогоняет через truth-gate "
            "П1-П6 и возвращает его с вердиктом truth_check. Нить проекта "
            "(docs/product/THREAD.md, v1): элемент с тегами thread:<slug> + "
            "thread_head — голова нити (claim «[THREAD:<slug>] последний шаг: … | "
            "следующий шаг: … | обновлено: <дата> <agent>/<session_id>»), kind "
            "всегда rule, без ttl; если активная голова уже есть — она "
            "ПЕРЕПИСЫВАЕТСЯ (rewritten: true, id прежний), а не дублируется; claim "
            "с префиксом [THREAD:<slug>] считается головой и без тега. "
            "Для thread_head и session обязателен паспорт agent/session_id.",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "claim": {"type": "string", "description": P(
                    "The statement (required)", "Утверждение (обязательно)")},
                "source": {"type": "string", "description": P(
                    "Where the statement comes from", "Источник утверждения")},
                "evidence": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": P(
                        "Evidence for reproducibility (P5)",
                        "Свидетельства для воспроизводимости (П5)"),
                },
                "context": {"type": "string", "description": P(
                    "Context (completeness, P6)", "Контекст (полнота, П6)")},
                "aliases": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": P(
                        "Alternative sources with the same content (the same vault "
                        "note duplicated across folders): one node instead of many",
                        "Альтернативные source того же содержания (дубли заметки в "
                        "разных папках vault): один узел вместо нескольких",
                    ),
                },
                "kind": {
                    "type": "string",
                    "enum": ["fact", "hypothesis", "refuted", "outdated", "rule", "api", "task", "result"],
                    "description": P(
                        "Node kind. rule — a team rule: never decays below 0.5 "
                        "and is never removed by cleanup. api — API catalogue "
                        "(public-apis). task — a subagent task, result — its answer "
                        "with parent=<task id>. Hubs (kind=hub) are not "
                        "created over MCP — only by the offline clusterer",
                        "Тип узла. rule — правило команды: не тускнеет ниже 0.5 "
                        "и не удаляется уборкой. api — каталог API (public-apis). "
                        "task — задача субагенту, result — его ответ с parent=<id задачи> "
                        ". Хабы (kind=hub) через MCP не создаются — только "
                        "офлайн-кластеризатором",
                    ),
                },
                "parent": {
                    "type": "string",
                    "description": P(
                        "id of the parent node: the new node becomes its child "
                        "(parent/children, like memory_link). For kind=result — the "
                        "task id. If no such node exists the node is still stored, "
                        "without the edge, tagged link:orphan and with warnings in "
                        "the response",
                        "id родительского узла: новый узел становится его ребёнком "
                        "(parent/children, как memory_link). Для kind=result — id задачи. "
                        "Если такого узла нет, узел всё равно записывается без ребра, "
                        "с тегом link:orphan и warnings в ответе",
                    ),
                },
                "strict_parent": {
                    "type": "boolean",
                    "description": P(
                        "true — a missing parent rejects the whole call (-32002) and "
                        "nothing is stored. Default false",
                        "true — несуществующий parent отвергает весь вызов (-32002), "
                        "узел не пишется. По умолчанию false",
                    ),
                },
                "author": {
                    "type": "string",
                    "description": P(
                        "Who creates the node/edges (e.g. alice) — the link_meta "
                        "passport of the edges",
                        "Кто создаёт узел/рёбра (например alice) — паспорт "
                        "рёбер link_meta",
                    ),
                },
                "links": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": P(
                        "Links to other nodes (consistency, P4)",
                        "Ссылки на другие узлы (непротиворечивость, П4)"),
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": P(
                        "Node tags (rule, trading, infra, p0 ...)",
                        "Метки узла (правило, торговля, инфра, p0 ...)"),
                },
                "confidence": {
                    "type": "number",
                    "description": P(
                        "Confidence 0..1 (default: truth-gate score / 6)",
                        "Уверенность 0..1 (по умолчанию — score truth-gate / 6)"),
                },
                "ttl_hours": {
                    "type": "number",
                    "description": P(
                        "Expires in N hours (volatile facts: balance, equity, status)",
                        "Протухнет через N часов (volatile-факты: баланс, equity, статус)"),
                },
                "valid_until": {
                    "type": "string",
                    "description": P(
                        "Explicit ISO-8601 expiry (takes precedence over ttl_hours)",
                        "Явный ISO-8601 срок годности (приоритетнее ttl_hours)"),
                },
                "agent": {"type": "string", "description": P(
                    "Who writes (for the log and the node passport)",
                    "Кто записывает (для журнала и паспорта узла)")},
                "session_id": {"type": "string", "description": P(
                    "Session the node was written in",
                    "Сессия, в которой записан узел")},
                "items": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": P(
                        "Batch (wave2): a list of objects with the same fields as a "
                        "single node (claim required). Each passes the gates on its "
                        "own; the response reports stored/rejected per item. A "
                        "top-level claim is then unnecessary",
                        "Батч (wave2): список объектов с теми же полями, что и один узел "
                        "(claim обязателен). Каждый проходит гейты отдельно; в ответе — "
                        "stored/rejected по каждому. claim на верхнем уровне тогда не нужен",
                    ),
                },
            },
        },
    },
    {
        "name": "memory_checkpoint",
        "description": P(
            "ONE call instead of memory_search + memory_ground_prepare (wave2): "
            "searches the graph, returns a compact excerpt (id | fact), checks "
            "graph-first and registers the session pre-pass. Next: answer from "
            "the excerpt and call memory_ground(answer_text, session_id).",
            "ОДИН вызов вместо memory_search + memory_ground_prepare (wave2): "
            "ищет по графу, отдаёт компактную выдержку (id | факт), проверяет "
            "graph-first и регистрирует пред-проход сессии. Дальше: ответь по "
            "выдержке и вызови memory_ground(answer_text, session_id).",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": P(
                    "Task topic or the user's question",
                    "Тема задачи или вопрос пользователя")},
                "session_id": {"type": "string", "description": P(
                    "Dialogue id; generated if omitted",
                    "id диалога; без него сгенерируется")},
                "agent": {"type": "string", "description": P("Who asks", "Кто спрашивает")},
                "top_k": {"type": "integer", "description": P(
                    "How many facts to return (default 8)",
                    "Сколько фактов вернуть (по умолчанию 8)")},
                "threshold": {"type": "number", "description": P(
                    "graph-first threshold (default 0.65)",
                    "Порог graph-first (по умолчанию 0.65)")},
                "thread": {
                    "type": "string",
                    "description": P(
                        "Project thread slug (docs/product/THREAD.md, v1): the response "
                        "gains a thread field (head: phase/last step/next step/open "
                        "decisions, recent sessions, open tails, questions for the owner, "
                        "decisions), the head is guaranteed to be facts[0] and text starts "
                        "with 'THREAD <slug> v1 | …'. Detected automatically when query "
                        "starts with '[THREAD:<slug>]'",
                        "Slug нити проекта (docs/product/THREAD.md, v1): в ответ добавляется "
                        "поле thread (голова: фаза/последний/следующий шаг/открытые решения, "
                        "свежие сессии, открытые хвосты, открытые вопросы, решения), голова "
                        "гарантированно в facts[0], text начинается с «THREAD <slug> v1 | …». "
                        "Определяется и автоматически, если query начинается с «[THREAD:<slug>]»",
                    ),
                },
                "sessions": {
                    "type": "integer",
                    "description": P(
                        "How many recent thread session entries to return (default 3, cap 20)",
                        "Сколько последних записей сессий нити вернуть (по умолчанию 3, потолок 20)"),
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "memory_verify",
        "description": P(
            "Verify a memory node against protocol P1-P6 -> verdict + score + notes.",
            "Проверить узел памяти по протоколу П1-П6 → verdict + score + notes."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": P(
                    "Memory node id", "id узла памяти")}
            },
            "required": ["node_id"],
        },
    },
    {
        "name": "memory_search",
        "description": P(
            "Find memory nodes, top-k. mode=substring — by substring "
            "(claim/source/context/evidence; for nodes at level L1/L2 — over the "
            "compacted level text + keys, L0/L1 boosted); if the whole phrase is "
            "not found, falls back to word stems (mode in the response is "
            "token_fallback). mode=budget — token budgeting (top_k auto by "
            "complexity, graph expansion). mode=semantic — by meaning (fastembed). "
            "mode=rrf — merges F1+BM25 (+dense when fastembed is present) via "
            "Reciprocal Rank Fusion; wins on keyword queries.",
            "Найти узлы памяти, топ-k. mode=substring — по подстроке "
            "(claim/source/context/evidence; у узлов на уровне L1/L2 — по "
            "сжатому тексту уровня + ключам, буст L0/L1); если целая фраза не "
            "найдена — фоллбек по основам слов (mode в ответе token_fallback). "
            "mode=budget — token-budgeting (top_k auto по сложности, граф-"
            "расширение). mode=semantic — по смыслу (fastembed). "
            "mode=rrf — слияние Ф1+BM25 (+плотный, если есть fastembed) по "
            "Reciprocal Rank Fusion; выигрыш даёт на ключевых словах.",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": P("Search query", "Поисковый запрос")},
                "top_k": {
                    "type": ["integer", "string"],
                    "description": P(
                        "How many results (1-50) or \"auto\" — by question "
                        "complexity: simple 5 / medium 10 / hard 20 (02.09)",
                        "Сколько результатов (1-50) или \"auto\" — по сложности "
                        "вопроса: простой 5 / средний 10 / сложный 20 (02.09)",
                    ),
                },
                "mode": {
                    "type": "string",
                    "enum": ["substring", "semantic", "budget", "rrf"],
                    "description": P(
                        "Search mode (default substring). budget — token budgeting: "
                        "substring + word stems (NL questions), graph expansion over "
                        "edges, hubs separately, token budget. rrf — signal fusion "
                        "(ML-BOOST 03.09): for keywords; worse than budget for an NL "
                        "question",
                        "Режим поиска (по умолчанию substring). budget — "
                        "token-budgeting: подстрока + основы слов (NL-вопросы), "
                        "граф-расширение по рёбрам, хабы отдельно, токенный бюджет. "
                        "rrf — слияние сигналов (ML-BOOST 03.09): для ключевых слов, "
                        "для NL-вопроса хуже budget",
                    ),
                },
                "budget": {"type": "boolean", "description": P(
                    "Same as mode=budget", "То же, что mode=budget")},
                "token_budget": {"type": "integer", "description": P(
                    "Token budget of the output (budget)",
                    "Бюджет токенов выдачи (budget)")},
                "expand": {"type": "boolean", "description": P(
                    "Graph expansion in budget (default true)",
                    "Граф-расширение в budget (по умолчанию true)")},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": P(
                        "Keep only nodes carrying all of these tags",
                        "Оставить только узлы со всеми этими тегами"),
                },
                "kind": {"type": "string", "description": P(
                    "Keep only nodes of this kind (e.g. rule)",
                    "Оставить только узлы этого вида (например rule)")},
                "hide_self": {
                    "type": "string",
                    "description": P(
                        "TS.5 (R4 L3): name of the agent whose own history is hidden "
                        "inside the thread:sandbox thread — the self-model ban of the "
                        "trip phase. Works together with relevance_gate=true and only "
                        "inside the sandbox; outside it an agent sees its history as usual",
                        "TS.5 (R4 Л3): имя агента, чью собственную историю скрыть "
                        "в нити thread:sandbox — запрет самомодели в фазе трипа. "
                        "Работает вместе с relevance_gate=true и только внутри "
                        "песочницы; вне её агент видит свою историю как обычно",
                    ),
                },
                "relevance_gate": {
                    "type": "boolean",
                    "description": P(
                        "Run the output through G2+G5 (freshness and relevance), default false",
                        "Прогнать выдачу через Г2+Г5 (свежесть и релевантность), по умолчанию false"),
                },
                "audience": {
                    "type": "string",
                    "enum": ["public", "all"],
                    "description": audience_desc,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "memory_get",
        "description": P(
            "Read one node by id in full (claim, kind, tags, parent, children, "
            "probe fields). A subagent receives task_name=TASK:<id> and reads the "
            "task with this call; the conductor reads the result by id.",
            "Прочитать один узел по id целиком (claim, kind, tags, parent, children, "
            "probe-поля). Субагент получает task_name=TASK:<id> и читает задачу этим "
            "вызовом; дирижёр — результат по id.",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"node_id": {"type": "string", "description": P(
                "Node id (mn_…)", "id узла (mn_…)")}},
            "required": ["node_id"],
        },
    },
    {
        "name": "memory_list",
        "description": P(
            "Batch walk over nodes by filters without a query: kind/tags/parent. "
            "kind=api — the API catalogue with probe fields (public-apis); "
            "parent=<task id> — subagent results.",
            "Пакетный перебор узлов по фильтрам без query: kind/tags/parent. "
            "kind=api — каталог API с probe-полями (public-apis); "
            "parent=<id задачи> — результаты субагентов.",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "description": P(
                    "Filter by node kind (e.g. api, result)",
                    "Фильтр по виду узла (например api, result)")},
                "parent": {"type": "string", "description": P(
                    "Only children of this node (task results by id)",
                    "Только дети этого узла (результаты задачи по id)")},
                "tags": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer", "description": P(
                    "1..10000, default 1000", "1..10000, по умолчанию 1000")},
                "offset": {"type": "integer", "description": P(
                    "How many nodes to skip (pagination)",
                    "Сколько узлов пропустить (пагинация)")},
                "audience": {
                    "type": "string",
                    "enum": ["public", "all"],
                    "description": audience_desc,
                },
            },
        },
    },
    {
        "name": "memory_archive",
        "description": P(
            "правил проекта — graph maintenance: delete the oldest and most useless, "
            "compact the not-very-useful into daily digests, keep the recent "
            "intact. Usefulness is computed from what is already stored: "
            "usage.count/hits (written by every search), weight (raised by a "
            "confirmed memory_ground) and the number of incoming edges. "
            "INVARIANTS: kind=rule/hub/digest is never touched; a node someone "
            "links to is never deleted; a node with an unparsable ts is not "
            "touched; max_delete/max_compress are hard caps. dry_run=true BY "
            "DEFAULT: numbers first, action second. Deletion requires an explicit "
            "actions=[\"compress\",\"delete\"] — compaction is reversible (the "
            "original becomes outdated and a child of the digest), deletion is not.",
            "правил проекта — обслуживание графа: самое старое и бесполезное удалить, "
            "не особо полезное сжать в сводки дня, свежее оставить целиком. "
            "Полезность считается по тому, что уже записано: usage.count/hits "
            "(их пишет каждый поиск), weight (его поднимает подтверждённый "
            "memory_ground) и число входящих рёбер. "
            "ИНВАРИАНТЫ: kind=rule/hub/digest не трогается никогда; узел, на "
            "который кто-то ссылается, не удаляется никогда; узел с "
            "неразбираемым ts не трогается; max_delete/max_compress — жёсткие "
            "потолки. dry_run=true ПО УМОЛЧАНИЮ: сначала числа, потом действие. "
            "Удаление требует явного actions=[\"compress\",\"delete\"] — сжатие "
            "обратимо (исходник становится outdated и ребёнком сводки), "
            "удаление нет.",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "dry_run": {"type": "boolean", "description": P(
                    "Default true", "По умолчанию true")},
                "actions": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["compress", "delete"]},
                    "description": P(
                        "What to apply. Default compress only",
                        "Что применять. По умолчанию только compress"),
                },
                "slug": {"type": "string", "description": P(
                    "Daily digest thread (default bot)",
                    "Нить сводок дня (по умолчанию bot)")},
                "older_than_days": {"type": "number", "description": P(
                    "A day younger than this is not folded (1.0)",
                    "День моложе — не сворачивается (1.0)")},
                "keep_days": {"type": "number", "description": P(
                    "Anything fresher than this is untouched (30)",
                    "Свежее этого не трогается (30)")},
                "compress_days": {"type": "number", "description": P(
                    "Older — a candidate for compaction (90)",
                    "Старше — кандидат на сжатие (90)")},
                "delete_days": {"type": "number", "description": P(
                    "Older and useless — up for deletion (365)",
                    "Старше и бесполезное — на удаление (365)")},
                "useful_hits": {"type": "integer", "description": P(
                    "usage.count at or above this — useful (3)",
                    "usage.count не ниже — полезный (3)")},
                "useful_weight": {"type": "number", "description": P(
                    "weight at or above this — useful (0.30)",
                    "weight не ниже — полезный (0.30)")},
                "max_delete": {"type": "integer", "description": P(
                    "Deletion cap per run (100)",
                    "Потолок удалений за проход (100)")},
                "max_compress": {"type": "integer", "description": P(
                    "Compaction cap per run (500)",
                    "Потолок свёрток за проход (500)")},
                "now": {"type": "string", "description": P(
                    "ISO-8601: a fixed 'now' (determinism)",
                    "ISO-8601: фиксированное «сейчас» (детерминизм)")},
                "agent": {"type": "string", "description": P(
                    "Passport: required when dry_run=false",
                    "Паспорт: обязателен при dry_run=false")},
                "session_id": {"type": "string", "description": P(
                    "Session passport", "Паспорт сессии")},
                "source": {"type": "string", "description": P(
                    "Source of the digests (default memory_archive)",
                    "Источник сводок (по умолчанию memory_archive)")},
                "product_tag": {"type": "string", "description": P(
                    "Extra product tag on the digest",
                    "Дополнительный тег продукта на сводке")},
            },
        },
    },
    {
        "name": "memory_export",
        "description": P(
            "Full cursor walk over the graph for export (Obsidian, backup). "
            "Unlike memory_list (offset by ts) the cursor is a node id: the order "
            "does not drift when new nodes are written mid-walk, and no node is "
            "lost between pages. since=<ISO> — only changed nodes; ids=[…] — "
            "exactly the named nodes, no walk.",
            "Полный обход графа с курсором для экспорта наружу (Obsidian, бэкап). "
            "В отличие от memory_list (offset по ts) курсор — id узла: порядок "
            "не плывёт, когда во время обхода пишут новые узлы, и ни один узел "
            "не пропадёт между страницами. since=<ISO> — только изменённые; ids=[…] — ровно названные узлы, без обхода.",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "cursor": {"type": "string", "description": P(
                    "id of the last node of the previous page (next_cursor)",
                    "id последнего узла прошлой страницы (next_cursor)")},
                "ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": P(
                        "правил проекта: return exactly these nodes instead of walking. The "
                        "cursor and kind/since then do not apply; sandbox and audience "
                        "filters do. Needed by the remote exporter: it keeps the graph "
                        "in memory and on an event pulls only the changed nodes instead "
                        "of all 3500",
                        "правил проекта: вернуть ровно эти узлы вместо обхода. Курсор и kind/since "
                        "при этом не действуют, фильтры песочницы и audience — действуют. "
                        "Нужен удалённому экспортёру: он держит граф в памяти и по событию "
                        "докачивает только изменившиеся узлы, а не все 3500",
                    ),
                },
                "limit": {"type": "integer", "description": P(
                    "1..5000, default 500", "1..5000, по умолчанию 500")},
                "kind": {"type": "string", "description": P(
                    "Filter by node kind", "Фильтр по виду узла")},
                "since": {"type": "string", "description": P(
                    "ISO-8601: only nodes with ts/last_used no earlier than this",
                    "ISO-8601: только узлы с ts/last_used не раньше")},
                "include_sandbox": {
                    "type": "boolean",
                    "description": P(
                        "TS.1: whether to return sandbox nodes (thread:sandbox / "
                        "state:trip). Default false — exports outward and into Obsidian "
                        "leave them behind",
                        "TS.1: отдавать ли узлы песочницы (thread:sandbox / state:trip). "
                        "По умолчанию false — выгрузка наружу и в Obsidian их не забирает",
                    ),
                },
                "audience": {
                    "type": "string",
                    "enum": ["public", "all"],
                    "description": audience_desc,
                },
            },
        },
    },
    {
        "name": "memory_update",
        "description": P(
            "Update the probe statuses of a node (observed_at/status/http_code/"
            "recheck_after/not_a_verdict). The claim is not rewritten: ingest and "
            "the liveness check address the node by id and by url.",
            "Обновить probe-статусы узла (observed_at/status/http_code/"
            "recheck_after/not_a_verdict). Claim не переписывается: ингест "
            "и liveness-проверка адресуют узел по id и по url.",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": P("Node id", "id узла")},
                "observed_at": {"type": "string", "description": P(
                    "ISO-8601 time of the check", "ISO-8601 время проверки")},
                "status": {"type": "string", "enum": ["alive", "auth_required", "dead", "unknown"]},
                "http_code": {"type": "integer"},
                "recheck_after": {"type": "string", "description": P(
                    "ISO-8601 next retry", "ISO-8601 следующий повтор")},
                "not_a_verdict": {"type": "boolean", "description": P(
                    "the probe is not a verdict about the product",
                    "probe не является вердиктом о продукте")},
            },
            "required": ["node_id"],
        },
    },
    {
        "name": "memory_rewrite",
        "description": P(
            "Rewrite a node with a new fact (plasticity): the claim is replaced, "
            "the old statement stays in revisions. The node passes truth-gate "
            "P1-P6 again.",
            "Переписать узел новым фактом (пластичность): claim заменяется, "
            "старое утверждение остаётся в revisions. Узел снова проходит "
            "truth-gate П1-П6.",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": P(
                    "Memory node id", "id узла памяти")},
                "new_claim": {"type": "string", "description": P(
                    "The new statement", "Новое утверждение")},
                "source": {"type": "string", "description": P(
                    "Source of the new fact", "Источник нового факта")},
                "context": {
                    "type": "string",
                    "description": P(
                        "New node context (the vault → mnemos return path: the full "
                        "note text changed while the claim did not). Omitted — the "
                        "previous one is kept",
                        "Новый контекст узла (обратный путь vault → mnemos: полный "
                        "текст заметки изменился, а claim — нет). Не передан — прежний",
                    ),
                },
                "reason": {"type": "string", "description": P(
                    "Why we rewrite it", "Почему переписываем")},
                "add_aliases": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": P(
                        "Append alternative sources (a duplicate note found later)",
                        "Дописать альтернативные source (дубль заметки найден позже)"),
                },
                "kind": {
                    "type": "string",
                    "enum": ["fact", "hypothesis", "refuted", "outdated", "rule"],
                    "description": P(
                        "Change the node kind (project thread, правил проекта: closing a tail = "
                        "kind=fact + tag closed; an answered question to the owner = "
                        "tag resolved)",
                        "Сменить вид узла (нить проекта, правил проекта: закрытие хвоста = "
                        "kind=fact + тег closed; снятый открытый вопрос = тег resolved)",
                    ),
                },
                "add_tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": P(
                        "Tags to add (e.g. closed, resolved); thread_head is forbidden",
                        "Теги, которые добавить (например closed, resolved); thread_head запрещён"),
                },
                "remove_tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": P(
                        "Tags to remove (e.g. open)",
                        "Теги, которые снять (например open)"),
                },
            },
            "required": ["node_id", "new_claim"],
        },
    },
    {
        "name": "memory_retract",
        "description": P(
            "Retract a node by id: kind=outdated, the validity window closes at "
            "the moment of retraction. The node leaves search, slices and "
            "grounded output but is NOT physically deleted — history, edges and "
            "revisions stay intact. Reversible: undo=true restores the previous "
            "kind and the previous validity.",
            "Отозвать узел по id: kind=outdated, окно валидности закрывается "
            "моментом отзыва. Узел уходит из поиска, среза и grounded, но "
            "физически НЕ удаляется — история, рёбра и revisions целы. "
            "Обратимо: undo=true возвращает прежний вид и прежний срок.",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": P(
                    "Memory node id", "id узла памяти")},
                "reason": {"type": "string", "description": P(
                    "Why the fact is retracted", "Почему факт отзывается")},
                "agent": {"type": "string", "description": P(
                    "Who retracts — written into the node",
                    "Кто отзывает — пишется в узел")},
                "undo": {
                    "type": "boolean",
                    "description": P(
                        "true — return a previously retracted node to service",
                        "true — вернуть ранее отозванный узел в строй"),
                },
            },
            "required": ["node_id"],
        },
    },
    {
        "name": "memory_counter_take",
        "description": P(
            "Hand out the next number from a counter node (tag counter:<name>) "
            "atomically: the read and the increment happen under one graph lock, "
            "the client receives an already-issued number. That way two agents on "
            "different machines cannot get the same number.",
            "Выдать следующий номер из узла-счётчика (тег counter:<имя>) "
            "атомарно: чтение и увеличение идут под одним замком графа, "
            "клиент получает уже выданное число. Так два агента с разных "
            "машин не могут получить один номер.",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "counter": {"type": "string", "description": counter_desc},
                "agent": {"type": "string", "description": P(
                    "Who the number is issued to — written into the node",
                    "Кому выдан номер — пишется в узел")},
                "session_id": {"type": "string", "description": P(
                    "Session passport (for the log)", "Паспорт сессии (в журнал)")},
                "reason": {"type": "string", "description": P(
                    "What the number is for — goes into the revision reason",
                    "Зачем номер — в reason ревизии")},
            },
            "required": ["counter", "agent"],
        },
    },
    {
        "name": "memory_counter_reserve",
        "description": P(
            "Record in the counter node a number taken outside the counter and "
            "move next past it — atomically, under the same graph lock as "
            "memory_counter_take. This is the second issuing point and races the "
            "same way: otherwise someone else's issue between the read and the "
            "write is lost and the number is handed out twice.",
            "Записать в узел-счётчик номер, занятый мимо счётчика, и подвинуть "
            "next за него — атомарно, тем же замком графа, что и "
            "memory_counter_take. Это вторая точка выдачи номеров, и гонка на "
            "ней возможна так же: иначе чужая выдача между чтением и записью "
            "теряется и номер выдаётся повторно.",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "counter": {"type": "string", "description": counter_desc},
                "number": {"type": "integer", "description": P(
                    "The taken number (e.g. 59)", "Занятый номер (например 59)")},
                "agent": {"type": "string", "description": P(
                    "Who took it — written into the node",
                    "Кем занят — пишется в узел")},
                "session_id": {"type": "string", "description": P(
                    "Session passport (for the log)", "Паспорт сессии (в журнал)")},
                "reason": {"type": "string", "description": P(
                    "What it was taken for — goes into the revision reason",
                    "Чем занят — в reason ревизии")},
            },
            "required": ["counter", "number", "agent"],
        },
    },
    {
        "name": "memory_reinforce",
        "description": P(
            "Reinforce a node: the weight grows (up to 1.0), last_used is "
            "updated. This is how memory remembers that a node was useful.",
            "Подкрепить узел: вес растёт (до 1.0), last_used обновляется. "
            "Так память запоминает, что узел пригодился.",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": P(
                    "Memory node id", "id узла памяти")},
                "delta": {"type": "number", "description": P(
                    "Weight increment (default 0.05)",
                    "Прибавка веса (по умолчанию 0.05)")},
            },
            "required": ["node_id"],
        },
    },
    {
        "name": "memory_link",
        "description": P(
            "Create a new child node inside a parent ('a graph within a node'). "
            "Depth is limited (MAX_DEPTH), cycles are forbidden.",
            "Создать новый узел-ребёнок внутри родителя («граф в узле»). "
            "Глубина ограничена (MAX_DEPTH), циклы запрещены.",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "parent_id": {"type": "string", "description": P(
                    "Parent node id", "id родительского узла")},
                "claim": {"type": "string", "description": P(
                    "The child node statement", "Утверждение дочернего узла")},
                "source": {"type": "string", "description": P("Source", "Источник")},
                "context": {"type": "string", "description": P(
                    "Context (P6)", "Контекст (П6)")},
                "evidence": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": P("Evidence (P5)", "Свидетельства (П5)"),
                },
            },
            "required": ["parent_id", "claim"],
        },
    },
    # -- инструменты уборки и связывания (01.09, аудит §5.6) ------------------
    {
        "name": "memory_link_existing",
        "description": P(
            "Link two ALREADY EXISTING nodes with an edge from_id -> to_id. "
            "memory_link can only create a new child node; before 01.09 there was "
            "no way to link two live nodes — hence 2 edges over 5251 nodes.",
            "Связать два УЖЕ СУЩЕСТВУЮЩИХ узла ребром from_id -> to_id. "
            "memory_link умеет только создавать новый узел-ребёнка; связать "
            "два живых узла до 01.09 было нечем — отсюда 2 ребра на 5251 узел.",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "from_id": {"type": "string", "description": P(
                    "Source node id", "id узла-источника")},
                "to_id": {"type": "string", "description": P(
                    "Target node id", "id узла-цели")},
                "bidirectional": {
                    "type": "boolean",
                    "description": P(
                        "Link both ways (default false)",
                        "Связать в обе стороны (по умолчанию false)"),
                },
                "author": {
                    "type": "string",
                    "description": P(
                        "Who made the link (e.g. alice). Written into the link_meta "
                        "passport of the edge; without it the author is unknown",
                        "Кто провёл связь (например alice). Пишется в паспорт "
                        "ребра link_meta; без него автор — unknown",
                    ),
                },
                "rel": {
                    "type": "string",
                    "enum": ["related_to", "part_of", "has_part", "conflicts_with",
                             "supersedes", "duplicate_of", "refers_to"],
                    "description": P(
                        "Relation type (02.09, Qwen's letter): related_to by default; "
                        "part_of/has_part — member/hub; conflicts_with — contradiction; "
                        "supersedes — a new order cancels the old one; duplicate_of; "
                        "refers_to — an explicit reference",
                        "Тип связи (02.09, письмо Qwen): related_to по умолчанию; "
                        "part_of/has_part — член/хаб; conflicts_with — противоречие; "
                        "supersedes — новый приказ отменяет старый; duplicate_of; "
                        "refers_to — явная ссылка",
                    ),
                },
            },
            "required": ["from_id", "to_id"],
        },
    },
    # -- рефакторинг по письму Qwen (02.09): промпт из памяти и граф-запросы --
    {
        "name": "memory_prompt",
        "description": P(
            "Assemble a system prompt from memory for a local LLM: budgeted "
            "search over the question and/or the 'constitution' (all sys_cmd + "
            "persona_def nodes), sections by router tags (rules first, never "
            "trimmed), contradictions and hubs. format: plain | chatml (Qwen) | "
            "llama3. The excerpt is a single prompt field: with format=plain the "
            "text field was a byte-for-byte duplicate and was removed "
            "(text_deprecated stays in the response). The header is byte-stable "
            "and cached; volatile nodes (tags counter:*, volatile) are returned in "
            "the volatile field and go into prompt after the header.",
            "Собрать system-prompt из памяти для локальной LLM: бюджетный поиск "
            "по вопросу и/или «конституция» (все sys_cmd + persona_def узлы), "
            "секции по тегам-маршрутизаторам (правила первыми, никогда не режутся), "
            "противоречия и хабы. format: plain | chatml (Qwen) | llama3. "
            "Выдержка — одно поле prompt: при format=plain поле text было "
            "побайтным дублем и убрано (в ответе остаётся text_deprecated). "
            "Шапка байт-стабильна и кэшируется, летучие узлы (теги counter:*, "
            "volatile) отдаются полем volatile и в prompt идут после шапки.",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": P(
                    "The agent's question (optional)",
                    "Вопрос агента (необязательно)")},
                "constitution": {
                    "type": "boolean",
                    "description": P(
                        "Add all rules/orders and roles (default false)",
                        "Добавить все правила/приказы и роли (по умолчанию false)"),
                },
                "with_volatile": {
                    "type": "boolean",
                    "description": P(
                        "Append the volatile-node section after the header in prompt "
                        "(default true)",
                        "Дописывать секцию летучих узлов после шапки в prompt (по умолчанию true)"),
                },
                "max_tokens": {"type": "integer", "description": P(
                    "Prompt budget in tokens (default 1200)",
                    "Бюджет промпта в токенах (по умолчанию 1200)")},
                "format": {"type": "string", "enum": ["plain", "chatml", "llama3"]},
                "session_id": {
                    "type": "string",
                    "description": P(
                        "Dialogue id: registers the pre-pass through the graph so that "
                        "a later memory_ground does not mark the answer ungrounded",
                        "id диалога: регистрирует пред-проход через граф, чтобы "
                        "последующий memory_ground не пометил ответ ungrounded",
                    ),
                },
                "agent": {"type": "string", "description": P(
                    "Who asks (for the pass log)",
                    "Кто спрашивает (для журнала проходов)")},
            },
        },
    },
    {
        "name": "memory_graph",
        "description": P(
            "Graph queries: op=neighbors (node_id[, rel]) | path (a, b) | "
            "hub (key: an entity or a hub id) | hubs | rules_for (situation: "
            "'which rules apply in a crisis') | conflicts.",
            "Граф-запросы: op=neighbors (node_id[, rel]) | path (a, b) | "
            "hub (key: сущность или id хаба) | hubs | rules_for (situation: "
            "«какие правила применять в кризисе») | conflicts.",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "op": {
                    "type": "string",
                    "enum": ["neighbors", "path", "hub", "hubs", "rules_for", "conflicts"],
                },
                "node_id": {"type": "string"},
                "a": {"type": "string"},
                "b": {"type": "string"},
                "key": {"type": "string"},
                "rel": {"type": "string"},
                "situation": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["op"],
        },
    },
    {
        "name": "memory_decay",
        "description": P(
            "Weight decay: nodes nobody used grow dim (half-life 168 h by "
            "default). kind=rule never drops below 0.5. One dump for the whole "
            "batch. Runs by cron 0 4 * * *.",
            "Затухание весов: узлы, которыми не пользовались, тускнеют "
            "(half-life по умолчанию 168 ч). kind=rule не опускается ниже 0.5. "
            "Один дамп на весь батч. Запускается по cron 0 4 * * *.",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": P(
                    "A single node (otherwise the whole store)",
                    "Один узел (иначе весь стор)")},
                "half_life_hours": {
                    "type": "number",
                    "description": P(
                        "Weight half-life in hours (default 168)",
                        "Период полураспада веса, часов (по умолчанию 168)"),
                },
            },
        },
    },
    {
        "name": "memory_prune",
        "description": P(
            "Store cleanup by a formal rule. dry_run=true by default — only the "
            "candidate list with reasons, nothing changes. kind=rule is never "
            "touched; nodes with incoming links are not deleted; deletion is "
            "capped by max_delete.",
            "Уборка стора по формальному правилу. По умолчанию dry_run=true — "
            "только список кандидатов с причинами, ничего не меняется. "
            "kind=rule не трогается никогда; узлы с входящими ссылками не "
            "удаляются; удаление ограничено max_delete.",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "rule": {
                    "type": "string",
                    "enum": ["expired_ttl", "exact_dupes", "source_prefix", "weak"],
                    "description": P(
                        "expired_ttl — expired TTL into outdated (no deletion); "
                        "exact_dupes — exact claim duplicates, the freshest survives; "
                        "source_prefix — move out a foreign corpus (needs export_path); "
                        "weak — weak, old and linked by nobody",
                        "expired_ttl — истёкший TTL в outdated (без удаления); "
                        "exact_dupes — полные дубли claim, выживает свежайший; "
                        "source_prefix — вынос чужого корпуса (нужен export_path); "
                        "weak — слабые, старые и никем не связанные",
                    ),
                },
                "dry_run": {"type": "boolean", "description": P(
                    "Default true", "По умолчанию true")},
                "max_delete": {"type": "integer", "description": P(
                    "Deletion cap (default 100)",
                    "Потолок удаления (по умолчанию 100)")},
                "source_prefix": {"type": "string", "description": P(
                    "source prefix for the source_prefix rule",
                    "Префикс source для правила source_prefix")},
                "older_than_days": {"type": "integer", "description": P(
                    "Age threshold for weak (30)",
                    "Порог возраста для weak (30)")},
                "weak_weight": {"type": "number", "description": P(
                    "Decision-weight threshold (base_weight) for weak (0.1); the "
                    "decaying weight is not read",
                    "Порог веса решения (base_weight) для weak (0.1); затухающий weight не читается")},
                "weak_limit": {"type": "integer", "description": P(
                    "weak safety catch: more candidates than this — refusal 'looks "
                    "like a mass decay' (50)",
                    "Предохранитель weak: кандидатов больше — отказ «похоже на массовый decay» (50)")},
                "export_path": {"type": "string", "description": P(
                    "Where to dump what is deleted (required for source_prefix)",
                    "Куда выгрузить удаляемое (обязателен для source_prefix)")},
            },
            "required": ["rule"],
        },
    },
    {
        "name": "memory_summarize",
        "description": P(
            "Fold a cluster of similar nodes into one concentrate node: the "
            "cluster is selected by source_prefix/tags/substring, the source nodes "
            "become children of the fold and are moved to kind=outdated (not "
            "deleted). dry_run=true by default.",
            "Свернуть кластер похожих узлов в один узел-концентрат: кластер "
            "отбирается по source_prefix/tags/подстроке, исходные узлы "
            "становятся детьми свёртки и переводятся в kind=outdated "
            "(не удаляются). dry_run=true по умолчанию.",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "claim": {"type": "string", "description": P(
                    "Statement of the fold node (required when dry_run=false)",
                    "Утверждение узла-свёртки (обязательно при dry_run=false)")},
                "source_prefix": {"type": "string", "description": P(
                    "Select the cluster by source prefix",
                    "Отбор кластера по префиксу source")},
                "contains": {"type": "string", "description": P(
                    "Select the cluster by a substring in claim",
                    "Отбор кластера по подстроке в claim")},
                "tags": {"type": "array", "items": {"type": "string"}, "description": P(
                    "Select the cluster by tags", "Отбор кластера по тегам")},
                "source": {"type": "string", "description": P(
                    "Source of the fold node", "Источник узла-свёртки")},
                "evidence": {"type": "array", "items": {"type": "string"}, "description": P(
                    "Evidence of the fold (P5)", "Свидетельства свёртки (П5)")},
                "context": {"type": "string", "description": P(
                    "Context of the fold (P6)", "Контекст свёртки (П6)")},
                "dry_run": {"type": "boolean", "description": P(
                    "Default true", "По умолчанию true")},
                "max_nodes": {"type": "integer", "description": P(
                    "Cap of folded nodes (default 500)",
                    "Потолок сворачиваемых узлов (по умолчанию 500)")},
            },
        },
    },
    {
        "name": "memory_stats",
        "description": P(
            "Memory passport: nodes, kinds, tags, edges (and broken ones), "
            "orphans, duplicates, weight distribution, TTL-expired, nodes without "
            "evidence, bytes.",
            "Паспорт памяти: узлы, виды, теги, рёбра (и битые), сироты, дубли, "
            "распределение весов, протухшие по TTL, узлы без evidence, байты.",
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    # -- обязательный проход через граф (03.09, приказ Ильи) ------------------
    {
        "name": "memory_ground_prepare",
        "description": P(
            "STEP 1 (BEFORE answering, mandatory). Searches the graph and "
            "assembles a system prompt out of the nodes found; registers the "
            "session pre-pass — without it memory_ground marks the answer "
            "ungrounded. Checks graph-first right away: if a ready answer is "
            "already in memory (graph_first.hit=true), return it and do NOT call "
            "the LLM — generation would burn the user's tokens for nothing. The "
            "graph excerpt is a single prompt field.",
            "ШАГ 1 (ДО ответа, обязателен). Ищет по графу и собирает "
            "system-prompt из найденных узлов; регистрирует пред-проход "
            "сессии — без него memory_ground пометит ответ ungrounded. "
            "Сразу проверяет graph-first: если готовый ответ уже есть в "
            "памяти (graph_first.hit=true), отдай его и НЕ зови LLM — "
            "генерация сожжёт токены пользователя впустую. Выдержка графа — "
            "одно поле prompt (в обёртке format).",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": P(
                    "The user's question", "Вопрос пользователя")},
                "session_id": {
                    "type": "string",
                    "description": P(
                        "Dialogue id — ties the pre-pass to the later memory_ground. "
                        "Without it one is generated (returned in the response)",
                        "id диалога — связывает пред-проход с последующим "
                        "memory_ground. Без него сгенерируется свой (в ответе)",
                    ),
                },
                "agent": {"type": "string", "description": P(
                    "Who asks (alice, fable, ...)",
                    "Кто спрашивает (alice, fable, ...)")},
                "constitution": {
                    "type": "boolean",
                    "description": P(
                        "Add rules/orders and roles to the prompt (default false)",
                        "Добавить правила/приказы и роли в промпт (по умолчанию false)"),
                },
                "max_tokens": {"type": "integer", "description": P(
                    "Prompt budget (default 1200)",
                    "Бюджет промпта (по умолчанию 1200)")},
                "format": {"type": "string", "enum": ["plain", "chatml", "llama3"]},
                "graph_first": {
                    "type": "boolean",
                    "description": P(
                        "Check for a ready answer from the graph (default true)",
                        "Проверять готовый ответ из графа (по умолчанию true)"),
                },
                "threshold": {
                    "type": "number",
                    "description": P(
                        "Coverage threshold of the question by a node for graph-first "
                        "(default 0.75)",
                        "Порог покрытия вопроса узлом для graph-first (по умолчанию 0.75)"),
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "memory_ground",
        "description": P(
            "STEP 3 (AFTER answering, mandatory). Splits the answer into claims "
            "and checks each against the graph -> verdict grounded | partial | "
            "ungrounded, 'passed through the graph: yes/no/partly', the list of "
            "source nodes and unsupported_claims — everything the graph did not "
            "confirm in full (inventions and half-remembered bits, each line with "
            "its own verdict). Without a pre-pass (memory_ground_prepare) the "
            "verdict is ungrounded.",
            "ШАГ 3 (ПОСЛЕ ответа, обязателен). Режет ответ на утверждения и "
            "сверяет каждое с графом -> вердикт grounded | partial | "
            "ungrounded, «прошёл через граф: да/нет/частично», список "
            "узлов-источников и unsupported_claims — всё, что граф не подтвердил "
            "целиком (выдумки и вспомненное наполовину, вердикт у каждой строки свой). "
            "Без пред-прохода (memory_ground_prepare) вердикт — ungrounded.",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "answer_text": {"type": "string", "description": P(
                    "The agent's answer text", "Текст ответа агента")},
                "query": {"type": "string", "description": P(
                    "The original question (for the log)",
                    "Исходный вопрос (для журнала)")},
                "session_id": {"type": "string", "description": P(
                    "The same id as in memory_ground_prepare",
                    "Тот же id, что в memory_ground_prepare")},
                "agent": {"type": "string", "description": P(
                    "Who answered", "Кто отвечал")},
                "require_pre_pass": {
                    "type": "boolean",
                    "description": P(
                        "Require the pre-pass. Default: the server policy "
                        "ground_by_default (on at startup: without a pre-pass the "
                        "answer is ungrounded). false — claim checking only, for "
                        "clients without sessions",
                        "Требовать пред-проход. По умолчанию — политика сервера "
                        "ground_by_default (при старте включена: без пред-прохода "
                        "ответ ungrounded). false — только сверка утверждений, "
                        "для клиентов без сессий",
                    ),
                },
                "reinforce": {
                    "type": "boolean",
                    "description": P(
                        "Reinforce the source nodes (default true): memory remembers "
                        "that a node was useful",
                        "Подкрепить узлы-источники (по умолчанию true): память запоминает, что узел пригодился"),
                },
                "max_claims": {"type": "integer", "description": P(
                    "Cap of parsed claims (default 24)",
                    "Потолок разбираемых утверждений (по умолчанию 24)")},
            },
            "required": ["answer_text"],
        },
    },
    {
        "name": "memory_answer",
        "description": P(
            "graph-first mode: if the answer to the question already lies in the "
            "graph (coverage >= threshold, weight and confidence above their "
            "thresholds, the leader clear of the runner-up) — return it WITHOUT "
            "calling the LLM (zero generation tokens). Otherwise llm_required=true "
            "plus a ready grounded prompt for the model.",
            "Режим graph-first: если ответ на вопрос уже лежит в графе "
            "(покрытие >= порога, вес и уверенность выше порогов, лидер "
            "оторвался от второго) — вернуть его БЕЗ вызова LLM (ноль "
            "токенов генерации). Иначе llm_required=true и готовый "
            "grounded-промпт для модели.",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": P(
                    "The user's question", "Вопрос пользователя")},
                "session_id": {"type": "string"},
                "agent": {"type": "string"},
                "threshold": {"type": "number", "description": P(
                    "Coverage threshold (default 0.75)",
                    "Порог покрытия (по умолчанию 0.75)")},
                "min_weight": {"type": "number", "description": P(
                    "Node weight threshold (default 0.5)",
                    "Порог веса узла (по умолчанию 0.5)")},
                "min_confidence": {"type": "number", "description": P(
                    "Confidence threshold (default 0.5)",
                    "Порог уверенности (по умолчанию 0.5)")},
                "with_prompt": {
                    "type": "boolean",
                    "description": P(
                        "Attach a prompt for the LLM on a miss (default true)",
                        "Приложить промпт для LLM при промахе (по умолчанию true)"),
                },
                "max_tokens": {"type": "integer", "description": P(
                    "Prompt budget on a miss", "Бюджет промпта при промахе")},
            },
            "required": ["query"],
        },
    },
    {
        "name": "memory_ground_log",
        "description": P(
            "Log of passes through the graph (append-only ground_log.jsonl): "
            "agent, time, query, nodes, verdict. Filters by session, event "
            "(prepare|ground|answer) and agent.",
            "Журнал проходов через граф (append-only ground_log.jsonl): "
            "агент, время, запрос, узлы, вердикт. Фильтры по сессии, "
            "событию (prepare|ground|answer) и агенту.",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": P(
                    "How many recent entries (default 50)",
                    "Сколько последних записей (по умолчанию 50)")},
                "session_id": {"type": "string"},
                "event": {"type": "string", "enum": ["prepare", "ground", "answer", "add"]},
                "agent": {"type": "string"},
                "stats": {
                    "type": "boolean",
                    "description": P(
                        "Add a summary of verdicts and token savings",
                        "Добавить сводку по вердиктам и экономии токенов"),
                },
            },
        },
    },
    {
        "name": "memory_recent",
        "description": P(
            "A digest of the last N log entries across ALL agents in one call "
            "(wave2): who wrote what (add), checked what (ground) and asked what "
            "(prepare/answer), when, with which verdicts; an event feed.",
            "Сводка последних N записей журнала по ВСЕМ агентам одним вызовом "
            "(wave2): кто что записал (add), проверил (ground) и спросил "
            "(prepare/answer), когда, с какими вердиктами; лента событий.",
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": P(
                    "How many recent entries (default 50)",
                    "Сколько последних записей (по умолчанию 50)")},
                "agent": {"type": "string"},
                "session_id": {"type": "string"},
                "event": {"type": "string", "enum": ["prepare", "ground", "answer", "add"]},
            },
        },
    },
]


TOOLS: List[Dict[str, Any]] = build_tools()


class MnemosCore:
    """Ядро MCP-сервера: логика инструментов, без HTTP.

    plugins — включённые плагины: None (по умолчанию) — цепочка конфигурации
    (env MNEMOS_PLUGINS -> plugins.json -> дефолты context_engine,gates);
    [] — без плагинов; список/строка — явный набор.
    plugins_config — явный путь к plugins.json (используется, если plugins=None).
    """

    def __init__(
        self, store: Store, plugins: Any = None, plugins_config: Optional[str] = None,
        ground_log_path: Optional[str] = None,
        ground_by_default: Optional[bool] = None,
    ) -> None:
        self.store = store
        search_dirs = [str(store.path.parent)] if getattr(store, "path", None) is not None else None
        enabled = resolve_enabled_plugins(
            plugins=plugins, config_path=plugins_config, search_dirs=search_dirs
        )
        self.plugins = PluginManager(enabled)
        # гейты качества (Г1-Г5) включаются плагином gates
        self.gates_enabled = "gates" in enabled
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
            "memory_add": self.memory_add,
            "memory_checkpoint": self.memory_checkpoint,
            "memory_verify": self.memory_verify,
            "memory_search": self.memory_search,
            "memory_get": self.memory_get,
            "memory_list": self.memory_list,
            "memory_export": self.memory_export,
            "memory_update": self.memory_update,
            "memory_rewrite": self.memory_rewrite,
            "memory_retract": self.memory_retract,
            "memory_counter_take": self.memory_counter_take,
            "memory_counter_reserve": self.memory_counter_reserve,
            "memory_reinforce": self.memory_reinforce,
            "memory_link": self.memory_link,
            "memory_link_existing": self.memory_link_existing,
            "memory_decay": self.memory_decay,
            "memory_prune": self.memory_prune,
            "memory_summarize": self.memory_summarize,
            "memory_stats": self.memory_stats,
            "memory_prompt": self.memory_prompt,
            "memory_graph": self.memory_graph,
            "memory_ground_prepare": self.memory_ground_prepare,
            "memory_ground": self.memory_ground,
            "memory_answer": self.memory_answer,
            "memory_ground_log": self.memory_ground_log,
            "memory_recent": self.memory_recent,
            # T2.9: недельная свёртка записей сессий нити. В список MCP-инструментов
            # намеренно НЕ добавлена — это обслуживание раз в неделю (curl/скрипт), а бюджет
            # схем бриджа тратить на неё незачем (правило (г)).
            "memory_thread_digest": self.memory_thread_digest,
            # правило: очередь событийного синка по HTTP — стор уехал на удалённый хост,
            # а vault остался на Маке, и читать `<стор>.export-queue.jsonl`
            # файлом экспортёр больше не может. В список MCP-инструментов не
            # добавлена намеренно: это труба между двумя демонами, модели там
            # делать нечего, а схема в бридже стоила бы места (правило (г)).
            "memory_sync_queue": self.memory_sync_queue,
            # правило: обслуживание графа. Есть и в TOOLS (в отличие от дайджеста):
            # оператор должен видеть её в tools/list, чтобы позвать dry-run и
            # посмотреть числа. В белый список бриджа НЕ добавлена — модель
            # чистку памяти не запускает.
            "memory_archive": self.memory_archive,
        }
        # Обязательный проход через граф (03.09): журнал проходов лежит рядом
        # со стором, сессии пред-проходов — в памяти процесса (журнал остаётся
        # источником правды и переживает рестарт).
        #
        # Строго ДО plugins.handlers(self) (баг-хант 03.09, D8): плагинам
        # передаётся `self`, и плагин, которому при инициализации понадобится
        # политика или журнал, получал бы AttributeError на недостроенном ядре.
        log_path = ground_log_path or (
            str(store.path.parent / grounding.GROUND_LOG_NAME)
            if getattr(store, "path", None) is not None
            else grounding.GROUND_LOG_NAME
        )
        self.ground_log = grounding.GroundLog(log_path)
        self.sessions = grounding.SessionTracker()
        # нить проекта (фаза 2): «одна активная голова на slug» держится этим
        # замком между поиском существующей головы и записью/переписыванием
        self._thread_lock = threading.Lock()
        # Политика сервера: проход через граф обязателен у всех, пока
        # администратор явно не отключил его (аргумент -> env -> дефолт True).
        self.ground_by_default = (
            _env_flag(GROUND_ENV, GROUND_BY_DEFAULT)
            if ground_by_default is None else bool(ground_by_default)
        )
        # Очередь изменённых узлов для событийного экспорта в Obsidian.
        # Файл лежит рядом со стором; выключается MNEMOS_SYNC_QUEUE=0 (тогда
        # витрина обновляется только полным прогоном по таймеру).
        self.sync_queue_path = (
            sync_queue.queue_path(store.path)
            if getattr(store, "path", None) is not None else None
        )
        # правило: состояние пульса — рядом со стором, как журнал проходов и
        # очередь. Сервер его только читает: пульс живёт отдельным процессом.
        self.pulse_state_path = (
            pulse_mod.state_path(store.path)
            if getattr(store, "path", None) is not None else None
        )
        if not _env_flag(SYNC_QUEUE_ENV, True):
            self.sync_queue_path = None
        self._handlers.update(self.plugins.handlers(self))

    # -- событийный экспорт -------------------------------------------
    def _sync_touch(self, ids: Any, reason: str, *extra: Any) -> None:
        """Пометить узлы изменёнными: очередь -> экспортёр -> vault за секунды.

        Кроме самого узла в очередь идут его прямые соседи (родитель, цели
        рёбер): в заметке соседа есть раздел «Связи», и он тоже стал другим.
        Никогда не бросает: узел уже записан, и падать на витрине по факту
        успешной записи нельзя — потерянную пометку догонит полный прогон.
        """
        if self.sync_queue_path is None:
            return
        want: List[str] = []
        for item in (ids, *extra):
            if item is None:
                continue
            for i in ([item] if isinstance(item, str) else list(item)):
                if isinstance(i, str) and i.strip():
                    want.append(i.strip())
        sync_queue.enqueue_quiet(self.sync_queue_path, want, reason)

    @property
    def tools(self) -> List[Dict[str, Any]]:
        """Схемы для tools/list на языке поверхности.

        Собираются на каждом обращении, а не при старте: `BARON_LANG` читается
        в момент запроса, поэтому один и тот же процесс отдаёт English по
        умолчанию и русский сессии, которая его попросила.
        """
        return build_tools() + list(self.plugins.tool_schemas())

    # -- инструменты ----------------------------------------------------------
    def memory_add(self, args: Dict[str, Any]) -> Dict[str, Any]:
        items = args.get("items")
        if items is not None:
            return self._memory_add_batch(args, items)
        claim = args.get("claim")
        if not isinstance(claim, str) or not claim.strip():
            raise ValueError("memory_add: parameter claim (string) is required")
        _text_limit(claim, MAX_CLAIM_CHARS, "memory_add: claim")
        _text_limit(args.get("context"), MAX_FIELD_CHARS, "memory_add: context")
        _text_limit(args.get("source"), MAX_FIELD_CHARS, "memory_add: source")
        _list_limit(args.get("evidence"), "memory_add: evidence", MAX_EVIDENCE_ITEM_CHARS)
        _list_limit(args.get("links"), "memory_add: links", MAX_ID_LEN)
        _list_limit(args.get("tags"), "memory_add: tags", MAX_ID_LEN)
        evidence = args.get("evidence")
        if evidence is None:
            evidence = []
        if isinstance(evidence, str):
            evidence = [evidence]
        links = args.get("links") or []
        if isinstance(links, str):
            links = [links]
        tags = args.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        tags = [str(t) for t in tags]
        aliases = self._alias_list(args.get("aliases"), "memory_add: aliases")
        ttl_hours = _as_float(args.get("ttl_hours"))
        valid_until = args.get("valid_until")
        conf = _as_float(args.get("confidence"))
        kind = str(args.get("kind", "fact"))
        parent = args.get("parent")
        if parent is not None and (not isinstance(parent, str) or not parent.strip()):
            raise ValueError("memory_add: parent must be a non-empty string (node id)")
        parent = parent.strip() if isinstance(parent, str) else None
        # правило: несуществующий parent — предупреждение, а не потеря узла;
        # strict_parent=true — старое поведение (KeyError -> -32002) для тех,
        # кому ребро обязательно
        strict_parent = bool(args.get("strict_parent", False))
        if kind == "hub":
            # ревью 02.09 (п.2): подставной хаб с тегом entity:X подменял
            # навигацию memory_graph/rules_for; хабы строит только
            # офлайн-кластеризатор (mnemos_hubs.py), не клиент
            raise ValueError("memory_add: kind=hub is not allowed over MCP — hubs are built offline")
        # -- нить проекта: голова и запись сессии ------------
        notes: List[str] = []
        is_head = "thread_head" in tags
        if not is_head and thread_mod.is_head_claim(claim):
            # префикс [THREAD:<slug>] зарезервирован за головой: узел-двойник без
            # тега заставил бы Г4 отвергнуть настоящую голову как дубликат
            is_head = True
            tags = list(tags) + ["thread_head"]
            notes.append("добавлен тег thread_head по префиксу [THREAD:<slug>] в claim")
        is_session = "session" in tags and thread_mod.slug_from_tags(tags) is not None
        if is_head or is_session:
            # паспорт: agent (или author — тот же фолбэк, что у обычных узлов) + session_id
            if not self._thread_agent(args) or not self._session_id(args):
                raise ValueError(
                    "memory_add: the agent/session_id passport is required for "
                    "thread nodes"
                )
        if is_head:
            slug, tags, kind, notes = self._thread_head_prepare(
                claim, tags, kind, ttl_hours, valid_until, notes)
            ttl_hours = valid_until = None
            # под замком: две параллельные записи головы не должны создать две
            with self._thread_lock:
                existing = self._active_thread_head(slug, notes)
                if existing is not None:
                    return self._rewrite_thread_head(existing, args, claim.strip(), tags, notes)
                out = self._store_new_node(args, claim, evidence, links, tags, kind,
                                           conf, ttl_hours, valid_until, parent, aliases,
                                           strict_parent=strict_parent)
            out["rewritten"] = False
            if notes:
                out["notes"] = notes
            return out
        return self._store_new_node(args, claim, evidence, links, tags, kind,
                                    conf, ttl_hours, valid_until, parent, aliases,
                                    strict_parent=strict_parent)

    def _store_new_node(self, args: Dict[str, Any], claim: str, evidence: List[Any],
                        links: List[Any], tags: List[str], kind: str,
                        conf: Optional[float], ttl_hours: Optional[float],
                        valid_until: Any, parent: Optional[str] = None,
                        aliases: Optional[List[str]] = None,
                        strict_parent: bool = False) -> Dict[str, Any]:
        """Хвост memory_add: узел -> truth-gate -> роутер-тег -> паспорт -> гейты -> стор -> журнал.
        parent — узел садится ребёнком (store.add_child, тот же путь, что memory_link).

        правило: если parent не найден, узел всё равно записывается (без ребра,
        с тегом link:orphan), а в ответе появляются warnings и parent_missing;
        strict_parent=True — как раньше, KeyError (-32002) и узла нет."""
        warnings: List[str] = []
        parent_missing: Optional[str] = None
        if parent is not None and self.store.get(parent) is None:
            if strict_parent:
                raise KeyError(f"memory_add: parent {parent} not found")
            parent_missing, parent = parent, None
            warnings.append(
                f"родитель {parent_missing} не найден: узел записан без ребра parent/children, "
                "помечен тегом link:orphan"
            )
            if "link:orphan" not in tags:
                tags = list(tags) + ["link:orphan"]
        node = make_node(
            claim=claim.strip(),
            source=str(args.get("source", "")),
            evidence=[str(e) for e in evidence],
            context=str(args.get("context", "")),
            kind=kind,
            links=[str(l) for l in links],
            confidence=conf,
            ttl_hours=ttl_hours,
            valid_until=valid_until,
            tags=list(tags),
            aliases=list(aliases or []),
        )
        check_and_update(node, registry=self.store.get)
        if conf is None:
            # уверенность по умолчанию — из truth-gate (score/6), а не 0.5:
            # узел 6/6 с evidence должен ранжироваться выше узла 3/6 без него
            tc = node.truth_check if isinstance(node.truth_check, dict) else {}
            score = _as_float(tc.get("score"))
            node.confidence = (
                max(0.05, min(1.0, score / 6.0)) if score is not None else 0.5
            )
        # Ф1 02.09 (письмо Qwen): каждому узлу — ровно один тег-маршрутизатор
        # sys_cmd / persona_def / world_state; явный тег клиента уважается,
        # без него — классификатор по эвристике (budget.classify_router)
        node.tags = ensure_router_tag(node.tags, {"claim": node.claim, "context": node.context, "kind": node.kind})
        author = str(args.get("author") or "").strip()
        if author and links:
            # рёбра, заданные при создании узла, тоже получают паспорт
            ts = node.ts
            node.link_meta = {
                str(l): {"author": author, "ts": ts} for l in links
            }
        # паспорт записи (wave2, фронт 5): агент и сессия — на узле и в журнале
        agent = self._short_text(args, "agent") or author
        session_id = self._session_id(args)
        node.agent = agent
        node.session_id = session_id
        with trace.phase("gates"):
            self._apply_write_gates(node)
        stored = self.store.add_child(parent, node) if parent else self.store.add(node)
        out = self.store.snapshot([stored])[0]
        self.ground_log.append(
            "add", session_id=session_id or None, agent=agent or None,
            node_ids=[out["id"]], kind=out.get("kind"),
            claim_preview=str(out.get("claim") or "")[:200], source=out.get("source") or None,
        )
        self._sync_touch(out["id"], "memory_add", parent, links)
        if warnings:
            out["warnings"] = warnings
            out["parent_missing"] = parent_missing
        return out

    def _memory_add_batch(self, args: Dict[str, Any], items: Any) -> Dict[str, Any]:
        """Батч memory_add (wave2, фронт 4): один вызов на все факты задачи.

        Каждый элемент проходит тот же путь, что и одиночный memory_add
        (truth-gate, гейты Г1-Г5, журнал); отказ гейта по одному факту не
        отменяет остальные — агенту важно узнать, ЧТО именно не записалось.
        Общие поля вызова (source, agent, session_id, context, tags) наследуются
        элементами, у которых их нет.
        """
        if not isinstance(items, list) or not items:
            raise ValueError("memory_add: items must be a non-empty list of objects")
        if len(items) > MAX_BATCH_ITEMS:
            raise ValueError(f"memory_add: items — no more than {MAX_BATCH_ITEMS} per call")
        shared = {k: v for k, v in args.items()
                  if k in ("source", "agent", "session_id", "context", "tags", "kind") and v is not None}
        results: List[Dict[str, Any]] = []
        stored = rejected = 0
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                results.append({"index": i, "ok": False, "error": "элемент должен быть объектом"})
                rejected += 1
                continue
            merged = {**shared, **item}
            merged.pop("items", None)
            try:
                node = self.memory_add(merged)
            except (ValueError, KeyError) as exc:
                results.append({"index": i, "ok": False, "error": str(exc),
                                "claim": str(item.get("claim") or "")[:120]})
                rejected += 1
                continue
            res = {"index": i, "ok": True, "id": node["id"], "kind": node.get("kind"),
                   "claim": str(node.get("claim") or "")[:120]}
            if "rewritten" in node:  # голова нити: переписана или создана
                res["rewritten"] = bool(node["rewritten"])
                rev = node.get("revisions")  # переписанная голова несёт число, новая — список
                res["revisions"] = rev if isinstance(rev, int) else len(rev or [])
            if node.get("notes"):
                res["notes"] = list(node["notes"])
            if node.get("warnings"):  # правило: битый parent — предупреждение элемента
                res["warnings"] = list(node["warnings"])
                res["parent_missing"] = node.get("parent_missing")
            results.append(res)
            stored += 1
        return {"batch": True, "stored": stored, "rejected": rejected,
                "results": results}

    # -- нить проекта -----------------------------------------
    def _thread_agent(self, args: Dict[str, Any]) -> str:
        """Агент для паспорта узла нити: agent, иначе author (как в _store_new_node)."""
        return self._short_text(args, "agent") or str(args.get("author") or "").strip()

    @staticmethod
    def _thread_head_prepare(claim: str, tags: List[str], kind: str,
                             ttl_hours: Optional[float], valid_until: Any,
                             notes: Optional[List[str]] = None) -> tuple:
        """Проверка элемента-головы: claim парсится, slug совпадает с тегом,
        kind принудительно rule, ttl игнорируется. -> (slug, tags, kind, notes)."""
        notes = list(notes or [])
        parsed = thread_mod.parse_head(claim)
        if parsed is None:
            raise ValueError(
                "memory_add: the thread head claim does not parse — expected "
                f"«{thread_mod.HEAD_FORMAT_HINT}» (docs/product/THREAD.md, v{thread_mod.SCHEMA_VERSION})"
            )
        slug = parsed["slug"]
        tag_slug = thread_mod.slug_from_tags(tags)
        if tag_slug is None:
            tags = list(tags) + [f"thread:{slug}"]
            notes.append(f"добавлен тег thread:{slug} из claim")
        elif tag_slug != slug:
            raise ValueError(
                f"memory_add: the head slug in claim ({slug}) does not match the tag thread:{tag_slug}"
            )
        if kind != "rule":
            notes.append(f"kind {kind!r} заменён на rule: голова нити всегда rule")
            kind = "rule"
        if ttl_hours is not None or valid_until:
            notes.append("ttl_hours/valid_until у головы нити игнорируются: голова без ttl")
        return slug, tags, kind, notes

    def _active_thread_head(self, slug: str, notes: List[str]) -> Optional[Dict[str, Any]]:
        """Активная голова нити. Если их вдруг несколько — настоящая (claim
        парсится, kind=rule), среди таких самая свежая (thread.rank_heads)."""
        heads = self.store.find_by_tags([f"thread:{slug}", "thread_head"], active_only=True)
        if not heads:
            return None
        heads = thread_mod.rank_heads(heads)
        if len(heads) > 1:
            notes.append(
                f"активных голов thread:{slug} — {len(heads)}; переписана настоящая/самая свежая "
                f"{heads[0].get('id')}, остальные ({', '.join(str(h.get('id')) for h in heads[1:])}) "
                "пометить outdated через memory_rewrite(kind=\"outdated\")"
            )
        return heads[0]

    def _rewrite_thread_head(self, existing: Dict[str, Any], args: Dict[str, Any],
                             claim: str, tags: List[str], notes: List[str]) -> Dict[str, Any]:
        """Голова уже есть -> rewrite на месте (id прежний, старый claim в revisions),
        паспорт последнего обновившего, truth-gate заново, событие add в журнале."""
        agent = self._thread_agent(args)
        session_id = self._session_id(args)
        source = str(args.get("source") or "").strip()
        if not source:
            # rewrite идёт мимо Г3 (пустой source у нового узла отвергается):
            # честно говорим, что источник остался прежним
            notes.append(f"source не передан — оставлен прежний ({existing.get('source') or '—'})")
        d = self.store.rewrite(existing["id"], claim, source=source,
                               reason=f"thread head update {agent}/{session_id}")
        node = MemoryNode.from_dict(d)
        node.kind = "rule"
        node.agent = agent
        node.session_id = session_id
        merged = list(node.tags) + [t for t in tags if t not in node.tags]
        node.tags = ensure_router_tag(merged, {"claim": node.claim, "context": node.context, "kind": node.kind})
        context = str(args.get("context") or "")
        if context:
            node.context = context
        evidence = args.get("evidence")
        if isinstance(evidence, str):
            evidence = [evidence]
        if evidence:
            node.evidence = [str(e) for e in evidence]
        check_and_update(node, registry=self.store.get)
        self.store.update(node)
        out = self.store.snapshot([self.store.get(node.id)])[0]
        out["rewritten"] = True
        out["revisions"] = len(out.get("revisions") or [])
        if notes:
            out["notes"] = list(notes)
        self.ground_log.append(
            "add", session_id=session_id or None, agent=agent or None,
            node_ids=[out["id"]], kind="rule", rewritten=True,
            claim_preview=str(out.get("claim") or "")[:200], source=out.get("source") or None,
        )
        self._sync_touch(out["id"], "memory_add.thread_head")
        return out

    def _apply_write_gates(self, node: MemoryNode) -> None:
        """Гейты записи Г1-Г5 ПЕРЕД store.add (фикс 01.09, аудит §5.1).

        Это та самая дыра, из которой вытекло всё остальное: run_write_gates
        существовал, был покрыт тестами и НЕ ВЫЗЫВАЛСЯ из memory_add — поэтому
        в сторе 5090 накопилось 2833 узла «алиса вердикт» без evidence и
        без context (замер 01.09), а в аудите 29.08 — 842 дубля из 5251.

        Поведение:
          * reject  -> запись запрещена (ValueError -> INVALID_PARAMS), и если
            гейт указал на конкретный узел-дубликат, тот узел ПОДКРЕПЛЯЕТСЯ
            (reinforce) — «подкрепите существующий, а не плодите копию»
            перестаёт быть просто советом в тексте ошибки;
          * flag    -> узел не отвергается, но понижается до kind=hypothesis
            (гипотеза, а не факт) и получает пометку в truth_check.gates.

        kind="rule" гейты проходит, но НЕ понижается по flag: правило команды
        задаёт Иван, а не порог уверенности.
        """
        if not self.gates_enabled:
            return
        # wave2: Г4 сверяет claim только с узлами, разделяющими с ним хотя бы
        # один токен (store.gate_candidates — надмножество всех, у кого
        # Jaccard > 0): результат тот же, что у линейного прохода по стору
        # (13 мс на 1000 узлов), а стоит O(кандидатов). Потолок GATE_MAX_SCAN
        # остаётся страховкой на вырожденных claim'ах из одних частых слов.
        existing = self.store.gate_candidates(node.claim)
        # TS.1, вторая сторона границы: карантин обязан быть симметричным.
        # Узел песочницы сверяется только с узлами песочницы, узел основного
        # графа — только с узлами основного. Иначе догадка трипа отвергала бы
        # законную запись основного графа как дубликат И забирала бы себе
        # подкрепление: факт после этого не существует ни в чекпойнте, ни в
        # выгрузке, а «оригинал», к которому отсылает текст ошибки, невидим.
        mine = sandbox_mod.is_quarantined(node.to_dict())
        existing = [d for d in existing if sandbox_mod.is_quarantined(d) == mine]
        if len(existing) > GATE_MAX_SCAN:
            existing = existing[:GATE_MAX_SCAN]  # уже отсортированы свежие первыми
        registry = {d["id"]: d for d in existing}
        for link in node.links or []:  # Г3: доверие по ссылкам — нужны сами узлы
            linked = self.store.get(str(link))
            if linked is not None:
                registry.setdefault(linked["id"], linked)
        d = node.to_dict()
        # TS.2 / R4 §3 Л1: доза гейтов берётся из тега руки НА САМОМ УЗЛЕ
        # (arm:<имя> внутри thread:sandbox). Сервер не хранит режима: узел
        # без тегов песочницы проходит те же гейты, что и до фазы S, и
        # включить трип «глобально» нечем — это и есть граница карантина.
        trip = sandbox_mod.write_gate_dose(d)
        res = run_write_gates(d, registry=registry, existing=existing, **trip)
        gate_note = {
            "verdict": res.verdict, "reason": res.reason,
            "scanned": len(existing), "capped": len(self.store) > GATE_MAX_SCAN,
        }
        if trip:
            gate_note["trip"] = {"arm": sandbox_mod.arm_of(d), **trip}
        if isinstance(node.truth_check, dict):
            node.truth_check = {**node.truth_check, "gates": gate_note}
        if res.verdict == "reject":
            dup_id = _first_node_id(res.reason)
            if dup_id and self.store.get(dup_id) is not None:
                # подкрепляем оригинал вместо создания копии.
                # Подкрепление — прибавка веса, а не сам смысл записи: если
                # замок файла занят, отказ обязан остаться отказом гейта с
                # именем оригинала. Иначе клиент видит «внутреннюю ошибку»
                # вместо «дубликат mn_…», не может сослаться на оригинал и
                # считает узел потерянным (замер 2026-09-09: 63 таймаута
                # блокировки nodes.json за сутки, 41 из них на memory_add —
                # ровно этой веткой, при 28 МБ снимка и load average 9).
                try:
                    w = self.store.reinforce(dup_id, delta=0.05)
                except (OSError, TimeoutError) as exc:
                    log.warning("дубликат %s не подкреплён (%s)", dup_id, exc)
                    raise GateRejected(
                        f"{res.reason} " + i18n.pick(
                            f"[node {dup_id} already exists, reinforcing failed: {exc}]",
                            f"[узел {dup_id} уже есть, подкрепить не удалось: {exc}]")
                    ) from None
                raise GateRejected(
                    f"{res.reason} " + i18n.pick(
                        f"[node {dup_id} reinforced, weight {w:.2f}]",
                        f"[узел {dup_id} подкреплён, вес {w:.2f}]")
                )
            raise GateRejected(res.reason)
        if res.verdict == "flag" and node.kind == "fact":
            node.kind = "hypothesis"

    def memory_verify(self, args: Dict[str, Any]) -> Dict[str, Any]:
        node_id = args.get("node_id")
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("memory_verify: parameter node_id (string) is required")
        node = self.store.get(node_id)
        if node is None:
            raise KeyError(f"memory_verify: node {node_id!r} not found")
        result = check_and_update(node, registry=self.store.get)
        if result.verdict == "pass":
            # проверенная память крепче: проход truth-gate подкрепляет узел.
            # Фикс 01.09 (аудит §5.7): прибавка зависит от score, а не всегда
            # +0.05. Иначе живой узел с почасовым обслуживанием упирается в
            # потолок 1.0 за сутки и теряет различимость с болтовнёй.
            # 6/6 -> +0.04, 5/6 -> +0.02, 4/6 -> 0.
            score = _as_float(getattr(result, "score", None))
            delta = 0.05 if score is None else max(0.0, 0.02 * (score - 4))
            mnode = MemoryNode.from_dict(node)
            mnode.reinforce(delta)
            node = mnode.to_dict()
        self.store.update(node)
        out = result.as_dict()
        out["weight"] = node["weight"]
        return out

    def memory_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("memory_search: parameter query (string) is required")
        _text_limit(query, MAX_QUERY_CHARS, "memory_search: query")
        top_k = args.get("top_k", 5)
        # 02.09 (письмо Qwen): top_k="auto" или budget=true -> бюджетный поиск,
        # где top_k выбирается по сложности запроса (5 / 10 / 20)
        auto_k = isinstance(top_k, str) and top_k.strip().lower() == "auto"
        use_budget = bool(args.get("budget", False)) or auto_k
        try:
            top_k = None if auto_k else int(top_k)
        except (TypeError, ValueError):
            top_k = 5
        mode = args.get("mode", "substring")
        if mode not in ("substring", "semantic", "budget", "rrf"):
            raise ValueError(
                f"memory_search: mode must be 'substring', 'semantic', "
                f"'budget' or 'rrf', got {mode!r}"
            )
        if mode == "budget":
            use_budget = True
        if mode in ("semantic", "rrf"):
            # semantic/rrf + top_k="auto" — это свой режим с k=5, а не budget
            use_budget = False
            top_k = top_k or 5
        want_tags = args.get("tags") or []
        if isinstance(want_tags, str):
            want_tags = [want_tags]
        want_tags = [str(t) for t in want_tags]
        want_kind = args.get("kind")
        use_read_gates = bool(args.get("relevance_gate", False))
        # TS.5: имя агента, чью собственную историю в песочнице скрыть.
        # Пустое значение = ничего не скрываем (поведение до фазы S).
        hide_self = self._short_text(args, "hide_self")
        # правило: приватность режет ПОСЛЕДНЕЙ и одинаково во всех режимах —
        # внутри `_filter`, через который проходит и budget, и rrf, и semantic,
        # и подстрочный путь. Отдельная проверка на каждом выходе рано или
        # поздно разъехалась бы, и утечка была бы именно в забытой ветке.
        audience = privacy.normalize_audience(args.get("audience"), "memory_search")

        def _filter(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            """Фильтры тегов/вида + Г5-релевантность (фикс 01.09, аудит §5.2/§5.4).

            До 01.09 отделить правило от болтовни можно было только регуляркой
            по claim: тегов не было ни в схеме, ни в данных (0 уникальных тегов
            на 5251 узел). Теперь memory_search(query="риск", tags=["правило"])
            возвращает правило, а не 685 узлов со словом «риск».
            """
            out = nodes
            if want_tags:
                out = [n for n in out if set(want_tags) <= set(n.get("tags") or [])]
            if want_kind:
                out = [n for n in out if n.get("kind") == want_kind]
            if use_read_gates and self.gates_enabled:
                # TS.5 / R4 §3 Л3: hide_self просят явно и только для песочницы —
                # запрет действует в фазе трипа, а не всегда, иначе агент
                # потерял бы выученное вместо того, чтобы отпустить нарратив.
                out = run_read_gates(
                    out, query,
                    hide_self=hide_self, hide_scope=sandbox_mod.SANDBOX_THREAD_TAG,
                )
            return privacy.filter_audience(out, audience)

        if use_budget:
            out = self.store.search_budget(
                query, top_k=top_k,
                token_budget=_as_int(args.get("token_budget")),
                expand=bool(args.get("expand", True)),
            )
            kept = {r["id"] for r in _filter(list(out.get("results") or []))}
            out["results"] = [r for r in out["results"] if r["id"] in kept]
            out["count"] = len(out["results"])
            out["mode"] = "budget"
            self.store.touch(out["results"])
            return out
        if mode == "rrf":
            # ML-BOOST 03.09: слияние Ф1 + BM25F (+ плотный, если есть
            # fastembed) по RRF. Стор не меняется: touch — ниже, по уже
            # отфильтрованной выдаче, как и в подстрочном пути.
            results = _filter(self.store.search_rrf(query, top_k=top_k))
            self.store.touch(results)
            return {"query": query, "mode": "rrf", "count": len(results),
                    "results": self.store.snapshot(results)}
        if mode == "semantic":
            # бенчмарк-фикс 26.08: семантический режим; если fastembed не
            # установлен — честная ошибка с текстом, а не «внутренняя ошибка».
            try:
                results = self.store.search_semantic(query, top_k=top_k)
            except ImportError as exc:
                raise ValueError(f"memory_search (semantic): {exc}") from exc
            kept = {id(n) for n in _filter([n for n, _ in results])}
            results = [(n, sc) for n, sc in results if id(n) in kept]
            self.store.touch([n for n, _ in results])
            snaps = self.store.snapshot([n for n, _ in results])
            return {
                "query": query,
                "mode": "semantic",
                "count": len(results),
                "results": [
                    {"node": node, "score": round(score, 6)}
                    for node, (_, score) in zip(snaps, results)
                ],
            }
        # Ф1: touch=False здесь — использование отмечаем ниже только для
        # узлов, прошедших фильтры tags/kind/гейты (то, что агент увидел)
        results = _filter(self.store.search(query, top_k=top_k, touch=False))
        mode_out = "substring"
        if not results and len(query.split()) >= 2:
            # Ф1 02.09: NL-фоллбек. Подстрока целой фразы («Кто принимает
            # решение пускать сигнал в ордер?») не встречается ни в одном узле
            # -> 0 результатов; по основам слов (budget-поиск) находится.
            # Ключевые слова этот путь не трогает: он включается только при
            # пустой подстрочной выдаче. Замер 02.09: NL recall@5 0.000 -> 0.6+.
            fb = self.store.search_budget(query, top_k=top_k)
            marks = {r["id"]: {"score": r.get("score"), "via": r.get("via"), "rel": r.get("rel"),
                               "matched": (r.get("why") or {}).get("matched")}
                     for r in fb.get("results") or []}
            got = [self.store.get(i) for i in marks]
            results = _filter([n for n in got if n])
            if results:
                mode_out = "token_fallback"
                self.store.touch(results)
                out = self.store.snapshot(results)
                for n in out:  # прозрачность: чем найден узел — словами или ребром (via/rel)
                    n["search"] = marks[n["id"]]
                return {"query": query, "mode": mode_out, "count": len(out), "results": out}
        self.store.touch(results)
        return {"query": query, "mode": mode_out, "count": len(results),
                "results": self.store.snapshot(results)}

    # -- уборка и связывание (01.09, аудит §5.6) ------------------------------
    def memory_link_existing(self, args: Dict[str, Any]) -> Dict[str, Any]:
        from_id, to_id = args.get("from_id"), args.get("to_id")
        if not isinstance(from_id, str) or not from_id.strip():
            raise ValueError("memory_link_existing: parameter from_id (string) is required")
        if not isinstance(to_id, str) or not to_id.strip():
            raise ValueError("memory_link_existing: parameter to_id (string) is required")
        out = self.store.link_existing(
            from_id.strip(),
            to_id.strip(),
            bidirectional=bool(args.get("bidirectional")),
            author=str(args.get("author") or ""),
            rel=str(args.get("rel") or ""),
        )
        self._sync_touch([from_id.strip(), to_id.strip()], "memory_link_existing")
        return out

    # -- рефакторинг по письму Qwen (02.09): промпт из памяти, граф-запросы ----
    def memory_prompt(self, args: Dict[str, Any]) -> Dict[str, Any]:
        from .budget import (ROUTER_PERSONA, ROUTER_SYS_CMD, build_system_prompt, is_volatile,
                             render_volatile_section, router_of, wrap_prompt)

        query = args.get("query")
        _text_limit(query, MAX_QUERY_CHARS, "memory_prompt: query")
        query = query.strip() if isinstance(query, str) and query.strip() else ""
        constitution = bool(args.get("constitution", False))
        if not query and not constitution:
            raise ValueError("memory_prompt: needs query and/or constitution=true")
        fmt = str(args.get("format") or "plain")
        if fmt not in ("plain", "chatml", "llama3"):
            raise ValueError("memory_prompt: format must be plain | chatml | llama3")
        max_tokens = _as_int(args.get("max_tokens"))
        if max_tokens is None:
            max_tokens = PROMPT_DEFAULT_TOKENS
        if max_tokens <= 0:
            raise ValueError("memory_prompt: max_tokens must be > 0")
        nodes: List[Dict[str, Any]] = []
        conflicts: List[Dict[str, Any]] = []
        hubs: List[Dict[str, Any]] = []
        if constitution:
            # TS.1: блок конституции набирается из ВСЕГО стора мимо поиска, и
            # без этого среза узел трипа с роутер-тегом sys_cmd печатался бы
            # агенту в разделе «ПРАВИЛА И ПРИКАЗЫ (обязательны)» — то есть
            # строже обычного факта. Тем же срезом уходит и status:archived.
            nodes += [
                n for n in self.store.all()
                if n.get("kind") not in ("refuted", "outdated", "hub")
                and router_of(n) in (ROUTER_SYS_CMD, ROUTER_PERSONA)
                and not _hidden_from_thread(n)
            ]
        search = args.get("_search") if isinstance(args.get("_search"), dict) else None
        if query and search is None:
            search = self.store.search_budget(query)
            search = _cut_hidden(search)
        if search is not None:
            nodes += [self.store.get(r["id"]) for r in search["results"]]
            conflicts = search["conflicts"]
            hubs = [self.store.get(h["id"]) for h in search["hubs"]]
        # отменённые приказы (входящее supersedes) — помечаем и режем первыми
        g = self.store.graph()
        superseded = {b: a for a, b, rel in ((a, b, r) for a, edges in g.out.items() for b, r in edges)
                      if rel == "supersedes"
                      and (self.store.get(a) or {}).get("kind") not in ("refuted", "outdated")}
        # T10.2: летучие узлы (счётчик решений и т.п.) — вон из
        # кэшируемой шапки. text — байт-стабильная шапка; volatile — отдельная
        # секция, которая в prompt идёт ПОСЛЕ неё (with_volatile=false — не идёт).
        with_volatile = args.get("with_volatile", True)
        with_volatile = True if with_volatile is None else bool(with_volatile)
        volatile_nodes = [n for n in nodes if n and is_volatile(n)]
        nodes = [n for n in nodes if n and not is_volatile(n)]
        res = build_system_prompt(nodes, max_tokens=max_tokens, conflicts=conflicts,
                                  hubs=[h for h in hubs if h], query=query or None,
                                  superseded=superseded)
        res["format"] = fmt
        res["volatile"] = render_volatile_section(volatile_nodes)
        res["volatile_ids"] = [n["id"] for n in volatile_nodes]
        full = res["text"]
        if with_volatile and res["volatile"]:
            full = f"{full}\n{res['volatile']}"
        res["prompt"] = wrap_prompt(full, fmt, query)
        res["node_ids"] = [n["id"] for n in nodes if n]
        # R12-6: при format=plain поля text и prompt
        # побайтно совпадали — модель платила за одну и ту же выдержку дважды
        # (замер 10.09: 1590 из 3394 токенов ответа, 46.9%). T10.1 (ef669e1)
        # убрал дубль в memory_ground_prepare; здесь то же самое и тем же
        # способом — поведением, а не флагом. Флаг MNEMOS_PROMPT_COMPACT снят.
        # Совместимость: одна версия отдаёт вместо поля короткое
        # предупреждение — клиенту хватает его, чтобы перейти на prompt.
        if res.get("text") == res.get("prompt"):
            res.pop("text", None)
            res["text_deprecated"] = prompt_text_deprecated()
        if search is not None:
            res["classification"] = search["classification"]
        # Пред-проход (03.09): memory_prompt по вопросу — это и есть «сначала
        # спросили граф». Клиент, который уже ходит через memory_prompt, чинит
        # свой grounding одним параметром session_id, не меняя вызов.
        sid = self._session_id(args)
        if sid and query:
            rec = self._register_pre_pass(sid, "memory_prompt", query,
                                          res["node_ids"],
                                          self._short_text(args, "agent"))
            res["session_id"] = sid
            res["logged_at"] = rec["ts"]
            self._slice_cache_note(sid, query, res, args,
                                   nodes + volatile_nodes)
        return res

    # R12/D, флаг MNEMOS_SLICE_CACHE (по умолчанию ВЫКЛЮЧЕН) ------------------
    # Замер журнала за 05–10.09: 63.5% вызовов prepare — это ПОВТОР того же
    # вопроса в той же сессии, и 64% доставок узлов — повторная доставка узла,
    # который агент в этом же диалоге уже получил. Срез при этом байт-в-байт
    # тот же. Флаг отдаёт на повторе не текст среза, а отметку «не изменился»:
    # выдержка уже лежит в контексте агента с прошлого хода (общий префикс,
    # правило). Чем ломается: если контекст агента был ужат, выдержки там больше
    # нет — на этот случай есть аргумент force_full=true, и кэш сбрасывается
    # сам, как только меняется состав узлов.
    _SLICE_CACHE_MAX = 512

    @staticmethod
    def _slice_signature(nodes: List[Dict[str, Any]]) -> str:
        """Подпись среза по СОДЕРЖИМОМУ, а не по списку id (R12-3).

        Store.rewrite/reinforce/retract id узла не меняют, поэтому подпись
        "|".join(node_ids) считала переписанный узел прежним: memory_rewrite
        между двумя prepare в одной сессии отдавал slice_unchanged со старым
        текстом. Берём то, что видно в срезе и в ранжировании: claim, context,
        вес и момент правки (число ревизий + valid_until/retracted).
        """
        h = hashlib.sha256()
        for n in nodes:
            if not n:
                continue
            h.update("\x1f".join([
                str(n.get("id") or ""),
                str(n.get("claim") or ""),
                str(n.get("context") or ""),
                f"{float(n.get('weight') or 0.0):.6f}",
                str(n.get("kind") or ""),
                str(len(n.get("revisions") or [])),
                str(n.get("valid_until") or ""),
                "1" if n.get("retracted") else "0",
            ]).encode("utf-8"))
            h.update(b"\x1e")
        return h.hexdigest()

    def _slice_cache_note(self, sid: str, query: str, res: Dict[str, Any],
                          args: Dict[str, Any],
                          nodes: Optional[List[Dict[str, Any]]] = None) -> None:
        if str(os.environ.get("MNEMOS_SLICE_CACHE", "")).strip().lower() not in (
                "1", "true", "yes", "on"):
            return
        cache = getattr(self, "_slice_cache", None)
        if cache is None:
            cache = self._slice_cache = {}
        key = (sid, query)
        if nodes is None:
            nodes = [self.store.get(i) for i in (res.get("node_ids") or [])]
        sig = self._slice_signature(nodes)
        prev = cache.get(key)
        cache[key] = sig
        if len(cache) > self._SLICE_CACHE_MAX:
            for k in list(cache)[: len(cache) - self._SLICE_CACHE_MAX]:
                cache.pop(k, None)
        if prev is None or prev != sig or bool(args.get("force_full")):
            res["slice_unchanged"] = False
            return
        res["slice_unchanged"] = True
        res["prompt"] = None
        res.pop("text", None)
        res["hint"] = ("срез не изменился с прошлого хода этой сессии — "
                       "используй выдержку, которая уже в твоём контексте; "
                       "нужен полный текст — вызови с force_full=true")

    def memory_graph(self, args: Dict[str, Any]) -> Dict[str, Any]:
        op = str(args.get("op") or "")
        g = self.store.graph()
        if op == "neighbors":
            nid = args.get("node_id")
            if not isinstance(nid, str) or not nid.strip():
                raise ValueError("memory_graph neighbors: parameter node_id is required")
            return g.neighbors(nid.strip(), rel=args.get("rel") or None)
        if op == "path":
            a, b = args.get("a"), args.get("b")
            if not (isinstance(a, str) and isinstance(b, str) and a.strip() and b.strip()):
                raise ValueError("memory_graph path: parameters a and b are required")
            return {"a": a, "b": b, "path": g.path(a.strip(), b.strip())}
        if op == "hub":
            key = args.get("key")
            if not isinstance(key, str) or not key.strip():
                raise ValueError("memory_graph hub: parameter key is required")
            return g.hub(key.strip())
        if op == "hubs":
            return {"hubs": g.list_hubs()}
        if op == "rules_for":
            sit = args.get("situation")
            if not isinstance(sit, str) or not sit.strip():
                raise ValueError("memory_graph rules_for: parameter situation is required")
            return g.rules_for(sit.strip(), limit=_as_int(args.get("limit")) or 10)
        if op == "conflicts":
            return {"conflicts": g.conflicts()}
        raise ValueError(f"memory_graph: unknown operation {op!r}; available: {g.OPS}")

    # -- обязательный проход через граф (03.09, приказ Ильи) ------------------
    def _new_session_id(self) -> str:
        return "gs_" + uuid.uuid4().hex[:12]

    def _register_pre_pass(self, session_id: str, tool: str, query: str,
                           node_ids: List[str], agent: str,
                           thread: Optional[str] = None) -> Dict[str, Any]:
        """Отметить пред-проход: и в памяти процесса, и в append-only журнале.

        Журнал — источник правды (переживает рестарт сервера), трекер в памяти
        — быстрый путь: ответ приходит через секунды после подготовки, лезть
        за этим в файл на каждый memory_ground незачем.

        `thread` пишется в журнал, когда slug нити известен: по нему
        checkpoint узнаёт, какие ещё сессии сейчас открыты на этой нити. Из `query`
        slug виден не всегда — его можно передать аргументом `thread=`.
        """
        self.sessions.register(session_id, tool=tool, query=query,
                               node_ids=list(node_ids), agent=agent or None)
        return self.ground_log.append(
            "prepare", tool=tool, session_id=session_id, agent=agent or None,
            query=query, node_ids=list(node_ids), nodes=len(node_ids),
            thread=thread or None,
        )

    def _find_pre_pass(self, session_id: str, agent: str = "") -> Optional[Dict[str, Any]]:
        if not session_id:
            return None
        return (self.sessions.get(session_id, agent=agent or None)
                or self.ground_log.find_pre_pass(session_id, agent=agent or None))

    def _policy_flag(self, args: Dict[str, Any], key: str,
                     default: Optional[bool] = None) -> bool:
        """Булев параметр протокола: отсутствие -> политика, мусор -> ошибка.

        Голый `bool(args[key])` был дырой (баг-хант 03.09, D4): схема объявляет
        boolean, а на деле проходило что угодно — `0`, `""`, `[]`, `{}` снимали
        требование пред-прохода, а строка `"false"` (истинная в питоне!) его,
        наоборот, включала. Ослабление политики опечаткой должно быть громким.
        """
        value = args.get(key)
        if value is None:
            return self.ground_by_default if default is None else default
        if isinstance(value, bool):
            return value
        raise ValueError(
            f"{key}: expected true or false, got {value!r} "
            f"({type(value).__name__})"
        )

    @staticmethod
    def _short_text(args: Dict[str, Any], key: str,
                    limit: int = MAX_ID_LEN) -> str:
        """Короткая строка-идентификатор (agent, session_id) с потолком длины.

        Потолок здесь, а не в журнале: session_id и agent пишутся в журнал
        как есть (обрезанный id перестал бы джойниться), поэтому мегабайтный
        id должен отлетать на входе, а не раздувать файл (D6).
        """
        value = args.get(key)
        if value is None:
            return ""
        if not isinstance(value, str):
            raise ValueError(f"{key}: expected a string, got {type(value).__name__}")
        value = value.strip()
        if len(value) > limit:
            raise ValueError(f"{key}: length {len(value)} — the cap is {limit} characters")
        return value

    def _session_id(self, args: Dict[str, Any]) -> str:
        return self._short_text(args, "session_id")

    @staticmethod
    def _threshold(args: Dict[str, Any], key: str, default: float) -> float:
        """Порог из аргументов; отсутствие -> умолчание, мусор -> ошибка.

        Через `or` тут нельзя: порог 0.0 — валидное «пропускать всё», и `or`
        подменил бы его умолчанием, тихо ужесточив то, что клиент ослабил.
        """
        if args.get(key) is None:
            return default
        v = _as_float(args.get(key))
        if v is None or not (0.0 <= v <= 1.0):
            raise ValueError(f"{key}: expected a number in [0, 1], got {args.get(key)!r}")
        return v

    def memory_ground_prepare(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """ШАГ 1: поиск по графу + промпт + graph-first, с записью пред-прохода."""
        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("memory_ground_prepare: parameter query (string) is required")
        _text_limit(query, MAX_QUERY_CHARS, "memory_ground_prepare: query")
        query = query.strip()
        session_id = self._session_id(args) or self._new_session_id()
        agent = self._short_text(args, "agent")

        gf: Dict[str, Any] = {"hit": False, "reason": "graph_first выключен параметром",
                              "answer": None}
        # один бюджетный поиск на весь шаг (wave2): graph-first и сборка
        # промпта раньше искали каждый сам по себе — дважды O(N) за один вызов
        search = self.store.search_budget(query)
        # TS.1: пред-проход — второй вход в graph_first, и до фазы S он не знал
        # ни про архив, ни про песочницу: узел трипа мог стать готовым ответом
        # в обход checkpoint. Режем тем же общим фильтром и здесь.
        search = _cut_hidden(search)
        if bool(args.get("graph_first", True)):
            gf = grounding.graph_first(
                self.store, query, search=search,
                coverage_threshold=self._threshold(
                    args, "threshold", grounding.GRAPH_FIRST_COVERAGE),
            )
        prompt = self.memory_prompt({
            "query": query,
            "constitution": bool(args.get("constitution", False)),
            "max_tokens": args.get("max_tokens"),
            "format": args.get("format"),
            "_search": search,
        })
        node_ids = list(prompt.get("node_ids") or [])
        if gf.get("hit") and gf.get("node_id") and gf["node_id"] not in node_ids:
            node_ids.append(gf["node_id"])
        rec = self._register_pre_pass(session_id, "memory_ground_prepare",
                                      query, node_ids, agent)
        return {
            "session_id": session_id,
            "query": query,
            "agent": agent or None,
            "policy": grounding.system_prompt(),
            "ground_by_default": self.ground_by_default,
            "graph_first": gf,
            # T10.1: раньше здесь лежали и prompt, и
            # text — при format=plain побайтно один текст дважды (4056 из
            # 4705 токенов ответа). Оставляем одно поле: prompt — это text
            # в обёртке формата, plain отдаёт его как есть.
            "prompt": prompt["prompt"],
            "tokens": prompt["tokens"],
            "over_budget": prompt.get("over_budget"),
            "sections": prompt.get("sections"),
            "classification": prompt.get("classification"),
            "node_ids": node_ids,
            "next_step": (
                "graph_first.hit=true -> отдай graph_first.answer без вызова LLM; "
                "иначе ответь по выдержке и вызови "
                f"memory_ground(answer_text=..., session_id={session_id!r})"
            ),
            "logged_at": rec["ts"],
        }

    def memory_checkpoint(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """search + prepare одним вызовом (wave2, фронт 4).

        Контракт Codex раньше требовал memory_search в начале задачи и
        memory_ground_prepare перед ответом — два похода в граф по одной теме.
        Здесь один: бюджетный поиск, компактная выдержка (id | факт), проверка
        graph-first, регистрация пред-прохода. Ответ не тащит system-prompt
        целиком — модели нужны факты и session_id, а не преамбула.
        """
        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("memory_checkpoint: parameter query (string) is required")
        _text_limit(query, MAX_QUERY_CHARS, "memory_checkpoint: query")
        query = query.strip()
        session_id = self._session_id(args) or self._new_session_id()
        agent = self._short_text(args, "agent")
        top_k = _as_int(args.get("top_k"))
        if top_k is None:
            top_k = CHECKPOINT_TOP_K
        elif top_k <= 0:
            raise ValueError("memory_checkpoint: top_k must be > 0")
        top_k = min(top_k, 50)
        # нить проекта (фаза 2): slug явно (thread=) или из «[THREAD:<slug>]» в query
        slug = self._short_text(args, "thread") or thread_mod.slug_from_query(query)
        if slug and not thread_mod.is_valid_slug(slug):
            raise ValueError(f"memory_checkpoint: thread {slug!r} — expected [A-Za-z0-9._-] with no spaces")
        sessions_n = _as_int(args.get("sessions"))
        if sessions_n is None:
            if args.get("sessions") is not None:
                raise ValueError("memory_checkpoint: sessions must be an integer (0..20)")
            sessions_n = THREAD_SESSIONS_DEFAULT
        elif sessions_n < 0:
            raise ValueError("memory_checkpoint: sessions must be >= 0")
        sessions_n = min(sessions_n, THREAD_SESSIONS_MAX)
        search = self.store.search_budget(query, top_k=top_k)
        # правило: архив (04 Архив в vault пользователя) лежит в памяти и находится
        # явным memory_search, но в выдержку начала сессии не поднимается:
        # checkpoint показывает живое состояние нити, а не то, что пользователь
        # сам убрал в архив. Режем ДО graph_first — иначе архивная заметка
        # могла бы стать готовым ответом.
        # TS.1: тем же срезом уходят узлы песочницы (thread:sandbox / state:trip).
        search = _cut_hidden(search)
        results = list(search["results"])
        gf = grounding.graph_first(
            self.store, query, search=search,
            coverage_threshold=self._threshold(args, "threshold", grounding.GRAPH_FIRST_COVERAGE),
        )
        view: Optional[Dict[str, Any]] = None
        if slug:
            # T2.7: agent/session_id -> changes_since_last (дельта нити с прошлой сессии дирижёра)
            # T2.11: хвост журнала prepare -> active_sessions (кто ещё сейчас на нити).
            # Хвост читается ОДИН раз и только когда нить известна: journal — файл, а checkpoint
            # зовётся в начале каждой сессии.
            view = thread_mod.thread_view(
                self.store, slug, sessions=sessions_n, agent=agent, session_id=session_id,
                pre_passes=self.ground_log.read(limit=THREAD_ACTIVE_JOURNAL_TAIL, event="prepare"),
            )
            head = view.get("head")
            if head and head.get("id"):
                # голова — всегда facts[0], даже если поиск её не поднял
                results = [r for r in results if r.get("id") != head["id"]]
                live_head = self.store.get(head["id"]) or {}
                results.insert(0, {
                    "id": head["id"], "claim": live_head.get("claim", head.get("claim")),
                    "kind": live_head.get("kind"), "score": None, "ts": live_head.get("ts"),
                    "source": live_head.get("source"), "via": "thread_head",
                })
        node_ids = [r["id"] for r in results]
        if gf.get("hit") and gf.get("node_id") and gf["node_id"] not in node_ids:
            node_ids.append(gf["node_id"])
        live = [self.store.get(i) for i in node_ids]
        self.store.touch([n for n in live if n])
        rec = self._register_pre_pass(session_id, "memory_checkpoint", query, node_ids, agent,
                                      thread=slug)
        facts = [{"id": r["id"], "claim": r.get("claim"), "kind": r.get("kind"),
                  "score": r.get("score"), "ts": r.get("ts"), "source": r.get("source"),
                  "via": r.get("via")} for r in results]
        lines = [f"{f['id']} | {str(f['claim'] or '').strip()}" for f in facts]
        if view is not None:
            # клиенты, видящие только text (MCP-бридж, curl | jq .text), получают суть первой строкой
            lines.insert(0, thread_mod.format_summary(view))
        # правило: жив ли пульс, что он смотрит сейчас, кто ещё на нити, сколько
        # находок открыто и какая температура графа. Блок необязательный: нет
        # состояния или оно протухло — checkpoint работает как раньше.
        pulse_block = pulse_mod.checkpoint_block(
            pulse_mod.read_state(self.pulse_state_path) if self.pulse_state_path else None)
        if pulse_block.get("alive"):
            lines.insert(0, pulse_mod.format_summary(pulse_block))
        out = {
            "session_id": session_id,
            "query": query,
            "agent": agent or None,
            "count": len(facts),
            "graph_first": gf,
            "facts": facts,
            "text": "\n".join(lines),
            "node_ids": node_ids,
            "conflicts": search.get("conflicts") or [],
            "ground_by_default": self.ground_by_default,
            "next_step": (
                "graph_first.hit=true -> отдай graph_first.answer без вызова LLM; "
                "иначе ответь по фактам выше (чего нет — того не знаешь) и вызови "
                f"memory_ground(answer_text=..., session_id={session_id!r})"
            ),
            "logged_at": rec["ts"],
        }
        if view is not None:
            out["thread"] = view
        out["pulse"] = pulse_block
        return out

    def memory_ground(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """ШАГ 3: сверка готового ответа с графом -> вердикт + узлы-источники."""
        answer = args.get("answer_text")
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("memory_ground: parameter answer_text (string) is required")
        _text_limit(answer, MAX_ANSWER_CHARS, "memory_ground: answer_text")
        _text_limit(args.get("query"), MAX_QUERY_CHARS, "memory_ground: query")
        session_id = self._session_id(args)
        agent = self._short_text(args, "agent")
        query = str(args.get("query") or "").strip()
        # Умолчание берём из политики сервера (ground_by_default), а не из
        # константы: `args.get(key, True)` вернул бы None при явном
        # require_pre_pass: null и тихо ослабил бы политику до False.
        require = self._policy_flag(args, "require_pre_pass")
        # не `or MAX_CLAIMS`: 0 — это ошибка клиента, а `or` молча превратил бы
        # её в умолчание и разобрал бы все 24 утверждения вместо нуля
        max_claims = _as_int(args.get("max_claims"))
        if max_claims is None:
            max_claims = grounding.MAX_CLAIMS
        elif max_claims <= 0:
            raise ValueError("memory_ground: max_claims must be > 0")

        pre = self._find_pre_pass(session_id, agent)
        if not query and pre:
            query = str(pre.get("query") or "")
        out = grounding.ground_answer(
            self.store, answer, query=query, pre_pass=pre,
            require_pre_pass=require, max_claims=max_claims,
        )
        out["session_id"] = session_id or None
        out["agent"] = agent or None
        out["ground_by_default"] = self.ground_by_default
        out["require_pre_pass"] = require
        # Узел, которым агент реально подкрепил ответ, пригодился — это ровно
        # тот сигнал, ради которого существует reinforce. Подкрепляем только
        # опоры подтверждённых утверждений, а не всё, что нашлось поиском.
        #
        # И только у ответа, который политику ПРОШЁЛ (баг-хант 03.09, D5):
        # раньше вес рос и при verdict=ungrounded, то есть клиент без
        # пред-прохода накачивал веса графа, а каждый такой вызов ещё и
        # переписывал nodes.json по разу на узел-опору. Отвергнутый ответ не
        # доказывает, что узел пригодился.
        reinforced: List[Dict[str, Any]] = []
        skipped_reinforce = None
        if self._policy_flag(args, "reinforce", default=True):
            if out["verdict"] == "ungrounded":
                skipped_reinforce = (
                    "вердикт ungrounded: веса узлов не трогаем — отвергнутый "
                    "ответ не подтверждает, что узел пригодился"
                )
            else:
                strong = {s["id"] for c in out["claims"] if c["verdict"] == "supported"
                          for s in c["support"][:1]}
                for nid in sorted(strong):
                    try:
                        reinforced.append({"id": nid,
                                           "weight": self.store.reinforce(nid)})
                    except KeyError:
                        continue  # узел удалили между ответом и сверкой — не беда
        out["reinforced"] = reinforced
        if skipped_reinforce:
            out["reinforce_skipped"] = skipped_reinforce
        rec = self.ground_log.append(
            "ground", session_id=session_id or None, agent=agent or None,
            query=query or None, verdict=out["verdict"],
            passed_through_graph=out["passed_through_graph"],
            claims_verdict=out["claims_verdict"],
            grounded_ratio=out["grounded_ratio"], counts=out["counts"],
            node_ids=out["source_node_ids"], pre_pass=bool(pre),
            # фиксируем и фактическое требование политики: обход через
            # require_pre_pass=false должен быть виден в журнале (D4)
            require_pre_pass=require, ground_by_default=self.ground_by_default,
            answer_sha256=grounding.answer_sha256(answer),
            answer_preview=answer.strip()[:200],
            answer_tokens=out["answer_tokens"],
        )
        out["logged_at"] = rec["ts"]
        return out

    def memory_answer(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """graph-first: готовый ответ из графа без LLM, иначе — промпт для LLM."""
        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("memory_answer: parameter query (string) is required")
        _text_limit(query, MAX_QUERY_CHARS, "memory_answer: query")
        query = query.strip()
        session_id = self._session_id(args) or self._new_session_id()
        agent = self._short_text(args, "agent")
        search = self.store.search_budget(query)
        # TS.1: третий вход в graph_first. Без этого среза узел трипа
        # становится готовым ответом с hit=true и предписанием «LLM звать
        # не нужно» — то есть текст песочницы выдаётся как ответ памяти.
        search = _cut_hidden(search)
        gf = grounding.graph_first(
            self.store, query, search=search,
            coverage_threshold=self._threshold(
                args, "threshold", grounding.GRAPH_FIRST_COVERAGE),
            min_weight=self._threshold(
                args, "min_weight", grounding.GRAPH_FIRST_WEIGHT),
            min_confidence=self._threshold(
                args, "min_confidence", grounding.GRAPH_FIRST_CONFIDENCE),
        )
        out: Dict[str, Any] = {
            "session_id": session_id, "query": query, "agent": agent or None,
            "mode": "graph_first",
            "hit": bool(gf.get("hit")),
            "llm_required": not gf.get("hit"),
            "answer": gf.get("answer"),
            "graph_first": gf,
        }
        node_ids = [gf["node_id"]] if gf.get("hit") else []
        if gf.get("hit"):
            # выдали узел агенту — отмечаем использование, как и обычный поиск
            node = self.store.get(gf["node_id"])
            if node is not None:
                self.store.touch([node])
        elif bool(args.get("with_prompt", True)):
            prompt = self.memory_prompt({"query": query,
                                         "max_tokens": args.get("max_tokens")})
            out["prompt"] = prompt["prompt"]
            out["tokens"] = prompt["tokens"]
            node_ids = list(prompt.get("node_ids") or [])
            out["policy"] = grounding.system_prompt()
        out["node_ids"] = node_ids
        rec = self._register_pre_pass(session_id, "memory_answer", query,
                                      node_ids, agent)
        self.ground_log.append(
            "answer", session_id=session_id, agent=agent or None, query=query,
            hit=bool(gf.get("hit")), node_ids=node_ids,
            tokens_saved_min=gf.get("tokens_saved_min"),
            llm_calls_saved=gf.get("llm_calls_saved"),
        )
        out["logged_at"] = rec["ts"]
        out["next_step"] = (
            "ответ из графа: LLM звать не нужно"
            if gf.get("hit") else
            "ответь по prompt и вызови memory_ground(answer_text=..., "
            f"session_id={session_id!r})"
        )
        return out

    def memory_recent(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Сводка последних N записей журнала по всем агентам одним вызовом
        (wave2, фронт 5): дирижёру нужно «кто что записал и проверил и когда»,
        а не сырые строки журнала.

        limit — сколько последних записей смотреть (по умолчанию 50, потолок
        1000); agent / session_id / event — фильтры. Ответ: агрегаты по агентам
        (записей, проходов, вердиктов, последняя активность) и компактная
        лента событий (ts, agent, session, event, суть).
        """
        limit = _as_int(args.get("limit"))
        if limit is None:
            limit = 50
        elif limit <= 0:
            raise ValueError("memory_recent: limit must be > 0")
        limit = min(limit, 1000)
        event = args.get("event")
        if event is not None and event not in grounding.GroundLog.EVENTS:
            raise ValueError(f"memory_recent: event must be one of {grounding.GroundLog.EVENTS}")
        sid = self._session_id(args) or None
        who = self._short_text(args, "agent") or None
        records = self.ground_log.read(
            limit=limit, event=event,
            session_id=sid,
            agent=who,
        )
        agents: Dict[str, Dict[str, Any]] = {}
        feed: List[Dict[str, Any]] = []
        for r in records:
            who = str(r.get("agent") or "?")
            a = agents.setdefault(who, {"agent": who, "add": 0, "prepare": 0, "ground": 0, "answer": 0,
                                        "nodes_added": 0, "verdicts": {}, "sessions": set(),
                                        "first_ts": r.get("ts"), "last_ts": r.get("ts")})
            ev = str(r.get("event") or "?")
            a[ev] = a.get(ev, 0) + 1
            a["last_ts"] = r.get("ts")
            if r.get("session_id"):
                a["sessions"].add(str(r["session_id"]))
            if ev == "add":
                a["nodes_added"] += len(r.get("node_ids") or [])
                what = str(r.get("claim_preview") or "")[:120]
            elif ev == "ground":
                v = str(r.get("verdict") or "?")
                a["verdicts"][v] = a["verdicts"].get(v, 0) + 1
                what = f"{v}: {str(r.get('answer_preview') or '')[:80]}"
            else:
                what = f"{str(r.get('query') or '')[:80]} -> {len(r.get('node_ids') or [])} узлов"
                if ev == "answer" and r.get("hit"):
                    what += " (graph-first)"
            feed.append({"ts": r.get("ts"), "agent": who, "session_id": r.get("session_id"),
                         "event": ev, "what": what, "node_ids": list(r.get("node_ids") or [])[:5]})
        by_agent = []
        for a in agents.values():
            a["sessions"] = len(a["sessions"])
            by_agent.append(a)
        by_agent.sort(key=lambda a: str(a["last_ts"] or ""), reverse=True)
        self.ground_log.append(
            "recent", limit=limit, session_id=sid, agent=who,
        )
        return {"window": len(records), "since": records[0].get("ts") if records else None,
                "until": records[-1].get("ts") if records else None,
                "agents": by_agent, "feed": feed}

    def memory_ground_log(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Журнал проходов через граф (append-only) + сводка."""
        limit = _as_int(args.get("limit"))
        if limit is None:
            limit = 50
        elif limit <= 0:
            raise ValueError("memory_ground_log: limit must be > 0")
        event = args.get("event")
        if event is not None and event not in grounding.GroundLog.EVENTS:
            raise ValueError(
                f"memory_ground_log: event must be one of "
                f"{grounding.GroundLog.EVENTS}, got {event!r}"
            )
        records = self.ground_log.read(
            limit=limit,
            session_id=str(args["session_id"]) if args.get("session_id") else None,
            event=event,
            agent=str(args["agent"]) if args.get("agent") else None,
        )
        out: Dict[str, Any] = {
            "path": str(self.ground_log.path),
            "count": len(records),
            "records": records,
        }
        if bool(args.get("stats", False)):
            grounds = [r for r in records if r.get("event") == "ground"]
            answers = [r for r in records if r.get("event") == "answer"]
            verdicts: Dict[str, int] = {}
            for r in grounds:
                v = str(r.get("verdict") or "?")
                verdicts[v] = verdicts.get(v, 0) + 1
            out["stats"] = {
                "window": len(records),
                "prepare": sum(1 for r in records if r.get("event") == "prepare"),
                "ground": len(grounds),
                "answer": len(answers),
                "verdicts": verdicts,
                "graph_first_hits": sum(1 for r in answers if r.get("hit")),
                "llm_calls_saved": sum(int(r.get("llm_calls_saved") or 0) for r in answers),
                "tokens_saved_min": sum(int(r.get("tokens_saved_min") or 0) for r in answers),
                "note": "сводка по окну журнала (последние limit записей), не за всё время",
            }
        return out

    def memory_decay(self, args: Dict[str, Any]) -> Dict[str, Any]:
        node_id = args.get("node_id")
        half_life = _as_float(args.get("half_life_hours")) or DEFAULT_HALF_LIFE_HOURS
        out = self.store.decay(
            node_id=node_id if isinstance(node_id, str) and node_id.strip() else None,
            half_life_hours=half_life,
        )
        weights = sorted(out.values())
        n = len(weights) or 1
        st = self.store.stats()
        return {
            "decayed": len(out),
            "half_life_hours": half_life,
            "levels": st.get("levels"),
            "quantized": st.get("quantized"),
            "weight_min": round(weights[0], 4) if weights else None,
            "weight_max": round(weights[-1], 4) if weights else None,
            "weight_mean": round(sum(weights) / n, 4) if weights else None,
            "below_0_5": sum(1 for w in weights if w < 0.5),
        }

    def memory_prune(self, args: Dict[str, Any]) -> Dict[str, Any]:
        rule = args.get("rule")
        if not isinstance(rule, str) or not rule.strip():
            raise ValueError("memory_prune: parameter rule (string) is required")
        return self.store.prune(
            rule=rule.strip(),
            dry_run=bool(args.get("dry_run", True)),   # безопасно по умолчанию
            max_delete=int(args.get("max_delete", 100)),
            source_prefix=str(args.get("source_prefix", "")),
            older_than_days=int(args.get("older_than_days", 30)),
            weak_weight=_as_float(args.get("weak_weight")) or 0.1,
            export_path=args.get("export_path"),
            weak_limit=int(args.get("weak_limit", WEAK_LIMIT)),
        )

    def memory_summarize(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Свёртка кластера похожих узлов в один узел-концентрат.

        Механизм для «узла сна» (Ж5) и свёрток N8/N9 из аудита: 2833 узла
        «алиса вердикт» — это не память, это лог; в память должна идти
        суточная свёртка. Исходные узлы НЕ удаляются: они становятся детьми
        свёртки и переводятся в kind=outdated — история сохраняется.
        """
        source_prefix = str(args.get("source_prefix", ""))
        contains = str(args.get("contains", ""))
        want_tags = args.get("tags") or []
        if isinstance(want_tags, str):
            want_tags = [want_tags]
        if not (source_prefix or contains or want_tags):
            raise ValueError(
                "memory_summarize: needs at least one cluster selector — "
                "source_prefix, contains or tags"
            )
        max_nodes = max(1, int(args.get("max_nodes", 500)))
        cluster = []
        for d in self.store.all():
            if d.get("kind") in ("rule", "outdated", "refuted"):
                continue
            if source_prefix and not str(d.get("source") or "").startswith(source_prefix):
                continue
            if contains and contains.lower() not in str(d.get("claim") or "").lower():
                continue
            if want_tags and not set(map(str, want_tags)) <= set(d.get("tags") or []):
                continue
            cluster.append(d)
        cluster.sort(key=lambda d: str(d.get("ts") or ""))
        capped = len(cluster) > max_nodes
        cluster = cluster[:max_nodes]
        preview = {
            "cluster_size": len(cluster),
            "capped_by_max_nodes": capped,
            "ts_from": cluster[0].get("ts") if cluster else None,
            "ts_to": cluster[-1].get("ts") if cluster else None,
            "sample_claims": [str(d.get("claim"))[:80] for d in cluster[:5]],
            "ids": [d["id"] for d in cluster[:200]],
        }
        if bool(args.get("dry_run", True)):
            return {**preview, "dry_run": True, "applied": False}
        claim = args.get("claim")
        if not isinstance(claim, str) or not claim.strip():
            raise ValueError(
                "memory_summarize: with dry_run=false the parameter claim "
                "(the claim of the summary node) is required"
            )
        if not cluster:
            raise ValueError("memory_summarize: the cluster is empty — nothing to summarize")
        evidence = args.get("evidence") or []
        if isinstance(evidence, str):
            evidence = [evidence]
        node = make_node(
            claim=claim.strip(),
            source=str(args.get("source", "memory_summarize")),
            evidence=[str(e) for e in evidence] or [
                f"свёртка {len(cluster)} узлов: {preview['ts_from']} .. {preview['ts_to']}"
            ],
            context=str(args.get("context", ""))
            or f"Свёртка кластера ({len(cluster)} узлов). Исходные узлы -> outdated.",
            kind="fact",
            tags=[str(t) for t in want_tags],
        )
        node.tags = ensure_router_tag(node.tags, {"claim": node.claim, "context": node.context, "kind": node.kind})
        check_and_update(node, registry=self.store.get)
        # свёртка по определению похожа на свои исходники — Г4 обязан её
        # отклонить; гейты здесь не применяем осознанно (это и есть лечение).
        summary = self.store.add(node)
        linked, marked = 0, 0
        for d in cluster:
            try:
                self.store.link_existing(summary["id"], d["id"])
                linked += 1
            except (KeyError, ValueError):
                continue
            cur = self.store.get(d["id"])
            if cur is not None and cur.get("kind") not in ("rule",):
                cur["kind"] = "outdated"
                marked += 1
        self.store._save()
        return {
            **preview,
            "dry_run": False,
            "applied": True,
            "summary_node": summary["id"],
            "linked": linked,
            "marked_outdated": marked,
        }

    def memory_stats(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self.store.stats()

    def health(self) -> Dict[str, Any]:
        """/health (wave2, фронт 6): узлы, размеры файлов, время последней
        записи, uptime, версия, журнал."""
        store = self.store
        snap = store.path
        jrn = store.journal_path
        last_write = None
        for p in (snap, jrn):
            try:
                mt = p.stat().st_mtime
            except OSError:
                continue
            last_write = mt if last_write is None else max(last_write, mt)
        js = store.journal_status()
        return {
            "ok": True,
            "name": SERVER_NAME,
            "product": PRODUCT_NAME,
            "legacy_name": LEGACY_SERVER_NAME,
            "version": SERVER_VERSION,
            "bridge_protocol": PROTOCOL_VERSION,
            "nodes": len(store),
            "store_path": str(snap),
            "store_bytes": js.get("snapshot_bytes", 0),
            "journal_bytes": js.get("journal_bytes", 0),
            "journal_records": js.get("journal_records", 0),
            "pending_usage": js.get("pending_usage", 0),
            "last_write": (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(last_write))
                           if last_write else None),
            "uptime_seconds": round(time.time() - STARTED_AT, 1),
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(STARTED_AT)),
            "ground_by_default": self.ground_by_default,
            "plugins": list(self.plugins.enabled),
            "tools": len(self.tools),
        }

    def memory_get(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Один узел по id целиком."""
        node_id = args.get("node_id")
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("memory_get: parameter node_id (string) is required")
        d = self.store.get(node_id.strip())
        if d is None:
            raise KeyError(f"memory_get: node {node_id.strip()} not found")
        return self.store.snapshot([d])[0]

    def memory_list(self, args: Dict[str, Any]) -> Dict[str, Any]:
        kind = args.get("kind")
        parent = args.get("parent")
        want_tags = [str(t) for t in (args.get("tags") or [])]
        limit = _as_int(args.get("limit"))
        limit = 1000 if limit is None else max(1, min(limit, 10000))
        offset = max(0, _as_int(args.get("offset")) or 0)
        audience = privacy.normalize_audience(args.get("audience"), "memory_list")
        nodes = self.store.find_by_tags(want_tags, kind=str(kind) if kind else None,
                                        active_only=False)
        if isinstance(parent, str) and parent.strip():
            nodes = [d for d in nodes if d.get("parent") == parent.strip()]
        # до подсчёта total: наружу не должно утечь даже число приватных узлов
        nodes = privacy.filter_audience(nodes, audience)
        nodes.sort(key=lambda d: str(d.get("ts") or ""), reverse=True)
        page = nodes[offset:offset + limit]
        results = self.store.snapshot(page)
        # Голова нити хранится одним claim'ом с русскими ключами (контракт
        # THREAD.md v1). Клиенту, который её показывает, разбирать русский
        # текст нельзя: публичные поверхности английские. Поэтому
        # разобранные поля отдаются рядом, с английскими именами, а сам claim
        # не трогается.
        for node in results:
            head = thread_mod.parse_head(node.get("claim"))
            if head:
                node["head"] = head
        return {"count": len(page), "total": len(nodes),
                "offset": offset, "results": results}

    def memory_export(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Полный обход графа страницами с курсором по id (экспорт в Obsidian).

        memory_list листает по offset поверх сортировки по ts: если во время
        обхода добавить узел, все последующие страницы сдвигаются и один узел
        читается дважды, а другой пропадает. Здесь ключ страницы — id узла
        (он не меняется за жизнь узла), поэтому обход полный и без дублей
        даже под записью. active_only=False: outdated/refuted тоже уезжают
        в vault — экспорт показывает память целиком, а не только живое.
        """
        cursor = args.get("cursor")
        cursor = str(cursor).strip() if isinstance(cursor, str) and cursor.strip() else None
        limit = _as_int(args.get("limit"))
        limit = 500 if limit is None else max(1, min(limit, 5000))
        kind = args.get("kind")
        kind = str(kind).strip() if isinstance(kind, str) and kind.strip() else None
        since = args.get("since")
        since = str(since).strip() if isinstance(since, str) and since.strip() else None

        audience = privacy.normalize_audience(args.get("audience"), "memory_export")

        # TS.1: выгрузка (в том числе Obsidian) по умолчанию не забирает узлы
        # песочницы. include_sandbox=true — явная просьба инструментов самой
        # песочницы; для основного графа умолчание «не отдавать» правильнее,
        # потому что забытый флаг здесь стоит утечки трипа в vault пользователя.
        include_sandbox = bool(args.get("include_sandbox", False))
        want_ids = args.get("ids")
        if want_ids is not None:
            # Адресная выборка: удалённый экспортёр докачивает по
            # событию только изменившиеся узлы. Идёт тем же путём, что и
            # обход, — иначе фильтры песочницы и audience пришлось бы
            # повторять во второй раз, а повторённый фильтр рано или поздно
            # расходится с первым.
            if not isinstance(want_ids, (list, tuple)):
                raise ValueError("memory_export: ids must be a list of strings")
            picked = [str(i).strip() for i in want_ids if isinstance(i, str) and i.strip()]
            nodes = [d for d in (self.store.get(i) for i in dict.fromkeys(picked))
                     if d is not None]
        else:
            nodes = self.store.find_by_tags([], kind=kind, active_only=False)
        if not include_sandbox:
            nodes = [d for d in nodes if not sandbox_mod.is_quarantined(d)]
        if since is not None and want_ids is None:
            nodes = [d for d in nodes
                     if max(str(d.get("ts") or ""), str(d.get("last_used") or "")) >= since]
        # раньше курсора и раньше total: has_more/next_cursor считаются по уже
        # отфильтрованному списку, иначе страница выходила бы пустой, а обход
        # выдавал бы наружу количество скрытых узлов
        nodes = privacy.filter_audience(nodes, audience)
        total = len(nodes)
        nodes.sort(key=lambda d: str(d.get("id") or ""))
        if cursor is not None and want_ids is None:
            nodes = [d for d in nodes if str(d.get("id") or "") > cursor]
        page = nodes[:limit]
        has_more = len(nodes) > len(page)
        next_cursor = str(page[-1].get("id")) if page and has_more else None
        return {"count": len(page), "total": total, "has_more": has_more,
                "next_cursor": next_cursor, "results": self.store.snapshot(page)}

    def memory_sync_queue(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Очередь изменённых узлов с курсором — для экспортёра на другой машине.

        правило: стор живёт на удалённый хост, vault пользователя — на Маке. Местный
        экспортёр знал об изменениях из файла `<стор>.export-queue.jsonl`
        рядом со стором; удалённому этот файл недоступен, а без него
        событийный синк вырождается в таймер.

        Чтение курсорное и неразрушительное: `drain` обнулил бы очередь, и
        два читателя (местный на VPS + удалённый) забирали бы пачки друг у
        друга. Курсор — сквозной номер записи (`seq`); что делать, когда он
        разошёлся с файлом, решает `sync_queue.since` флагом `reset`.

        Состояние пульса едет в том же ответе. Оно тоже лежит файлом рядом со
        стором, и второй запрос раз в секунду ради десятка байт добавил бы
        круг по туннелю на каждый тик покраски — а не добавить его значило бы
        показывать пользователю vault без пути пульса.
        """
        if self.sync_queue_path is None:
            # MNEMOS_SYNC_QUEUE=0: очереди нет вовсе. Не ошибка — читатель
            # должен просто остаться на полных прогонах по таймеру.
            return {"queue": False, "cursor": "0", "ids": [], "records": [], "count": 0,
                    "has_more": False, "reset": False, "mtime": None, "pulse": None}

        cursor = args.get("cursor")
        if isinstance(cursor, bool):
            cursor = None
        if isinstance(cursor, str):
            cursor = cursor.strip() or None
        if cursor is not None:
            try:
                cursor = int(cursor)
            except (TypeError, ValueError):
                raise ValueError("memory_sync_queue: cursor must be an integer (the cursor field of the response)")
            if cursor < 0:
                raise ValueError("memory_sync_queue: cursor cannot be negative")

        limit = _as_int(args.get("limit"))
        limit = sync_queue.SINCE_LIMIT if limit is None else max(1, min(limit, 5000))

        out = sync_queue.since(self.sync_queue_path, cursor, limit)
        out["queue"] = True
        out["pulse"] = (pulse_mod.read_state(self.pulse_state_path)
                        if args.get("include_pulse", True) and self.pulse_state_path else None)
        return out

    def _update_node_fields(self, node_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Обновление структурных полей узла (public-apis: probe-статусы).

        В отличие от memory_rewrite это НЕ переписывание claim: url-адресуемый
        узел API остаётся тем же фактом, меняются только результаты проверки.
        """
        allowed = ("observed_at", "status", "http_code", "recheck_after", "not_a_verdict")
        unknown = [k for k in updates if k not in allowed]
        if unknown:
            raise ValueError(f"memory_update: unknown fields {unknown}; allowed: {allowed}")
        d = self.store.get(node_id)
        if d is None:
            raise KeyError(f"memory_update: node {node_id} not found")
        d = dict(d)
        d.update(updates)
        self.store.update(d)  # тот же путь записи, что у memory_rewrite (валидация схемы + дамп)
        self._sync_touch(node_id, "memory_update")
        return self.store.snapshot([self.store.get(node_id)])[0]

    def memory_update(self, args: Dict[str, Any]) -> Dict[str, Any]:
        node_id = args.get("node_id")
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("memory_update: parameter node_id (string) is required")
        updates = {k: args[k] for k in
                   ("observed_at", "status", "http_code", "recheck_after", "not_a_verdict")
                   if args.get(k) is not None}
        if not updates:
            raise ValueError("memory_update: needs at least one probe field status")
        return self._update_node_fields(node_id.strip(), updates)

    def memory_thread_digest(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """T2.9 / правило — недельный дайджест записей сессий нити.

        По каждой ISO-неделе, все записи сессий которой старше `older_than_days` (7) дней
        и у которой ещё нет дайджеста, создаётся один узел `kind=digest` с тегами
        `thread:<slug>`, `digest`: сколько сессий, какие дирижёры, что сделано, что решено,
        какие хвосты. **Исходные записи не удаляются и не переводятся в outdated** (правило:
        узлы нити живут без TTL) — их просто перестаёт показывать checkpoint за пределами
        глубины правило (3 сессии), отдавая вместо них дайджест.

        `dry_run=true` (по умолчанию) — только показать, что было бы свёрнуто.
        """
        slug = self._short_text(args, "thread") or thread_mod.slug_from_query(args.get("query"))
        if not slug or not thread_mod.is_valid_slug(slug):
            raise ValueError("memory_thread_digest: parameter thread (thread slug) is required")
        agent = self._short_text(args, "agent")
        session_id = self._session_id(args) or self._new_session_id()
        older = _as_int(args.get("older_than_days"))
        if older is None:
            older = thread_mod.DIGEST_DAYS
        elif older < 0:
            raise ValueError("memory_thread_digest: older_than_days must be >= 0")
        dry_run = args.get("dry_run", True)
        if not isinstance(dry_run, bool):
            raise ValueError("memory_thread_digest: dry_run must be true/false")
        if not dry_run and not agent:
            raise ValueError("memory_thread_digest: with dry_run=false agent is required")
        now = args.get("now")   # ISO-момент «сейчас» (тесты и детерминированный недельный прогон)
        if now is not None and not isinstance(now, str):
            raise ValueError("memory_thread_digest: now must be an ISO string or absent")

        nodes = self.store.find_by_tags([f"thread:{slug}"], active_only=True)

        def has(n, t):
            return t in (n.get("tags") or [])

        digests = [n for n in nodes
                   if (n.get("kind") == thread_mod.DIGEST_KIND or has(n, thread_mod.DIGEST_TAG))
                   and thread_mod.parse_digest(n.get("claim")) is not None]
        existing_weeks = [(thread_mod.parse_digest(n.get("claim")) or {}).get("week") for n in digests]
        sessions = [n for n in nodes
                    if not has(n, "thread_head") and n not in digests
                    and not sandbox_mod.is_quarantined(n)
                    and (has(n, "session") or any(str(t).startswith("agent:") for t in (n.get("tags") or [])))]

        items = thread_mod.build_digest_items(
            slug, sessions, agent or "unknown", session_id,
            source=str(args.get("source") or "memory_thread_digest"),
            older_than_days=older, existing_weeks=existing_weeks, now=now,
            product_tag=self._short_text(args, "product_tag"),
        )
        preview = {"thread": slug, "sessions_total": len(sessions),
                   "digests_existing": sorted(w for w in existing_weeks if w),
                   "weeks": [thread_mod.parse_digest(i["claim"])["week"] for i in items],
                   "claims": [i["claim"] for i in items]}
        if dry_run or not items:
            return {**preview, "dry_run": bool(dry_run), "applied": False, "created": 0, "results": []}
        # Дайджест по определению похож на свои исходники — Г4 обязан был бы его отвергнуть;
        # гейты здесь не применяются осознанно, как и в memory_summarize.
        created = []
        for item in items:
            node = make_node(claim=item["claim"], source=item["source"], evidence=item["evidence"],
                             context=item["context"], kind=item["kind"], tags=item["tags"])
            node.agent, node.session_id = item["agent"], item["session_id"]
            node.tags = ensure_router_tag(node.tags, {"claim": node.claim, "context": node.context,
                                                      "kind": node.kind})
            check_and_update(node, registry=self.store.get)
            created.append(self.store.add(node))
        return {**preview, "dry_run": False, "applied": True, "created": len(created),
                "results": self.store.snapshot(created)}

    def memory_archive(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """правило — обслуживание графа: старое и бесполезное убрать, среднее сжать.

        Правило проекта (2026-09-08): мост бота пишет максимум, прореживания
        на входе нет; объём разгребается здесь. Три исхода на узел —
        **самое старое и бесполезное удаляется**, **не особо полезное сжимается
        в архивные сводки дня**, **свежее остаётся целиком**.

        Полезность считается по тому, что уже записано, и не выдумывается:
        `usage.count`/`usage.hits` (их пишет каждый поиск), `weight` (его
        поднимает `store.reinforce` на подтверждённом `memory_ground` — это и
        есть след «узел пригодился в ответе») и число **входящих** рёбер.

        Инварианты, повторяющие `store.prune` (их нельзя ослаблять):
        `kind` из `protected_kinds` (rule/hub/digest) не трогается никогда;
        узел, на который кто-то ссылается, не удаляется никогда (иначе
        появились бы висячие рёбра); узел с неразбираемым `ts` не трогается
        (непонятое не удаляем); `max_delete`/`max_compress` — жёсткие потолки.

        `dry_run=true` по умолчанию: сначала числа, потом действие. Удаление
        требует **отдельной** явной просьбы `actions=["compress","delete"]` —
        сжатие обратимо (исходники остаются детьми сводки), удаление нет.
        """
        dry_run = args.get("dry_run", True)
        if not isinstance(dry_run, bool):
            raise ValueError("memory_archive: dry_run must be true/false")
        # нить, в которой копятся сводки дня: у циклов бота она своя
        slug = args.get("slug") or ARCHIVE_DEFAULT_SLUG
        if not isinstance(slug, str) or not thread_mod.is_valid_slug(slug.strip()):
            raise ValueError("memory_archive: parameter slug (the daily digest thread) is required")
        slug = slug.strip()
        actions = args.get("actions") or ["compress"]
        if isinstance(actions, str):
            actions = [actions]
        if not isinstance(actions, list) or not actions:
            raise ValueError("memory_archive: parameter actions must be a list of compress/delete")
        actions = [str(a).strip() for a in actions]
        unknown = [a for a in actions if a not in ("compress", "delete")]
        if unknown:
            raise ValueError(
                f"memory_archive: parameter actions only knows compress and delete, "
                f"got {unknown!r}")
        now = self._now_arg(args, "memory_archive")
        policy = self._archive_policy(args)
        agent = self._short_text(args, "agent")
        session_id = self._session_id(args) or self._new_session_id()

        # TS.1: обслуживание графа не смотрит в песочницу. Иначе содержимое
        # узла трипа дословно переезжало бы в сводку дня, у которой меток
        # карантина нет, — и уезжало бы в checkpoint и в выгрузку. Песочницу
        # разгребают её собственные инструменты своей же нитью.
        nodes = [d for d in self.store.find_by_tags([], active_only=False)
                 if not sandbox_mod.is_quarantined(d)]
        incoming = self._incoming_counts(nodes)
        report = archive_mod.plan(nodes, now, policy=policy, incoming_counts=incoming)

        by_id = {str(d.get("id")): d for d in nodes}
        cycles = [by_id[i] for i in report["to_compress"]
                  if i in by_id and archive_mod.is_bot_cycle(by_id[i])]
        digests = [d for d in nodes
                   if archive_mod.ARCHIVE_TAG in (d.get("tags") or [])
                   and archive_mod.parse_day(d.get("claim")) is not None]
        existing_days = [(archive_mod.parse_day(d.get("claim")) or {}).get("day") for d in digests]
        # existing_days сюда НЕ передаётся сознательно: идемпотентность держится
        # на метке archived_by у самого узла. По дню «опоздавший» цикл уже
        # свёрнутого дня не попал бы в сводку никогда и позже ушёл бы под нож.
        items = archive_mod.build_day_items(
            slug, cycles, agent or "unknown", session_id,
            source=str(args.get("source") or "memory_archive"),
            older_than_days=float(args.get("older_than_days", 1.0)),
            now=now, product_tag=self._short_text(args, "product_tag"),
        )
        folded = {i: True for item in items for i in item.get("node_ids") or []}
        preview = {
            **report,
            "thread": slug,
            "actions": actions,
            "cycles_to_fold": len(cycles),
            "days": [i["claim"] for i in items],
            "days_existing": sorted(d for d in existing_days if d),
            # кандидат на сжатие, для которого сводки в этом проходе не будет
            # (например «живой» день, который ещё пополняется): числа плана и
            # числа применения обязаны сходиться, поэтому разница названа вслух
            "compress_not_folded_now": [i for i in report["to_compress"] if i not in folded],
        }
        if dry_run:
            return {**preview, "dry_run": True, "applied": False,
                    "digests_created": 0, "compressed": 0, "deleted": 0}
        if not agent:
            raise ValueError("memory_archive: with dry_run=false the parameter agent is required")

        created: List[Dict[str, Any]] = []
        compressed = 0
        if "compress" in actions:
            for item in items:
                # сводка по определению похожа на свои исходники — Г4 отверг бы её;
                # гейты здесь не применяются осознанно, как в memory_thread_digest
                node = make_node(claim=item["claim"], source=item["source"],
                                 evidence=item["evidence"], context=item["context"],
                                 kind=item["kind"], tags=item["tags"])
                node.agent, node.session_id = item["agent"], item["session_id"]
                node.tags = ensure_router_tag(node.tags, {"claim": node.claim,
                                                          "context": node.context,
                                                          "kind": node.kind})
                check_and_update(node, registry=self.store.get)
                digest = self.store.add(node)
                created.append(digest)
                for nid in item.get("node_ids") or []:
                    src = self.store.get(str(nid))
                    if src is None:
                        continue
                    # исходник НЕ удаляется: он становится outdated и получает
                    # метку сводки — ровно как в memory_summarize, чтобы
                    # свёртка оставалась обратимой одной правкой
                    tags = [str(x) for x in (src.get("tags") or [])]
                    mark = archive_mod.archived_by(digest["id"])
                    if mark not in tags:
                        tags.append(mark)
                    src["tags"] = tags
                    src["kind"] = "outdated"
                    self.store.update(src)
                    self.store.link_existing(digest["id"], src["id"],
                                             author="memory_archive", rel="has_part")
                    compressed += 1
        deleted = 0
        if "delete" in actions:
            for nid in report["to_delete"]:
                if self.store.delete(str(nid)):
                    deleted += 1
        return {**preview, "dry_run": False, "applied": True,
                "digests_created": len(created), "compressed": compressed,
                "deleted": deleted, "nodes_after": len(self.store),
                "results": self.store.snapshot(created)}

    @staticmethod
    def _incoming_counts(nodes: List[Dict[str, Any]]) -> Dict[str, int]:
        """Сколько узлов ссылается на каждый узел (рёбра links + дерево parent).

        Считается одним проходом: `Store.find_by_tags` и так отдаёт весь стор,
        второй обход графа ради того же числа не нужен.
        """
        counts: Dict[str, int] = {}
        for d in nodes:
            for link in d.get("links") or []:
                key = str(link)
                counts[key] = counts.get(key, 0) + 1
            parent = d.get("parent")
            if parent:
                counts[str(parent)] = counts.get(str(parent), 0) + 1
            for child in d.get("children") or []:
                counts[str(child)] = counts.get(str(child), 0) + 1
        return counts

    @staticmethod
    def _archive_policy(args: Dict[str, Any]) -> "archive_mod.Policy":
        """Политика обслуживания: умолчания правило плюс явные правки вызывающего."""
        base = archive_mod.DEFAULT_POLICY
        fields = {
            "keep_days": _as_float(args.get("keep_days")),
            "compress_days": _as_float(args.get("compress_days")),
            "delete_days": _as_float(args.get("delete_days")),
            "useful_hits": _as_int(args.get("useful_hits")),
            "useful_weight": _as_float(args.get("useful_weight")),
            "max_delete": _as_int(args.get("max_delete")),
            "max_compress": _as_int(args.get("max_compress")),
        }
        given = {k: v for k, v in fields.items() if v is not None}
        policy = replace(base, **given) if given else base
        policy.validate()
        return policy

    @staticmethod
    def _now_arg(args: Dict[str, Any], where: str) -> datetime:
        """«Сейчас» из аргумента или системные часы (детерминизм тестов)."""
        raw = args.get("now")
        if raw is None:
            return datetime.now(timezone.utc)
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError(f"{where}: parameter now must be an ISO timestamp string")
        try:
            moment = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{where}: parameter now did not parse as a timestamp: {raw!r}") from exc
        return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)

    def memory_rewrite(self, args: Dict[str, Any]) -> Dict[str, Any]:
        node_id = args.get("node_id")
        new_claim = args.get("new_claim")
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("memory_rewrite: parameter node_id (string) is required")
        if not isinstance(new_claim, str) or not new_claim.strip():
            raise ValueError("memory_rewrite: parameter new_claim (string) is required")
        # фаза 2 (нить проекта): смена вида и тегов тем же вызовом — закрытие
        # хвоста (kind=fact + closed, минус open), снятие открытого вопроса
        # (resolved). Без этих полей поведение прежнее.
        new_kind = args.get("kind")
        if new_kind is not None:
            if new_kind not in REWRITE_KINDS:
                raise ValueError(f"memory_rewrite: kind must be one of {REWRITE_KINDS}, got {new_kind!r}")
        add_tags = self._tag_list(args.get("add_tags"), "memory_rewrite: add_tags")
        remove_tags = self._tag_list(args.get("remove_tags"), "memory_rewrite: remove_tags")
        if "thread_head" in add_tags:
            # инвариант «одна активная голова»: голова только через memory_add
            # (там rewrite существующей вместо второй), не тегом на любой узел
            raise ValueError(
                "memory_rewrite: the thread_head tag via add_tags is not allowed — a "
                "thread head is created/updated only by memory_add (docs/product/THREAD.md)"
            )
        # context: обратный путь vault → mnemos (ingest.py). Текст заметки пользователя
        # живёт в context; он меняется и тогда, когда claim (заголовок + первые
        # 500 символов) остался прежним. Без этого поля повторный ingest не мог бы
        # обновить узел, не заводя второй, — а source адресует ровно один узел.
        new_context = args.get("context")
        if new_context is not None:
            _text_limit(new_context, MAX_FIELD_CHARS, "memory_rewrite: context")
        # add_aliases: дубль заметки нашёлся позже первого прогона — путь
        # дописывается к узлу, второй узел на то же содержание не заводится.
        add_aliases = self._alias_list(args.get("add_aliases"), "memory_rewrite: add_aliases")
        d = self.store.rewrite(
            node_id,
            new_claim.strip(),
            source=str(args.get("source", "")),
            reason=str(args.get("reason", "")),
        )
        if new_kind is None and not add_tags and not remove_tags and not add_aliases:
            if new_context is not None:
                d["context"] = str(new_context)
            check_and_update(d, registry=self.store.get)
            self.store.update(d)
            self._sync_touch(d["id"], "memory_rewrite")
            return self.store.snapshot([d])[0]
        node = MemoryNode.from_dict(d)
        if new_context is not None:
            node.context = str(new_context)
        if new_kind is not None:
            node.kind = str(new_kind)
        drop = set(remove_tags)
        tags = [t for t in node.tags if t not in drop]
        tags += [t for t in add_tags if t not in tags]
        node.tags = ensure_router_tag(tags, {"claim": node.claim, "context": node.context, "kind": node.kind})
        node.aliases = node.aliases + [a for a in add_aliases if a not in node.aliases]
        check_and_update(node, registry=self.store.get)
        self.store.update(node)
        self._sync_touch(node.id, "memory_rewrite")
        return self.store.snapshot([self.store.get(node.id)])[0]

    def memory_retract(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Отзыв факта по id — обратимая замена удалению (находка R12).

        В наборе не было операции «этот факт больше не верен»: memory_archive
        убирает нить целиком, memory_prune ходит пачкой по правилам, а
        memory_rewrite требует нового claim — им нельзя снять факт, не выдумав
        ему замену. Отзыв закрывает окно валидности узла (valid_from остаётся
        ts записи, valid_until = момент отзыва) и переводит его в outdated:
        дальше он отсекается тем же фильтром, что и протухшие по TTL, то есть
        уходит из поиска, среза и grounded. С диска не пропадает ничего.
        """
        node_id = args.get("node_id")
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("memory_retract: parameter node_id (string) is required")
        node_id = node_id.strip()
        undo = args.get("undo", False)
        if not isinstance(undo, bool):
            raise ValueError("memory_retract: parameter undo must be true/false")
        if undo:
            d = self.store.unretract(node_id)
        else:
            d = self.store.retract(
                node_id,
                reason=str(args.get("reason", "")),
                agent=self._short_text(args, "agent") or "",
                now=self._now_arg(args, "memory_retract"),
            )
        self._sync_touch(d["id"], "memory_retract")
        return self.store.snapshot([d])[0]

    def memory_counter_take(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Атомарная выдача номера из узла-счётчика.

        Почему это отдельная операция, а не memory_rewrite на стороне клиента:
        rewrite переписывает узел тем телом, которое клиент собрал ПОСЛЕ своего
        чтения, и между чтением и записью помещается чужая выдача. Клиент может
        закрыть это окно только на своей машине (flock), а агенты живут на двух.
        Здесь чтение и увеличение идут под транзакцией стора — тем же замком,
        под которым стор пишет журнал, — и клиенту возвращается уже занятое им
        число. См. mnemos/counter.py.

        Запись идёт тем же путём, что и memory_rewrite: старое тело уходит в
        revisions, узел заново проходит truth-gate, изменение попадает в
        очередь синка. В журнал переходов пишется событие `counter` с тем же
        паспортом (agent, session_id), что и у memory_add.
        """
        name = args.get("counter") or args.get("tag")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("memory_counter_take: parameter counter (counter name) is required")
        agent = self._short_text(args, "agent")
        if not agent:
            raise ValueError(
                "memory_counter_take: parameter agent is required — a number has to "
                "belong to someone, or the issue log cannot answer whose D-NNN it is")
        session_id = self._session_id(args)
        reason = str(args.get("reason", ""))

        return self._counter_op("memory_counter_take", name, agent, session_id,
                                lambda write: counter_mod.take(
                                    self.store, name.strip(), agent,
                                    reason=reason, write=write))

    def memory_counter_reserve(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Записать номер, занятый мимо счётчика, — той же операцией графа.

        Вторая точка выдачи. Клиентский путь через flock закрывал её только на
        своей машине, и между чтением узла и записью помещалась чужая выдача:
        `next` уезжал назад, а вместе с ним терялась чужая строка журнала — и
        счётчик выдавал занятое число повторно. Здесь чтение, проверка «этого
        номера ещё нет» и запись идут под одной транзакцией стора.
        """
        name = args.get("counter") or args.get("tag")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("memory_counter_reserve: parameter counter (counter name) is required")
        number = args.get("number")
        if isinstance(number, bool) or not isinstance(number, int):
            raise ValueError("memory_counter_reserve: parameter number (the taken "
                             "number) is required and must be an integer")
        agent = self._short_text(args, "agent")
        if not agent:
            raise ValueError(
                "memory_counter_reserve: parameter agent is required — a taken number "
                "also has to belong to someone, or the issue log cannot say whose D-NNN it is")
        session_id = self._session_id(args)
        reason = str(args.get("reason", ""))
        return self._counter_op("memory_counter_reserve", name, agent, session_id,
                                lambda write: counter_mod.reserve(
                                    self.store, name.strip(), number, agent,
                                    reason=reason, write=write))

    def _counter_op(self, op: str, name: str, agent: str, session_id: str,
                    run: Any) -> Dict[str, Any]:
        """Общая обвязка выдачи и записи номера: запись, журнал, синк.

        Обе точки обязаны писать узел одним путём (`memory_rewrite`: старое тело
        в revisions, truth-gate, очередь синка) и оставлять один и тот же след в
        журнале переходов — иначе по журналу нельзя восстановить, кто и как
        двигал счётчик.
        """
        def write(node_id: str, new_claim: str, why: str) -> None:
            d = self.store.rewrite(node_id, new_claim, reason=why)
            check_and_update(d, registry=self.store.get)
            self.store.update(d)

        try:
            out = run(write)
        except counter_mod.CounterError as exc:
            raise ValueError(f"{op}: {exc}") from exc
        self.ground_log.append(
            "counter", session_id=session_id or None, agent=agent or None,
            node_ids=[out["node_id"]], counter=out["counter"], number=out["number"],
            op=op,
        )
        self._sync_touch(out["node_id"], op)
        return out

    @staticmethod
    def _alias_list(value: Any, what: str) -> List[str]:
        """aliases: строка или список непустых строк (альтернативные source).

        Ограничение длины — как у source (MAX_FIELD_CHARS), а не как у тега:
        alias это путь в vault, и он бывает длиннее имени тега.
        """
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{what}: expected a list of strings, got {type(value).__name__}")
        _list_limit(value, what, MAX_FIELD_CHARS)
        out: List[str] = []
        for a in value:
            if not isinstance(a, str) or not a.strip():
                raise ValueError(f"{what}: items must be non-empty strings, got {a!r}")
            if a.strip() not in out:
                out.append(a.strip())
        return out

    @staticmethod
    def _tag_list(value: Any, what: str) -> List[str]:
        """add_tags/remove_tags: строка или список непустых строк; иначе ValueError
        (раньше [None] давал тег «None», а int — TypeError без подсказки)."""
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{what}: expected a list of strings, got {type(value).__name__}")
        _list_limit(value, what, MAX_ID_LEN)
        out: List[str] = []
        for t in value:
            if not isinstance(t, str) or not t.strip():
                raise ValueError(f"{what}: items must be non-empty strings, got {t!r}")
            if t.strip() not in out:
                out.append(t.strip())
        return out

    def memory_reinforce(self, args: Dict[str, Any]) -> Dict[str, Any]:
        node_id = args.get("node_id")
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("memory_reinforce: parameter node_id (string) is required")
        delta = args.get("delta", 0.05)
        try:
            delta = float(delta)
        except (TypeError, ValueError):
            delta = 0.05
        weight = self.store.reinforce(node_id, delta=delta)
        return {"node_id": node_id, "weight": weight}

    def memory_link(self, args: Dict[str, Any]) -> Dict[str, Any]:
        parent_id = args.get("parent_id")
        claim = args.get("claim")
        if not isinstance(parent_id, str) or not parent_id.strip():
            raise ValueError("memory_link: parameter parent_id (string) is required")
        if not isinstance(claim, str) or not claim.strip():
            raise ValueError("memory_link: parameter claim (string) is required")
        evidence = args.get("evidence")
        if evidence is None:
            evidence = []
        if isinstance(evidence, str):
            evidence = [evidence]
        node = make_node(
            claim=claim.strip(),
            source=str(args.get("source", "")),
            evidence=[str(e) for e in evidence],
            context=str(args.get("context", "")),
        )
        node.tags = ensure_router_tag(node.tags, {"claim": node.claim, "context": node.context, "kind": node.kind})
        check_and_update(node, registry=self.store.get)
        child = self.store.add_child(parent_id, node)
        self._sync_touch(child["id"], "memory_link", parent_id)
        return {
            "node": self.store.snapshot([child])[0],
            "parent_id": parent_id,
            "depth": self.store.depth(child["id"]),
        }

    # -- оркестратор ------------------------------------------------------------
    def handle_request(self, req: Any) -> Optional[Dict[str, Any]]:
        """Обрабатывает JSON-RPC запрос; None для нотификаций (без id)."""
        if not isinstance(req, dict):
            return self._error(None, INVALID_REQUEST, "the request must be an object")
        method = req.get("method")
        req_id = req.get("id")
        if req_id is None:
            # нотификация — ответ не нужен
            return None
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                    # Контракт едет клиенту на рукопожатии: агент узнаёт про
                    # обязательный проход через граф до первого ответа, а не из
                    # README, который он не читал.
                    #
                    # Именно здесь, в корне InitializeResult (баг-хант 03.09,
                    # D1). Лежало в serverInfo — а serverInfo по спеке MCP это
                    # Implementation{name, version}, и SDK разбирает его через
                    # z.object: лишние ключи не роняют клиента, их МОЛЧА
                    # вырезает. Контракт доезжал до нас, но не до клиента.
                    **({"instructions": grounding.system_prompt()}
                       if self.ground_by_default else {}),
                    "_meta": {"ground_by_default": self.ground_by_default},
                },
            }
        if method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": self.tools}}
        if method == "tools/call":
            params = req.get("params") or {}
            if not isinstance(params, dict):
                return self._error(req_id, INVALID_PARAMS, "params must be an object")
            name = params.get("name")
            args = params.get("arguments") or {}
            if not isinstance(args, dict):
                return self._error(req_id, INVALID_PARAMS, "arguments must be an object")
            handler = self._handlers.get(name)
            if handler is None:
                return self._error(req_id, INVALID_PARAMS, f"unknown tool: {name!r}")
            return self._call_tool(req_id, str(name), handler, args)
        return self._error(req_id, METHOD_NOT_FOUND, f"method not found: {method!r}")

    def _call_tool(self, req_id: Any, name: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]],
                   args: Dict[str, Any]) -> Dict[str, Any]:
        """Вызов инструмента + структурная запись в лог (wave2, фронт 6):
        tool, ms, agent, session, фазы (search/verify/gates/disk/journal),
        размер ответа; медленнее SLOW_MS — WARNING; ошибка параметров —
        INFO; внутренняя ошибка — ERROR с трассировкой В ЛОГЕ, а клиенту —
        короткий текст с id ошибки (трассировка наружу не уходит, фронт 7)."""
        trace.reset()
        t0 = time.perf_counter()
        agent = args.get("agent") if isinstance(args.get("agent"), str) else None
        session = args.get("session_id") if isinstance(args.get("session_id"), str) else None
        fields: Dict[str, Any] = {"tool": name, "agent": (agent or "")[:MAX_ID_LEN] or None,
                                  "session_id": (session or "")[:MAX_ID_LEN] or None}
        try:
            out = handler(args)
        except (ValueError, KeyError) as exc:
            code = NODE_NOT_FOUND if isinstance(exc, KeyError) else INVALID_PARAMS
            ms = (time.perf_counter() - t0) * 1000
            log.info("tool rejected", extra={**fields, "ms": round(ms, 2), "ok": False, "code": code,
                                             "error": str(exc)[:300], "phases": trace.collect()})
            return self._error(req_id, code, str(exc))
        except (TypeError, AttributeError, IndexError, OverflowError, UnicodeError) as exc:
            # мусорные параметры (список вместо строки, None вместо числа):
            # это ошибка клиента, а не сервера — INVALID_PARAMS без трассировки
            ms = (time.perf_counter() - t0) * 1000
            log.info("tool bad params", extra={**fields, "ms": round(ms, 2), "ok": False,
                                               "code": INVALID_PARAMS, "error": f"{type(exc).__name__}: {exc}"[:300],
                                               "phases": trace.collect()})
            return self._error(req_id, INVALID_PARAMS,
                               f"{name}: bad parameters ({type(exc).__name__})")
        except Exception as exc:
            err_id = uuid.uuid4().hex[:8]
            ms = (time.perf_counter() - t0) * 1000
            log.error("tool internal error", exc_info=True,
                      extra={**fields, "ms": round(ms, 2), "ok": False, "code": INTERNAL_ERROR,
                             "error_id": err_id, "error": f"{type(exc).__name__}: {exc}"[:300],
                             "phases": trace.collect()})
            return self._error(req_id, INTERNAL_ERROR,
                               f"internal error {err_id} — see the server log")
        text = json.dumps(out, ensure_ascii=False)
        ms = (time.perf_counter() - t0) * 1000
        phases = trace.collect()
        rec = {**fields, "ms": round(ms, 2), "ok": True, "bytes_out": len(text), "phases": phases,
               "nodes": len(self.store)}
        if ms >= SLOW_MS:
            log.warning("tool slow", extra=rec)
        else:
            log.info("tool", extra=rec)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": text}],
                "isError": False,
            },
        }

    @staticmethod
    def _error(req_id: Any, code: int, message: str) -> Dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": code, "message": message},
        }


class _Handler(BaseHTTPRequestHandler):
    server: "MCPHttpServer"  # тип: наш сервер (устанавливается HTTPServer)

    # HTTP/1.1 = keep-alive (wave2). BaseHTTPRequestHandler по умолчанию
    # отвечает HTTP/1.0 и закрывает соединение после каждого ответа, поэтому
    # бридж открывал новый TCP-сокет на КАЖДЫЙ вызов инструмента (замер 05.09:
    # 31 reconnect и 0 переиспользований на 31 вызов). Все ответы сервера
    # несут Content-Length (см. _send_json и ветку нотификации), а тело
    # запроса читается ровно по Content-Length — этого HTTP/1.1 и требует.
    protocol_version = "HTTP/1.1"

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self) -> None:
        """Разрешение браузеру читать ответ — только уже разрешённому источнику.

        Проверка Origin (ниже) отклоняет чужие страницы, но одного отказа мало:
        без этих заголовков браузер не отдаст ответ и той странице, которую мы
        разрешили. Поэтому разрешение и заголовки идут парой и читают один и
        тот же список MNEMOS_ALLOWED_ORIGINS. Пустой список — прежнее
        поведение: заголовков нет вовсе.
        """
        origin = self.headers.get("Origin")
        if not origin:
            return
        allowed = self.allowed_origins()
        norm = origin.strip().rstrip("/").lower()
        if "*" not in allowed and norm not in allowed:
            return
        self.send_header("Access-Control-Allow-Origin", origin.strip())
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "content-type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Max-Age", "600")

    # Защита от браузера (аудит 05.09). Сервер слушает localhost, но localhost
    # доступен любой открытой в браузере странице: POST с Content-Type
    # text/plain уходит без preflight, и страница могла молча писать и чистить
    # память (memory_add, memory_prune dry_run=false). Поэтому:
    #   * запрос с заголовком Origin — 403, если origin не перечислен в
    #     MNEMOS_ALLOWED_ORIGINS (через запятую; "*" — разрешить все);
    #   * POST без Content-Type: application/json — 415 (браузерный «простой»
    #     запрос такой заголовок без preflight послать не может).
    ALLOWED_ORIGINS_ENV = "MNEMOS_ALLOWED_ORIGINS"
    limiter = RateLimiter()  # один на процесс: ключ — адрес клиента

    def _reject(self, status: int, message: str) -> None:
        """Отказ неразрешённому источнику с учётом частоты (wave2, фронт 7):
        свыше RATE_LIMIT_REJECTS отказов в минуту с одного адреса — 429."""
        ip = str(self.client_address[0]) if self.client_address else "?"
        if not self.limiter.hit(ip, RATE_LIMIT_REJECTS):
            body = json.dumps(self.server.mnemos._error(
                None, INVALID_REQUEST,
                f"слишком много отклонённых запросов с {ip}: потолок "
                f"{RATE_LIMIT_REJECTS} в минуту"), ensure_ascii=False).encode("utf-8")
            self.send_response(429)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Retry-After", str(int(RATE_LIMIT_WINDOW)))
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            log.warning("rate limited", extra={"client": ip, "status": 429})
            return
        log.info("request rejected", extra={"client": ip, "status": status, "error": message[:200]})
        self._send_json(status, self.server.mnemos._error(None, INVALID_REQUEST, message))

    @classmethod
    def allowed_origins(cls) -> set:
        raw = os.environ.get(cls.ALLOWED_ORIGINS_ENV, "")
        return {o.strip().rstrip("/").lower() for o in raw.split(",") if o.strip()}

    def _guard(self, json_body: bool) -> bool:
        """True — запрос можно обрабатывать; False — отказ уже отправлен."""
        origin = self.headers.get("Origin")
        if origin is not None:
            allowed = self.allowed_origins()
            if "*" not in allowed and origin.strip().rstrip("/").lower() not in allowed:
                self._reject(403, f"запрос из браузера (Origin {origin[:100]!r}) отклонён; разрешить "
                                  f"можно через {self.ALLOWED_ORIGINS_ENV}")
                return False
        if json_body:
            ctype = (self.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
            if ctype != "application/json":
                self._reject(415, f"нужен Content-Type: application/json, получено {ctype[:60] or 'пусто'!r}")
                return False
        return True

    def do_OPTIONS(self) -> None:
        """Preflight. Разрешённому источнику — 204 с заголовками, чужому — отказ
        тем же путём, что и обычный запрос."""
        if not self._guard(json_body=False):
            return
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self._cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        if not self._guard(json_body=False):
            return
        path = urlparse(self.path).path
        if path == "/health":
            self._send_json(200, self.server.mnemos.health())
        else:
            self._send_json(
                404,
                self.server.mnemos._error(None, METHOD_NOT_FOUND, f"no such path {path!r}"),
            )

    def do_POST(self) -> None:
        if not self._guard(json_body=True):
            return
        try:
            try:
                length = int(self.headers.get("Content-Length", 0))
            except (TypeError, ValueError):  # кривой Content-Length — как 0
                length = 0
            length = max(0, length)  # отрицательный — тоже как 0 (B5)
            if length > MAX_BODY_BYTES:
                # фикс аудита 26.08: лимит тела — отвечаем 413 ДО чтения тела,
                # чтобы огромный Content-Length не съел память (B5); тело не
                # вычитывается, поэтому соединение закрывается (keep-alive для
                # него невозможен), а клиент, который ещё шлёт тело, может
                # получить обрыв вместо 413 — это осознанно.
                self._reject(413, f"тело запроса превышает лимит {MAX_BODY_BYTES} байт")
                self.close_connection = True
                return
            raw = self.rfile.read(length) if length else b""
            try:
                req = json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
                self._send_json(
                    400,
                    self.server.mnemos._error(None, PARSE_ERROR, "invalid JSON"),
                )
                return
            resp = self.server.mnemos.handle_request(req)
            if resp is None:  # нотификация
                self.send_response(202)
                self.send_header("Content-Length", "0")
                self.end_headers()
            else:
                self._send_json(200, resp)
        except Exception:  # pragma: no cover
            err_id = uuid.uuid4().hex[:8]
            log.error("http internal error", exc_info=True, extra={"error_id": err_id})
            self._send_json(
                500, self.server.mnemos._error(None, INTERNAL_ERROR,
                                               f"внутренняя ошибка HTTP {err_id} — см. лог сервера")
            )

    def log_message(self, *args: Any) -> None:  # тихо
        pass


class MCPHttpServer(ThreadingHTTPServer):
    """HTTP-сервер MCP (JSON-RPC 2.0), потоковый, с ядром MnemosCore."""

    daemon_threads = True

    def __init__(
        self, addr: tuple, store: Store, plugins: Any = None,
        plugins_config: Optional[str] = None,
        ground_by_default: Optional[bool] = None,
    ) -> None:
        self.mnemos = MnemosCore(store, plugins=plugins, plugins_config=plugins_config,
                                 ground_by_default=ground_by_default)
        super().__init__(addr, _Handler)


def startup_banner(host: str, httpd: "MCPHttpServer", store: Store,
                   created_blank: bool, store_path: Optional[str]) -> List[str]:
    """Строки баннера при старте — то, что пользователь видит первым.

    По умолчанию English: публичный `baron` уезжает к англоязычным
    пользователям. Русский вариант возвращается целиком по BARON_LANG=ru —
    ночным сменам и пользователю привычнее он.
    """
    lines = [i18n.pick(
        f"{PRODUCT_NAME} MCP {SERVER_VERSION} on http://{host}:{httpd.server_address[1]}/",
        f"{PRODUCT_NAME} MCP {SERVER_VERSION} на http://{host}:{httpd.server_address[1]}/",
    )]
    note = i18n.pick("  (created empty: blank)", "  (создан пустым: blank)") if created_blank else ""
    lines.append(i18n.pick(
        f"Store: {store.path}  (nodes: {len(store)}){note}",
        f"Хранилище: {store.path}  (узлов: {len(store)}){note}",
    ))
    # режим определяем разбором спецификации, а не по префиксу строки: путь
    # blankgraph.json — это обычный путь, и врать про него нельзя (Д3)
    if not created_blank and blank_target(store_path) is not None:
        lines.append(i18n.pick(
            "blank: the file was already there and empty — opened as is, not overwritten",
            "blank: файл уже был на месте и пуст — открыт как есть, не перезаписан",
        ))
    ground = httpd.mnemos.ground_by_default
    lines.append(i18n.pick(
        "Grounding required (ground_by_default): "
        + ("yes — an answer without memory_ground_prepare is marked ungrounded"
           if ground else f"NO (switched off via {GROUND_ENV}/--no-ground-by-default)"),
        "Проход через граф обязателен (ground_by_default): "
        + ("да — ответ без memory_ground_prepare помечается ungrounded"
           if ground else f"НЕТ (выключен через {GROUND_ENV}/--no-ground-by-default)"),
    ))
    enabled = httpd.mnemos.plugins.enabled
    plugins_line = ", ".join(enabled) if enabled else i18n.pick("(none)", "(нет)")
    lines.append(i18n.pick(f"Plugins: {plugins_line}", f"Плагины: {plugins_line}"))
    return lines


def run(
    host: str = "127.0.0.1",
    port: int = 8765,
    store_path: Optional[str] = None,
    plugins: Any = None,
    plugins_config: Optional[str] = None,
    ground_by_default: Optional[bool] = None,
) -> None:
    """Запускает MCP-сервер (блокирующий).

    store_path     — путь к nodes.json, либо "blank"/"blank:<путь>" для чистого
                     графа новой инстанции (None — env MNEMOS_STORE);
    plugins        — включённые плагины (None — env/plugins.json/дефолты);
    plugins_config — явный путь к plugins.json;
    ground_by_default — обязательный проход через граф (None — env/дефолт True).
    """
    configure_logging()
    path, created_blank = resolve_store_path(store_path)
    store = Store(path)
    log.info("server start", extra={"store": str(store.path), "nodes": len(store),
                                    "version": SERVER_VERSION, "host": host, "port": port})
    httpd = MCPHttpServer((host, port), store, plugins=plugins,
                          plugins_config=plugins_config,
                          ground_by_default=ground_by_default)
    for line in startup_banner(host, httpd, store, created_blank, store_path):
        print(line)

    # Ф1 02.09: systemctl stop шлёт SIGTERM — переводим его в KeyboardInterrupt,
    # чтобы finally записал накопленные usage/level (иначе попадания в поиск
    # и подъёмы L1->L0 с момента последней записи терялись бы при рестарте)
    def _sigterm(_signum: int, _frame: Any) -> None:
        raise KeyboardInterrupt

    try:
        signal.signal(signal.SIGTERM, _sigterm)
    except (ValueError, OSError):  # не главный поток / Windows
        pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print(i18n.pick("\nStopped.", "\nОстановлен."))
    finally:
        httpd.server_close()
        if store.close():
            print(i18n.pick("journal compacted into a snapshot on shutdown",
                            "журнал скомпактирован в снимок при остановке"))


def serve_in_thread(store: Store, host: str = "127.0.0.1", port: int = 0) -> MCPHttpServer:
    """Запускает сервер в фоновом потоке (для тестов и встраивания)."""
    httpd = MCPHttpServer((host, port), store)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd
