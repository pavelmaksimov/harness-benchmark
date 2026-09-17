# -*- coding: utf-8 -*-
"""Запуск MCP-сервера Baron Munchausen.

Пользовательская команда — `baron` (D-123). Старые имена (`python3.12 -m
mnemos`, точка входа `mnemos`) продолжают работать и печатают в stderr
предупреждение о переименовании.

baron [--host ..] [--port ..] [--store nodes.json|blank]
                   [--plugins "context_engine,gates"] [--plugins-config plugins.json]
                   [--no-ground-by-default]

Плагины (контекст-модуль — отдельный плагин): env MNEMOS_PLUGINS или
plugins.json; --plugins задаёт явный список (пустая строка — без плагинов).

Стор: --store <путь> либо env MNEMOS_STORE. Значение "blank" (или
"blank:<путь>") — новая инстанция с ЧИСТЫМ графом: ни одного чужого узла,
инструменты без данных. Существующий файл никогда не перезаписывается.

Проход через граф (grounded) включён по умолчанию: без memory_ground_prepare
ответ агента помечается ungrounded. Выключить осознанно —
--no-ground-by-default или env MNEMOS_GROUND_BY_DEFAULT=0.
"""

import argparse
import sys

from . import i18n
from .server import run


RENAME_NOTE = (
    "note: the command was renamed to `baron` (Baron Munchausen, D-123). "
    "`{old}` still works and behaves identically."
)


def main(prog: str = "baron", legacy: str = "") -> None:
    """Точка входа. prog — имя в --help; legacy — старое имя для предупреждения."""
    if legacy:
        print(RENAME_NOTE.format(old=legacy), file=sys.stderr)
    parser = argparse.ArgumentParser(
        prog=prog, description="Baron Munchausen MCP memory server (truth gates P1-P6)"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--store",
        default=None,
        help=i18n.pick(
            'path to nodes.json; "blank" or "blank:<path>" — a clean graph for a '
            "fresh instance (default: env MNEMOS_STORE -> ./nodes.json)",
            'путь к nodes.json; "blank" или "blank:<путь>" — чистый граф новой '
            "инстанции (по умолчанию env MNEMOS_STORE -> ./nodes.json)",
        ),
    )
    parser.add_argument(
        "--plugins",
        default=None,
        help=i18n.pick(
            'comma-separated list of enabled plugins, e.g. "context_engine,gates"; '
            'an empty string or "none" means no plugins (default: env '
            "MNEMOS_PLUGINS -> plugins.json -> defaults: context_engine,gates)",
            'включённые плагины через запятую, напр. "context_engine,gates"; '
            'пустая строка или "none" — без плагинов (по умолчанию env '
            "MNEMOS_PLUGINS -> plugins.json -> дефолты: context_engine,gates)",
        ),
    )
    parser.add_argument(
        "--plugins-config",
        default=None,
        help=i18n.pick(
            'path to plugins.json ({"enabled": ["context_engine"]})',
            'путь к plugins.json ({"enabled": ["context_engine"]})',
        ),
    )
    parser.add_argument(
        "--ground-by-default",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=i18n.pick(
            "require a pass through the graph before answering (ON by default; "
            "--no-ground-by-default switches it off, as does env "
            "MNEMOS_GROUND_BY_DEFAULT=0)",
            "обязательный проход через граф перед ответом (по умолчанию ВКЛЮЧЁН; "
            "--no-ground-by-default выключает, как и env MNEMOS_GROUND_BY_DEFAULT=0)",
        ),
    )
    args = parser.parse_args()
    try:
        run(
            host=args.host,
            port=args.port,
            store_path=args.store,
            plugins=args.plugins,
            plugins_config=args.plugins_config,
            ground_by_default=args.ground_by_default,
        )
    except (ValueError, OSError) as exc:
        # Ошибка конфигурации (непустой blank-граф, каталог вместо файла, нет
        # прав, занятый порт) — это сообщение оператору, а не трассировка на
        # 12 строк, в которой само сообщение теряется последней строкой.
        print(f"{prog}: {exc}", file=sys.stderr)
        raise SystemExit(2) from None


def legacy_main() -> None:
    """Точка входа `mnemos` из pyproject: то же самое плюс предупреждение."""
    main(prog="mnemos", legacy="mnemos")


if __name__ == "__main__":
    # `python3.12 -m mnemos` — старая форма, работает с предупреждением.
    main(prog="mnemos", legacy="python -m mnemos")
