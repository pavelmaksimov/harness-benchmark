# -*- coding: utf-8 -*-
"""Фазы запроса для структурного лога (wave2, фронт 6). Только stdlib.

    with trace.phase("search"):
        ...
    phases = trace.collect()   # {"search": 1.234, ...} — миллисекунды за запрос

Счётчики лежат в thread-local: ThreadingHTTPServer обслуживает каждый запрос
своим потоком, и фазы одного вызова не смешиваются с соседним. Вне запроса
(тесты, скрипты) фазы копятся и сбрасываются тем же collect() — без вреда.
"""

from __future__ import annotations

import contextlib
import threading
import time
from typing import Dict, Iterator

_local = threading.local()


def _bucket() -> Dict[str, float]:
    b = getattr(_local, "phases", None)
    if b is None:
        b = {}
        _local.phases = b
    return b


@contextlib.contextmanager
def phase(name: str) -> Iterator[None]:
    """Прибавить время блока к фазе name (мс). Вложенные фазы считаются
    каждая по себе: «disk» внутри «add» видна отдельно."""
    t0 = time.perf_counter()
    try:
        yield
    finally:
        b = _bucket()
        b[name] = b.get(name, 0.0) + (time.perf_counter() - t0) * 1000.0


def add(name: str, ms: float) -> None:
    b = _bucket()
    b[name] = b.get(name, 0.0) + float(ms)


def collect() -> Dict[str, float]:
    """Забрать фазы текущего потока (округлённые до 0.01 мс) и обнулить."""
    b = _bucket()
    out = {k: round(v, 2) for k, v in b.items()}
    b.clear()
    return out


def reset() -> None:
    _bucket().clear()
