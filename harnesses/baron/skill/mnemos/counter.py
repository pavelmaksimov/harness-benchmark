# -*- coding: utf-8 -*-
"""Счётчики-узлы: выдача следующего номера под одним замком графа.

Зачем это на сервере. Номер решения D-NNN агент себе не выбирает — он
берёт его из узла-счётчика: читает `next=NNN`, дописывает строку выдачи, пишет
узел обратно. Клиент сериализовать такое чтение-и-запись может только у себя:
`flock` на `~/.baron/decision-number.lock` разводит агентов одной
машины и ничего не знает об агентах с другой. Между чтением и записью остаётся
окно, и два писателя видят одно и то же `next` — оба возвращают один номер
(воспроизведено шестью процессами с отключённым flock: двое получили 56).

Единственное место, где чтение и увеличение закрываются одним замком, — сам
граф. Стор держит внутрипроцессный RLock и межпроцессный flock и подтягивает
чужие записи перед чтением, поэтому `take()` внутри `store.transaction()` —
настоящая атомарность, а не сторож. Клиенту возвращается уже выданное число.

Формат тела узла — строки, читаемые человеком: узел лежит в графе и уезжает в
выгрузку vault, разбирать его глазами приходится и пользователю.

    [COUNTER:next_decision] Счётчик номеров решений Baron Munchausen. …
    next=056
    taken: правило orchestrator 2026-09-08T09:00:00Z

Заголовок (первая строка) при выдаче сохраняется как есть, а не пересобирается
из шаблона: он объясняет человеку, что это за узел, и переписывать его выдачей
номера — значит менять живую память мимо чьего-либо решения.

Модуль — только stdlib и никаких импортов из `mnemos`: его читает и клиент
(`tools/decisions/decision_number.py`), чтобы формат тела был определён в одном
месте. Разъехавшиеся регулярки на двух концах — ровно тот баг, от которого
счётчик и защищает.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

COUNTER_PREFIX = "counter:"
NEXT_RE = re.compile(r"next=(\d{3,4})")
TAKEN_RE = re.compile(r"taken:\s*D-(\d{3,4})\s+(\S+)\s+(\S+)")
# Хвост выдач в теле узла. Журнал стора хранит всю историю в revisions, а узел
# должен оставаться читаемым: 200 строк — примерно экран истории.
TAKEN_TAIL = 200
NAME_RE = re.compile(r"^[a-z0-9_]{1,64}$")


class CounterError(RuntimeError):
    """Счётчик не найден, узлов больше одного или тело не разобрано."""


def counter_tag(name: str) -> str:
    """Имя счётчика -> тег узла. Полный тег на входе принимается как есть."""
    text = str(name or "").strip()
    if text.startswith(COUNTER_PREFIX):
        text = text[len(COUNTER_PREFIX):]
    if not NAME_RE.match(text):
        raise CounterError(
            f"имя счётчика {name!r} не годится: ждём [a-z0-9_] до 64 символов "
            f"(тег узла — {COUNTER_PREFIX}<имя>)")
    return COUNTER_PREFIX + text


def counter_name(name: str) -> str:
    """Имя счётчика без префикса тега (после проверки)."""
    return counter_tag(name)[len(COUNTER_PREFIX):]


def now_iso() -> str:
    """Метка выдачи: секунды и Z — тот же вид, что уже лежит в живом узле."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_header(name: str) -> str:
    return (f"[COUNTER:{counter_name(name)}] Счётчик Baron Munchausen. "
            "Номер выдаётся только операцией memory_counter_take; "
            "руками это тело не правят.")


def header_of(claim: str, name: str) -> str:
    """Заголовок узла = его первая строка. Если она уже данные — шаблон."""
    first = (str(claim or "").splitlines() or [""])[0]
    if not first.strip() or NEXT_RE.search(first) or first.lstrip().startswith("taken:"):
        return default_header(name)
    return first


def parse(claim: str) -> Tuple[int, List[Dict[str, str]]]:
    """Тело узла → (следующий свободный номер, список выданных)."""
    m = NEXT_RE.search(claim or "")
    if not m:
        raise CounterError("узел счётчика без 'next=NNN' — вручную его не правят, "
                           "и без числа выдавать нечего")
    taken = [{"number": int(n), "agent": a, "ts": t}
             for n, a, t in TAKEN_RE.findall(claim or "")]
    return int(m.group(1)), taken


def render(nxt: int, taken: List[Dict[str, str]], header: Optional[str] = None,
           name: str = "next_decision") -> str:
    """(следующий номер, выданные) → тело узла. Хвост выдач обрезан до TAKEN_TAIL."""
    lines = [header or default_header(name), f"next={int(nxt):03d}"]
    for row in taken[-TAKEN_TAIL:]:
        lines.append(f"taken: D-{int(row['number']):03d} {row['agent']} {row['ts']}")
    return "\n".join(lines)


