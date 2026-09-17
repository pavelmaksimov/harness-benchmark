#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Приватность памяти: видимость узла и фильтр секретов до записи.

Два независимых механизма, оба обязательны до того, как в память поедет
vault пользователя целиком.

**1. Видимость.** Узел приватен, пока его не пометили публичным. Метка живёт
тегом — `visibility:private` / `visibility:public`, — потому что теги уже
есть в схеме узла, переживают `memory_rewrite`, уезжают в Obsidian-выгрузку
и читаются любым клиентом без миграции `nodes.json` (обещание продукта:
старый стор остаётся читаемым).

Фильтр — `audience="public"` в `memory_search` / `memory_list` /
`memory_export`. Он **режет по умолчанию**: наружу проходит только то, на чём
стоит явный `visibility:public`. Узел без меток — приватный; узел, помеченный
и так и так, — приватный (запрет сильнее разрешения). Это ровно тот выбор,
который просил пользователь: «любой вывод наружу читает ТОЛЬКО visibility:public».
Без параметра поведение прежнее — фильтр не включается сам и не ломает
внутренние вызовы.

**2. Фильтр секретов.** Ключи, пароли, seed-фразы и токены не должны стать
узлами вообще: узел живёт годами, ездит в выгрузку и в чужие контексты.
`redact()` заменяет найденный фрагмент на `[REDACTED]` и возвращает счётчик —
заметка узлом становится, секрет в ней нет. Режем именно фрагмент, а не
заметку целиком: пользователь пишет ключ посреди рабочего текста, и выбрасывать
из-за одной строки весь смысл заметки — хуже, чем вырезать строку.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Sequence, Tuple

VIS_PREFIX = "visibility:"
VIS_PUBLIC = "visibility:public"
VIS_PRIVATE = "visibility:private"
AUDIENCES = ("public", "all")
REDACTED = "[REDACTED]"

#: Черновик. Любой тег вида `draft:…` (`draft:owner` ставит baron/reward.py)
#: означает «текст ещё пишут». До 2026-09-10 тег не читал никто за пределами
#: baron/: и внешние публикаторы отбирали материал по одному
#: `visibility:public`, так что помеченный черновик пользователя уезжал наружу
#: ровно так же, как готовая находка. Проверка живёт здесь, а не у каждого
#: потребителя: `is_public` — единственная дверь наружу (`filter_audience`,
#: `filters.public_only`, `rules.decide`), и второй список признаков черновика
#: разъехался бы с первым.
DRAFT_PREFIX = "draft:"


# --------------------------------------------------------------------------- #
# Видимость
# --------------------------------------------------------------------------- #
def _tags_of(node: Any) -> set:
    tags = node.get("tags") if isinstance(node, dict) else node
    return {str(t) for t in (tags or [])}


def is_draft(node: Any) -> bool:
    """Черновик ли узел: есть тег `draft:…`. Наружу черновик не выходит."""
    return any(t.startswith(DRAFT_PREFIX) for t in _tags_of(node))


def draft_tags(node: Any) -> List[str]:
    """Теги-черновики узла, по порядку — для причины отказа."""
    return sorted(t for t in _tags_of(node) if t.startswith(DRAFT_PREFIX))


def is_public(node: Any) -> bool:
    """Публичен ли узел. Умолчание — нет.

    `node` — снимок узла или его теги. Явный `visibility:private` перебивает
    `visibility:public`: если пользователь пометил узел приватным, случайно
    добавленный публичный тег не должен его выпустить. Тег `draft:…` перебивает
    так же и по той же причине: черновик — это «ещё не решено», а не «можно».
    """
    tags = _tags_of(node)
    if is_draft(tags):
        return False
    return VIS_PUBLIC in tags and VIS_PRIVATE not in tags


