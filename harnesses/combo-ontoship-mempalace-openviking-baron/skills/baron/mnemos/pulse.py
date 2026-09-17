# -*- coding: utf-8 -*-
"""Baron Munchausen: пульс — непрерывный обход графа без LLM.

Зачем. Память просыпалась только тогда, когда её спрашивали. Между
вопросами граф лежал: противоречие, записанное вчера двумя агентами,
ждало, пока кто-нибудь случайно задаст правильный запрос; узел с
`recheck_after` в прошлом протухал молча; ссылка на умерший источник
оставалась «фактом». Пульс делает то, что делает обмен веществ: ходит по
графу постоянно, дёшево, сам по себе — и находит это раньше, чем на него
наткнётся агент.

Чего пульс НЕ делает:
  * не пишет узлы, кроме kind=incident (свои находки). Это жёсткое
    правило, а не соглашение: процесс, который ходит по памяти круглые
    сутки и умеет писать, за неделю перепишет память под себя;
  * не ходит в облако. Раз в N шагов он зовёт ЛОКАЛЬНУЮ модель (LM Studio
    на 127.0.0.1) на один спорный узел; недоступна — шаг пропускается.
    Адрес проверяется на loopback до запроса: у hub есть маршрут `*` в
    openrouter, и «локальный» вызов, ушедший туда по опечатке, увёз бы
    содержимое памяти наружу;
  * не трогает nodes.json руками. Читает — через Store (тот сам догоняет
    журнал сервера), пишет — только через memory_add по JSON-RPC, то есть
    через те же гейты, что все (правило, правило (г)).

Как ходит. Два курсора, переплетённых в одном цикле:
  * горячее ядро — голова нити, недавно спрошенное (журнал проходов),
    свежее, тяжёлое по весу. Пересобирается раз в HOT_REBUILD с, обходится
    целиком каждые несколько секунд;
  * полный круг — round-robin по всем id, темп подбирается так, чтобы круг
    закрывался не реже LAP_TARGET с (по умолчанию 10 минут).
Темп общий: PULSE_STEPS_PER_SEC шагов в секунду, между пачками сон. На
3452 узлах это доли процента CPU — пульс обязан быть незаметным, иначе
его выключат, и памяти снова нечем будет дышать.

Что проверяет на каждом шаге (всё — арифметика по уже записанным полям):
  * противоречие соседей — по тем же эвристикам, что гейт Г4 на записи
    (gates._jaccard / _has_negation / _salient), плюс объявленные рёбра
    conflicts_with / supersedes, у которых оба конца живы;
  * протухание — recheck_after в прошлом;
  * мёртвый источник — status=dead;
  * узел без единого ребра — но только в горячем ядре: одинокий узел в
    холодном хвосте это просто заметка, а одинокий узел, который агенты
    читают каждый день, — дыра в графе.

Состояние — один файл ~/.mnemos/pulse.json: путь за последние 60 с,
счётчики, «сейчас», присутствие агентов, температура графа и счётчик
посещений на узел. Файл переписывается
атомарно и целиком; его читает memory_checkpoint и экспортёр Obsidian.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from . import gates, qmem
from .budget import _active as budget_active, _decayed_weight

STATE_NAME = "pulse.json"
SCHEMA_VERSION = 1

# -- темп -------------------------------------------------------------------- #
STEPS_PER_SEC = 30.0       # шагов в секунду суммарно (горячее ядро + круг)
BATCH_SLEEP = 0.1          # с между пачками шагов
LAP_TARGET = 600.0         # с: полный круг по всему графу не реже
LAP_MARGIN = 1.05          # темп круга берётся на 5 % выше расчётного: круг
                           # закрывается на той пачке, что перешагнула черту,
                           # и ровно расчётный темп давал круг за 600.3 с —
                           # формально дольше обещанных десяти минут
HOT_SIZE = 60              # узлов в горячем ядре
HOT_REBUILD = 20.0         # с между пересборками горячего ядра
HOT_LAP = 5.0              # с: горячее ядро обходится целиком не реже
TRAIL_SECONDS = 60.0       # длина хвоста пути в состоянии
TRAIL_MAX = 400            # точек в хвосте: минута на полном темпе — это
                           # больше тысячи шагов, и держать их все значило бы
                           # переписывать сотни килобайт состояния каждые 2 с
STATE_EVERY = 2.0          # с между записями pulse.json
HEAVY_EVERY = 10.0         # с между пересчётами сводок (присутствие, находки,
                           # температура): каждая — линейный проход по графу,
                           # и на каждой записи состояния они съедали бы больше,
                           # чем сам обход
ORDER_EVERY = 5.0          # с между пересборками порядка обхода
ALIVE_AFTER = 30.0         # с без обновления состояния — пульс считается мёртвым

# -- находки ------------------------------------------------------------------ #
INCIDENT_KIND = "incident"
PULSE_TAG = "pulse"
KEY_TAG_PREFIX = "pulse_key:"
INCIDENTS_PER_LAP = 40     # потолок новых инцидентов за круг: пульс сообщает
                           # о находках, а не заваливает память своим отчётом
TYPES = ("contradiction", "stale", "dead_source", "orphan")
# Находки этих типов только считаются, инцидентов по ним не заводится
#: одинокий узел в горячем ядре — это повод посмотреть
# на граф глазами, а не отдельная запись в памяти на каждый такой узел;
# число видно в блоке `pulse` (поле `counted_only`) и в _PULSE.md.
COUNT_ONLY_TYPES = ("orphan",)

# -- локальная модель --------------------------------------------------------- #
# Тот же адрес, который внешний шлюз держит маршрутом `local` для gemma-*.
# Ходим напрямую, а не через hub: у hub последним маршрутом стоит `*` в
# openrouter, и отказ локальной модели не должен иметь физической
# возможности превратиться в облачный вызов.
LOCAL_URL_ENV = "MNEMOS_PULSE_MODEL_URL"
LOCAL_MODEL_ENV = "MNEMOS_PULSE_MODEL"
DEFAULT_LOCAL_URL = "http://127.0.0.1:1234/v1/chat/completions"
DEFAULT_LOCAL_MODEL = "gemma-3-4b-it"
LOCAL_TIMEOUT = 20.0
LOCAL_EVERY = 200          # шагов между вызовами локальной модели
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1", "[::1]")

LOCAL_PROMPT = (
    "Два утверждения из графа памяти. Скажи, противоречат ли они друг другу.\n"
    "Ответь ровно двумя строками:\n"
    "Вердикт: да | нет\n"
    "Почему: <одно предложение>\n\n"
)


# --------------------------------------------------------------------------- #
# Время
# --------------------------------------------------------------------------- #
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="milliseconds")


def _parse_iso(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def state_path(store_path: Any) -> Path:
    """pulse.json рядом со стором — там же, где журнал проходов и очередь."""
    return Path(store_path).parent / STATE_NAME


# --------------------------------------------------------------------------- #
# Находки: ключ и дедупликация
# --------------------------------------------------------------------------- #
def finding_key(kind: str, ids: Sequence[str]) -> str:
    """Ключ находки: вид + пара узлов (порядок неважен).

    По нему инцидент ищется тегом за один find_by_tags. Дедуп именно «по
    паре», а не по тексту: одно и то же противоречие пульс встретит сотни
    раз за сутки, и без ключа память забилась бы копиями одной находки.
    """
    body = kind + "|" + "|".join(sorted(str(i) for i in ids if i))
    return hashlib.sha1(body.encode("utf-8")).hexdigest()[:12]


def key_tag(key: str) -> str:
    return f"{KEY_TAG_PREFIX}{key}"


# --------------------------------------------------------------------------- #
# Детекторы — только арифметика по записанным полям, без модели
# --------------------------------------------------------------------------- #
def check_contradiction(node: Dict[str, Any], other: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Соседи говорят противоположное об одном и том же?

    Те же пороги, что у гейта Г4 на записи (gates.CONTRADICTION_THRESHOLD):
    общая тема по Jaccard и разная полярность. Считать это здесь заново
    нельзя было бы оправдать — но и звать check_consistency нельзя: он
    ходит по всему списку кандидатов и возвращает вердикт записи, а пульсу
    нужен ответ про одну конкретную пару рёбер.
    """
    a, b = str(node.get("claim") or ""), str(other.get("claim") or "")
    if not a or not b:
        return None
    if gates._has_negation(a) == gates._has_negation(b):
        return None
    j = gates._jaccard(gates._content_tokens(a), gates._content_tokens(b))
    if j < gates.CONTRADICTION_THRESHOLD:
        return None
    return {"type": "contradiction", "ids": [node["id"], other["id"]], "score": round(j, 3),
            "why": f"соседи говорят противоположное об одном и том же (сходство {j:.0%})"}


