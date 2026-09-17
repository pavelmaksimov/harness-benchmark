# -*- coding: utf-8 -*-
"""правило — обслуживание графа: что удалить, что сжать, что оставить целиком.

Правило проекта (2026-09-08): «мост бота пишет максимум, прореживания на
входе нет; обслуживание графа: самое старое и бесполезное удаляется, не особо
полезное сжимается в архивные сводки, свежее целиком».

Модуль — ЧИСТЫЙ слой политики, как `thread` и `gates`: ни файлов, ни сети, ни
стора внутри. На входе — снимки узлов (dict'ы того же вида, что отдаёт Store),
на выходе — план; применяет план сервер. Поэтому `plan()` ничего не мутирует и
годится как готовый `--dry-run с числами`: сколько узлов и байт уйдёт, каких
видов, и упёрлись ли мы в предохранители.

Три исхода на узел:

  protected — не трогаем вообще (вид из `protected_kinds`, входящие рёбра,
              свежесть, непонятный `ts`);
  delete    — самое старое и бесполезное;
  compress  — не особо полезное: узел остаётся, но его содержание
              переезжает в дневную сводку `[ARCHIVE:<slug>]`;
  keep      — всё остальное.

Грамматика дневной сводки — та же, что у недельного дайджеста нити
(`thread.format_digest`), сегменты через « | », ключ до первого «: »:

  [ARCHIVE:<slug>] день: 2026-09-05 | период: <ts>..<ts> | циклов: 12
  | сделал: … | решил: … | итог: …

Пустые списки в строку не пишутся: у дня бота «решил» бывает пусто, и поле
«решил: —» в такой сводке только шумит.

Внешних зависимостей нет; из своих — `mnemos.thread` (единый формат строк
нити) и `mnemos.model` (границы веса).
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from mnemos import thread
from mnemos.model import DEFAULT_HALF_LIFE_HOURS, WEIGHT_MAX, weight_floor

# --------------------------------------------------------------------------- #
# Константы контракта
# --------------------------------------------------------------------------- #
ARCHIVE_TAG = "archive:day"        # тег дневной сводки
ARCHIVED_BY_TAG = "archived_by:"   # префикс: archived_by:<id сводки> на сжатых узлах

DIGEST_KIND = thread.DIGEST_KIND   # вид узла сводки — тот же digest, что у нити
DIGEST_TAG = thread.DIGEST_TAG

KEY_DAY = "день"
KEY_CYCLES = "циклов"
KEY_RESULT = "итог"

BOT_TAG = "source:bot"             # метка цикла бота, если вид узла обычный
CYCLE_KINDS = ("task", "result")   # канал дирижёр→субагент — тоже цикл

# префикс регистронезависим на чтении ([archive:demo] тоже сводка), пишем верхний
_RE_ARCHIVE = re.compile(r"^\[ARCHIVE:([^\]\s]+)\]", re.IGNORECASE)
# любой служебный префикс claim'а: [THREAD:x], [SESSION:x], [ARCHIVE:x]…
_RE_PREFIX = re.compile(r"^\[[A-Za-zА-Яа-я_]+:[^\]\s]+\]\s*")

RECENT_DAYS = 30.0    # окно «свежее обращение» для usage.hits
HITS_FULL = 10.0      # столько обращений дают полный балл за источник (1)
RECENT_FULL = 5.0     # столько свежих обращений дают полный балл
LINKS_FULL = 5.0      # столько входящих рёбер дают полный балл

W_HITS = 0.30         # доли источников в score; в сумме ровно 1.0
W_RECENT = 0.15
W_WEIGHT = 0.35
W_LINKS = 0.20

AGE_UNKNOWN = -1.0    # возраст узла, чей ts не разобрался
LIST_LIMIT = 12       # потолок списка в сводке (как thread._dedup)
ITEMS_LIMIT = 200     # потолок подробностей в плане
CLAIM_CHARS = 80      # обрезка claim'а в строке плана
ESSENCE_CHARS = 120   # обрезка сути цикла в сводке

ACTIONS = ("keep", "compress", "delete", "protected")
_ACTION_ORDER = {"delete": 0, "compress": 1, "keep": 2, "protected": 3}


# --------------------------------------------------------------------------- #
# Мелкие помощники
# --------------------------------------------------------------------------- #
def _parse_ts(value: Any) -> Optional[dt.datetime]:
    """ISO-момент -> aware datetime (UTC). Непонятное -> None."""
    if isinstance(value, dt.datetime):
        return value if value.tzinfo else value.replace(tzinfo=dt.timezone.utc)
    text = str(value or "").strip()
    if not text:
        return None
    try:
        moment = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=dt.timezone.utc)


def _stamp(moment: dt.datetime) -> str:
    """Момент в строку периода: минуты по UTC («2026-09-05T07:00»)."""
    return moment.astimezone(dt.timezone.utc).isoformat(timespec="minutes")[:16]


def _need_now(now: Any, where: str = "archive") -> dt.datetime:
    """«Сейчас» приходит параметром и никогда не берётся из системных часов."""
    moment = _parse_ts(now)
    if moment is None:
        raise ValueError(f"{where}: параметр now (момент времени, ISO или datetime) обязателен")
    return moment


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ("" if value is None else str(value))


def _tags(node: Dict[str, Any]) -> List[str]:
    return [str(t) for t in (node.get("tags") or [])]


def archived_by(digest_id: Any) -> str:
    """Тег «этот узел свёрнут в сводку <id>» — его вешает сервер при сжатии."""
    ident = str(digest_id or "").strip()
    if not ident:
        raise ValueError("archive: параметр digest_id (строка) обязателен")
    return f"{ARCHIVED_BY_TAG}{ident}"


def day_key(ts: Any) -> str:
    """Календарный день момента ПО UTC: «2026-09-05». Непонятный ts -> пустая строка.

    День берётся от разобранного момента, а не от первых десяти символов строки:
    у «2026-09-05T23:00:00-05:00» момент приходится на шестое число по UTC, и
    ведро дня обязано быть тем же, в котором этот узел сравнивается по времени.
    """
    moment = _parse_ts(ts)
    if moment is None:
        return ""
    return moment.astimezone(dt.timezone.utc).date().isoformat()


def is_bot_cycle(node: Dict[str, Any]) -> bool:
    """Цикл бота: узел вида task/result или помеченный source:bot."""
    if not isinstance(node, dict):
        return False
    return str(node.get("kind") or "") in CYCLE_KINDS or BOT_TAG in _tags(node)


# --------------------------------------------------------------------------- #
# Политика обслуживания
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Policy:
    """Пороги обслуживания графа. Замороженная: план не должен менять политику.

    Значения по умолчанию — прямая раскладка исходной формулировки:
    30 дней «свежее целиком», 90 дней «не особо полезное — в сводку»,
    365 дней «самое старое и бесполезное — удалить».
    """

    keep_days: float = 30.0
    compress_days: float = 90.0
    delete_days: float = 365.0
    useful_hits: int = 3
    useful_weight: float = 0.30
    protected_kinds: Tuple[str, ...] = ("rule", "hub", "digest")
    max_delete: int = 100
    max_compress: int = 500

    def validate(self) -> None:
        """Проверка порогов. Нелепая политика — это выкошенная память, поэтому
        ошибки жёсткие и называют поле."""
        for name in ("keep_days", "compress_days", "delete_days"):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"archive: параметр {name} (дни, число) обязателен")
            if float(value) < 0:
                raise ValueError(f"archive: параметр {name} (дни) не может быть отрицательным")
        if not (float(self.keep_days) <= float(self.compress_days) <= float(self.delete_days)):
            raise ValueError(
                "archive: пороги должны идти по возрастанию — "
                f"keep_days ({self.keep_days}) <= compress_days ({self.compress_days}) "
                f"<= delete_days ({self.delete_days})")
        if not isinstance(self.useful_hits, int) or isinstance(self.useful_hits, bool):
            raise ValueError("archive: параметр useful_hits (целое число обращений) обязателен")
        if self.useful_hits < 0:
            raise ValueError("archive: параметр useful_hits (обращения) не может быть отрицательным")
        if not isinstance(self.useful_weight, (int, float)) or isinstance(self.useful_weight, bool):
            raise ValueError("archive: параметр useful_weight (вес 0..1) обязателен")
        if not (0.0 <= float(self.useful_weight) <= 1.0):
            raise ValueError(
                f"archive: параметр useful_weight (вес) должен быть в [0, 1], "
                f"получено {self.useful_weight!r}")
        for name in ("max_delete", "max_compress"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"archive: параметр {name} (целое число узлов) обязателен")
            if value < 0:
                raise ValueError(f"archive: параметр {name} (узлы) не может быть отрицательным")
        if not isinstance(self.protected_kinds, (tuple, list)):
            raise ValueError("archive: параметр protected_kinds (кортеж строк) обязателен")
        for kind in self.protected_kinds:
            if not isinstance(kind, str) or not kind.strip():
                raise ValueError(
                    f"archive: параметр protected_kinds (виды узлов) содержит мусор {kind!r}")

    def as_dict(self) -> Dict[str, Any]:
        """Поля политики для отчёта (protected_kinds — списком, чтобы JSON был честным)."""
        return {
            "keep_days": float(self.keep_days),
            "compress_days": float(self.compress_days),
            "delete_days": float(self.delete_days),
            "useful_hits": int(self.useful_hits),
            "useful_weight": float(self.useful_weight),
            "protected_kinds": [str(k) for k in self.protected_kinds],
            "max_delete": int(self.max_delete),
            "max_compress": int(self.max_compress),
        }


DEFAULT_POLICY = Policy()


def _policy(policy: Optional[Policy]) -> Policy:
    if policy is None:
        return DEFAULT_POLICY
    if not isinstance(policy, Policy):
        raise ValueError("archive: параметр policy (Policy) ожидается объектом политики")
    return policy


# --------------------------------------------------------------------------- #
# Полезность узла
# --------------------------------------------------------------------------- #
def decayed_weight(node: Dict[str, Any], now_dt: dt.datetime) -> float:
    """Вес узла с учётом ЕЩЁ НЕ ПРИМЕНЁННОГО затухания — без мутации узла.

    Повторяет `Store._node_decayed_weight` (mnemos/store.py) и по той же
    причине: поле `weight` меняется только когда кто-то позвал `store.decay`,
    а ранжирование при чтении считает затухание на лету. Если брать сырое
    поле, на графе, где `memory_decay` ни разу не запускали, у всех узлов
    навсегда останется вес 1.0 — и порог полезности не отличит живой узел от
    мёртвого. Это не гипотеза: dry-run на живом графе 2026-09-08 дал 3256
    узлов из 3256 с весом >= 0.30 и, как следствие, ноль кандидатов при любом
    сдвиге «сейчас» вперёд — операция была бы вечным no-op.

    Точка отсчёта — максимум из `last_used` и `decayed_at`: иначе одно и то же
    затухание учитывается дважды (один раз в сохранённом весе, второй поверх).
    """
    raw = min(max(_float(node.get("weight"), WEIGHT_MAX), 0.0), 1.0)
    last = _parse_ts(node.get("last_used"))
    done = _parse_ts(node.get("decayed_at"))
    ref = max([m for m in (last, done) if m is not None], default=None)
    if ref is None or now_dt <= ref or DEFAULT_HALF_LIFE_HOURS <= 0:
        return raw
    hours = (now_dt - ref).total_seconds() / 3600.0
    floor = weight_floor(str(node.get("kind") or "fact"))
    return max(floor, raw * (0.5 ** (hours / DEFAULT_HALF_LIFE_HOURS)))


def usefulness(node: Dict[str, Any], now: Any, incoming: int = 0) -> Dict[str, Any]:
    """Насколько узел пригодился. Три источника, каждый реально есть в схеме.

    (1) обращения — `usage.count` (пишется на каждом поиске, qmem.touch) и
        сколько отметок `usage.hits` попало в последние 30 дней;
    (2) вес — `weight` С УЧЁТОМ ЗАТУХАНИЯ (`decayed_weight`): его поднимает
        `store.reinforce` на подтверждённом `memory_ground`, то есть это след
        «узел пригодился в ответе», и он же тускнеет со временем без
        подкрепления. Берётся именно затухший, а не сырой: сырое поле меняется
        только прогоном `memory_decay`, и без него вес всех узлов навсегда
        остался бы 1.0;
    (3) рёбра — `incoming`: сколько узлов ссылаются на этот. Считать это
        внутри нечего: у нас на руках один узел, счёт приходит снаружи.

    Формула (монотонна по каждому источнику, значение в [0, 1]):

        score = 0.30 * min(1, обращения / 10)
              + 0.15 * min(1, свежих обращений / 5)
              + 0.35 * вес
              + 0.20 * min(1, входящих рёбер / 5)

    Узел без поля `weight` считается тяжёлым (1.0): чего мы не поняли, то не
    удаляем — тот же принцип, что и с неразбираемым `ts`. Узел без `last_used`
    и `decayed_at` затуханию не подлежит по той же причине: точки отсчёта нет.
    """
    now_dt = _need_now(now, "archive.usefulness")
    node = node if isinstance(node, dict) else {}

    usage = node.get("usage")
    usage = usage if isinstance(usage, dict) else {}
    hits_list = [h for h in (usage.get("hits") or []) if h] if isinstance(usage.get("hits"), list) else []
    # count — источник истины, но список отметок мог пережить потерю счётчика
    hits = max(_int(usage.get("count")), len(hits_list))
    edge = now_dt - dt.timedelta(days=RECENT_DAYS)
    recent = 0
    for h in hits_list:
        moment = _parse_ts(h)
        if moment is not None and moment >= edge:
            recent += 1

    weight = decayed_weight(node, now_dt)
    incoming = max(0, _int(incoming))

    hit_part = min(1.0, hits / HITS_FULL)
    recent_part = min(1.0, recent / RECENT_FULL)
    link_part = min(1.0, incoming / LINKS_FULL)
    score = W_HITS * hit_part + W_RECENT * recent_part + W_WEIGHT * weight + W_LINKS * link_part

    reasons = [
        f"обращений: {hits}",
        f"свежих обращений за {RECENT_DAYS:g} дней: {recent}",
        f"вес: {weight:.2f}",
        f"входящих рёбер: {incoming}",
    ]
    return {
        "score": round(min(1.0, max(0.0, score)), 4),
        "hits": hits,
        "recent_hits": recent,
        "weight": round(weight, 4),
        "incoming": incoming,
        "reasons": reasons,
    }


# --------------------------------------------------------------------------- #
# Классификация одного узла
# --------------------------------------------------------------------------- #
def _age_days(node: Dict[str, Any], now_dt: dt.datetime) -> Optional[float]:
    moment = _parse_ts(node.get("ts"))
    if moment is None:
        return None
    return (now_dt - moment).total_seconds() / 86400.0


def _useless(use: Dict[str, Any], pol: Policy) -> bool:
    """Бесполезен = мало обращений И маленький вес. Оба условия сразу: один
    подтверждённый ответ (вес) или один живой поиск (обращения) спасают узел."""
    return int(use["hits"]) < int(pol.useful_hits) and float(use["weight"]) < float(pol.useful_weight)


def _classify(node: Dict[str, Any], now_dt: dt.datetime, pol: Policy,
              incoming: int) -> Dict[str, Any]:
    """Тело classify без повторной проверки политики (её делает вызывающий)."""
    use = usefulness(node, now_dt, incoming)
    kind = str(node.get("kind") or "")

    def out(action: str, reason: str, age: float) -> Dict[str, Any]:
        return {"action": action, "reason": reason, "age_days": round(age, 3), "usefulness": use}

    age = _age_days(node, now_dt)
    if age is None:
        return out("protected", "непонятное время — не трогаем", AGE_UNKNOWN)
    if kind in tuple(pol.protected_kinds):
        return out("protected", f"вид {kind} защищён политикой", age)
    if int(use["incoming"]) > 0:
        return out("protected",
                   f"на узел ссылаются ({use['incoming']} входящих) — битых рёбер быть не должно",
                   age)
    if age <= float(pol.keep_days):
        return out("protected", f"свежее {pol.keep_days:g} дней — оставляем целиком", age)

    useless = _useless(use, pol)
    detail = (f"обращений {use['hits']} при пороге {pol.useful_hits}, "
              f"вес {use['weight']:.2f} при пороге {pol.useful_weight:.2f}")
    # Сжимается только то, для чего сводка физически существует, — цикл бота.
    # Иначе кэп max_compress тратился бы на узлы, которые сервер свернуть не
    # может, реальные кандидаты вытеснялись бы в keep, и операция снова стала
    # бы вечным no-op — тем самым, который однажды уже чинили.
    foldable = is_bot_cycle(node)
    folded = any(str(tag).startswith(ARCHIVED_BY_TAG) for tag in _tags(node))
    if age > float(pol.delete_days) and useless:
        if foldable and not folded:
            # цикл, который ни разу не попал в сводку, удалять нельзя: его
            # содержание не сохранено нигде, а правило обещает сжатие ДО удаления
            return out("compress", f"старше {pol.delete_days:g} дней, но ещё не в сводке "
                                   f"({detail}) — сначала свернуть", age)
        return out("delete", f"старше {pol.delete_days:g} дней и бесполезен ({detail})", age)
    if age > float(pol.compress_days) and useless:
        if not foldable:
            return out("keep", f"старше {pol.compress_days:g} дней и мало нужен ({detail}), "
                               f"но это не цикл бота — автоматической сводки для него нет "
                               f"(ручная свёртка — memory_summarize)", age)
        if folded:
            return out("keep", f"уже свёрнут в сводку дня ({detail})", age)
        return out("compress", f"старше {pol.compress_days:g} дней и мало нужен ({detail}) — в сводку", age)
    if useless:
        return out("keep", f"возраст {age:.1f} дн ещё не дошёл до порога сжатия "
                           f"({pol.compress_days:g} дн)", age)
    return out("keep", f"пригождается (полезность {use['score']:.2f}: {detail})", age)


def classify(node: Dict[str, Any], now: Any, policy: Optional[Policy] = None,
             incoming: int = 0) -> Dict[str, Any]:
    """Что делать с узлом: keep / compress / delete / protected.

    Порядок приоритета (первое сработавшее правило побеждает):

    1. protected — `ts` не разобрался («никогда не удаляем то, чего не поняли»);
       вид из `policy.protected_kinds`; есть входящие рёбра или дети
       (`incoming > 0`, инвариант Store.prune — битых рёбер быть не должно);
       возраст <= `keep_days` («свежее целиком» — исходная формулировка);
    2. delete — возраст > `delete_days` И полезность ниже обоих порогов;
    3. compress — возраст > `compress_days` И полезность ниже обоих порогов;
    4. keep — всё остальное.

    `age_days` = -1.0 (`AGE_UNKNOWN`), если время узла не разобралось.
    """
    if not isinstance(node, dict):
        raise ValueError("archive: параметр node (словарь узла) обязателен")
    pol = _policy(policy)
    pol.validate()
    return _classify(node, _need_now(now, "archive.classify"), pol, _int(incoming))


# --------------------------------------------------------------------------- #
# План обслуживания (dry-run с числами)
# --------------------------------------------------------------------------- #
def _size(node: Dict[str, Any]) -> int:
    """Грубая оценка веса узла в байтах: claim + context в UTF-8.

    Считаем именно байты, а не символы: у кириллического claim'а байт вдвое
    больше, и оценка в символах врала бы ровно вдвое.
    """
    return len(_text(node.get("claim")).encode("utf-8")) + \
        len(_text(node.get("context")).encode("utf-8"))


def plan(nodes: Sequence[Dict[str, Any]], now: Any, policy: Optional[Policy] = None,
         incoming_counts: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """План обслуживания БЕЗ применения: что удалить, что сжать, сколько это байт.

    Ничего не мутирует — ни узлы, ни политику: сервер получает списки id и
    применяет их сам. Это и есть `--dry-run` с числами, которого требует правило.

    Кэпы: кандидаты сортируются от наименее полезных к наиболее (при равной
    полезности первым идёт самый старый) и режутся по `max_delete` /
    `max_compress`. Отброшенные кэпом переходят в `keep` — и в `counts`, и в
    `by_kind`, поэтому сумма `counts` всегда равна `nodes_total`.

    `items` — до 200 строк для человека, самые действенные сверху:
    delete, потом compress, потом keep и protected.
    """
    pol = _policy(policy)
    pol.validate()
    now_dt = _need_now(now, "archive.plan")
    incoming_counts = incoming_counts if isinstance(incoming_counts, dict) else {}

    rows: List[Dict[str, Any]] = []
    for node in nodes or []:
        if not isinstance(node, dict):
            continue    # мусор в списке не узел: молча пропускаем, в числа не берём
        nid = str(node.get("id") or "")
        verdict = _classify(node, now_dt, pol, _int(incoming_counts.get(nid)))
        rows.append({
            "id": nid,
            "action": verdict["action"],
            "reason": verdict["reason"],
            "kind": str(node.get("kind") or ""),
            "age_days": verdict["age_days"],
            "score": verdict["usefulness"]["score"],
            "claim": _text(node.get("claim"))[:CLAIM_CHARS],
            "_size": _size(node),
        })

    def rank(row: Dict[str, Any]) -> Tuple[float, float, str]:
        # наименее полезные первыми; при равной полезности — самые старые
        return (float(row["score"]), -float(row["age_days"]), row["id"])

    capped: Dict[str, bool] = {}
    picked: Dict[str, List[str]] = {}
    for action, limit in (("delete", int(pol.max_delete)), ("compress", int(pol.max_compress))):
        candidates = sorted((r for r in rows if r["action"] == action), key=rank)
        picked[action] = [r["id"] for r in candidates[:limit]]
        capped[action] = len(candidates) > limit
        for row in candidates[limit:]:
            row["action"] = "keep"
            row["reason"] = (f"кандидат на {action}, но упёрлись в предохранитель "
                             f"(max_{action}={limit}) — оставлен до следующего прохода")

    counts = {a: 0 for a in ACTIONS}
    by_kind: Dict[str, Dict[str, int]] = {}
    # Освобождает байты ТОЛЬКО удаление. Сжатие не освобождает ничего: исходник
    # остаётся целиком (меняются вид и теги), а сверху добавляется узел-сводки,
    # то есть стор растёт. Два разных числа под разными именами — потому что
    # пользователь принимает решение «запускать ли чистку» именно по ним.
    bytes_estimate = {"freed_by_delete": 0, "compressed_source": 0}
    size_key = {"delete": "freed_by_delete", "compress": "compressed_source"}
    for row in rows:
        action = row["action"]
        counts[action] += 1
        by_kind.setdefault(row["kind"], {a: 0 for a in ACTIONS})[action] += 1
        if action in size_key:
            bytes_estimate[size_key[action]] += int(row["_size"])

    items = sorted(rows, key=lambda r: (_ACTION_ORDER[r["action"]], float(r["score"]), r["id"]))
    return {
        "policy": pol.as_dict(),
        "now": now_dt.isoformat(),
        "nodes_total": len(rows),
        "counts": counts,
        "by_kind": by_kind,
        "bytes_estimate": bytes_estimate,
        "capped": capped,
        "to_delete": picked["delete"],
        "to_compress": picked["compress"],
        "items": [{k: v for k, v in row.items() if k != "_size"} for row in items[:ITEMS_LIMIT]],
    }


# --------------------------------------------------------------------------- #
# Дневная сводка: строка claim'а
# --------------------------------------------------------------------------- #
def format_day(slug: str, day: Any, cycles: Any, did: Any = None, decided: Any = None,
               result: Any = None, period: Any = None) -> str:
    """[ARCHIVE:<slug>] день: 2026-09-05 | период: <ts>..<ts> | циклов: 12
    | сделал: … | решил: … | итог: …

    Пустой список не печатается вовсе: у дня бота «решил» обычно пусто, и
    поле-прочерк в такой сводке только мешает читать.
    """
    if not thread.is_valid_slug(slug):
        raise ValueError(f"archive: slug {slug!r} — ожидается [A-Za-z0-9._-] без пробелов")
    day_txt = thread._clean(day)
    if not day_txt:
        raise ValueError("archive: параметр day (день YYYY-MM-DD) обязателен")
    parts = [f"{KEY_DAY}{thread.KEY_SEP}{day_txt}"]
    if thread._clean(period):
        parts.append(f"{thread.KEY_PERIOD}{thread.KEY_SEP}{thread._clean(period)}")
    parts.append(f"{KEY_CYCLES}{thread.KEY_SEP}{thread._clean(cycles)}")
    for key, values in ((thread.KEY_DID, did), (thread.KEY_DECIDED, decided), (KEY_RESULT, result)):
        joined = thread._join_list(values)
        if joined != thread.EMPTY_MARK:
            parts.append(f"{key}{thread.KEY_SEP}{joined}")
    return f"[ARCHIVE:{slug}] " + thread.SEP.join(parts)


def parse_day(claim: Any) -> Optional[Dict[str, Any]]:
    """Разбор claim дневной сводки. Не сводка или нет дня -> None."""
    if not isinstance(claim, str):
        return None
    m = _RE_ARCHIVE.match(claim.strip())
    if not m or not thread.is_valid_slug(m.group(1)):
        return None
    fields, _ = thread._split_segments(claim.strip()[m.end():].strip())
    day = fields.get(KEY_DAY)
    if not day:
        return None
    return {
        "slug": m.group(1),
        "day": day,
        "period": fields.get(thread.KEY_PERIOD),
        "cycles": _int(str(fields.get(KEY_CYCLES) or "0").strip()),
        "did": thread._split_list(fields.get(thread.KEY_DID)),
        "decided": thread._split_list(fields.get(thread.KEY_DECIDED)),
        "result": thread._split_list(fields.get(KEY_RESULT)),
    }


# --------------------------------------------------------------------------- #
# Дневная сводка: items для memory_add
# --------------------------------------------------------------------------- #
def _essence(claim: Any, limit: int = ESSENCE_CHARS) -> str:
    """Короткая суть цикла из claim'а — механически, без LLM.

    Берём первый сегмент до « | » (у узлов бота там суть, дальше служебное),
    снимаем служебный префикс вида [TASK:…] и режем по длине.
    """
    head = str(claim or "").split(thread.SEP, 1)[0]
    text = thread._clean_item(_RE_PREFIX.sub("", head).strip())
    if limit and len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


def build_day_items(slug: str, nodes: Any, agent: str, session_id: str, source: str,
                    now: Any = None, older_than_days: float = 1.0,
                    product_tag: Optional[str] = None) -> List[Dict[str, Any]]:
    """Items для memory_add: по одному узлу-сводке на КАЖДЫЙ календарный день
    циклов бота, который уже закончился и ещё не свёрнут.

    Правила ровно те же, что у недельного дайджеста нити
    (`thread.build_digest_items`), только ведро — календарный день `ts`:
      * узел, уже помеченный `archived_by:<id>`, пропускается — он в сводке;
        ключ идемпотентности именно узел, а не день: при ключе-дне любой цикл,
        добравшийся до уже свёрнутого дня, не попал бы в сводку НИКОГДА;
      * день, чей САМЫЙ СВЕЖИЙ узел моложе `older_than_days`, пропускается:
        «живой» день не сворачиваем, иначе сводку пришлось бы переписывать
        после каждого нового цикла;
      * исходные узлы не трогаются — сжатие делает сервер, повесив им
        `archived_by:<id сводки>` по списку `node_ids` элемента.

    Цикл бота — узел вида task/result или помеченный `source:bot`; всё
    остальное в сводку не попадает.
    """
    if not thread.is_valid_slug(slug):
        raise ValueError(f"archive: slug {slug!r} — ожидается [A-Za-z0-9._-] без пробелов")
    if not thread._clean(agent) or not thread._clean(session_id):
        raise ValueError("archive: паспорт agent/session_id обязателен для дневной сводки")
    now_dt = _parse_ts(now) if now is not None else dt.datetime.now(dt.timezone.utc)
    if now_dt is None:
        raise ValueError("archive: параметр now (момент времени, ISO или datetime) не разобрался")
    edge = now_dt - dt.timedelta(days=max(0.0, _float(older_than_days)))

    # момент каждого узла разбираем ОДИН раз и дальше сравниваем моменты, а не
    # ISO-строки: «2026-09-07T10:00-05:00» лексикографически меньше края
    # «2026-09-07T12:00+00:00», хотя наступил позже, — на строках живой день
    # уехал бы в сводку, а закончившийся не свернулся бы никогда.
    by_day: Dict[str, List[Tuple[dt.datetime, Dict[str, Any]]]] = {}
    for node in nodes or []:
        if not isinstance(node, dict) or not is_bot_cycle(node):
            continue
        # узел, уже попавший в сводку, второй раз не сворачивается — это и есть
        # ключ идемпотентности. Ключ-день оставлял бы «опоздавший» цикл уже
        # свёрнутого дня без сводки навсегда, а по возрасту он потом попал бы
        # под удаление: содержание исчезло бы, не сохранившись нигде.
        if any(str(tag).startswith(ARCHIVED_BY_TAG) for tag in _tags(node)):
            continue
        moment = _parse_ts(node.get("ts"))
        if moment is None:
            continue        # непонятное время — узел не в дне, сворачивать нечего
        key = day_key(moment)
        if key:
            by_day.setdefault(key, []).append((moment, node))

    base_tags = [f"thread:{slug}", DIGEST_TAG, ARCHIVE_TAG]
    if product_tag:
        base_tags.append(str(product_tag))

    items: List[Dict[str, Any]] = []
    for key in sorted(by_day):
        pairs = sorted(by_day[key], key=lambda p: p[0])
        if pairs[-1][0] >= edge:
            continue        # день ещё «живой» — не сворачиваем
        day_nodes = [node for _, node in pairs]
        did = thread._dedup([_essence(n.get("claim")) for n in day_nodes
                             if str(n.get("kind") or "") != "result"], LIST_LIMIT)
        result = thread._dedup([_essence(n.get("claim")) for n in day_nodes
                                if str(n.get("kind") or "") == "result"], LIST_LIMIT)
        decided = thread._dedup([_essence(n.get("claim")) for n in day_nodes
                                 if "decision" in _tags(n)], LIST_LIMIT)
        period = f"{_stamp(pairs[0][0])}..{_stamp(pairs[-1][0])}"
        items.append({
            "claim": format_day(slug, key, len(day_nodes), did, decided, result, period=period),
            "kind": DIGEST_KIND,
            "tags": list(base_tags),
            "context": (f"дневная сводка {key} нити {slug}: свёрнуто циклов "
                        f"{len(day_nodes)}, период {period}"),
            "evidence": ([source] if source else []) + [str(n.get("id")) for n in day_nodes],
            # свёрнутые узлы отдельным полем, а не «evidence[1:]»: сервер вешает
            # на них archived_by и ребро has_part, и выводить их из позиции в
            # evidence значило бы держать неявный контракт на порядке списка
            "node_ids": [str(n.get("id")) for n in day_nodes],
            "source": source,
            "agent": agent,
            "session_id": session_id,
        })
    return items
