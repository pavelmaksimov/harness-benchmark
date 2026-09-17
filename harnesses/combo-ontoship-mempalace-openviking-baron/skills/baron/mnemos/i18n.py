# -*- coding: utf-8 -*-
"""Язык того, что видит пользователь.

Правило: наружу — English. Консольный баннер, объяснения `reason`, вердикт
словами и сообщения об ошибках JSON-RPC по умолчанию английские; русский
вариант остаётся рядом (`*_ru`) и включается целиком переменной окружения
`BARON_LANG=ru`.

Внутренние журналы (`log.info`, docstrings, комментарии) правилу не подчинены:
их читают дирижёры, а не пользователи Show HN.
"""

import os
from typing import Optional

LANG_ENV = "BARON_LANG"
DEFAULT_LANG = "en"
SUPPORTED = ("en", "ru")


def lang(explicit: Optional[str] = None) -> str:
    """Текущий язык пользовательских поверхностей: 'en' (по умолчанию) или 'ru'.

    Значение читается на каждом вызове, а не при импорте: тесты и сессии
    переключают язык через monkeypatch окружения уже после импорта модуля.
    """
    raw = explicit if explicit is not None else os.environ.get(LANG_ENV, "")
    value = (raw or "").strip().lower()
    return value if value in SUPPORTED else DEFAULT_LANG


def pick(en: str, ru: str, explicit: Optional[str] = None) -> str:
    """Английский текст по умолчанию, русский — при BARON_LANG=ru."""
    return ru if lang(explicit) == "ru" else en