def check_declared_conflict(node: Dict[str, Any], other: Dict[str, Any],
                            rel: str, now: datetime) -> Optional[Dict[str, Any]]:
    """Ребро conflicts_with / supersedes, у которого оба конца ещё живы.

    Такое ребро — это конфликт, который кто-то ЗАПИСАЛ и не разрешил:
    вытесняющий узел есть, вытесненный так и не стал outdated.
    """
    if rel not in ("conflicts_with", "supersedes"):
        return None
    if not budget_active(node, now) or not budget_active(other, now):
        return None
    return {"type": "contradiction", "ids": [node["id"], other["id"]], "score": 1.0,
            "why": f"объявленное ребро {rel} не разрешено: оба узла живы"}


def check_stale(node: Dict[str, Any], now: datetime) -> Optional[Dict[str, Any]]:
    """recheck_after в прошлом: узел сам просил перепроверить себя."""
    due = _parse_iso(node.get("recheck_after"))
    if due is None or due > now:
        return None
    days = (now - due).total_seconds() / 86400.0
    return {"type": "stale", "ids": [node["id"]], "score": round(days, 2),
            "why": f"recheck_after прошёл {days:.1f} дн назад, узел не перепроверяли"}


def check_dead_source(node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """status=dead: источник больше не отвечает, а узел всё ещё факт."""
    if str(node.get("status") or "") != "dead":
        return None
    code = node.get("http_code")
    return {"type": "dead_source", "ids": [node["id"]], "score": 1.0,
            "why": f"источник мёртв (status=dead"
                   + (f", код {code}" if code else "") + "), а узел живой"}


def check_orphan(node: Dict[str, Any], hot: bool) -> Optional[Dict[str, Any]]:
    """Узел без единого ребра — находка только в горячем ядре.

    В холодном хвосте одинокий узел это просто заметка (в графе таких
    большинство и всегда будет). Одинокий узел, который агенты читают
    каждый день, — дыра: его знают, но не связали ни с чем, и он не
    поднимется ни по одному обходу, кроме прямого поиска.
    """
    if not hot:
        return None
    if node.get("links") or node.get("children") or node.get("parent"):
        return None
    return {"type": "orphan", "ids": [node["id"]], "score": 1.0,
            "why": "узел из горячего ядра не связан ни с чем: его читают, но он не в графе"}


# --------------------------------------------------------------------------- #
# Локальная модель
# --------------------------------------------------------------------------- #
def is_loopback(url: str) -> bool:
    """Адрес указывает на эту машину? Единственный допустимый для пульса."""
    try:
        host = urllib.parse.urlsplit(url).hostname
    except ValueError:
        return False
    return bool(host) and host.lower() in LOOPBACK_HOSTS


class LocalModel:
    """Один вопрос локальной модели (LM Studio, OpenAI-совместимый API).

    Недоступна — возвращает None и считает пропуск. Никакого запасного
    маршрута нет и быть не должно: «если недоступна — пропуск, не облако».
    """

    def __init__(self, url: Optional[str] = None, model: Optional[str] = None,
                 timeout: float = LOCAL_TIMEOUT, enabled: bool = True) -> None:
        self.url = url or os.environ.get(LOCAL_URL_ENV) or DEFAULT_LOCAL_URL
        self.model = model or os.environ.get(LOCAL_MODEL_ENV) or DEFAULT_LOCAL_MODEL
        self.timeout = float(timeout)
        loopback = is_loopback(self.url)
        self.enabled = bool(enabled) and loopback
        self.calls = 0
        self.skipped = 0
        # Разница важна для отчёта: «выключили флагом» и «адрес увёл бы наружу» —
        # это разные новости, и вторая должна быть видна сразу.
        self.last_error = "" if loopback else f"адрес не loopback: {self.url}"
        if loopback and not enabled:
            self.last_error = "выключена флагом"

    def ask(self, prompt: str) -> Optional[str]:
        if not self.enabled:
            self.skipped += 1
            return None
        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 160,
            "stream": False,
        }).encode("utf-8")
        req = urllib.request.Request(self.url, data=body,
                                     headers={"content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError) as exc:
            self.skipped += 1
            self.last_error = str(exc)[:200]
            return None
        text = extract_text(payload)
        if not text:
            self.skipped += 1
            self.last_error = "пустой ответ модели"
            return None
        self.calls += 1
        self.last_error = ""
        return text

    def judge(self, claim_a: str, claim_b: str) -> Optional[Dict[str, Any]]:
        """Спор двух утверждений -> {verdict: bool, why: str} или None."""
        out = self.ask(LOCAL_PROMPT + f"А: {claim_a[:800]}\nБ: {claim_b[:800]}\n")
        if out is None:
            return None
        verdict, why = None, ""
        for line in out.splitlines():
            low = line.strip().lower()
            if low.startswith("вердикт"):
                verdict = "да" in low.split(":", 1)[-1]
            elif low.startswith("почему"):
                why = line.split(":", 1)[-1].strip()
        if verdict is None:
            return None
        return {"verdict": verdict, "why": why or out.strip()[:200]}


def extract_text(payload: Dict[str, Any]) -> str:
    """Текст из chat/completions и из Responses API — обе формы у LM Studio."""
    for choice in payload.get("choices") or []:
        msg = choice.get("message") or {}
        if isinstance(msg.get("content"), str) and msg["content"].strip():
            return msg["content"].strip()
    chunks: List[str] = []
    for item in payload.get("output") or []:
        if item.get("type") != "message":
            continue
        for part in item.get("content") or []:
            if part.get("type") in ("output_text", "text") and part.get("text"):
                chunks.append(str(part["text"]))
    if not chunks and isinstance(payload.get("output_text"), str):
        chunks.append(payload["output_text"])
    return "\n".join(chunks).strip()


# --------------------------------------------------------------------------- #
# Запись находок: только через RPC, только kind=incident
# --------------------------------------------------------------------------- #
class Writer:
    """Единственный способ, которым пульс пишет в память.

    Именно здесь держится обещание «пульс не создаёт узлов, кроме
    incident»: другого метода записи в классе нет, kind зашит константой.
    """

    def __init__(self, url: str = "http://127.0.0.1:8765/", agent: str = "pulse",
                 timeout: float = 20.0, enabled: bool = True) -> None:
        self.url, self.agent, self.timeout = url, agent, float(timeout)
        self.enabled = bool(enabled)
        self.written = 0
        self.failed = 0
        self.last_error = ""

    def _rpc(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                           "params": {"name": name, "arguments": args}}).encode("utf-8")
        req = urllib.request.Request(self.url, data=body,
                                     headers={"content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if "error" in payload:
            raise RuntimeError(str(payload["error"].get("message"))[:200])
        return json.loads(payload["result"]["content"][0]["text"])

    def incident(self, finding: Dict[str, Any], key: str, session_id: str,
                 claims: Sequence[str] = ()) -> Optional[str]:
        if not self.enabled:
            return None
        ids = finding["ids"]
        claim = (f"[PULSE:{finding['type']}] {finding['why']} — "
                 + ", ".join(ids))
        context = "\n".join(f"{i}: {str(c)[:400]}" for i, c in zip(ids, claims))
        args = {
            "claim": claim,
            "kind": INCIDENT_KIND,
            "parent": ids[0],
            "source": "mnemos/pulse.py",
            "context": context,
            "links": list(ids[1:]),
            "tags": [PULSE_TAG, f"incident:{finding['type']}", key_tag(key),
                     "product:shinemnemos"],
            "agent": self.agent,
            "session_id": session_id,
        }
        try:
            out = self._rpc("memory_add", args)
        except (urllib.error.URLError, OSError, ValueError, RuntimeError, KeyError) as exc:
            self.failed += 1
            self.last_error = str(exc)[:200]
            return None
        self.written += 1
        self.last_error = ""
        return str(out.get("id") or "") or None

    def mark_judged(self, incident_id: str, verdict: bool, why: str,
                    claim: str, session_id: str) -> bool:
        """Вердикт локальной модели на инциденте: тег + одна строка причины."""
        if not self.enabled or not incident_id:
            return False
        tag = "pulse:llm_confirmed" if verdict else "pulse:llm_rejected"
        try:
            self._rpc("memory_rewrite", {
                "node_id": incident_id, "new_claim": claim,
                "source": "mnemos/pulse.py + локальная модель",
                "reason": f"вердикт локальной модели: {'да' if verdict else 'нет'}",
                "new_context": why[:400], "add_tags": [tag],
                "agent": self.agent, "session_id": session_id,
            })
        except (urllib.error.URLError, OSError, ValueError, RuntimeError, KeyError) as exc:
            self.failed += 1
            self.last_error = str(exc)[:200]
            return False
        return True


# --------------------------------------------------------------------------- #
# Состояние пульса
# --------------------------------------------------------------------------- #
def read_state(path: Any) -> Optional[Dict[str, Any]]:
    """pulse.json как есть или None. Никогда не бросает: читатели —
    memory_checkpoint и экспортёр, и падать из-за файла-спутника нельзя."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def is_alive(state: Optional[Dict[str, Any]], now: Optional[datetime] = None,
             max_age: float = ALIVE_AFTER) -> bool:
    """Пульс жив, если состояние свежее max_age секунд.

    По pid не проверяем намеренно: pid переживает зависший процесс, а
    свежесть файла — нет. Мёртвый пульс обязан выглядеть мёртвым.
    """
    if not state:
        return False
    updated = _parse_iso(state.get("updated"))
    if updated is None:
        return False
    return ((now or _now()) - updated).total_seconds() <= max_age


def checkpoint_block(state: Optional[Dict[str, Any]],
                     now: Optional[datetime] = None) -> Dict[str, Any]:
    """Блок `pulse` для memory_checkpoint: жив ли, что сейчас, кто рядом,
    сколько находок открыто, какая температура."""
    alive = is_alive(state, now)
    st = state or {}
    unique = (st.get("found") or {}).get("unique") or {}
    return {
        "alive": alive,
        "now": st.get("now") if alive else None,
        "presence": st.get("presence") or [],
        "incidents_open": st.get("incidents_open") or {},
        "counted_only": {t: unique.get(t, 0) for t in COUNT_ONLY_TYPES},
        "temperature": st.get("temperature") or {},
        "lap_seconds": (st.get("lap") or {}).get("seconds"),
        "updated": st.get("updated"),
    }


def format_summary(block: Dict[str, Any]) -> str:
    """Одна строка для клиентов, которые видят только text."""
    if not block.get("alive"):
        return "PULSE спит — обход графа не идёт"
    cur = block.get("now") or {}
    inc = block.get("incidents_open") or {}
    temp = block.get("temperature") or {}
    who = ", ".join(str(p.get("agent")) for p in (block.get("presence") or [])[:4])
    open_txt = ", ".join(f"{k}: {v}" for k, v in sorted(inc.items()) if v) or "нет"
    only = block.get("counted_only") or {}
    only_txt = ", ".join(f"{k}: {v}" for k, v in sorted(only.items()) if v)
    return (f"PULSE жив | сейчас: {cur.get('id') or '?'} ({cur.get('why') or '—'}) "
            f"| находок открыто: {open_txt} "
            + (f"| только счётом: {only_txt} " if only_txt else "")
            + f"| температура: {temp.get('ratio', 0):.0%} "
            + f"| рядом: {who or 'никого'}")


# --------------------------------------------------------------------------- #
# Обход
# --------------------------------------------------------------------------- #
class Pulse:
    """Непрерывный обход графа. Один процесс, один поток, без своей памяти
    кроме pulse.json."""

    def __init__(self, store: Any, ground_log: Any = None,
                 state_file: Optional[Any] = None,
                 writer: Optional[Writer] = None,
                 model: Optional[LocalModel] = None,
                 steps_per_sec: float = STEPS_PER_SEC,
                 lap_target: float = LAP_TARGET,
                 hot_size: int = HOT_SIZE,
                 local_every: int = LOCAL_EVERY,
                 thread_slug: str = "shinemnemos",
                 session_id: Optional[str] = None) -> None:
        self.store = store
        self.ground_log = ground_log
        self.state_file = Path(state_file) if state_file else state_path(store.path)
        self.writer = writer if writer is not None else Writer(enabled=False)
        self.model = model if model is not None else LocalModel(enabled=False)
        self.steps_per_sec = float(steps_per_sec)
        self.lap_target = float(lap_target)
        self.hot_size = int(hot_size)
        self.local_every = int(local_every)
        self.thread_slug = thread_slug
        self.session_id = session_id or f"pulse-{_now().date().isoformat()}"

        self.started = _now()
        self.stop = False
        self.steps = 0
        self.laps = 0
        self.checks = 0
        self.incidents_new = 0
        self.incidents_lap = 0
        self.found_by_type: Dict[str, int] = {t: 0 for t in TYPES}
        # Ключи РАЗНЫХ находок по типам. Счётчиком это быть не может: находка,
        # упёршаяся в потолок инцидентов, встретится снова на следующем круге,
        # и счётчик посчитал бы её второй раз — отчёт врал бы в большую сторону.
        self.found_keys: Dict[str, set] = {t: set() for t in TYPES}
        self.trail: List[Dict[str, Any]] = []
        self.now_node: Optional[Dict[str, Any]] = None
        self.visits: Dict[str, List[Any]] = {}     # id -> [сколько раз, unixtime]
        self.lap_info: Dict[str, Any] = {}
        self._order: List[str] = []
        self._cursor = 0
        self._lap_started = time.monotonic()
        self._hot: List[str] = []
        self._hot_why: Dict[str, str] = {}
        self._hot_at = 0.0
        self._hot_set: set = set()
        self._hot_cursor = 0
        self._state_at = 0.0
        self._budget_hot = 0.0
        self._budget_cold = 0.0
        self._heavy: Dict[str, Any] = {}
        self._heavy_at = 0.0
        self._order_at = 0.0
        self._known_keys: Optional[set] = None

    # -- горячее ядро ---------------------------------------------------------- #
    def hot_core(self, now: Optional[datetime] = None) -> List[str]:
        """Что пульс считает горячим: голова нити, недавно спрошенное,
        свежее, тяжёлое. Порядок — это и есть приоритет обхода."""
        now = now or _now()
        nodes = {n["id"]: n for n in self.store.all()}
        score: Dict[str, float] = {}
        why: Dict[str, str] = {}

        def bump(nid: str, value: float, reason: str) -> None:
            if nid not in nodes:
                return
            if value > score.get(nid, -1.0):
                why[nid] = reason
            score[nid] = score.get(nid, 0.0) + value

        # 1. Голова нити — всегда первая: с неё начинается любая сессия.
        for head in self.store.find_by_tags([f"thread:{self.thread_slug}", "thread_head"],
                                            active_only=True):
            bump(head["id"], 1000.0, "голова нити")

        # 2. Недавно спрошенное: журнал проходов помнит, какие узлы
        #    выдавались агентам — это буквально «о чём сейчас думают».
        if self.ground_log is not None:
            try:
                recent = self.ground_log.read(limit=200)
            except (OSError, ValueError):
                recent = []
            for rank, rec in enumerate(reversed(recent)):
                for nid in rec.get("node_ids") or []:
                    bump(nid, max(1.0, 100.0 - rank), "недавно спрашивали")

        # 3. Свежесть и вес — по уже посчитанным полям, без своей арифметики.
        for nid, n in nodes.items():
            if not budget_active(n, now):
                continue
            age_h = None
            ts = _parse_iso(n.get("ts"))
            if ts is not None:
                age_h = (now - ts).total_seconds() / 3600.0
            if age_h is not None and age_h < 24:
                bump(nid, 50.0 * (1.0 - age_h / 24.0), "свежий")
            hits = qmem.hits_7d(n, now)
            if hits:
                bump(nid, min(40.0, 4.0 * hits), "часто читают")
            bump(nid, 10.0 * _decayed_weight(n, now), "вес")

        top = sorted(score, key=lambda i: -score[i])[:self.hot_size]
        self._hot_why = {i: why.get(i, "горячее ядро") for i in top}
        return top

    # -- проверки одного узла --------------------------------------------------- #
    def neighbours(self, node: Dict[str, Any]) -> List[Tuple[Dict[str, Any], str]]:
        """Прямые соседи узла: рёбра links (с rel), родитель, дети."""
        out: List[Tuple[Dict[str, Any], str]] = []
        seen = {node["id"]}
        graph = self.store.graph()
        for to, rel in graph.out.get(node["id"], []):
            if to in seen:
                continue
            other = self.store.get(to)
            if other is not None:
                seen.add(to)
                out.append((other, rel))
        for nid in [node.get("parent")] + list(node.get("children") or []):
            if not nid or nid in seen:
                continue
            other = self.store.get(str(nid))
            if other is not None:
                seen.add(str(nid))
                out.append((other, "parent" if nid == node.get("parent") else "child"))
        return out

    def inspect(self, node: Dict[str, Any], hot: bool,
                now: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Все дешёвые проверки одного узла и его рёбер."""
        now = now or _now()
        found: List[Dict[str, Any]] = []
        if not budget_active(node, now):
            return found          # refuted/outdated и протухшие по TTL — не новость
        for probe in (check_stale(node, now), check_dead_source(node),
                      check_orphan(node, hot)):
            if probe:
                found.append(probe)
        for other, rel in self.neighbours(node):
            self.checks += 1
            hit = check_declared_conflict(node, other, rel, now)
            if hit is None:
                hit = check_contradiction(node, other)
            if hit:
                found.append(hit)
        return found

    # -- дедупликация находок ---------------------------------------------------- #
    def known_keys(self) -> set:
        """Ключи находок, уже записанных инцидентами. Читается один раз и
        дополняется на лету: иначе на каждую находку шёл бы линейный скан."""
        if self._known_keys is None:
            keys = set()
            for n in self.store.all():
                if n.get("kind") != INCIDENT_KIND:
                    continue
                for t in n.get("tags") or []:
                    if isinstance(t, str) and t.startswith(KEY_TAG_PREFIX):
                        keys.add(t[len(KEY_TAG_PREFIX):])
            self._known_keys = keys
        return self._known_keys

    def report(self, finding: Dict[str, Any]) -> Optional[str]:
        """Находка -> инцидент в графе, если такой ещё не записан."""
        key = finding_key(finding["type"], finding["ids"])
        if key in self.known_keys():
            return None
        if self.incidents_lap >= INCIDENTS_PER_LAP:
            return None
        claims = [str((self.store.get(i) or {}).get("claim") or "") for i in finding["ids"]]
        nid = self.writer.incident(finding, key, self.session_id, claims)
        # Ключ помечается занятым даже когда сервер не ответил: иначе пульс
        # будет ломиться с одной и той же находкой каждые несколько секунд.
        self.known_keys().add(key)
        if nid:
            self.incidents_new += 1
            self.incidents_lap += 1
            finding["incident_id"] = nid
        return nid

    # -- один шаг --------------------------------------------------------------- #
    def step(self, nid: str, hot: bool, why: str,
             now: Optional[datetime] = None) -> List[Dict[str, Any]]:
        now = now or _now()
        node = self.store.get(nid)
        self.steps += 1
        rec = self.visits.setdefault(nid, [0, 0])
        rec[0] += 1
        rec[1] = int(now.timestamp())
        self.now_node = {"id": nid, "why": why, "ts": _iso(now), "hot": hot}
        self.trail.append(self.now_node)
        cutoff = now.timestamp() - TRAIL_SECONDS
        while self.trail and ((_parse_iso(self.trail[0]["ts"]) or now).timestamp() < cutoff
                              or len(self.trail) > TRAIL_MAX):
            self.trail.pop(0)
        if node is None:
            return []
        found = self.inspect(node, hot, now)
        for f in found:
            self.found_by_type[f["type"]] = self.found_by_type.get(f["type"], 0) + 1
            self.found_keys.setdefault(f["type"], set()).add(
                finding_key(f["type"], f["ids"]))
            if f["type"] in COUNT_ONLY_TYPES:
                continue          # правило: считаем, но инцидент не заводим
            self.report(f)
        if found:
            self.now_node["found"] = [f["type"] for f in found]
        return found

    # -- вызов локальной модели -------------------------------------------------- #
    def maybe_ask_model(self) -> Optional[Dict[str, Any]]:
        """Раз в local_every шагов — один вопрос локальной модели по одному
        спорному узлу. Спорный = у него есть открытый инцидент-противоречие."""
        if self.local_every <= 0 or self.steps % self.local_every != 0:
            return None
        target = None
        for n in self.store.find_by_tags([PULSE_TAG, "incident:contradiction"],
                                         kind=INCIDENT_KIND, active_only=True):
            tags = set(n.get("tags") or [])
            if "pulse:llm_confirmed" in tags or "pulse:llm_rejected" in tags:
                continue
            target = n
            break
        if target is None:
            return None
        ids = [target.get("parent")] + list(target.get("links") or [])
        claims = [str((self.store.get(i) or {}).get("claim") or "") for i in ids if i]
        if len(claims) < 2:
            return None
        verdict = self.model.judge(claims[0], claims[1])
        if verdict is None:
            return None
        self.writer.mark_judged(target["id"], verdict["verdict"], verdict["why"],
                                str(target.get("claim") or ""), self.session_id)
        return {"incident": target["id"], **verdict}

    # -- состояние ---------------------------------------------------------------- #
    def presence(self, now: Optional[datetime] = None,
                 window_min: float = 30.0) -> List[Dict[str, Any]]:
        """Кто сейчас рядом: агенты, писавшие узлы в последние window_min
        минут. «Я здесь, делаю X» — это последний узел агента, а не отдельный
        протокол: агенты и так пишут о том, что делают."""
        now = now or _now()
        cutoff = now - timedelta(minutes=window_min)
        latest: Dict[str, Dict[str, Any]] = {}
        for n in self.store.all():
            agent = str(n.get("agent") or "").strip()
            if not agent or agent == self.writer.agent:
                continue
            ts = _parse_iso(n.get("ts"))
            if ts is None or ts < cutoff:
                continue
            prev = latest.get(agent)
            if prev is None or ts > (_parse_iso(prev["ts"]) or cutoff):
                latest[agent] = {"agent": agent, "ts": _iso(ts),
                                 "session_id": n.get("session_id"),
                                 "what": str(n.get("claim") or "")[:120]}
        return sorted(latest.values(), key=lambda d: d["ts"], reverse=True)

    def temperature(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        """Доля неподтверждённого в горячем ядре: flag гейтов или fail П1–П6."""
        hot = self._hot or self.hot_core(now)
        flagged = 0
        for nid in hot:
            n = self.store.get(nid)
            if not n:
                continue
            tc = n.get("truth_check") if isinstance(n.get("truth_check"), dict) else {}
            gate = tc.get("gates") if isinstance(tc.get("gates"), dict) else {}
            if gate.get("verdict") == "flag" or tc.get("verdict") == "fail":
                flagged += 1
        total = len(hot) or 1
        return {"hot": len(hot), "flagged": flagged, "ratio": round(flagged / total, 3)}

    def incidents_open(self) -> Dict[str, int]:
        counts = {t: 0 for t in TYPES}
        for n in self.store.find_by_tags([PULSE_TAG], kind=INCIDENT_KIND, active_only=True):
            for t in n.get("tags") or []:
                if isinstance(t, str) and t.startswith("incident:"):
                    key = t.split(":", 1)[1]
                    if key in counts:
                        counts[key] += 1
        return counts

    def archive_hint(self, idle_days: float = 30.0, top: int = 50) -> Dict[str, Any]:
        """Вход для memory_archive: кого пульс давно не встречал и
        кого встречает постоянно.

        Счётчик живёт здесь, а не на узле, намеренно: посещение пульсом —
        это факт о работе пульса, а не о памяти, и класть его в узел значило
        бы каждые несколько секунд переписывать 3452 заметки в vault.
        """
        now_ts = time.time()
        cutoff = now_ts - idle_days * 86400.0
        hot = set(self._hot)
        candidates: List[Tuple[str, int]] = []
        protected: List[Tuple[str, int]] = []
        for nid, (count, last) in self.visits.items():
            if nid in hot:
                protected.append((nid, count))
            elif last and last < cutoff:
                candidates.append((nid, count))
        candidates.sort(key=lambda p: p[1])
        protected.sort(key=lambda p: -p[1])
        return {"idle_days": idle_days, "seen": len(self.visits),
                "candidates": [i for i, _ in candidates[:top]],
                "protected": [i for i, _ in protected[:top]]}

    def heavy(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        """Сводки, каждая из которых — проход по всему графу.

        Считаются раз в HEAVY_EVERY с и переиспользуются: на живом графе в
        3455 узлов пересчёт на каждой записи состояния стоил дороже, чем
        весь обход (профиль 08.09: 0.141 с из 0.163 с уходило в save_state).
        """
        mono = time.monotonic()
        if self._heavy and mono - self._heavy_at < HEAVY_EVERY:
            return self._heavy
        now = now or _now()
        self._heavy = {
            "incidents_open": self.incidents_open(),
            "temperature": self.temperature(now),
            "presence": self.presence(now),
            "archive": self.archive_hint(),
        }
        self._heavy_at = mono
        return self._heavy

    def state(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        now = now or _now()
        heavy = self.heavy(now)
        return {
            "schema_version": SCHEMA_VERSION,
            "pid": os.getpid(),
            "started": _iso(self.started),
            "updated": _iso(now),
            "store": str(getattr(self.store, "path", "")),
            "now": self.now_node,
            "trail": list(self.trail),
            "counters": {"steps": self.steps, "laps": self.laps, "checks": self.checks,
                         "incidents": self.incidents_new,
                         "llm_calls": self.model.calls, "llm_skipped": self.model.skipped,
                         "incidents_failed": self.writer.failed},
            "lap": dict(self.lap_info),
            "hot": list(self._hot),
            "found": {"seen": dict(self.found_by_type),
                      "unique": {t: len(k) for t, k in self.found_keys.items()}},
            "incidents_open": heavy["incidents_open"],
            "temperature": heavy["temperature"],
            "presence": heavy["presence"],
            "visits": {k: list(v) for k, v in self.visits.items()},
            "archive": heavy["archive"],
            "model": {"url": self.model.url, "model": self.model.model,
                      "enabled": self.model.enabled, "last_error": self.model.last_error},
        }

    def save_state(self, now: Optional[datetime] = None) -> Path:
        """Атомарная запись pulse.json: читатели (checkpoint, экспортёр)
        никогда не должны увидеть половину файла."""
        path = self.state_file
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(self.state(now), ensure_ascii=False, indent=1),
                       encoding="utf-8")
        os.replace(tmp, path)
        self._state_at = time.monotonic()
        return path

    # -- цикл --------------------------------------------------------------------- #
    def _refresh_order(self, mono: Optional[float] = None, force: bool = False) -> None:
        """Порядок обхода. Пересобирается раз в ORDER_EVERY с: сортировка
        3455 id стоит полмиллисекунды, а на каждой пачке это уже заметно."""
        mono = time.monotonic() if mono is None else mono
        if self._order and not force and mono - self._order_at < ORDER_EVERY:
            return
        self._order_at = mono
        ids = sorted(n["id"] for n in self.store.all())
        if ids != self._order:
            self._order = ids
            self._cursor = min(self._cursor, len(ids))

    def _refresh_hot(self, mono: float) -> None:
        if self._hot and mono - self._hot_at < HOT_REBUILD:
            return
        self._hot = self.hot_core()
        self._hot_set = set(self._hot)
        self._hot_at = mono
        self._hot_cursor = 0

    def rates(self) -> Tuple[float, float]:
        """Шагов в секунду по горячему ядру и по общему кругу.

        Оба темпа заданы обещаниями, а не подобраны: горячее ядро обходится
        целиком не реже HOT_LAP секунд, полный круг — не реже lap_target.
        Сумма прижимается к steps_per_sec: пульс не имеет права занимать
        машину пользователя, и если граф вырастет настолько, что круг за 10
        минут стоит дороже потолка, честнее замедлить круг, чем съесть CPU.
        """
        cold = LAP_MARGIN * len(self._order) / max(1.0, self.lap_target)
        hot = len(self._hot) / max(0.1, HOT_LAP) if self._hot else 0.0
        total = hot + cold
        if total > self.steps_per_sec and total > 0:
            k = self.steps_per_sec / total
            hot, cold = hot * k, cold * k
        return hot, cold

    def batch(self, count: Optional[int] = None, now: Optional[datetime] = None,
              dt: float = BATCH_SLEEP) -> List[Dict[str, Any]]:
        """Пачка шагов: часть по горячему ядру, часть по общему кругу.

        Шаги копятся дробно. Целочисленная выдача на пачку ломалась на
        медленных темпах: при 1.15 шага на пачку int(1 * доля) давал ноль
        горячих шагов, и горячее ядро не обходилось вовсе.
        """
        now = now or _now()
        mono = time.monotonic()
        self._refresh_order(mono)
        self._refresh_hot(mono)
        hot_rate, cold_rate = self.rates()
        if count is None:
            self._budget_hot += hot_rate * dt
            self._budget_cold += cold_rate * dt
        else:
            share = hot_rate / (hot_rate + cold_rate) if (hot_rate + cold_rate) else 0.0
            self._budget_hot += count * share
            self._budget_cold += count * (1.0 - share)
        found: List[Dict[str, Any]] = []

        while self._budget_hot >= 1.0 and self._hot:
            self._budget_hot -= 1.0
            nid = self._hot[self._hot_cursor % len(self._hot)]
            self._hot_cursor += 1
            found += self.step(nid, True, self._hot_why.get(nid, "горячее ядро"), now)
            self.maybe_ask_model()
        if not self._hot:
            self._budget_hot = 0.0

        while self._budget_cold >= 1.0 and self._order:
            self._budget_cold -= 1.0
            if self._cursor >= len(self._order):
                self._cursor = 0
                self.laps += 1
                self.lap_info = {"seconds": round(mono - self._lap_started, 2),
                                 "nodes": len(self._order), "finished": _iso(now)}
                self._lap_started = mono
                self.incidents_lap = 0
            nid = self._order[self._cursor]
            self._cursor += 1
            found += self.step(nid, nid in self._hot_set, "круг по графу", now)
            self.maybe_ask_model()
        if not self._order:
            self._budget_cold = 0.0
        return found

    def run(self, seconds: Optional[float] = None) -> Dict[str, Any]:
        """Цикл. seconds=None — до сигнала остановки."""
        deadline = None if seconds is None else time.monotonic() + float(seconds)
        self._refresh_order(force=True)
        self._lap_started = time.monotonic()
        self.save_state()
        last = time.monotonic()
        while not self.stop:
            mono = time.monotonic()
            self.batch(dt=min(1.0, mono - last))
            last = mono
            mono = time.monotonic()
            if mono - self._state_at >= STATE_EVERY:
                self.save_state()
            if deadline is not None and mono >= deadline:
                break
            time.sleep(BATCH_SLEEP)
        self.save_state()
        return self.state()


# --------------------------------------------------------------------------- #
# Отдельный процесс (LaunchAgent)
# --------------------------------------------------------------------------- #
def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    import signal

    from . import grounding
    from .store import Store, resolve_store_path

    ap = argparse.ArgumentParser(
        prog="python3 -m mnemos.pulse",
        description="Пульс: непрерывный обход графа памяти без LLM")
    ap.add_argument("--store", default=os.environ.get("MNEMOS_STORE"),
                    help="nodes.json (по умолчанию — как у сервера)")
    ap.add_argument("--url", default=os.environ.get("MNEMOS_URL", "http://127.0.0.1:8765/"),
                    help="JSON-RPC сервера: единственный путь, которым пульс пишет")
    ap.add_argument("--state", help="файл состояния (по умолчанию pulse.json рядом со стором)")
    ap.add_argument("--seconds", type=float, help="работать столько и выйти (прогон, замер)")
    ap.add_argument("--steps-per-sec", type=float, default=STEPS_PER_SEC)
    ap.add_argument("--lap-target", type=float, default=LAP_TARGET,
                    help="сколько секунд отводится на полный круг по графу")
    ap.add_argument("--hot-size", type=int, default=HOT_SIZE)
    ap.add_argument("--local-every", type=int, default=LOCAL_EVERY,
                    help="шагов между вызовами локальной модели; 0 — не звать")
    ap.add_argument("--thread", default="shinemnemos")
    ap.add_argument("--dry-run", action="store_true",
                    help="ходить и считать, но не записывать инциденты")
    ap.add_argument("--no-model", action="store_true", help="без локальной модели")
    ap.add_argument("--json", action="store_true", help="итог в JSON")
    a = ap.parse_args(argv)

    store_path = Path(a.store).expanduser() if a.store else resolve_store_path()[0]
    store = Store(store_path, use_hash_index=False)
    log = grounding.GroundLog(store_path.parent / grounding.GROUND_LOG_NAME)
    model = LocalModel(enabled=not a.no_model)
    writer = Writer(url=a.url, enabled=not a.dry_run)
    pulse = Pulse(store, ground_log=log, state_file=a.state, writer=writer, model=model,
                  steps_per_sec=a.steps_per_sec, lap_target=a.lap_target,
                  hot_size=a.hot_size, local_every=a.local_every, thread_slug=a.thread)

    def _stop(_signum: int, _frame: Any) -> None:
        pulse.stop = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    print(f"[{_iso(_now())}] пульс: граф {store_path} ({len(store)} узлов), "
          f"состояние {pulse.state_file}, круг за {a.lap_target:.0f} c, "
          f"модель {'выключена' if not model.enabled else model.model} "
          f"{'' if model.enabled else '(' + model.last_error + ')'}", flush=True)
    state = pulse.run(seconds=a.seconds)
    if a.json:
        print(json.dumps({k: v for k, v in state.items() if k != "visits"},
                         ensure_ascii=False, indent=2))
    else:
        c = state["counters"]
        seen = state["found"]["seen"]
        uniq = state["found"]["unique"]
        print(f"[{_iso(_now())}] шагов {c['steps']}, кругов {c['laps']}, "
              f"проверок рёбер {c['checks']}, инцидентов записано {c['incidents']}, "
              f"вызовов модели {c['llm_calls']} (пропущено {c['llm_skipped']})", flush=True)
        print("находки: " + ", ".join(f"{t} {uniq.get(t, 0)} (встреч {seen.get(t, 0)})"
                                      for t in TYPES), flush=True)
        lap = state.get("lap") or {}
        if lap:
            print(f"круг: {lap.get('seconds')} c по {lap.get('nodes')} узлам", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
