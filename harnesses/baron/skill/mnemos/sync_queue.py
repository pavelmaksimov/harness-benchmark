# -*- coding: utf-8 -*-
"""Baron Munchausen: очередь изменённых узлов для событийного экспорта.

Зачем. Экспорт в Obsidian ходил по таймеру раз в 900 с: узел, записанный
сразу после тика, лежал в памяти и не был виден пользователю до четверти часа.
Память, которая показывает вчерашнее состояние, — это не память, а отчёт.

Как. Каждая мутация графа (memory_add / memory_rewrite / memory_update /
архивация) кладёт сюда id изменённых узлов. Экспортёр (tools/obsidian/
watch.py) держит очередь на глазах, копит пачку 2–3 с — чтобы серия из
десяти memory_add дала один прогон, а не десять — и выгружает только эти
id. Таймер остаётся страховкой на редкий случай, когда экспортёр не
работал: он же чинит карты видов и хронологию.

Формат — append-only JSONL рядом со стором (`<store>.export-queue.jsonl`):

    {"seq": 12, "ts": "...", "ids": ["mn_…", "mn_…"], "reason": "memory_add"}

Замок — общий с шиной и журналом проходов (`bus.locked_file`): два
независимых писателя одного формата не должны иметь двух разных
реализаций блокировки. Под замком идёт и чтение-с-усечением (drain):
иначе экспортёр забирал бы пачку, а параллельная запись терялась.

Очередь НЕ является источником истины. Потеряли файл, не успели прочитать,
экспортёр лежал — граф от этого не страдает: полный прогон по таймеру
приводит vault в соответствие с памятью. Поэтому все ошибки записи здесь
глушатся: событийный экспорт — удобство, а не часть контракта записи.

Читателя стало два.
Местный экспортёр забирает очередь разрушительно (`drain`) — он один на
машине сервера, и забранное ему больше не нужно. Удалённый ходит по HTTP
(`memory_sync_queue` -> `since`) и файла не трогает вовсе: он читает с
курсором. Курсор — поле `seq`, сквозной номер записи, который проставляет
`enqueue`, подглядев номер последней строки файла. Номер нужен именно
потому, что читатель удалённый: по `ts` две записи одной миллисекунды
слились бы в одну, а по смещению в файле курсор врал бы после `trim`.

Разрушительный и курсорный читатели на одном сторе одновременно не живут.
Чтобы это не превратилось в молчаливую потерю, `drain` оставляет вместо
забранных строк водяной знак (`drained: true` с номером последней забранной
записи), а `since` отвечает на него `reset` — читатель делает полный прогон.
Без знака файл после drain пуст, нумерация идёт с единицы, и удалённый
читатель принял бы номер 1 за свою следующую запись.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from .bus import locked_file

QUEUE_SUFFIX = ".export-queue.jsonl"

# Потолок файла: очередь читают пачками по 2–3 с, и в норме в ней единицы
# строк. Разрастись она может, только если экспортёр не работает часами —
# а тогда его догоняет полный прогон по таймеру, и хранить мегабайты
# устаревших id незачем.
MAX_LINES = 5000

# Потолок страницы курсорного чтения. Читатель ходит раз в секунду и в
# норме забирает единицы записей; тысяча — это уже «экспортёр лежал»,
# и добирать остаток он будет следующим запросом (has_more).
SINCE_LIMIT = 1000

# Водяной знак, который `drain` оставляет вместо забранных строк. Без него
# файл после drain пуст, нумерация идёт с единицы, и курсорный читатель не
# отличает «ничего не менялось» от «мою пачку забрал кто-то другой»: он
# получил бы номер 1 на новую запись и решил бы, что всё в порядке.
DRAINED_KEY = "drained"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def queue_path(store_path: Union[str, Path]) -> Path:
    """Путь очереди рядом со стором: <store>.export-queue.jsonl."""
    p = Path(store_path)
    return p.with_name(p.name + QUEUE_SUFFIX)


def enqueue(path: Union[str, Path], ids: Iterable[str], reason: str = "",
            timeout: float = 2.0) -> int:
    """Положить id изменённых узлов в очередь. Возвращает сколько записано.

    Дубликаты внутри одного вызова схлопываются, порядок сохраняется.
    Таймаут короткий намеренно: это хвост запроса на запись в память, и
    ждать на нём десять секунд чужой блокировки нельзя.
    """
    uniq = [i for i in dict.fromkeys(str(i) for i in ids if i)]
    if not uniq:
        return 0
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with locked_file(path, timeout=timeout):
        # Номер берётся под тем же замком, что и дозапись: иначе два писателя
        # подглядели бы один хвост и выдали бы двум записям один seq — а
        # курсорный читатель по такому номеру пропустил бы вторую.
        line = json.dumps({"seq": next_seq(path), "ts": _now_iso(), "ids": uniq,
                           "reason": str(reason or "")}, ensure_ascii=False) + "\n"
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            # Писателя могли убить посреди строки. Без этого перевода строки
            # следующая запись приклеилась бы к обрывку и пропала бы вместе с
            # ним: одна оборванная пачка уносила бы соседнюю.
            if _needs_newline(path):
                f.write("\n")
            f.write(line)
            f.flush()
    return len(uniq)


def _needs_newline(path: Path) -> bool:
    """Файл кончается оборванной строкой (не переводом строки)?"""
    try:
        with open(path, "rb") as f:
            if not f.seek(0, os.SEEK_END):
                return False
            f.seek(-1, os.SEEK_END)
            return f.read(1) != b"\n"
    except OSError:
        return False


def enqueue_quiet(path: Union[str, Path], ids: Iterable[str], reason: str = "",
                  timeout: float = 2.0) -> int:
    """enqueue, который не может уронить запись в память.

    Вызывается из обработчиков сервера: узел уже записан и зафиксирован,
    и падать на очереди — значит отдать клиенту ошибку по факту успешной
    записи. Полный прогон по таймеру такую потерю всё равно догонит.
    """
    try:
        return enqueue(path, ids, reason, timeout=timeout)
    except (OSError, TimeoutError, ValueError):
        return 0


# --------------------------------------------------------------------------- #
# Сквозной номер записи: курсор удалённого читателя
# --------------------------------------------------------------------------- #
def _last_record(path: Path) -> Optional[Dict[str, Any]]:
    """Последняя целая запись файла, читая с конца.

    С конца, а не разбором всего файла: это хвост каждого memory_add, а в
    очереди может лежать пять тысяч строк. Первая строка прочитанного куска
    берётся в расчёт, только если кусок дотянулся до начала файла — иначе
    это обрезок посередине записи, а не запись.
    """
    try:
        with open(path, "rb") as f:
            end = f.seek(0, os.SEEK_END)
            if not end:
                return None
            pos, step = end, 4096
            while pos > 0:
                pos = max(0, pos - step)
                f.seek(pos)
                lines = [ln for ln in f.read(end - pos).split(b"\n") if ln.strip()]
                for ln in reversed(lines[0 if pos == 0 else 1:]):
                    try:
                        rec = json.loads(ln.decode("utf-8"))
                    except (ValueError, UnicodeDecodeError):
                        continue          # оборванная строка — смотрим выше
                    if isinstance(rec, dict):
                        return rec
                step *= 4
    except OSError:
        return None
    return None


def next_seq(path: Union[str, Path]) -> int:
    """Номер следующей записи. Вызывать только под замком файла.

    Счётчик живёт в самом файле, а не отдельным состоянием на диске: очередь
    и так не источник истины, и второй файл, который можно рассинхронить с
    первым, здесь стоил бы дороже, чем даёт.
    """
    path = Path(path)
    rec = _last_record(path)
    if rec is None:
        return 1                          # файла нет или он пуст — с единицы
    try:
        last = int(rec["seq"])
    except (KeyError, TypeError, ValueError):
        # Очередь от версии без номеров: продолжаем с числа строк, чтобы не
        # выдать старым и новым записям пересекающиеся номера.
        return max(size(path), 1) + 1
    return last + 1 if last >= 0 else 1


def _numbered(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Записи с гарантированно возрастающим seq (у старых его нет)."""
    out: List[Dict[str, Any]] = []
    prev = 0
    for rec in records:
        try:
            seq = int(rec["seq"])
        except (KeyError, TypeError, ValueError):
            seq = prev + 1
        if seq <= prev:
            seq = prev + 1                # номера не убывают, даже если файл склеен
        prev = seq
        out.append({**rec, "seq": seq})
    return out