def normalize_audience(value: Any, where: str) -> str:
    """Разбор параметра `audience`. Отсутствие = 'all'."""
    if value is None:
        return "all"
    aud = str(value).strip().lower()
    if aud not in AUDIENCES:
        raise ValueError(
            f"{where}: audience должен быть 'public' или 'all', получено {value!r}")
    return aud


def filter_audience(nodes: Sequence[Dict[str, Any]], audience: str) -> List[Dict[str, Any]]:
    """Отсечь всё, что не помечено `visibility:public`, если audience='public'."""
    if audience != "public":
        return list(nodes)
    return [n for n in nodes if is_public(n)]


def visibility_tags(public: bool = False) -> List[str]:
    """Тег видимости для записи: приватно, пока не сказано иначе."""
    return [VIS_PUBLIC if public else VIS_PRIVATE]


# --------------------------------------------------------------------------- #
# Фильтр секретов
# --------------------------------------------------------------------------- #
# Ключевые слова, после которых значение — секрет. Значение берётся до конца
# строки: ключи и пароли в заметках пишут одной строкой, а перенос означает
# новую мысль.
# Слово «пароль» пишут во всех падежах и во множественном числе («Пароли: …»),
# а сид 2FA пользователь называет коротко — «сид». До 2026-09-10 список знал только
# три формы, и строка «Пароли: VNC-вход `…`» проходила фильтр насквозь
# (mn_9b8c…, mn_e888… — судья R12 нашёл в пакете пароль VNC и сид 2FA).
_SECRET_WORDS = (
    r"парол\w*|пасс|password|passwords|passwd|pwd|passphrase|"
    r"сид|сида|сиде|seed|totp|vnc[\s_-]?вход|vnc[\s_-]?пароль|"
    r"секрет|secret|api[\s_-]?key|apikey|ключ\s+api|api[\s_-]?токен|"
    r"токен|token|access[\s_-]?key|secret[\s_-]?key|private[\s_-]?key|"
    r"приватный\s+ключ|закрытый\s+ключ|seed[\s_-]?phrase|seed[\s_-]?фраза|"
    r"мнемоник\w*|mnemonic|пин[\s_-]?код|2fa|otp[\s_-]?secret"
)

# Узкий список — для шаблонов, которые ищут значение в кавычках, в ячейке
# таблицы или просто рядом. Там нельзя опираться на «токен», «ключ», «секрет»:
# в этом графе токен — это монета («новые токены через ShineStream `…`»), ключ
# бывает ключом словаря, а секрет — фигурой речи. Пароль, сид, 2FA и приватный
# ключ в прозе так не звучат, поэтому в кавычках рядом с ними стоит значение.
_QUOTED_WORDS = (
    r"парол\w*|пасс|password|passwords|passwd|pwd|passphrase|"
    r"сид|сида|сиде|seed[\s_-]?(?:phrase|фраза)?|mnemonic|мнемоник\w*|"
    r"2fa|totp|otp[\s_-]?secret|второй\s+фактор|"
    r"api[\s_-]?key|apikey|secret[\s_-]?key|private[\s_-]?key|"
    r"приватный\s+ключ|закрытый\s+ключ|vnc[\s_-]?вход"
)

