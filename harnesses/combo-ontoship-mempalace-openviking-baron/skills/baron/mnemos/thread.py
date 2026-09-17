# -*- coding: utf-8 -*-
"""Нить проекта: голова, записи сессий, хвосты.

Контракт: docs/product/THREAD.md (схема SCHEMA_VERSION). Любой дирижёр одним
memory_checkpoint(query="[THREAD:<slug>]") получает, где проект, последний и
следующий шаг, открытые правила проекта, свежие сессии и хвосты, а одним
memory_add(items=[голова, сессия, хвосты…]) в конце сессии обновляет нить.

Грамматика claim'ов (сегменты разделены « | », ключ — до ПЕРВОГО «: »
внутри сегмента, поэтому значения могут содержать «: » свободно):

  голова   [THREAD:<slug>] [фаза: …] | последний шаг: … | следующий шаг: …
           [| ждут ответа: …] [| <другие ключи>: …] | обновлено: <дата> <agent>/<session_id>
  сессия   [SESSION:<slug>] <дата> <agent>/<session_id> | сделал: a; b | решил: …
           | хвосты: … | следующий шаг: …            (списки через «; », пусто — «—»)
  хвост    [TAIL:<slug>] <текст> | открыт: <дата> <agent>/<session_id>

Всё чистые функции над dict'ами узлов; thread_view ходит в стор только через
публичные методы (find_by_tags). Внешних зависимостей нет.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from . import sandbox

SCHEMA_VERSION = 1

SEP = " | "
KEY_SEP = ": "
LIST_SEP = "; "
EMPTY_MARK = "—"

KEY_PHASE = "фаза"
KEY_LAST = "последний шаг"
KEY_NEXT = "следующий шаг"
KEY_OPEN = "ждут ответа"
KEY_OPEN_ALT = "открытые решения"
KEY_UPDATED = "обновлено"
KEY_DID = "сделал"
KEY_DECIDED = "решил"
KEY_TAILS = "хвосты"
KEY_OPENED = "открыт"
KEY_WEEK = "неделя"
KEY_SESSIONS = "сессий"
KEY_AGENTS = "дирижёры"
KEY_PERIOD = "период"

DIGEST_KIND = "digest"          # вид узла-дайджеста; в KINDS модели с 2026-09-08
DIGEST_TAG = "digest"
DIGEST_DAYS = 7                 # «раз в неделю»: сворачиваются сессии старше стольких дней
TAIL_TTL_HOURS = 720           # хвост живёт 30 дней с момента записи

ACTIVE_MINUTES = 90             # окно «сессия ещё открыта», минут с последнего обращения

HEAD_KEYS = (KEY_PHASE, KEY_LAST, KEY_NEXT, KEY_OPEN, KEY_OPEN_ALT, KEY_UPDATED)
# Ключи, которые format_head пишет из именованных аргументов; «открытые решения»
# сюда не входит: если в claim были ОБА синонима, второй живёт в extra и
# переживает round-trip (раньше терялся).
_HEAD_FIXED_KEYS = (KEY_PHASE, KEY_LAST, KEY_NEXT, KEY_OPEN, KEY_UPDATED)
SESSION_KEYS = (KEY_DID, KEY_DECIDED, KEY_TAILS, KEY_NEXT)
DIGEST_KEYS = (KEY_PERIOD, KEY_SESSIONS, KEY_AGENTS, KEY_DID, KEY_DECIDED, KEY_TAILS)

HEAD_FORMAT_HINT = (
    "[THREAD:<slug>] последний шаг: … | следующий шаг: … "
    "[| ждут ответа: …] | обновлено: <дата> <agent>/<session_id>"
)

_RE_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*$")
# префиксы регистронезависимы ([thread:demo] тоже голова); format_* пишут верхний регистр
_RE_HEAD = re.compile(r"^\[THREAD:([^\]\s]+)\]", re.IGNORECASE)
_RE_SESSION = re.compile(r"^\[SESSION:([^\]\s]+)\]", re.IGNORECASE)
_RE_TAIL = re.compile(r"^\[TAIL:([^\]\s]+)\]", re.IGNORECASE)
_RE_DIGEST = re.compile(r"^\[DIGEST:([^\]\s]+)\]", re.IGNORECASE)
_RE_UPDATED = re.compile(r"^(\S+)\s+([^/\s]+)/(\S+)$")
_RE_OD = re.compile(r"\bOD-\d+\b")

# Потолок поля в компактной строке checkpoint (полный claim головы всё равно
# лежит в facts[0]); при 0 — без обрезки.
SUMMARY_FIELD_CHARS = 400


def is_valid_slug(slug: Any) -> bool:
    """slug нити: латиница/цифры/._- без пробелов (идёт в тег thread:<slug>)."""
    return isinstance(slug, str) and bool(_RE_SLUG.match(slug))


def slug_from_query(query: Any) -> Optional[str]:
    """«[THREAD:<slug>] …» в начале запроса -> slug, иначе None."""
    if not isinstance(query, str):
        return None
    m = _RE_HEAD.match(query.strip())
    if not m or not is_valid_slug(m.group(1)):
        return None
    return m.group(1)


def is_head_claim(claim: Any) -> bool:
    """Claim начинается с «[THREAD:<slug>]» — префикс зарезервирован за головой:
    такой элемент memory_add считает головой даже без тега thread_head (иначе
    узел-двойник заставил бы Г4 отвергнуть настоящую голову как дубликат)."""
    return slug_from_query(claim) is not None


def slug_from_tags(tags: Any) -> Optional[str]:
    """Первый тег thread:<slug> -> slug (None, если тега нет)."""
    for t in tags or []:
        t = str(t)
        if t.startswith("thread:") and is_valid_slug(t[7:]):
            return t[7:]
    return None


def _clean(value: Any) -> str:
    """Значение поля: одна строка, без разделителя сегментов внутри."""
    text = " ".join(str(value if value is not None else "").split())
    return text.replace(SEP, " / ")


def _clean_item(value: Any) -> str:
    """Элемент списка: дополнительно без разделителя списка внутри."""
    return _clean(value).replace(LIST_SEP, ", ")


def _split_segments(body: str) -> Tuple[Dict[str, str], List[str]]:
    """Сегменты « | » -> {ключ: значение} (ключ до первого «: ») + сегменты без ключа."""
    fields: Dict[str, str] = {}
    unkeyed: List[str] = []
    for seg in body.split(SEP):
        seg = seg.strip()
        if not seg:
            continue
        if KEY_SEP in seg:
            key, value = seg.split(KEY_SEP, 1)
            key = key.strip().lower()
            if key and key not in fields:
                # значение нормализуется как при сборке (пробелы/переводы строк
                # схлопываются): parse(format(parse(x))) == parse(x)
                fields[key] = _clean(value)
                continue
        unkeyed.append(_clean(seg))
    return fields, unkeyed


def parse_passport(text: Any) -> Dict[str, Optional[str]]:
    """«<дата> <agent>/<session_id>» -> {date, agent, session_id}; не разобралось — raw."""
    raw = _clean(text)
    m = _RE_UPDATED.match(raw)
    if not m:
        return {"date": None, "agent": None, "session_id": None, "raw": raw}
    return {"date": m.group(1), "agent": m.group(2), "session_id": m.group(3)}


def format_passport(date: Any, agent: Any, session_id: Any) -> str:
    return f"{_clean(date)} {_clean(agent)}/{_clean(session_id)}"


def _split_list(value: Any) -> List[str]:
    text = _clean(value)
    if not text or text == EMPTY_MARK:
        return []
    return [p.strip() for p in text.split(LIST_SEP) if p.strip()]


def _join_list(items: Any) -> str:
    if isinstance(items, str):
        items = [items]
    cleaned = [_clean_item(i) for i in (items or []) if _clean_item(i)]
    return LIST_SEP.join(cleaned) if cleaned else EMPTY_MARK


def open_decision_ids(text: Any) -> List[str]:
    """OD-N из текста «ждут ответа» (порядок появления, без повторов)."""
    out: List[str] = []
    for m in _RE_OD.findall(str(text or "")):
        if m not in out:
            out.append(m)
    return out


# -- голова -------------------------------------------------------------------

def parse_head(claim: Any) -> Optional[Dict[str, Any]]:
    """Claim головы -> dict или None, если это не голова.

    Голова = префикс [THREAD:<slug>] и оба обязательных поля «последний шаг»
    и «следующий шаг». Неизвестные ключи сохраняются в extra (round-trip).
    """
    if not isinstance(claim, str):
        return None
    text = claim.strip()
    m = _RE_HEAD.match(text)
    if not m or not is_valid_slug(m.group(1)):
        return None
    fields, unkeyed = _split_segments(text[m.end():])
    last_step = fields.pop(KEY_LAST, None)
    next_step = fields.pop(KEY_NEXT, None)
    if not last_step or not next_step:
        return None
    open_key = KEY_OPEN if KEY_OPEN in fields else (KEY_OPEN_ALT if KEY_OPEN_ALT in fields else None)
    open_decisions = fields.pop(open_key) if open_key else None
    phase = fields.pop(KEY_PHASE, None)
    updated_raw = fields.pop(KEY_UPDATED, None)
    updated = parse_passport(updated_raw) if updated_raw is not None else None
    extra: Dict[str, Any] = dict(fields)
    if unkeyed:
        extra["_unkeyed"] = unkeyed
    return {
        "slug": m.group(1),
        "last_step": last_step,
        "next_step": next_step,
        "open_decisions": open_decisions,
        "open_decision_ids": open_decision_ids(open_decisions),
        "phase": phase,
        "updated": updated,
        "extra": extra,
    }


def format_head(slug: str, last_step: Any, next_step: Any, updated: Any,
                open_decisions: Any = None, phase: Any = None,
                extra: Optional[Dict[str, Any]] = None) -> str:
    """Обратная parse_head. updated — dict {date, agent, session_id} или строка «<дата> <agent>/<sid>».

    Порядок сегментов фиксирован: [фаза] | последний шаг | следующий шаг |
    [ждут ответа] | [extra…] | обновлено. Пустые необязательные поля опускаются.
    """
    if not is_valid_slug(slug):
        raise ValueError(f"thread: slug {slug!r} — expected [A-Za-z0-9._-] with no spaces")
    if not _clean(last_step) or not _clean(next_step):
        raise ValueError("thread: a head must carry \u00abпоследний шаг\u00bb and \u00abследующий шаг\u00bb (last step / next step)")
    parts: List[str] = []
    if _clean(phase):
        parts.append(f"{KEY_PHASE}{KEY_SEP}{_clean(phase)}")
    parts.append(f"{KEY_LAST}{KEY_SEP}{_clean(last_step)}")
    parts.append(f"{KEY_NEXT}{KEY_SEP}{_clean(next_step)}")
    if _clean(open_decisions):
        parts.append(f"{KEY_OPEN}{KEY_SEP}{_clean(open_decisions)}")
    for key, value in (extra or {}).items():
        if str(key).startswith("_") or str(key).lower() in _HEAD_FIXED_KEYS:
            continue
        if _clean(value):
            parts.append(f"{_clean(key)}{KEY_SEP}{_clean(value)}")
    for seg in (extra or {}).get("_unkeyed") or []:
        if _clean(seg):
            parts.append(_clean(seg))
    if isinstance(updated, dict):
        if updated.get("raw") and not updated.get("agent"):
            upd = _clean(updated["raw"])
        else:
            upd = format_passport(updated.get("date"), updated.get("agent"), updated.get("session_id"))
    else:
        upd = _clean(updated)
    if not upd.strip():
        raise ValueError("thread: a head must carry the passport \u00abобновлено: <date> <agent>/<session_id>\u00bb")
    parts.append(f"{KEY_UPDATED}{KEY_SEP}{upd}")
    return f"[THREAD:{slug}] " + SEP.join(parts)


# -- запись сессии ------------------------------------------------------------

def parse_session(claim: Any) -> Optional[Dict[str, Any]]:
    """Claim записи сессии -> dict или None, если это не запись сессии."""
    if not isinstance(claim, str):
        return None
    text = claim.strip()
    m = _RE_SESSION.match(text)
    if not m or not is_valid_slug(m.group(1)):
        return None
    fields, unkeyed = _split_segments(text[m.end():])
    passport = parse_passport(unkeyed.pop(0)) if unkeyed else parse_passport("")
    out = {
        "slug": m.group(1),
        "date": passport.get("date"),
        "agent": passport.get("agent"),
        "session_id": passport.get("session_id"),
        "did": _split_list(fields.pop(KEY_DID, "")),
        "decided": _split_list(fields.pop(KEY_DECIDED, "")),
        "tails": _split_list(fields.pop(KEY_TAILS, "")),
        "next_step": fields.pop(KEY_NEXT, None),
        "extra": dict(fields),
    }
    if unkeyed:
        out["extra"]["_unkeyed"] = unkeyed
    return out


def format_session(slug: str, date: Any, agent: Any, session_id: Any,
                   did: Any = None, decided: Any = None, tails: Any = None,
                   next_step: Any = None, extra: Optional[Dict[str, Any]] = None) -> str:
    """Обратная parse_session."""
    if not is_valid_slug(slug):
        raise ValueError(f"thread: slug {slug!r} — expected [A-Za-z0-9._-] with no spaces")
    if not _clean(date) or not _clean(agent) or not _clean(session_id):
        raise ValueError("thread: a session entry must carry the passport <date> <agent>/<session_id>")
    parts = [
        format_passport(date, agent, session_id),
        f"{KEY_DID}{KEY_SEP}{_join_list(did)}",
        f"{KEY_DECIDED}{KEY_SEP}{_join_list(decided)}",
        f"{KEY_TAILS}{KEY_SEP}{_join_list(tails)}",
        f"{KEY_NEXT}{KEY_SEP}{_clean(next_step) or EMPTY_MARK}",
    ]
    for key, value in (extra or {}).items():
        if str(key).startswith("_") or str(key).lower() in SESSION_KEYS:
            continue
        if _clean(value):
            parts.append(f"{_clean(key)}{KEY_SEP}{_clean(value)}")
    return f"[SESSION:{slug}] " + SEP.join(parts)


# -- хвост --------------------------------------------------------------------

def parse_tail(claim: Any) -> Optional[Dict[str, Any]]:
    """Claim хвоста -> {slug, text, opened{date, agent, session_id}} или None."""
    if not isinstance(claim, str):
        return None
    text = claim.strip()
    m = _RE_TAIL.match(text)
    if not m or not is_valid_slug(m.group(1)):
        return None
    fields, unkeyed = _split_segments(text[m.end():])
    opened = fields.pop(KEY_OPENED, None)
    return {
        "slug": m.group(1),
        "text": unkeyed[0] if unkeyed else "",
        "opened": parse_passport(opened) if opened is not None else None,
        "extra": dict(fields),
    }


def format_tail(slug: str, text: Any, date: Any, agent: Any, session_id: Any) -> str:
    if not is_valid_slug(slug):
        raise ValueError(f"thread: slug {slug!r} — expected [A-Za-z0-9._-] with no spaces")
    body = _clean(text)
    if not body:
        raise ValueError("thread: the tail text is empty")
    return (f"[TAIL:{slug}] {body}{SEP}{KEY_OPENED}{KEY_SEP}"
            f"{format_passport(date, agent, session_id)}")


# -- items для memory_add в конце сессии ---------------------------------------

def build_session_items(slug: str, agent: str, session_id: str, date: str,
                        did: Any, decided: Any, tails: Any, next_step: Any,
                        source: str, last_step: Any = None,
                        open_decisions: Any = None, phase: Any = None,
                        product_tag: Optional[str] = None) -> List[Dict[str, Any]]:
    """Список items для ОДНОГО memory_add(items=…) в конце сессии.

    [0] голова (kind=rule, теги thread:<slug>, thread_head [+product_tag]) —
        сервер перепишет существующую голову (rewrite), а не создаст вторую;
    [1] запись сессии (kind=fact, теги thread:<slug>, session, agent:<agent>);
    [2:] новые хвосты (kind=hypothesis, теги thread:<slug>, tail, open).
    Записи сессий и голова не имеют TTL. Хвосты живут 720 ч и
    продлеваются при упоминании в checkpoint.
    last_step по умолчанию — «сделал» через «; ».
    """
    if not is_valid_slug(slug):
        raise ValueError(f"thread: slug {slug!r} — expected [A-Za-z0-9._-] with no spaces")
    if not _clean(agent) or not _clean(session_id):
        raise ValueError("the agent/session_id passport is required for thread nodes")
    if isinstance(did, str):
        did = [did]
    if isinstance(tails, str):
        tails = [tails]
    did = list(did or [])
    tails = list(tails or [])
    if last_step is None:
        last_step = LIST_SEP.join(_clean_item(d) for d in did if _clean_item(d)) or EMPTY_MARK
    base_tags = [f"thread:{slug}"]
    if product_tag:
        base_tags.append(str(product_tag))
    passport = {"agent": agent, "session_id": session_id, "source": source}
    context = f"сессия {session_id}, агент {agent}, {date}"
    items: List[Dict[str, Any]] = [
        {
            "claim": format_head(slug, last_step, next_step,
                                 {"date": date, "agent": agent, "session_id": session_id},
                                 open_decisions=open_decisions, phase=phase),
            "kind": "rule",
            "tags": base_tags + ["thread_head"],
            "context": context,
            "evidence": [source] if source else [],
            **passport,
        },
        {
            "claim": format_session(slug, date, agent, session_id, did, decided, tails, next_step),
            "kind": "fact",
            "tags": base_tags + ["session", f"agent:{agent}"],
            "context": context,
            "evidence": [source] if source else [],
            **passport,
        },
    ]
    for tail in tails:
        if not _clean(tail):
            continue
        items.append({
            "claim": format_tail(slug, tail, date, agent, session_id),
            "kind": "hypothesis",
            "tags": base_tags + ["tail", "open"],
            "context": context,
            "ttl_hours": TAIL_TTL_HOURS,
            **passport,
        })
    return items


# -- одновременные дирижёры -------------------------------------

def _parse_ts(value: Any):
    """ISO-момент журнала -> aware datetime (UTC). Непонятное -> None."""
    import datetime as _dt
    if isinstance(value, _dt.datetime):
        return value if value.tzinfo else value.replace(tzinfo=_dt.timezone.utc)
    text = str(value or "").strip()
    if not text:
        return None
    try:
        dt = _dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=_dt.timezone.utc)


def active_sessions(pre_passes: Any, slug: str, closed_session_ids: Any = (),
                    now: Any = None, session_id: Any = None,
                    minutes: float = ACTIVE_MINUTES) -> List[Dict[str, Any]]:
    """Сессии на нити <slug>, которые сейчас открыты.

    Открыта = в журнале есть `prepare` по этой нити, записи `[SESSION:<slug>]` с этим
    `session_id` ещё нет (сессия не завершена), а последнее обращение — не старше
    `minutes` минут. Своя сессия (`session_id`) в список не попадает.

    Ничего не блокируется: это подсказка «ты здесь не один», по которой дирижёры сами
    разводят работу по границам, а голова при закрытии сливает «следующий шаг» обоих.
    """
    import datetime as _dt
    now_dt = _parse_ts(now) or _dt.datetime.now(_dt.timezone.utc)
    edge = now_dt - _dt.timedelta(minutes=max(0.0, float(minutes)))
    closed = {str(x) for x in (closed_session_ids or [])}
    mine = str(session_id or "")
    by_session: Dict[str, Dict[str, Any]] = {}
    for rec in pre_passes or []:
        if not isinstance(rec, dict) or rec.get("event") != "prepare":
            continue
        sid = str(rec.get("session_id") or "")
        if not sid or sid == mine or sid in closed:
            continue
        # нить: явное поле журнала (пишется с 2026-09-08) или префикс [THREAD:<slug>] в query
        if str(rec.get("thread") or "") != slug and slug_from_query(rec.get("query")) != slug:
            continue
        ts = _parse_ts(rec.get("ts"))
        if ts is None:
            continue
        cur = by_session.get(sid)
        if cur is None:
            by_session[sid] = {"session_id": sid, "agent": str(rec.get("agent") or "") or None,
                               "since": rec.get("ts"), "last_seen": rec.get("ts"),
                               "passes": 1, "_since_dt": ts, "_last_dt": ts}
            continue
        cur["passes"] += 1
        if ts < cur["_since_dt"]:
            cur["_since_dt"], cur["since"] = ts, rec.get("ts")
        if ts > cur["_last_dt"]:
            cur["_last_dt"], cur["last_seen"] = ts, rec.get("ts")
            if rec.get("agent"):
                cur["agent"] = str(rec["agent"])
    out = []
    for item in by_session.values():
        if item["_last_dt"] < edge:
            continue
        idle = (now_dt - item["_last_dt"]).total_seconds() / 60.0
        out.append({"session_id": item["session_id"], "agent": item["agent"],
                    "since": item["since"], "last_seen": item["last_seen"],
                    "passes": item["passes"], "idle_min": round(max(0.0, idle), 1),
                    "open_min": round(max(0.0, (now_dt - item["_since_dt"]).total_seconds() / 60.0), 1)})
    out.sort(key=lambda x: str(x.get("last_seen") or ""), reverse=True)
    return out


def format_active(active: Any) -> str:
    """«активны сессии: codex-conductor/<sid> с 2026-09-08T10:12 (открыта 34 мин)». Пусто — «»."""
    items = list(active or [])
    if not items:
        return ""
    bits = []
    for a in items[:3]:
        since = str(a.get("since") or "")[:16].replace("T", " ")
        bits.append(f"{a.get('agent') or '?'}/{a.get('session_id')} с {since} "
                    f"(открыта {a.get('open_min')} мин)")
    tail = f" (+{len(items) - 3})" if len(items) > 3 else ""
    return f"активные сессии{KEY_SEP}{len(items)} — " + LIST_SEP.join(bits) + tail


# -- недельный дайджест сессий -----------------------------------

def week_key(ts: Any) -> str:
    """ISO-неделя момента: «2026-W36». Пустой/непонятный ts -> пустая строка."""
    text = str(ts or "")[:10]
    try:
        import datetime as _dt
        y, w, _ = _dt.date.fromisoformat(text).isocalendar()
    except (ValueError, TypeError):
        return ""
    return f"{y}-W{w:02d}"


def format_digest(slug: str, week: Any, sessions_count: Any, agents: Any, did: Any,
                  decided: Any, tails: Any, period: Any = None) -> str:
    """[DIGEST:<slug>] неделя: 2026-W36 | период: 2026-09-01..2026-09-07 | сессий: 5
    | дирижёры: a, b | сделал: … | решил: … | хвосты: …"""
    if not is_valid_slug(slug):
        raise ValueError(f"thread: slug {slug!r} — expected [A-Za-z0-9._-] with no spaces")
    parts = [f"[DIGEST:{slug}]", f"{KEY_WEEK}{KEY_SEP}{_clean(week)}"]
    if period:
        parts.append(f"{KEY_PERIOD}{KEY_SEP}{_clean(period)}")
    parts.append(f"{KEY_SESSIONS}{KEY_SEP}{_clean(sessions_count)}")
    parts.append(f"{KEY_AGENTS}{KEY_SEP}{_join_list(agents)}")
    parts.append(f"{KEY_DID}{KEY_SEP}{_join_list(did)}")
    parts.append(f"{KEY_DECIDED}{KEY_SEP}{_join_list(decided)}")
    parts.append(f"{KEY_TAILS}{KEY_SEP}{_join_list(tails)}")
    return parts[0] + " " + SEP.join(parts[1:])


def parse_digest(claim: Any) -> Optional[Dict[str, Any]]:
    """Разбор claim дайджеста. Не дайджест или нет недели -> None."""
    if not isinstance(claim, str):
        return None
    m = _RE_DIGEST.match(claim.strip())
    if not m or not is_valid_slug(m.group(1)):
        return None
    fields, _ = _split_segments(claim.strip()[m.end():].strip())
    week = fields.get(KEY_WEEK)
    if not week:
        return None
    try:
        count = int(str(fields.get(KEY_SESSIONS) or "0").strip())
    except ValueError:
        count = 0
    return {
        "slug": m.group(1), "week": week, "period": fields.get(KEY_PERIOD),
        "sessions_count": count,
        "agents": _split_list(fields.get(KEY_AGENTS)),
        "did": _split_list(fields.get(KEY_DID)),
        "decided": _split_list(fields.get(KEY_DECIDED)),
        "tails": _split_list(fields.get(KEY_TAILS)),
    }


def _dedup(items: Any, limit: int = 12) -> List[str]:
    """Список без повторов (первое вхождение выигрывает), не длиннее limit."""
    out: List[str] = []
    for it in items or []:
        text = _clean_item(it)
        if text and text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def build_digest_items(slug: str, session_nodes: Any, agent: str, session_id: str,
                       source: str, now: Any = None, older_than_days: int = DIGEST_DAYS,
                       existing_weeks: Any = None, product_tag: Optional[str] = None) -> List[Dict[str, Any]]:
    """Items для memory_add: по одному узлу-дайджесту на КАЖДУЮ неделю, у которой все
    записи сессий старше `older_than_days` дней и дайджеста ещё нет.

    Исходные записи сессий не трогаются: без TTL, не удаляются и не помечаются
    outdated — checkpoint просто показывает вместо них дайджест за пределами глубины
    правило (3 сессии). Неделя, в которой есть хоть одна свежая сессия, не сворачивается:
    иначе дайджест пришлось бы переписывать при каждой новой записи той же недели.
    """
    if not is_valid_slug(slug):
        raise ValueError(f"thread: slug {slug!r} — expected [A-Za-z0-9._-] with no spaces")
    if not _clean(agent) or not _clean(session_id):
        raise ValueError("the agent/session_id passport is required for thread nodes")
    import datetime as _dt
    if now is None:
        now_dt = _dt.datetime.now(_dt.timezone.utc)
    elif isinstance(now, str):
        now_dt = _dt.datetime.fromisoformat(now.replace("Z", "+00:00"))
    else:
        now_dt = now
    edge = (now_dt - _dt.timedelta(days=max(0, int(older_than_days)))).isoformat()
    have = {str(w) for w in (existing_weeks or [])}

    by_week: Dict[str, List[Dict[str, Any]]] = {}
    for node in session_nodes or []:
        wk = week_key(_ts(node))
        if wk:
            by_week.setdefault(wk, []).append(node)

    base_tags = [f"thread:{slug}", DIGEST_TAG]
    if product_tag:
        base_tags.append(str(product_tag))
    items: List[Dict[str, Any]] = []
    for wk in sorted(by_week):
        if wk in have:
            continue
        nodes = sorted(by_week[wk], key=_ts)
        if _ts(nodes[-1]) >= edge:      # неделя ещё «живая» — не сворачиваем
            continue
        entries = [_session_entry(n) for n in nodes]
        agents = _dedup([e.get("agent") for e in entries])
        did = _dedup([d for e in entries for d in (e.get("did") or [])])
        decided = _dedup([d for e in entries for d in (e.get("decided") or [])])
        tails = _dedup([t for e in entries for t in (e.get("tails") or [])])
        period = f"{_ts(nodes[0])[:10]}..{_ts(nodes[-1])[:10]}"
        items.append({
            "claim": format_digest(slug, wk, len(nodes), agents, did, decided, tails, period=period),
            "kind": DIGEST_KIND,
            "tags": list(base_tags),
            "context": f"недельный дайджест {wk} нити {slug}: {len(nodes)} сессий, {period}",
            "evidence": ([source] if source else []) + [str(n.get("id")) for n in nodes],
            "agent": agent, "session_id": session_id, "source": source,
        })
    return items


# -- вид нити для checkpoint ---------------------------------------------------

def _ts(d: Dict[str, Any]) -> str:
    return str(d.get("ts") or "")


def rank_heads(heads: Any) -> List[Dict[str, Any]]:
    """Порядок кандидатов в голову: сначала настоящие (claim парсится и
    kind=rule), внутри группы — свежие по ts первыми. Узел, которому тег
    thread_head достался по ошибке (бывший хвост), не должен обгонять голову."""
    def key(n: Dict[str, Any]) -> Tuple[int, int, str]:
        return (1 if parse_head(n.get("claim")) else 0,
                1 if n.get("kind") == "rule" else 0,
                _ts(n))
    return sorted(heads, key=key, reverse=True)


def _head_entry(node: Dict[str, Any]) -> Dict[str, Any]:
    parsed = parse_head(node.get("claim")) or {}
    return {
        "id": node.get("id"),
        "claim": node.get("claim"),
        "parsed": bool(parsed),
        "last_step": parsed.get("last_step"),
        "next_step": parsed.get("next_step"),
        "open_decisions": parsed.get("open_decisions"),
        "open_decision_ids": parsed.get("open_decision_ids") or [],
        "phase": parsed.get("phase"),
        "updated": parsed.get("updated"),
        "ts": node.get("ts"),
        "weight": node.get("weight"),
        "agent": node.get("agent") or None,
        "session_id": node.get("session_id") or None,
        "revisions": len(node.get("revisions") or []),
        "active": True,
    }


def _session_entry(node: Dict[str, Any]) -> Dict[str, Any]:
    parsed = parse_session(node.get("claim"))
    if parsed is None:
        # запись сессии без формата: показываем как есть, не теряем
        return {
            "id": node.get("id"), "ts": node.get("ts"),
            "agent": node.get("agent") or None, "session_id": node.get("session_id") or None,
            "date": _ts(node)[:10] or None, "did": [str(node.get("claim") or "")],
            "decided": [], "tails": [], "next_step": None, "parsed": False,
        }
    return {
        "id": node.get("id"), "ts": node.get("ts"),
        "agent": node.get("agent") or parsed.get("agent"),
        "session_id": node.get("session_id") or parsed.get("session_id"),
        "date": parsed.get("date") or _ts(node)[:10] or None,
        "did": parsed["did"], "decided": parsed["decided"], "tails": parsed["tails"],
        "next_step": parsed.get("next_step"), "parsed": True,
    }


def _node_agent(node: Dict[str, Any]) -> str:
    """Имя дирижёра узла: поле agent, иначе паспорт из claim записи сессии."""
    agent = str(node.get("agent") or "").strip()
    if agent:
        return agent
    parsed = parse_session(node.get("claim")) or {}
    return str(parsed.get("agent") or "").strip()


def _same_agent(a: Any, b: Any) -> bool:
    return bool(a) and bool(b) and str(a).strip().lower() == str(b).strip().lower()


def _request_targets(node: Dict[str, Any]) -> List[str]:
    """Адресаты узла-запроса: теги request:<кому>."""
    out = []
    for t in node.get("tags") or []:
        t = str(t)
        if t.startswith("request:") and t[8:] and t[8:] not in out:
            out.append(t[8:])
    return out


def _brief(node: Dict[str, Any], limit: int = 200) -> Dict[str, Any]:
    return {"id": node.get("id"), "claim": _short(node.get("claim"), limit),
            "ts": node.get("ts"), "agent": _node_agent(node) or None}


def _last_revision_ts(node: Dict[str, Any]) -> str:
    """ts последней ревизии узла (memory_rewrite). Пусто, если узел не переписывали.

    Нужен для хвостов: закрытие хвоста — это rewrite (kind=fact, +closed, −open), при котором
    `session_id` узла остаётся от того, кто хвост ОТКРЫЛ. Без ревизии закрытие своего старого
    хвоста чужими руками было бы не видно.
    """
    revs = node.get("revisions") or []
    return str((revs[-1] or {}).get("ts") or "") if revs else ""


def changes_since_last(nodes: Any, agent: Any, session_id: Any = None,
                       head_node: Optional[Dict[str, Any]] = None,
                       is_session: Any = None) -> Dict[str, Any]:
    """T2.7 — дельта нити с последней записи сессии дирижёра `agent`.

    Опорная точка — самая свежая запись сессии этого же дирижёра, кроме текущей
    сессии (`session_id`). Всё, что записано ПОЗЖЕ неё, — это то, чего дирижёр
    ещё не видел: записи других дирижёров, новые решения, открытые и закрытые
    хвосты, запросы `request:*`, обновление головы.

    Узлы той самой опорной сессии (тот же `session_id`) и текущей сессии в
    дельту не попадают: дирижёр писал их сам.

    `agent` не назван (клиент не передал) → `{"since": null, "reason": …}`:
    сравнивать не с чем, и выдумывать «изменилось всё» нельзя.
    """
    is_session = is_session or (lambda n: "session" in (n.get("tags") or []))
    nodes = list(nodes or [])
    empty = {"since": None, "sessions": [], "decisions": [], "tails_opened": [],
             "tails_closed": [], "requests": [], "head_updated": None,
             "counts": {"sessions": 0, "decisions": 0, "tails_opened": 0,
                        "tails_closed": 0, "requests": 0}}
    if not agent:
        return {**empty, "reason": "agent не передан — не с чем сравнивать"}

    mine = sorted((n for n in nodes
                   if is_session(n) and _same_agent(_node_agent(n), agent)
                   and not (session_id and _same_agent(n.get("session_id"), session_id))),
                  key=_ts, reverse=True)
    if not mine:
        return {**empty, "reason": f"первая сессия дирижёра {agent} в этой нити"}

    base = mine[0]
    cutoff = _ts(base)
    skip_sessions = {str(base.get("session_id") or "")} | ({str(session_id)} if session_id else set())
    skip_sessions.discard("")

    def is_new(n: Dict[str, Any]) -> bool:
        """Строго позже опорной записи и не из своих сессий (опорной и текущей).

        Исключение — узел, переписанный после опорной записи: закрытие хвоста не меняет
        `session_id`, поэтому по нему свой старый хвост, закрытый позже, остался бы невидимым.
        Автор rewrite неизвестен (memory_rewrite паспорта не несёт), поэтому такой узел
        показывается по ВРЕМЕНИ правки, а не по автору.
        """
        if _ts(n) <= cutoff:
            return False
        return (str(n.get("session_id") or "") not in skip_sessions
                or _last_revision_ts(n) > cutoff)

    def has(n: Dict[str, Any], t: str) -> bool:
        return t in (n.get("tags") or [])

    fresh = sorted((n for n in nodes if is_new(n)), key=_ts, reverse=True)
    head_id = (head_node or {}).get("id")

    sessions_new = [{**_session_entry(n), "by_other": not _same_agent(_node_agent(n), agent)}
                    for n in fresh if is_session(n) and n.get("id") != head_id]
    # Решения бывают отдельным узлом с тегом decision И строкой «решил: …» в записи сессии —
    # в живой нити встречается и то, и другое, поэтому в дельте есть оба, с пометкой via.
    decisions_new = [{**_brief(n), "via": "node"} for n in fresh if has(n, "decision")]
    for entry in sessions_new:
        for line in entry.get("decided") or []:
            decisions_new.append({"id": entry.get("id"), "claim": _short(line), "ts": entry.get("ts"),
                                  "agent": entry.get("agent"), "via": "session"})
    tails_opened = [_brief(n) for n in fresh
                    if n.get("kind") == "hypothesis" and has(n, "open")
                    and not has(n, "owner-question") and not has(n, "closed")]
    tails_closed = [_brief(n) for n in fresh if has(n, "closed") and not has(n, "owner-question")]
    requests = [{**_brief(n), "to": _request_targets(n), "resolved": has(n, "resolved")}
                for n in fresh if _request_targets(n)]

    # Голову проверяем строже, чем прочие узлы: при rewrite сервер обновляет её паспорт
    # (agent/session_id), поэтому автор правки известен и «свою» правку показывать не нужно —
    # послабление is_new про ревизии здесь только мешало бы.
    head_updated = None
    if (head_node is not None and _ts(head_node) > cutoff
            and str(head_node.get("session_id") or "") not in skip_sessions):
        parsed = parse_head(head_node.get("claim")) or {}
        head_updated = {"id": head_node.get("id"), "ts": head_node.get("ts"),
                        "agent": _node_agent(head_node) or None,
                        "updated": parsed.get("updated"),
                        "next_step": _short(parsed.get("next_step"))}

    return {
        "since": {"id": base.get("id"), "ts": base.get("ts"),
                  "session_id": base.get("session_id") or None,
                  "agent": _node_agent(base) or None,
                  "date": (parse_session(base.get("claim")) or {}).get("date") or cutoff[:10] or None},
        "sessions": sessions_new,
        "decisions": decisions_new,
        "tails_opened": tails_opened,
        "tails_closed": tails_closed,
        "requests": requests,
        "head_updated": head_updated,
        "counts": {"sessions": len(sessions_new), "decisions": len(decisions_new),
                   "tails_opened": len(tails_opened), "tails_closed": len(tails_closed),
                   "requests": len(requests)},
    }


def format_changes(changes: Any) -> str:
    """Одна строка дельты для клиентов, видящих только text. Пусто — «изменений нет»."""
    if not isinstance(changes, dict):
        return ""
    since = changes.get("since")
    if not since:
        return f"изменения с прошлой сессии{KEY_SEP}{changes.get('reason') or 'нет опорной записи'}"
    c = changes.get("counts") or {}
    total = sum(int(v or 0) for v in c.values()) + (1 if changes.get("head_updated") else 0)
    head = (f"изменения с {since.get('date') or str(since.get('ts') or '')[:10]} "
            f"({since.get('agent') or '?'}){KEY_SEP}")
    if not total:
        return head + "нет"
    bits = []
    for label, key in (("сессий", "sessions"), ("решений", "decisions"), ("хвостов открыто", "tails_opened"),
                       ("хвостов закрыто", "tails_closed"), ("запросов", "requests")):
        if c.get(key):
            bits.append(f"{label} {c[key]}")
    if changes.get("head_updated"):
        bits.append("голова обновлена")
    who = sorted({s.get("agent") for s in (changes.get("sessions") or []) if s.get("by_other") and s.get("agent")})
    if who:
        bits.append("дирижёры: " + ", ".join(str(w) for w in who))
    return head + ", ".join(bits)


def thread_view(store: Any, slug: str, sessions: int = 3, now: Any = None,
                agent: Any = None, session_id: Any = None, pre_passes: Any = None,
                active_minutes: float = ACTIVE_MINUTES) -> Dict[str, Any]:
    """Вид нити <slug> из активных узлов стора (публичный Store.find_by_tags).

    Источник истины по открытым решениям — поле головы; owner_questions —
    информационно (kind=hypothesis, тег owner-question, без тега resolved).

    `agent`/`session_id` (T2.7) добавляют `changes_since_last` — что изменилось
    в нити с последней записи сессии ЭТОГО дирижёра. Поле только добавляется,
    контракт v1 не ломается: без `agent` оно есть, но с `since: null`.

    `pre_passes` (T2.11) — записи журнала `prepare` (`GroundLog.read`); из них
    считается `active_sessions` — кто ещё сейчас работает на этой нити. Без них
    поле есть и пусто: не знаем — не выдумываем.
    """
    if not is_valid_slug(slug):
        raise ValueError(f"thread: slug {slug!r} — expected [A-Za-z0-9._-] with no spaces")
    sessions = max(0, int(sessions))
    tag = f"thread:{slug}"
    nodes = store.find_by_tags([tag], active_only=True, now=now)
    if slug != sandbox.SANDBOX_SLUG:
        # TS.1: узел может нести ДВА тега нити — свой и thread:sandbox. Отбор
        # идёт по одному тегу, поэтому без этого среза узел трипа попадал бы в
        # sessions / open_tails / decisions_recent / changes_since_last вида
        # основной нити, а checkpoint отдаёт этот вид целиком — включая голову,
        # которая вставляется в facts[0] безусловно, мимо фильтра выдачи.
        nodes = [n for n in nodes if not sandbox.is_quarantined(n)]
    warnings: List[str] = []

    def has(n: Dict[str, Any], t: str) -> bool:
        return t in (n.get("tags") or [])

    heads = rank_heads(n for n in nodes if has(n, "thread_head"))
    head: Optional[Dict[str, Any]] = None
    if not heads:
        warnings.append("нет головы: активный узел с тегами thread_head и " + tag + " не найден")
    else:
        if len(heads) > 1:
            warnings.append(f"активных голов {len(heads)} > 1 — показана настоящая/самая свежая "
                            f"{heads[0].get('id')}, остальные ({', '.join(str(h.get('id')) for h in heads[1:])}) "
                            "пометить outdated")
        head = _head_entry(heads[0])
        if not head["parsed"]:
            warnings.append("голова не парсится (ожидается " + HEAD_FORMAT_HINT + ")")
        elif heads[0].get("kind") != "rule":
            warnings.append(f"голова kind={heads[0].get('kind')!r}, ожидается rule")

    def session_like(n: Dict[str, Any]) -> bool:
        # запись сессии по контракту (тег session) ИЛИ handoff-запись дирижёра в
        # свободной форме с тегом agent:<имя> (так пишет дирижёр Codex:
        # agent:codex-conductor, 2026-09-07) — её тоже показываем, parsed=false
        if has(n, "thread_head"):
            return False
        return has(n, "session") or any(str(t).startswith("agent:") for t in (n.get("tags") or []))

    def digest_like(n: Dict[str, Any]) -> bool:
        return (n.get("kind") == DIGEST_KIND or has(n, DIGEST_TAG)) and parse_digest(n.get("claim")) is not None

    digest_nodes = sorted((n for n in nodes if digest_like(n)), key=_ts, reverse=True)
    session_nodes = sorted((n for n in nodes if session_like(n) and not digest_like(n)),
                           key=_ts, reverse=True)
    session_entries = [_session_entry(n) for n in session_nodes[:sessions]]

    # T2.9 / правило: записи сессий не удаляются и не гасятся, но за пределами глубины правило
    # (по умолчанию 3 сессии) вместо них показывается недельный дайджест той же недели.
    hidden = session_nodes[sessions:]
    hidden_weeks = {week_key(_ts(n)) for n in hidden} - {""}
    digests = []
    for n in digest_nodes:
        parsed = parse_digest(n.get("claim")) or {}
        if parsed.get("week") not in hidden_weeks:
            continue     # неделя целиком видна записями сессий — дайджест вместо них не нужен
        digests.append({"id": n.get("id"), "ts": n.get("ts"), "week": parsed.get("week"),
                        "period": parsed.get("period"), "sessions_count": parsed.get("sessions_count"),
                        "agents": parsed.get("agents") or [], "did": parsed.get("did") or [],
                        "decided": parsed.get("decided") or [], "tails": parsed.get("tails") or [],
                        "claim": n.get("claim")})
    covered = sum(1 for n in hidden if week_key(_ts(n)) in {d["week"] for d in digests})

    tails = sorted(
        (n for n in nodes
         if n.get("kind") == "hypothesis" and has(n, "open")
         and not has(n, "owner-question") and not has(n, "closed")),
        key=_ts, reverse=True)
    # T2.9: упоминание хвоста — это использование. Продлеваем TTL и сбрасываем
    # долг затухания; затем отдаем актуальный срок, если читатель видит хвост.
    for tail in tails:
        tail_id = tail.get("id")
        if tail_id and hasattr(store, "extend_ttl"):
            try:
                tail["valid_until"] = store.extend_ttl(tail_id, hours=TAIL_TTL_HOURS)
            except KeyError:
                pass
    open_tails = [{"id": n.get("id"), "claim": n.get("claim"), "ts": n.get("ts"),
                   "agent": n.get("agent") or None, "valid_until": n.get("valid_until")}
                  for n in tails]

    questions = sorted(
        (n for n in nodes
         if n.get("kind") == "hypothesis" and has(n, "owner-question") and not has(n, "resolved")),
        key=_ts, reverse=True)
    owner_questions = [{"id": n.get("id"), "claim": n.get("claim")} for n in questions]

    decisions = sorted((n for n in nodes if has(n, "decision")), key=_ts, reverse=True)
    decisions_recent = [{"id": n.get("id"), "claim": n.get("claim")} for n in decisions[:5]]

    closed_sessions = {str(n.get("session_id") or "") for n in session_nodes} | {
        str((parse_session(n.get("claim")) or {}).get("session_id") or "") for n in session_nodes}
    active = active_sessions(pre_passes, slug, closed_sessions - {""}, now=now,
                             session_id=session_id, minutes=active_minutes)

    changes = changes_since_last(nodes, agent, session_id,
                                 head_node=heads[0] if heads else None, is_session=session_like)

    return {
        "schema_version": SCHEMA_VERSION,
        "slug": slug,
        "head": head,
        "sessions": session_entries,
        "digests": digests,
        "sessions_hidden": len(hidden),
        "sessions_hidden_covered": covered,
        "active_sessions": active,
        "changes_since_last": changes,
        "sessions_total": len(session_nodes),
        "open_tails": open_tails,
        "owner_questions": owner_questions,
        "decisions_recent": decisions_recent,
        "active_heads": len(heads),
        "active_nodes": len(nodes),
        "warnings": warnings,
    }


def _short(value: Any, limit: int = SUMMARY_FIELD_CHARS) -> str:
    text = _clean(value)
    if not text:
        return EMPTY_MARK
    if limit and len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


def format_summary(view: Dict[str, Any]) -> str:
    """Компактная строка для клиентов, видящих только text:
    «THREAD <slug> v1 | фаза: … | последний шаг: … | следующий шаг: … |
    открытые решения: … | сессии: N (последняя: <дата> <agent>) | хвосты: N»."""
    head = view.get("head") or {}
    sessions = view.get("sessions") or []
    total = view.get("sessions_total", len(sessions))
    if sessions:
        last = sessions[0]
        last_txt = f"{last.get('date') or str(last.get('ts') or '')[:10] or '?'} {last.get('agent') or '?'}"
        sess = f"{total} (последняя: {last_txt})"
    else:
        sess = str(total)
    parts = [
        f"THREAD {view.get('slug')} v{view.get('schema_version', SCHEMA_VERSION)}",
        f"{KEY_PHASE}{KEY_SEP}{_short(head.get('phase'))}",
        f"{KEY_LAST}{KEY_SEP}{_short(head.get('last_step'))}",
        f"{KEY_NEXT}{KEY_SEP}{_short(head.get('next_step'))}",
        f"{KEY_OPEN_ALT}{KEY_SEP}{_short(head.get('open_decisions'))}",
        f"сессии{KEY_SEP}{sess}",
        f"{KEY_TAILS}{KEY_SEP}{len(view.get('open_tails') or [])}",
    ]
    digests = view.get("digests") or []
    if digests:
        hidden = int(view.get("sessions_hidden") or 0)
        covered = int(view.get("sessions_hidden_covered") or 0)
        weeks = ", ".join(str(d.get("week")) for d in digests[:4])
        tail = f" (+{len(digests) - 4})" if len(digests) > 4 else ""
        parts.append(f"дайджесты{KEY_SEP}{len(digests)} — {weeks}{tail}; "
                     f"свёрнуто сессий {covered} из {hidden}")
    active_line = format_active(view.get("active_sessions"))
    if active_line:
        parts.append(active_line)
    changes_line = format_changes(view.get("changes_since_last"))
    if changes_line:
        parts.append(changes_line)
    if view.get("warnings"):
        parts.append("предупреждения" + KEY_SEP + "; ".join(_short(w, 160) for w in view["warnings"]))
    return SEP.join(parts)