def since(path: Union[str, Path], cursor: Optional[int] = None,
          limit: int = SINCE_LIMIT) -> Dict[str, Any]:
    """Что появилось в очереди после `cursor`, НЕ забирая (курсорное чтение).

    Читает без замка и ничего не пишет: удалённый экспортёр не имеет
    права мешать записи в память, а рваная последняя строка здесь стоит одной
    пропущенной пачки, которую догонит полный прогон.

    cursor=None — подписка с текущей головы: id не отдаются. Читатель как раз
    сделал полный прогон, и вся накопленная история ему не нужна — она
    заставила бы его переписать пол-vault сразу после старта.

    reset=True — нумерация в файле разошлась с курсором (местный экспортёр
    сделал drain, или trim срезал голову). Отдаём всё, что есть, и просим
    читателя сделать полный прогон: выборочным тут не обойтись, потому что
    неизвестно, что именно потерялось.
    """
    path = Path(path)
    _ids, raw = _read(path)
    records = _numbered(raw)
    last = records[-1]["seq"] if records else None
    if cursor is None:
        return {"cursor": str(last or 0), "ids": [], "records": [], "count": 0,
                "has_more": False, "reset": False, "mtime": mtime(path)}
    cursor = int(cursor)
    reset = False
    fresh = [r for r in records if r["seq"] > cursor]
    if records and (
        last < cursor                                   # нумерация начиналась заново
        or records[0]["seq"] > cursor + 1               # голову срезал trim
        # чужой drain забрал пачку, которую мы ещё не читали
        or any(r.get(DRAINED_KEY) and r["seq"] > cursor for r in records)
    ):
        reset, fresh = True, records
    page = fresh[:max(1, int(limit))]
    ids: List[str] = []
    seen = set()
    for rec in page:
        for i in rec.get("ids") or []:
            if isinstance(i, str) and i and i not in seen:
                seen.add(i)
                ids.append(i)
    out_cursor = page[-1]["seq"] if page else (cursor if last is None else max(cursor, last))
    return {"cursor": str(out_cursor), "ids": ids, "records": page, "count": len(page),
            "has_more": len(fresh) > len(page), "reset": reset, "mtime": mtime(path)}