# Каждый шаблон режет ГРУППУ `val` (или всё совпадение, если группы нет).
PATTERNS: Tuple[Tuple[str, "re.Pattern[str]"], ...] = (
    # -- ключи провайдеров, узнаваемые по префиксу --------------------------
    ("api-key", re.compile(
        r"\b(?:sk-ant-[A-Za-z0-9_\-]{20,}|sk-or-v1-[A-Za-z0-9]{20,}|sk-proj-[A-Za-z0-9_\-]{20,}"
        r"|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|gho_[A-Za-z0-9]{30,}"
        r"|github_pat_[A-Za-z0-9_]{30,}|glpat-[A-Za-z0-9_\-]{15,}|AIza[A-Za-z0-9_\-]{30,}"
        r"|xox[baprs]-[A-Za-z0-9\-]{10,}|AKIA[0-9A-Z]{16}|hf_[A-Za-z0-9]{30,}"
        r"|pplx-[A-Za-z0-9]{30,}|r8_[A-Za-z0-9]{30,}|nvapi-[A-Za-z0-9_\-]{30,})\b")),
    # -- токен telegram-бота: 8-10 цифр, двоеточие, 35 символов -------------
    ("tg-bot-token", re.compile(r"\b\d{8,10}:[A-Za-z0-9_\-]{30,45}\b")),
    # -- JWT ----------------------------------------------------------------
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b")),
    # -- Authorization: Bearer <...> ---------------------------------------
    ("bearer", re.compile(r"(?i)\b(?:authorization\s*:\s*)?bearer\s+(?P<val>[A-Za-z0-9_\-.=]{16,})")),
    # -- PEM-блок приватного ключа -----------------------------------------
    # Хвост `-----END …-----` необязателен: узел мог обрезать текст, а один
    # заголовок PEM — уже достаточный признак, что дальше лежал ключ.
    ("pem", re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----"
        r"(?:.*?-----END [A-Z ]*PRIVATE KEY-----)?",
        re.S)),
    # -- приватный ключ кошелька: 0x + 64 hex -------------------------------
    ("hex-key", re.compile(r"\b0x[0-9a-fA-F]{64}\b")),
    # -- пара «почта:пароль» одной строкой ---------------------------------
    ("login-pair", re.compile(
        r"\b[\w.+\-]+@[\w\-]+\.[\w.]{2,}\s*[:|]\s*(?P<val>\S{6,})")),
    # -- «пароль: …», «api_key = …» — значение одним словом ----------------
    # Именно одним: секрет пробелов не содержит, а «токен = средство обмена
    # внутри экономики» — это проза, и вырезать из неё полстроки нельзя.
    ("keyword", re.compile(
        rf"(?i)\b(?:{_SECRET_WORDS})\s*(?:\(.*?\))?\s*[:=]\s*(?P<val>\S{{4,}})(?P<rest>[^\n]*)")),
    # -- otpauth://…?secret=… — QR второго фактора строкой -------------------
    ("otpauth", re.compile(r"otpauth://[^\s`'\"<>]+")),
    # -- секрет TOTP: base32 из 16-32 символов рядом со словом «сид»/2FA ----
    # Отдельно от «keyword»: сид пишут без двоеточия — «сид `JBSWY3DP…`».
    ("totp-seed", re.compile(
        rf"(?i)(?:{_QUOTED_WORDS})[^\n`'\"]{{0,25}}[`'\"]?(?P<val>[A-Z2-7]{{16,64}})[`'\"]?")),
    # -- «Пароли: VNC-вход `Xxx1234!`» — значение в обратных кавычках -------
    # Ключевое слово может стоять в начале строки, а само значение — дальше по
    # строке в кавычках. Режем каждое такое значение, кроме путей, файлов и
    # почты: пользователю нужно знать, ГДЕ лежит секрет, но не сам секрет.
    ("keyword-quoted", re.compile(
        rf"(?i)(?:{_QUOTED_WORDS})[^\n]{{0,40}}?[`'\"](?P<val>[^\s`'\"|]{{6,80}})[`'\"]")),
    # -- строка markdown-таблицы: | Пароль | Xxx1234x | --------------------
    ("table-secret", re.compile(
        rf"(?im)^\s*\|[^|\n]*(?:{_QUOTED_WORDS})[^|\n]*\|\s*(?P<val>[^\s|]{{6,80}})\s*\|")),
    # -- seed-фраза: 12/15/18/21/24 латинских слова подряд отдельной строкой -
    ("mnemonic", re.compile(
        r"(?m)^\s*(?P<val>(?:[a-z]{3,8}\s+){11,23}[a-z]{3,8})\s*$")),
)

