# -*- coding: utf-8 -*-
"""Baron Munchausen — пользовательское имя продукта.

Тонкий пакет-алиас к `mnemos`: код живёт там, наружу продукт называется
Baron Munchausen, команда — `baron`. Импорт `baron.<модуль>` отдаёт тот же
объект, что и `mnemos.<модуль>`, поэтому состояние (стор, счётчики) общее.

    import baron            # == mnemos
    from baron import server
    python3.12 -m baron --port 8770 --store blank
"""

from __future__ import annotations

import sys as _sys

import mnemos as _mnemos

PRODUCT_NAME = "Baron Munchausen"
COMMAND_NAME = "baron"

__all__ = list(getattr(_mnemos, "__all__", []))
__version__ = getattr(_mnemos, "__version__", "")
# Подмодули берутся из mnemos, но СВОЙ каталог остаётся первым: иначе
# `python3.12 -m baron` находит mnemos/__main__.py и печатает чужое имя.
__path__ = list(__path__) + list(_mnemos.__path__)


def __getattr__(name: str):
    """Всё, чего нет здесь, берётся из mnemos — включая подмодули."""
    try:
        return getattr(_mnemos, name)
    except AttributeError:
        pass
    module = __import__(f"mnemos.{name}", fromlist=[name])
    _sys.modules[f"{__name__}.{name}"] = module
    return module