def peek(path: Union[str, Path]) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Что лежит в очереди, не забирая. Для статуса и тестов."""
    return _read(Path(path))


def _read(path: Path) -> Tuple[List[str], List[Dict[str, Any]]]:
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, ValueError):
        return [], []
    records: List[Dict[str, Any]] = []
    ids: List[str] = []
    seen = set()
    for ln in raw.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            rec = json.loads(ln)
        except ValueError:
            # Битая строка — это оборванная запись, а не повод потерять
            # остальную пачку: пропускаем и читаем дальше.
            continue
        if not isinstance(rec, dict):
            continue
        records.append(rec)
        for i in rec.get("ids") or []:
            if isinstance(i, str) and i and i not in seen:
                seen.add(i)
                ids.append(i)
    return ids, records


def drain(path: Union[str, Path], timeout: float = 5.0) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Забрать очередь целиком и очистить файл (атомарно, под замком).

    Возвращает (уникальные id в порядке появления, сырые записи). Пустая
    очередь — ([], []) без записи на диск.
    """
    path = Path(path)
    if not path.exists():
        return [], []
    with locked_file(path, timeout=timeout):
        ids, records = _read(path)
        if not ids:
            # В файле либо пусто, либо один водяной знак от прошлого drain.
            # Переписывать его на каждом тике незачем: id в нём нет, а mtime
            # он бы двигал и заставлял бы экспортёр просыпаться впустую.
            return [], records
        seq = _numbered(records)[-1]["seq"]
        mark = json.dumps({"seq": seq, "ts": _now_iso(), "ids": [],
                           "reason": "drain", DRAINED_KEY: True}, ensure_ascii=False) + "\n"
        # Усечение, а не unlink: файл держат открытым на запись, и
        # unlink оставил бы писателю отвязанный inode — его строки
        # ушли бы в никуда.
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(mark)
    return ids, records


def size(path: Union[str, Path]) -> int:
    """Сколько строк в очереди (дёшево, без разбора JSON)."""
    try:
        with open(path, "rb") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def trim(path: Union[str, Path], max_lines: int = MAX_LINES, timeout: float = 5.0) -> int:
    """Обрезать очередь до последних max_lines строк. Сколько выброшено."""
    path = Path(path)
    if size(path) <= max_lines:
        return 0
    with locked_file(path, timeout=timeout):
        try:
            lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        except (OSError, ValueError):
            return 0
        if len(lines) <= max_lines:
            return 0
        dropped = len(lines) - max_lines
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text("".join(lines[-max_lines:]), encoding="utf-8")
        os.replace(tmp, path)
    return dropped


def mtime(path: Union[str, Path]) -> Optional[float]:
    """Время последней записи в очередь (для пачки 2–3 с) или None."""
    try:
        return Path(path).stat().st_mtime
    except OSError:
        return None