# Значения, которые формально попадают под «keyword», но секретом не являются:
# пользователь пишет «пароль: не хранится», «token: см. 1Password».
# Значение из одних кириллических букв — обычное слово, а не секрет. Но если
# после него строка кончается («пароль: солнышко»), это всё-таки пароль:
# признак прозы — продолжение фразы, а не сам алфавит.
_CYRILLIC_WORD = re.compile(r"^[А-Яа-яЁё\-]+$")

_NOT_A_SECRET = re.compile(
    r"(?i)^(?:нет|없|none|null|-+|—+|\[redacted\]|не\s+хран|см\.|смотри|в\s+1password|"
    r"в\s+keychain|<[^>]*>|\{\{.*\}\}|xxx+|\*{3,}|todo|tbd|\?+)")


# Ссылка на место хранения — не секрет: «пароль в `C:\Пароли\bybit.txt`»,
# «сид сохранён в `/etc/secrets.env`», «логин `shine@example.com`». Пользователь
# держит секреты файлом (это и есть цель правила), и вырезать путь означало бы
# отнять у него единственную рабочую подсказку. Признак места — разделитель
# пути, расширение файла, схема URL или собака почты.
_PLACE_NOT_SECRET = re.compile(
    r"(?i)^(?:[a-z]+://|~|\.{0,2}/|[a-z]:\\\\?|\\\\)|[/\\]|@|\.(?:txt|md|env|json|ya?ml|conf|"
    r"cfg|ini|py|sh|log|csv|db|sqlite|pem|key|asc|gpg|kdbx|plist|toml)\b")

#: Классы, где значение в кавычках/таблице может оказаться просто ссылкой.
_PLACE_AWARE = ("keyword-quoted", "table-secret", "totp-seed")


def _looks_like_value(value: str) -> bool:
    """Похоже ли на само значение секрета, а не на путь к нему или на прозу."""
    val = value.strip()
    if len(val) < 6:
        return False
    if _NOT_A_SECRET.match(val) or _PLACE_NOT_SECRET.search(val):
        return False
    if _CYRILLIC_WORD.match(val):
        return False
    # Секрет — набор символов, а не слово. Смешанного регистра мало: `camelCase`
    # и `ShineStream` — имена, а не пароли. Нужна цифра рядом с буквами, знак
    # препинания в середине или длинная base32/hex-строка.
    if re.search(r"\d", val) and re.search(r"[A-Za-z]", val):
        return True
    # Знак препинания сам по себе признаком не служит: `draft:*` в описании
    # выборки судей — не пароль. Цена ошибки несимметрична: пропущенный пароль
    # без цифры пользователь увидит в отчёте сканера, а вырезанный кусок прозы
    # молча испортит каждую заметку.
    return bool(len(val) >= 16 and re.fullmatch(r"[A-Z2-7]+", val))


def _is_login_prose(value: str) -> bool:
    """Не пароль после «логин@адрес:»: путь (`root@vps:/opt/app`) или русское
    слово (`root@vps: сделать бэкап` — это команда, а не учётные данные)."""
    val = value.strip()
    return bool(_PLACE_NOT_SECRET.search(val) or _CYRILLIC_WORD.match(val))


def _mnemonic_ok(value: str) -> bool:
    """Отсеять прозу от seed-фразы: у seed слова короткие и без повторов."""
    words = value.split()
    if len(words) not in (12, 15, 18, 21, 24):
        return False
    return len(set(words)) >= len(words) - 1