def find(store: Any, name: str) -> Dict[str, Any]:
    """Узел счётчика по тегу. Их ровно один — иначе это уже не счётчик."""
    tag = counter_tag(name)
    rows = [d for d in store.find_by_tags([tag], active_only=False)
            if isinstance(d, dict) and d.get("id")]
    if not rows:
        raise CounterError(f"узел счётчика с тегом {tag} не найден — "
                           "создать его командой 'next-decision init <первый свободный номер>'")
    if len(rows) > 1:
        ids = ", ".join(str(d.get("id")) for d in rows)
        raise CounterError(f"узлов счётчика больше одного ({ids}) — это уже не счётчик, "
                           "лишние снять тегом вручную")
    return rows[0]


def take(store: Any, name: str, agent: str, reason: str = "",
         write: Optional[Callable[[str, str, str], Any]] = None) -> Dict[str, Any]:
    """Выдать следующий номер. Чтение, разбор и запись — под одной транзакцией.

    `write(node_id, new_claim, reason)` — как записывать узел; по умолчанию
    `store.rewrite` (старое тело уходит в revisions). Сервер подставляет свой
    писатель, чтобы узел прошёл тот же truth-gate, что и `memory_rewrite`.

    Возвращает выданный номер вместе с паспортом выдачи: клиенту не нужно
    перечитывать узел, чтобы узнать, что именно ему досталось.
    """
    agent = str(agent or "").strip()
    if not agent:
        raise CounterError("выдача без имени агента запрещена — номер должен "
                           "быть за кем-то, иначе журнал выдач бесполезен")
    writer = write or (lambda nid, claim, why: store.rewrite(nid, claim, reason=why))
    with store.transaction():
        node = find(store, name)
        nxt, taken = parse(node.get("claim") or "")
        stamp = now_iso()
        taken.append({"number": nxt, "agent": agent, "ts": stamp})
        body = render(nxt + 1, taken, header=header_of(node.get("claim") or "", name))
        why = f"выдан D-{nxt:03d} агенту {agent}" + (f": {reason}" if reason else "")
        writer(str(node["id"]), body, why)
        return {
            "counter": counter_name(name),
            "node_id": str(node["id"]),
            "number": nxt,
            "next": nxt + 1,
            "agent": agent,
            "ts": stamp,
        }


def reserve(store: Any, name: str, number: int, agent: str, reason: str = "",
            write: Optional[Callable[[str, str, str], Any]] = None) -> Dict[str, Any]:
    """Записать номер, занятый мимо счётчика, и подвинуть `next` за него.

    Вторая точка выдачи номеров, и гонка на ней возможна ровно так же, как на
    `take()`: между чтением узла и записью помещается чужая выдача, и `next`
    уезжает назад — тогда счётчик выдаст уже занятое число повторно. Поэтому
    чтение, проверка «номер ещё не в журнале» и запись идут под той же
    транзакцией стора, что и выдача.

    Числа между прежним `next` и занятым остаются незанятыми навсегда, как
    правило: дырка в нумерации дешевле, чем два решения с одним номером.
    """
    agent = str(agent or "").strip()
    if not agent:
        raise CounterError("запись занятого номера без имени агента запрещена — "
                           "журнал выдач должен отвечать, чей это D-NNN")
    try:
        number = int(number)
    except (TypeError, ValueError):
        raise CounterError(f"номер {number!r} — не число") from None
    if number < 0:
        raise CounterError(f"номер D-{number} отрицательный — такого решения не бывает")
    writer = write or (lambda nid, claim, why: store.rewrite(nid, claim, reason=why))
    with store.transaction():
        node = find(store, name)
        nxt, taken = parse(node.get("claim") or "")
        if any(r["number"] == number for r in taken):
            raise CounterError(f"D-{number:03d} уже есть в журнале выдач — "
                               "второй раз не записываем")
        stamp = now_iso()
        taken.append({"number": number, "agent": agent, "ts": stamp})
        taken.sort(key=lambda r: r["number"])
        new_next = max(nxt, number + 1)
        body = render(new_next, taken, header=header_of(node.get("claim") or "", name))
        why = (f"D-{number:03d} занят мимо счётчика ({agent})"
               + (f": {reason}" if reason else ""))
        writer(str(node["id"]), body, why)
        return {
            "counter": counter_name(name),
            "node_id": str(node["id"]),
            "number": number,
            "next": new_next,
            "agent": agent,
            "ts": stamp,
        }


def peek(store: Any, name: str) -> Dict[str, Any]:
    """Посмотреть, не забирая. Замок не нужен: это снимок, а не выдача."""
    node = find(store, name)
    nxt, taken = parse(node.get("claim") or "")
    return {"counter": counter_name(name), "node_id": str(node["id"]),
            "next": nxt, "taken": taken}