def redact(text: str) -> Tuple[str, int]:
    """Заменить секреты на `[REDACTED]`. Возвращает (текст, сколько фрагментов).

    Идемпотентна: `[REDACTED]` под шаблоны не подходит, повторный прогон
    ничего не находит — иначе каждый повторный ингест заметки «менял» бы её
    и плодил ревизии.
    """
    if not text:
        return text or "", 0
    count = 0
    out = text
    for name, rx in PATTERNS:
        def _sub(m: "re.Match[str]") -> str:
            nonlocal count
            grouped = "val" in (rx.groupindex or {})
            value = m.group("val") if grouped else m.group(0)
            if not value or REDACTED in value:
                return m.group(0)
            if name == "keyword":
                if _NOT_A_SECRET.match(value.strip()):
                    return m.group(0)
                rest = (m.groupdict().get("rest") or "").strip()
                if _CYRILLIC_WORD.match(value.strip()) and rest:
                    return m.group(0)
            if name in _PLACE_AWARE and not _looks_like_value(value):
                return m.group(0)
            # `root@1.2.3.4:/opt/exampleapp` — это адрес репозитория, а не
            # пара «почта:пароль»: путь после двоеточия секретом не бывает.
            if name == "login-pair" and _is_login_prose(value):
                return m.group(0)
            if name == "mnemonic" and not _mnemonic_ok(value):
                return m.group(0)
            count += 1
            if not grouped:
                return REDACTED
            start, end = m.start("val") - m.start(0), m.end("val") - m.start(0)
            whole = m.group(0)
            return whole[:start] + REDACTED + whole[end:]

        out = rx.sub(_sub, out)
    return out, count


def redact_fields(**fields: str) -> Tuple[Dict[str, str], int]:
    """`redact` по нескольким полям сразу (claim + context) с общим счётчиком."""
    out: Dict[str, str] = {}
    total = 0
    for key, value in fields.items():
        cleaned, n = redact(value or "")
        out[key] = cleaned
        total += n
    return out, total


def redaction_report(fragments: int, notes: int) -> str:
    """Строка отчёта в исходной формулировке."""
    return f"пропущено {fragments} фрагментов в {notes} заметках"


# --------------------------------------------------------------------------- #
# Сторож: один список признаков на всех потребителей
# --------------------------------------------------------------------------- #
def node_text(node: Dict[str, Any]) -> str:
    """Весь текст узла, по которому ищут секрет: claim + context + source."""
    return "\n".join(str(node.get(k) or "") for k in ("claim", "context", "source"))


def scan(text: str) -> List[Tuple[str, int]]:
    """Найденные секреты как (класс, длина значения) — без самих значений.

    Отчёт по живому графу печатает только это: id узла, вид, класс и длину.
    Значение секрета не возвращается никогда, чтобы отчёт можно было положить
    в репозиторий и показать пользователю.
    """
    if not text:
        return []
    found: List[Tuple[str, int]] = []
    for name, rx in PATTERNS:
        grouped = "val" in (rx.groupindex or {})
        for m in rx.finditer(text):
            value = (m.group("val") if grouped else m.group(0)) or ""
            if not value or REDACTED in value:
                continue
            if name == "keyword":
                if _NOT_A_SECRET.match(value.strip()):
                    continue
                rest = (m.groupdict().get("rest") or "").strip()
                if _CYRILLIC_WORD.match(value.strip()) and rest:
                    continue
            if name in _PLACE_AWARE and not _looks_like_value(value):
                continue
            if name == "login-pair" and _is_login_prose(value):
                continue
            if name == "mnemonic" and not _mnemonic_ok(value):
                continue
            found.append((name, len(value)))
    return found


def has_secret(node: Dict[str, Any]) -> bool:
    """Есть ли в узле опознанный секрет. Одна дверь для пакета и публикатора."""
    return bool(scan(node_text(node)))


def scan_nodes(nodes: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Отчёт по списку узлов: id, kind, теги, классы секретов и их длины."""
    report: List[Dict[str, Any]] = []
    for node in nodes:
        found = scan(node_text(node))
        if not found:
            continue
        report.append({
            "id": str(node.get("id") or "?"),
            "kind": str(node.get("kind") or "?"),
            "tags": sorted(str(t) for t in (node.get("tags") or [])),
            "classes": sorted({name for name, _ in found}),
            "lengths": [ln for _, ln in found],
            "hits": len(found),
        })
    report.sort(key=lambda r: (-r["hits"], r["id"]))
    return report
