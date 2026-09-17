# -*- coding: utf-8 -*-
"""Baron Munchausen: обязательный проход ответа через граф памяти (Grounded Answer).

Приказ Ильи 03.09: перед КАЖДЫМ ответом агент обязан пройти через граф —
чтобы пользователь не жёг токены вникуда, а ответ опирался на свою память,
а не на выдумку модели. Здесь — механика этого прохода.

Протокол (три шага, все три пишутся в append-only журнал ground_log.jsonl):

  1. ДО ответа  — memory_ground_prepare(query): бюджетный поиск по графу +
     сборка system-prompt из найденных узлов. Регистрирует «пред-проход»
     (pre-pass) сессии: время, запрос, id выданных узлов. Без этого шага
     ответ на шаге 3 помечается ungrounded (reason=no_pre_pass) — сколько бы
     утверждений он ни подтвердил.
  2. Ответ      — генерирует клиент (LLM) поверх полученного промпта. Либо
     не генерирует вовсе: см. graph_first() — режим «ноль токенов».
  3. ПОСЛЕ      — memory_ground(answer_text): ответ режется на утверждения,
     каждое сверяется с графом (покрытие по idf-взвешенным основам слов +
     жёсткая сверка чисел), выдаётся вердикт по утверждению и по ответу
     целиком: grounded / partial / ungrounded, плюс список узлов-источников.

Почему покрытие, а не «семантическая похожесть»: рантайм Mnemos — stdlib,
без моделей (fastembed опционален и на проде не стоит). Покрытие по основам
слов с весами idf — тот же сигнал, на котором работает budget-поиск, то есть
grounding меряет ровно ту память, которую агент реально мог прочитать.

Числа — отдельный жёсткий гейт. Выдумка модели чаще всего выглядит как
правильные слова с неправильной цифрой («вес 0.9», «14 сделок»), и покрытие
по словам такую подмену пропускает: слова-то из графа. Поэтому число из
утверждения, которого нет в узле-опоре, роняет вердикт до unsupported
(reason=number_mismatch) даже при покрытии 1.0.

Только stdlib.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from collections import OrderedDict, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union

from . import trace
from .budget import KIND_HUB, estimate_tokens, node_text, norm, tokens
from . import i18n
from .bus import locked_file

# --- пороги (все вынесены сюда: приказ требует «порог», а не магию в коде) ---

SUPPORT_STRONG = 0.60   # покрытие утверждения графом -> supported
SUPPORT_WEAK = 0.30     # покрытие -> partial (ниже — unsupported)
GROUNDED_RATIO = 0.80   # доля подтверждённых утверждений -> grounded
PARTIAL_RATIO = 0.40    # доля -> partial (ниже — ungrounded)

# --- i18n объяснений ---------------------------------------------
# Публичные поверхности англоязычные, а `reason` исторически по-русски. Ломать
# русскую строку нельзя (её читают дирижёры и нить), поэтому каждое объяснение
# собирается один раз из кода и подставляется в оба языка сразу: `reason` —
# по-русски, `reason_en` — по-английски, `reason_code` — машинное имя, по
# которому поверхность может построить свой текст и вовсе без наших слов.

REASONS: Dict[str, Tuple[str, str]] = {
    "no_words": (
        "в утверждении нет значимых слов для сверки",
        "the claim has no significant words to check against the graph",
    ),
    "no_candidate": (
        "ни один узел графа не содержит слов утверждения",
        "no node in the graph contains the words of this claim",
    ),
    "refuted": (
        "лучшая опора — узел {id} вида {kind}: память это утверждение отменила",
        "the closest support is node {id} of kind {kind}: memory has already "
        "withdrawn this claim",
    ),
    "supported": (
        "покрытие {cov} узлом {id}",
        "coverage {cov} against node {id}",
    ),
    "number_mismatch": (
        "слова из памяти (покрытие {cov}), но чисел {items} нет в опоре {id} "
        "— number_mismatch",
        "the words come from memory (coverage {cov}), but the numbers {items} "
        "are not in support {id} — number_mismatch",
    ),
    "missing_rare": (
        "слова из памяти (покрытие {cov}), но редких слов {items} нет "
        "в опоре {id} — missing_rare",
        "the words come from memory (coverage {cov}), but the rare terms "
        "{items} are not in support {id} — missing_rare",
    ),
    "value_mismatch": (
        "слова из памяти (покрытие {cov}), но значения полей {items} "
        "в опоре {id} другие — value_mismatch",
        "the words come from memory (coverage {cov}), but support {id} gives "
        "different values for the fields {items} — value_mismatch",
    ),
    "partial_coverage": (
        "частичное покрытие {cov} узлом {id}",
        "partial coverage {cov} against node {id}",
    ),
    "below_floor": (
        "покрытие {cov} ниже порога {need}",
        "coverage {cov} is below the {need} floor",
    ),
    "empty_query": (
        "пустой запрос",
        "the query is empty",
    ),
    "nothing_found": (
        "граф ничего не нашёл по запросу",
        "the graph found nothing for this query",
    ),
    "candidates_gone": (
        "кандидаты исчезли из стора",
        "the candidates disappeared from the store between search and check",
    ),
    "graph_first_thresholds": (
        "не прошли пороги graph-first: {items}",
        "graph-first thresholds not met: {items}",
    ),
    "no_pre_pass": (
        "no_pre_pass: перед ответом не было memory_ground_prepare/"
        "memory_prompt по этой сессии — либо пред-проход был, но не нашёл "
        "в графе ни одного узла, что то же самое: опереться было не на что",
        "no_pre_pass: this session ran no memory_ground_prepare/memory_prompt "
        "before the answer — or it ran and found no node at all, which comes "
        "to the same thing: there was nothing to lean on",
    ),
    "no_claims": (
        "в ответе не нашлось проверяемых утверждений",
        "the answer contains no checkable claims",
    ),
}

# Итоговый вердикт словами. Русская форма историческая
# (`passed_through_graph`), английская — для публичных поверхностей.
HUMAN_RU = {"grounded": "да", "partial": "частично", "ungrounded": "нет"}
HUMAN_EN = {"grounded": "yes", "partial": "partly", "ungrounded": "no"}


def explain(code: str, **kw: Any) -> Dict[str, str]:
    """Одно объяснение в четырёх видах: код, `reason` (язык поверхности),
    `reason_en`, `reason_ru`.

    `reason` с правило английский по умолчанию: его читает пользователь
    публичного `baron`. Русский остаётся в `reason_ru` и возвращается в
    `reason` целиком при BARON_LANG=ru; `reason_en` сохранён как алиас для
    внутренних потребителей (tools/site/verdict_service.py, демо).
    """
    ru, en = REASONS[code]
    ru_text, en_text = ru.format(**kw), en.format(**kw)
    return {
        "reason_code": code,
        "reason": i18n.pick(en_text, ru_text),
        "reason_en": en_text,
        "reason_ru": ru_text,
    }


# «Пред-проход» протухает: поиск, сделанный вчера, не заземляет сегодняшний
# ответ — граф между ними мог измениться (decay в 04:00, новые узлы).
PRE_PASS_TTL_SECONDS = 3600.0

MAX_CLAIMS = 24         # потолок разбора ответа (защита от простыни на 10 КБ)
# Редкая основа (wave2): встречается не более чем в RARE_DF_FRACTION узлов
# графа (но не менее RARE_DF_MIN). Утверждение, в котором есть редкая основа,
# отсутствующая в узле-опоре, не может быть supported: пересказ выбрасывает
# слова, но не приносит новых имён, чисел и значений — их приносит выдумка
# («Мария отвечает за …» при опоре «Кирилл отвечает за …»).
RARE_DF_FRACTION = 0.02
RARE_DF_MIN = 2
MIN_CLAIM_TOKENS = 2    # короче — не утверждение, а связка («Итак, вот:»)
TOP_SUPPORT = 3         # сколько узлов-опор показывать на утверждение
CANDIDATE_TOKENS = 8    # по скольким самым редким основам собирать кандидатов
MAX_CANDIDATES = 400    # потолок кандидатов на утверждение

# --- graph-first: ответ прямо из графа, без вызова LLM (ноль токенов) --------
# Порог откалиброван на 15 запросах ground_truth.json (замер 03.09,
# eval_grounding.py, таблица «КАЛИБРОВКА ПОРОГА»): 0.70 и выше не срабатывает
# ни разу, 0.60-0.65 срабатывают на 2-3 запросах и НИ РАЗУ не отдают узел не
# из эталона. Взят верхний край этого коридора: выборка мала (15 запросов), а
# цена ошибки тут — молча отданный пользователю неверный ответ вместо честного
# «не знаю». Клиент может опустить порог параметром threshold.
GRAPH_FIRST_COVERAGE = 0.65    # покрытие вопроса узлом (recall вопроса узлом)
GRAPH_FIRST_WEIGHT = 0.50      # вес узла с учётом затухания
GRAPH_FIRST_CONFIDENCE = 0.50  # уверенность узла (truth-gate score/6)
GRAPH_FIRST_MARGIN = 1.15      # во сколько раз лидер должен обойти второго

GROUND_LOG_NAME = "ground_log.jsonl"
GROUND_LOG_MAX_TAIL = 512 * 1024  # сколько байт хвоста журнала читать
# Потолки записи (баг-хант 03.09, D6). Ответ обрезался и раньше
# (answer_preview), а вопрос — нет: один вызов с мегабайтным query давал
# мегабайтную строку журнала. Журнал лежит рядом со стором, то есть у нас — в
# git-репозитории с автопушем каждые 5 минут; расти без границ ему нельзя.
GROUND_LOG_MAX_TEXT = 400          # вопрос и прочие длинные строковые поля
GROUND_LOG_MAX_BYTES = 16 * 1024 * 1024  # ротация: .jsonl -> .jsonl.1
GROUND_LOG_TRUNC_MARK = "…[обрезано]"
# Поля, которые обрезать нельзя: это идентификаторы и хеши — обрезанные, они
# врут (sha перестаёт сходиться, session_id перестаёт джойниться). Их длину
# ограничивает сервер на входе (MAX_ID_LEN), а не журнал на выходе.
GROUND_LOG_KEEP_WHOLE = ("answer_sha256", "session_id", "event", "ts")

# Шаблон для клиентов (приказ, п.2). Отдаётся в memory_ground_prepare, чтобы
# контракт ехал вместе с промптом, а не только жил в README.
def system_prompt(lang: Optional[str] = None) -> str:
    """Инструкции MCP-сервера клиенту: English по умолчанию.

    Их читает модель на том конце, и по умолчанию это англоязычный клиент
    публичного `baron`; русский возвращается целиком при BARON_LANG=ru.
    """
    return i18n.pick(
        "You have the team memory (the Baron Munchausen MCP server). This order "
        "of work is mandatory and must not be broken:\n"
        "1. BEFORE answering call memory_ground_prepare(query=<the user's "
        "question>, session_id=<dialogue id>). It returns an excerpt from the "
        "memory graph and graph_first — a ready answer if memory already holds "
        "one.\n"
        "2. If graph_first.hit = true — return graph_first.answer as is and do "
        "NOT generate your own text: the answer is already in memory, "
        "generating would burn the user's tokens for nothing.\n"
        "3. Otherwise answer ONLY from the facts in the excerpt you were given. "
        "What is not in the excerpt you do not know: say so, do not make it "
        "up.\n"
        "4. AFTER answering call memory_ground(answer_text=<your answer>, "
        "session_id=<the same id>). If the verdict is not grounded — show the "
        "user the unconfirmed statements from unsupported_claims and do not "
        "pass them off as facts.",
        "У тебя есть память команды (MCP-сервер Baron Munchausen). Порядок работы "
        "обязателен и нарушать его нельзя:\n"
        "1. ДО ответа вызови memory_ground_prepare(query=<вопрос пользователя>, "
        "session_id=<id диалога>). Он вернёт выдержку из графа памяти и "
        "graph_first — готовый ответ, если он в памяти уже есть.\n"
        "2. Если graph_first.hit = true — отдай graph_first.answer как есть и "
        "НЕ генерируй свой текст: ответ уже в памяти, генерация сожжёт токены "
        "пользователя впустую.\n"
        "3. Иначе отвечай ТОЛЬКО на фактах из выданной выдержки. Чего нет в "
        "выдержке — того ты не знаешь: так и напиши, не додумывай.\n"
        "4. ПОСЛЕ ответа вызови memory_ground(answer_text=<твой ответ>, "
        "session_id=<тот же id>). Если вердикт не grounded — покажи "
        "пользователю неподтверждённые утверждения из unsupported_claims "
        "и не выдавай их за факты.",
        lang,
    )


# Совместимость: константа остаётся, но её значение — язык по умолчанию на
# момент импорта. Живым клиентам отдаётся system_prompt(), а не она.
SYSTEM_PROMPT_TEMPLATE = system_prompt()

# Разметка, которую надо снять перед разбором. Подчёркивание сюда НЕ входит
# специально: в этом графе оно живёт внутри путей и имён (proxy_pool.txt,
# alice_signal_decision, /opt/migration_backup/...), то есть ровно в самых
# различающих токенах. Стирая «_» как markdown-выделение, мы разбивали такой
# токен надвое и теряли опору: узел с точной цитатой пути переставал
# подтверждать ответ с этим путём.
_MD_NOISE = re.compile(
    r"\*+|`+|~~|^[ \t]*#{1,6}[ \t]+|^[ \t]*>[ \t]?", re.MULTILINE
)
_BULLET = re.compile(r"^\s*(?:[-*•—]|\d+[.)])\s+")
# Markdown-таблица (wave2): строка-разделитель |---|---| выбрасывается вместе
# с заголовком над ней, строка данных превращается в одно утверждение
# «ячейка, ячейка, ячейка» — иначе «|» уходил в токены, а разделитель давал
# пустое утверждение.
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
_SENT_SPLIT = re.compile(
    r"(?<=[.!?…])\s+(?=[«\"'(\[]?[A-ZА-ЯЁ0-9])"   # конец предложения
    r"|[\n\r]+"                                     # перевод строки
    r"|\s*;\s+"                                     # точка с запятой
)
# Число: 12, 0.75, 1,5, 2x3090, 12345678, 13:10, 90%. Проценты и разделители
# нормализуются в _numbers, чтобы «0,75» и «0.75» считались одним числом.
_NUM = re.compile(r"\d+(?:[.,:]\d+)*")
# Служебные зачины — это не утверждения о мире, проверять их нечего.
_META = re.compile(
    r"^\s*(вот|итак|ниже|коротко|кратко|резюме|итого|проверил|проверила|"
    r"смотри|смотрите|отвечаю|поясню|например|то есть|здесь|тут|"
    r"here|so|ok|okay|summary|in short|note)\b[\s,:—-]*$",
    re.IGNORECASE,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime] = None) -> str:
    return (dt or _now()).isoformat(timespec="milliseconds")


def _parse_iso(ts: Any) -> Optional[datetime]:
    if not isinstance(ts, str) or not ts.strip():
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


# ============================================================================
# Разбор ответа на утверждения
# ============================================================================

# Код в ответе — не утверждение о мире (аудит 05.09). Строки fenced-блока
# ```…``` резались по переводам строк на «утверждения», inline-код `…` уходил
# в сверку слов и чисел, и верный ответ кодинг-агента получал partial из-за
# `MCPHttpServer((host, port), store)`. Код вырезается ДО разбиения и
# заменяется плейсхолдером, которого tokens() не видит: кусок из одного
# плейсхолдера отбрасывается как пустой, а «Таймаут задаётся в […]» теряет
# только сам код и сверяется по оставшимся словам.
_FENCED_CODE = re.compile(r"(```|~~~).*?(?:\1|\Z)", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`\n]+`")
CODE_PLACEHOLDER = "[…]"
# Обвязка кода («В коде это […]») — подпись к коду, а не факт: без кода в ней
# остаётся пара служебных слов, и сверять их с графом бессмысленно. Кусок с
# плейсхолдером считается утверждением, только если значимых основ в нём не
# меньше MIN_CODE_CAPTION_TOKENS.
MIN_CODE_CAPTION_TOKENS = 3


def strip_code(text: str) -> str:
    """Заменяет fenced-блоки и inline-код плейсхолдером CODE_PLACEHOLDER.

    Fenced-блок заменяется с переводами строк по краям, чтобы текст до и после
    него не склеился в одно утверждение. Незакрытый ``` режется до конца
    текста: обрывок кода утверждением быть не может.
    """
    text = _FENCED_CODE.sub("\n" + CODE_PLACEHOLDER + "\n", str(text or ""))
    return _INLINE_CODE.sub(CODE_PLACEHOLDER, text)


_PH = re.compile("\x00(\\d+)\x00")


def _flatten_tables(text: str) -> str:
    """Markdown-таблицы -> строки «ячейка, ячейка». Заголовок и разделитель
    выбрасываются (это не факты, а названия колонок)."""
    lines = text.split("\n")
    out: List[str] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if _TABLE_SEP.match(ln):
            i += 1
            continue
        if _TABLE_ROW.match(ln):
            if i + 1 < len(lines) and _TABLE_SEP.match(lines[i + 1]):
                i += 2  # заголовок + разделитель
                continue
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            out.append(", ".join(c for c in cells if c))
            i += 1
            continue
        out.append(ln)
        i += 1
    return "\n".join(out)


def split_claims_ex(text: str, max_claims: int = MAX_CLAIMS) -> List[Dict[str, Any]]:
    """Как split_claims, но каждое утверждение несёт и свой код (wave2):
    inline-код из того же предложения и fenced-блок сразу под ним. Сам текст
    утверждения — без кода, как раньше; код сверяется отдельно и только с
    узлом, у которого код есть (см. verify_claim)."""
    if not isinstance(text, str) or not text.strip():
        return []
    snippets: List[str] = []

    def _fence(m: "re.Match[str]") -> str:
        snippets.append(m.group(0))
        return f"\n\x00{len(snippets) - 1}\x00\n"

    def _inline(m: "re.Match[str]") -> str:
        snippets.append(m.group(0))
        return f"\x00{len(snippets) - 1}\x00"

    marked = _INLINE_CODE.sub(_inline, _FENCED_CODE.sub(_fence, _flatten_tables(str(text))))
    out: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for piece in _SENT_SPLIT.split(marked):
        if piece is None:
            continue
        codes = [snippets[int(i)] for i in _PH.findall(piece)]
        piece = _PH.sub(CODE_PLACEHOLDER, piece)
        s = _BULLET.sub("", _MD_NOISE.sub(" ", piece)).strip()
        if s.endswith("?"):
            continue  # вопрос — не утверждение, проверять нечего
        s = s.strip(" \t\r\n-—:;.!…")
        dropped = False
        if not s or _META.match(s):
            dropped = True
        else:
            n_tokens = len(tokens(s))
            if n_tokens < MIN_CLAIM_TOKENS:
                dropped = True
            elif CODE_PLACEHOLDER in s and n_tokens < MIN_CODE_CAPTION_TOKENS:
                dropped = True  # подпись к коду, а не утверждение
        if dropped:
            if codes and out:
                out[-1]["code"].extend(codes)  # код под утверждением — его код
            continue
        key = norm(s) + "\x00" + norm(" ".join(codes))
        if key in seen:      # повтор одного и того же тезиса не должен
            continue         # ни улучшать, ни ухудшать долю подтверждённых
        seen.add(key)        # (тезис с ДРУГИМ кодом — другое утверждение)
        out.append({"claim": s, "code": codes})
        if len(out) >= max_claims:
            break
    return out


def split_claims(text: str, max_claims: int = MAX_CLAIMS) -> List[str]:
    """Режет ответ агента на проверяемые утверждения.

    Выбрасывает код (см. strip_code), вопросы (агент спрашивает, а не
    утверждает), служебные зачины и обрывки короче MIN_CLAIM_TOKENS значимых
    основ: «Итак:» проверять нечем, и попытка это сделать только размывает
    итоговую долю. Предложение с маленькой буквы после точки и перевода
    строки — отдельное утверждение: перевод строки режет всегда, независимо
    от регистра следующего символа (ветка [\\n\\r]+ в _SENT_SPLIT).
    """
    return [c["claim"] for c in split_claims_ex(text, max_claims=max_claims)]


_CODE_NOISE = re.compile(r"[`\s]+")


def code_text(snippets: Iterable[str]) -> str:
    """Код утверждения одной строкой без обратных кавычек и языка fence."""
    parts: List[str] = []
    for snip in snippets:
        s = str(snip or "")
        if s.startswith(("```", "~~~")):
            s = s[3:]
            s = re.sub(r"^[A-Za-z0-9_+-]*\n", "", s, count=1)  # ```python
            s = s.rstrip("`~")
        parts.append(s.strip("`").strip())
    return " ".join(p for p in parts if p)


def _norm_num(raw: str) -> str:
    """Число в нормальной форме: 0,75 -> 0.75, 12.50 -> 12.5, «90%» -> 90."""
    v = raw.replace(",", ".")
    if "." in v and ":" not in v:
        v = v.rstrip("0").rstrip(".") or "0"
    return v


def _numbers(text: str) -> Set[str]:
    """Множество чисел текста (без контекста)."""
    return {_norm_num(m) for m in _NUM.findall(str(text or ""))}


_WORD = re.compile(r"[^\s]+")


def number_contexts(text: str) -> Dict[str, Set[str]]:
    """Числа текста с соседями: {число: {"<основа-слева", ">основа-справа"}}.

    Голой сверки множеств чисел мало, и это видно на замере 03.09: ответ
    «ПРАВИЛО 2 Акмеа» подтверждался узлом «ПРАВИЛО 1 Акмеа ... В2 свежее
    доказательство» — двойка в узле есть, но совсем не та. Соседнее слово
    привязывает число к тому, что оно измеряет.

    Соседи берутся по СЛОВАМ (не по токенам поиска), потому что число часто
    сидит внутри слова: «В2», «2x3090», «ЧЕК-5».

    Ключ «=основа» — само слово, внутри которого стоит число. Оно сильнее
    любых соседей: если и в ответе, и в узле написано «0xE606...», число
    подтверждено, что бы вокруг ни стояло. Без этого ключа честный пересказ,
    выбросивший соседнее слово, ловил ложную тревогу (замер 03.09, D12).
    """
    words = _WORD.findall(str(text or ""))
    stems = [stem_of(w) for w in words]
    out: Dict[str, Set[str]] = defaultdict(set)
    for i, w in enumerate(words):
        for m in _NUM.findall(w):
            v = _norm_num(m)
            if stems[i]:
                out[v].add("=" + stems[i])
            if i > 0 and stems[i - 1]:
                out[v].add("<" + stems[i - 1])
            if i + 1 < len(words) and stems[i + 1]:
                out[v].add(">" + stems[i + 1])
    return out


def stem_of(word: str) -> str:
    """Основа слова-соседа: та же нормализация, что у поиска (6 символов)."""
    toks = tokens(word, min_len=2)
    return toks[0] if toks else ""


# «поле: значение» — одно слово-поле, двоеточие, одно слово-значение.
# `(?!//)` отсекает схему URL: в «https://api.svc.io» двоеточие не поле.
_FIELD = re.compile(r"(?<![\w/])([A-Za-zА-Яа-яЁё][\w.-]{0,31})\s*:\s*(?!//)([^\s|,;]+)")


def field_values(text: str) -> Dict[str, Set[str]]:
    """Пары «поле: значение» текста: {поле: {значения}}.

    Замер mn_example: 8 промахов из 8 — одно семейство. Ответ дословно
    повторяет узел каталога, но `auth: apiKey` подменён на `auth: OAuth`, а
    `https: yes` на `https: no`. Покрытие считается по основам слов, и
    подменённое значение не число (жёсткая сверка чисел его не видит) и не
    редкая основа (`oauth`, `yes`, `no` встречаются в каталоге десятками) —
    гейт отвечал grounded. Значение поля обязано сверяться со значением.

    Поле и значение нормализуются в нижний регистр, хвостовая пунктуация
    снимается: «https: yes.» и «HTTPS: YES» — одно и то же.
    """
    out: Dict[str, Set[str]] = defaultdict(set)
    for field, value in _FIELD.findall(str(text or "")):
        v = norm(value.strip(".,;:!?)]}»\"'"))
        if v:
            out[norm(field)].add(v)
    return out


def values_conflicting(claim_fields: Dict[str, Set[str]],
                       node_fields: Dict[str, Set[str]]) -> List[str]:
    """Поля, которые есть в обоих текстах, но со всеми разными значениями.

    Поле, которого в опоре нет вовсе, — не подмена, а лишнее слово: его ловят
    покрытие и редкие основы. Подмена — это когда узел про то же поле говорит
    другое.
    """
    bad = [f for f, vals in claim_fields.items()
           if f in node_fields and not (vals & node_fields[f])]
    return sorted(bad)


def numbers_missing(claim_ctx: Dict[str, Set[str]],
                    node_ctx: Dict[str, Set[str]]) -> List[str]:
    """Числа утверждения, которых узел-опора не подтверждает.

    Число считается подтверждённым, если оно есть в узле И совпал хотя бы
    один сосед (слева или справа). Достаточно одного соседа: пересказ
    своими словами переставляет и выбрасывает слова, и требование обоих
    давало бы ложные тревоги на честном пересказе. Если соседей нет ни у
    одной из сторон (число стоит особняком) — засчитываем голое совпадение.
    """
    missing: List[str] = []
    for num, ctx in claim_ctx.items():
        if num not in node_ctx:
            missing.append(num)
            continue
        node_side = node_ctx[num]
        if ctx and node_side and not (ctx & node_side):
            missing.append(num)
    return sorted(missing)


# ============================================================================
# Индекс опор поверх BudgetSearch
# ============================================================================

class SupportIndex:
    """Обратный индекс основа -> узлы поверх готового BudgetSearch.

    Строится один раз на движок и живёт вместе с ним: движок обновляется
    точечно при каждой записи (wave2) и зовёт upsert/remove у своих
    listeners — этот индекс среди них. Полная пересборка на 1000 узлов
    стоила 57 мс на каждый ход контракта (number_contexts всех узлов).
    """

    __slots__ = ("engine", "inv", "nums", "fields", "by_node", "_unseen")

    def __init__(self, engine: Any) -> None:
        self.engine = engine
        self.inv: Dict[str, Dict[str, None]] = {}
        self.nums: Dict[str, Dict[str, Set[str]]] = {}
        self.fields: Dict[str, Dict[str, Set[str]]] = {}
        self.by_node: Dict[str, Set[str]] = {}
        self._unseen: Tuple[int, float] = (-1, 1.0)
        for nid, n in engine.nodes.items():
            self._index(nid, n)

    def _index(self, nid: str, n: Dict[str, Any]) -> None:
        if n.get("kind") == KIND_HUB:
            return  # хаб — навигация, а не факт: опорой быть не может
        toks = self.engine.toks.get(nid) or set()
        self.by_node[nid] = toks
        for s in toks:
            self.inv.setdefault(s, {})[nid] = None
        text = node_text(n)
        self.nums[nid] = number_contexts(text)
        self.fields[nid] = field_values(text)

    def _unindex(self, nid: str) -> None:
        for s in self.by_node.pop(nid, ()):
            bucket = self.inv.get(s)
            if bucket is not None:
                bucket.pop(nid, None)
                if not bucket:
                    del self.inv[s]
        self.nums.pop(nid, None)
        self.fields.pop(nid, None)

    def upsert(self, nid: str, n: Dict[str, Any]) -> None:
        self._unindex(nid)
        self._index(nid, n)

    def remove(self, nid: str) -> None:
        self._unindex(nid)

    @classmethod
    def of(cls, engine: Any) -> "SupportIndex":
        idx = getattr(engine, "_ground_index", None)
        if idx is None:
            idx = cls(engine)
            try:
                engine._ground_index = idx
                listeners = getattr(engine, "listeners", None)
                if isinstance(listeners, list):
                    listeners.append(idx)
            except AttributeError:  # движок со __slots__ — просто не кэшируем
                pass
        return idx

    @property
    def unseen_idf(self) -> float:
        """Вес основы, которой в графе НЕТ ВООБЩЕ. BudgetSearch подставляет
        таким основам 1.0 — для поиска это неважно (их всё равно никто не
        matched), а для grounding это переворачивает смысл: слово, которого
        память не знает, — самый сильный признак выдумки, а получает вес
        меньше, чем любая известная редкая основа (на 5000 узлов idf редкой
        основы ~8.5 против 1.0). Тогда ответ, где половина слов выдумана,
        набирал высокое покрытие за счёт второй половины. Незнакомая основа
        весит как самая редкая известная. Пересчёт — лениво по версии idf."""
        idf = self.engine.idf
        ver = getattr(self.engine, "idf_version", 0)
        if self._unseen[0] != ver:
            self._unseen = (ver, max(idf.values(), default=1.0))
        return self._unseen[1]

    def idf(self, token: str) -> float:
        """Вес основы: известной — её idf, незнакомой — вес самой редкой."""
        return self.engine.idf.get(token, self.unseen_idf)

    def df(self, token: str) -> int:
        """В скольких узлах есть основа (0 — граф её не знает)."""
        df = getattr(self.engine, "_df", None)
        if isinstance(df, dict):
            return int(df.get(token, 0))
        return 1 if token in self.engine.idf else 0

    def is_rare(self, token: str) -> bool:
        n = max(1, int(getattr(self.engine, "_n_real", len(self.engine.nodes)) or 1))
        return self.df(token) <= max(RARE_DF_MIN, int(RARE_DF_FRACTION * n))

    def has_code(self, nid: str) -> bool:
        n = self.engine.nodes.get(nid) or {}
        return "`" in str(n.get("claim") or "") or "`" in str(n.get("context") or "")

    def qmass(self, qtoks: Iterable[str]) -> float:
        """Полная «масса» утверждения — знаменатель покрытия."""
        return sum(self.idf(t) for t in qtoks) or 1.0

    def coverage(self, nid: str, qtoks: List[str], qmass: float
                 ) -> Tuple[float, List[str]]:
        """Доля массы утверждения, покрытая узлом (0..1), и что совпало."""
        ntoks = self.engine.toks.get(nid) or set()
        matched = [t for t in qtoks if t in ntoks]
        got = sum(self.idf(t) for t in matched)
        return (got / qmass if qmass else 0.0), matched

    def candidates(self, qtoks: List[str]) -> List[str]:
        """Кандидаты в опоры: узлы, содержащие самые редкие основы запроса.

        Полный скан стора на каждое утверждение — это O(утверждений × узлов);
        на 5000 узлов и 24 утверждениях это заметно. Редкие основы дают тот же
        топ дешевле: узел без единой редкой основы утверждения всё равно не
        наберёт покрытия выше порога. Основы, которых в графе нет, из отбора
        выброшены: постинг-лист у них пустой, а место в лимите они занимают.
        """
        known = [t for t in set(qtoks) if t in self.inv]
        rare = sorted(known, key=lambda t: -self.idf(t))[:CANDIDATE_TOKENS]
        seen: Dict[str, None] = OrderedDict()
        for t in rare:
            for nid in self.inv.get(t, ()):
                seen.setdefault(nid, None)
                if len(seen) >= MAX_CANDIDATES:
                    return list(seen)
        return list(seen)


def _brief(n: Dict[str, Any], coverage: float, matched: List[str],
           nums_ok: Optional[bool] = None) -> Dict[str, Any]:
    """Краткая карточка узла-опоры. nums_ok=None — сверять было нечего
    (graph-first сверяет вопрос с узлом, а не утверждение ответа)."""
    out = {
        "id": n.get("id"),
        "kind": n.get("kind"),
        "claim": str(n.get("claim") or "")[:200],
        "source": n.get("source"),
        "ts": n.get("ts"),
        "weight": round(float(n.get("weight", 1.0) or 1.0), 4),
        "confidence": round(float(n.get("confidence", 0.5) or 0.5), 4),
        "coverage": round(coverage, 3),
        "matched": matched,
    }
    if nums_ok is not None:
        out["numbers_ok"] = nums_ok
    return out


def verify_claim(engine: Any, claim: str, code: Optional[List[str]] = None) -> Dict[str, Any]:
    """Сверяет одно утверждение с графом -> вердикт + узлы-опоры.

    Вердикты:
      supported   — покрытие >= SUPPORT_STRONG, все числа утверждения нашлись
                    в узле-опоре и нет редких основ, которых в опоре нет;
      partial     — покрытие >= SUPPORT_WEAK (или сильное покрытие, но число
                    не сошлось: слова из памяти, цифра выдумана; или редкое
                    слово/значение подменено — missing_rare);
      unsupported — в графе нет опоры;
      refuted     — лучшая опора найдена, но это узел kind=refuted/outdated:
                    ответ опирается на то, что память уже отменила.

    code (wave2) — сниппеты кода этого утверждения. Код сверяется с кодом:
    если у узла-опоры есть код, числа и редкие идентификаторы из кода ответа
    обязаны найтись в узле (`retries=4` против `retries=3` — подмена). Узел
    без кода код ответа не оценивает: кодинг-агент цитирует репозиторий, а не
    память, и это не выдумка.
    """
    idx = SupportIndex.of(engine)
    qtoks = list(dict.fromkeys(tokens(claim)))
    qnums_ctx = number_contexts(claim)
    qnums = set(qnums_ctx)
    qfields = field_values(claim)
    ctext = code_text(code or [])
    code_toks = [t for t in dict.fromkeys(tokens(ctext)) if t not in qtoks] if ctext else []
    code_nums_ctx = number_contexts(ctext) if ctext else {}
    empty = {
        "claim": claim, "verdict": "unsupported", "coverage": 0.0,
        **explain("no_words"),
        "numbers": {"in_claim": sorted(qnums), "matched": [], "missing": sorted(qnums)},
        "support": [],
    }
    if not qtoks:
        return empty
    qmass = idx.qmass(qtoks)

    live: List[Tuple[float, Dict[str, Any]]] = []
    stale: List[Tuple[float, Dict[str, Any]]] = []
    for nid in idx.candidates(qtoks):
        n = engine.nodes.get(nid)
        if n is None:
            continue
        cov, matched = idx.coverage(nid, qtoks, qmass)
        if cov <= 0.0:
            continue
        ntoks = engine.toks.get(nid) or set()
        missing = numbers_missing(qnums_ctx, idx.nums.get(nid, {}))
        # редкие основы утверждения, которых в опоре нет (подмена имени/значения)
        missing_rare = [t for t in qtoks if t not in ntoks and idx.is_rare(t)]
        if ctext and idx.has_code(nid):
            # код сверяется с кодом: числа и редкие идентификаторы сниппета
            missing += [x for x in numbers_missing(code_nums_ctx, idx.nums.get(nid, {}))
                        if x not in missing]
            missing_rare += [t for t in code_toks if t not in ntoks and idx.is_rare(t)]
        brief = _brief(n, cov, matched, not missing)
        brief["numbers_missing"] = missing
        brief["missing_rare"] = missing_rare
        # подмена значения поля: узел говорит про то же поле другое
        brief["values_conflict"] = values_conflicting(qfields,
                                                      idx.fields.get(nid, {}))
        (stale if n.get("kind") in ("refuted", "outdated") else live).append((cov, brief))
    # Лучшая опора — по покрытию, а при равном покрытии та, с которой
    # сходятся числа и редкие слова: у шаблонных утверждений («retries are
    # set with […]», пересказ без имени сервиса) покрытие 1.0 дают сразу
    # несколько узлов, и различает их только число или код.
    live.sort(key=lambda t: (-t[0], len(t[1]["numbers_missing"]) + len(t[1]["missing_rare"])))
    stale.sort(key=lambda t: (-t[0], len(t[1]["numbers_missing"]) + len(t[1]["missing_rare"])))

    if not live and not stale:
        return {**empty, **explain("no_candidate")}

    best_cov, best = (live[0] if live else (0.0, None))
    stale_cov, stale_best = (stale[0] if stale else (0.0, None))

    # Опора на отменённую память — отдельный, самый громкий вердикт: ответ
    # звучит подтверждённым, а подтверждает его узел, который память отменила.
    if stale_best is not None and stale_cov >= SUPPORT_STRONG and stale_cov >= best_cov:
        return {
            "claim": claim, "verdict": "refuted", "coverage": round(stale_cov, 3),
            **explain("refuted", id=stale_best["id"], kind=stale_best["kind"]),
            "numbers": {"in_claim": sorted(qnums),
                        "matched": sorted(qnums - set(stale_best["numbers_missing"])),
                        "missing": stale_best["numbers_missing"]},
            "support": [s for _, s in stale[:TOP_SUPPORT]],
        }

    if best is None:
        best_cov, best = stale_cov, stale_best

    # Числа сверяем по узлу-опоре, а не по всему графу: «0.944» из другого
    # исследования не подтверждает цифру в этом утверждении.
    missing = list(best["numbers_missing"])
    missing_rare = list(best["missing_rare"])
    conflict = list(best.get("values_conflict") or ())
    matched_nums = sorted(qnums - set(missing))
    cov_s = f"{best_cov:.2f}"
    if conflict:
        # Слова взяты из узла, но значение поля узел называет другое. Это не
        # «половина ответа мимо», а прямое расхождение с памятью, и вердикт
        # у него самый строгий из доступных: подтверждать тут нечего.
        verdict = "unsupported"
        why = explain("value_mismatch", cov=cov_s, id=best["id"],
                      items=", ".join(conflict[:4]))
    elif best_cov >= SUPPORT_STRONG and not missing and not missing_rare:
        verdict = "supported"
        why = explain("supported", cov=cov_s, id=best["id"])
    elif best_cov >= SUPPORT_STRONG and missing:
        verdict = "partial"
        why = explain("number_mismatch", cov=cov_s, id=best["id"],
                      items=", ".join(missing))
    elif best_cov >= SUPPORT_STRONG and missing_rare:
        verdict = "partial"
        why = explain("missing_rare", cov=cov_s, id=best["id"],
                      items=", ".join(missing_rare[:4]))
    elif best_cov >= SUPPORT_WEAK:
        verdict = "partial"
        why = explain("partial_coverage", cov=cov_s, id=best["id"])
    else:
        verdict = "unsupported"
        why = explain("below_floor", cov=cov_s, need=SUPPORT_WEAK)

    return {
        "claim": claim, "verdict": verdict, "coverage": round(best_cov, 3),
        **why,
        "numbers": {"in_claim": sorted(qnums), "matched": matched_nums,
                    "missing": missing},
        "support": [s for _, s in (live or stale)[:TOP_SUPPORT]],
    }


# ============================================================================
# Итоговый вердикт по ответу
# ============================================================================

def _aggregate(claims: List[Dict[str, Any]]) -> Tuple[str, float, Dict[str, int]]:
    counts = {"total": len(claims), "supported": 0, "partial": 0,
              "unsupported": 0, "refuted": 0}
    for c in claims:
        counts[c["verdict"]] = counts.get(c["verdict"], 0) + 1
    if not claims:
        return "ungrounded", 0.0, counts
    # частичное подтверждение считаем половиной: ответ, где всё «похоже на
    # правду, но без опоры», не должен получать тот же вердикт, что ответ,
    # каждое утверждение которого лежит в графе.
    ratio = (counts["supported"] + 0.5 * counts["partial"]) / counts["total"]
    if not counts["supported"]:
        # «частично прошёл через граф» обязано означать «часть ответа граф
        # подтвердил». Без единого подтверждённого утверждения подтверждать
        # нечего: замер 03.09 показал 5 ответов, выдуманных целиком, которым
        # одно только лексическое сходство («кошелёк», «ключи», «трейдера»)
        # давало ratio 0.5 и успокаивающий вердикт partial.
        return "ungrounded", round(ratio, 3), counts
    if counts["refuted"]:
        verdict = "ungrounded" if ratio < GROUNDED_RATIO else "partial"
    elif ratio >= GROUNDED_RATIO and not counts["unsupported"]:
        # grounded — это обещание «в ответе нет ничего мимо памяти», поэтому
        # одного неподтверждённого утверждения достаточно, чтобы его снять.
        # Иначе длина ответа разбавляет выдумку: замер 03.09, D03 — пять
        # подтверждённых предложений и одно ложное давали ratio 0.83 и
        # вердикт grounded, хотя ложное утверждение было честно помечено.
        verdict = "grounded"
    elif ratio >= PARTIAL_RATIO:
        verdict = "partial"
    else:
        verdict = "ungrounded"
    return verdict, round(ratio, 3), counts


_HUMAN = HUMAN_RU


def ground_answer(
    store: Any,
    answer_text: str,
    query: str = "",
    pre_pass: Optional[Dict[str, Any]] = None,
    require_pre_pass: bool = True,
    max_claims: int = MAX_CLAIMS,
) -> Dict[str, Any]:
    """Прогоняет готовый ответ агента через граф.

    pre_pass — запись пред-прохода (см. GroundLog.find_pre_pass) или None.
    require_pre_pass=True (умолчание, приказ Ильи): без пред-прохода итоговый
    вердикт — ungrounded, даже если все утверждения подтвердились. Вердикт по
    самим утверждениям при этом не теряется: он лежит в claims_verdict.

    unsupported_claims перечисляет КАЖДОЕ утверждение, которое граф не
    подтвердил целиком (unsupported, refuted, partial). Инвариант: вердикт
    partial без единой строки в этом списке невозможен — «частично» обязано
    называть ту часть, которая не прошла.
    """
    parsed = split_claims_ex(answer_text, max_claims=max_claims)
    claim_texts = [c["claim"] for c in parsed]
    with store._lock, trace.phase("verify"):
        # под локом стора: движок обновляется точечно при записи (wave2), и
        # параллельный memory_add не должен менять индекс посреди сверки
        engine = store._budget_engine()
        claims = [verify_claim(engine, c["claim"], code=c["code"]) for c in parsed]
    claims_verdict, ratio, counts = _aggregate(claims)

    pre_ok = bool(pre_pass)
    verdict = claims_verdict
    notes: List[str] = []
    notes_en: List[str] = []
    notes_ru: List[str] = []
    if require_pre_pass and not pre_ok:
        verdict = "ungrounded"
        why = explain("no_pre_pass")
        notes.append(why["reason"])
        notes_en.append(why["reason_en"])
        notes_ru.append(why["reason_ru"])
    if not claim_texts:
        why = explain("no_claims")
        notes.append(why["reason"])
        notes_en.append(why["reason_en"])
        notes_ru.append(why["reason_ru"])

    # узлы-источники: уникальные опоры подтверждённых и частичных утверждений
    sources: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
    for c in claims:
        if c["verdict"] in ("unsupported",):
            continue
        for s in c["support"]:
            prev = sources.get(s["id"])
            if prev is None or s["coverage"] > prev["coverage"]:
                sources[s["id"]] = s
    ordered = sorted(sources.values(), key=lambda s: -s["coverage"])

    return {
        "verdict": verdict,
        "passed_through_graph": i18n.pick(HUMAN_EN[verdict], _HUMAN[verdict]),
        "passed_through_graph_en": HUMAN_EN[verdict],
        "passed_through_graph_ru": _HUMAN[verdict],
        "claims_verdict": claims_verdict,
        "grounded_ratio": ratio,
        "counts": counts,
        "query": query,
        "pre_pass": pre_pass or {"present": False},
        "require_pre_pass": bool(require_pre_pass),
        "notes": notes,
        "notes_en": notes_en,
        "notes_ru": notes_ru,
        "claims": claims,
        # Всё, что граф НЕ подтвердил целиком: unsupported, refuted и partial.
        # Раньше сюда шли только unsupported/refuted, и вердикт partial можно
        # было получить с пустым списком: ответ «частично прошёл через граф», а
        # что именно не прошло — не сказано. Пункт 4 политики («покажи
        # пользователю неподтверждённые утверждения») в таком ответе было
        # нечего выполнять, и самый опасный случай — подменённое значение или
        # полупамять (покрытие 0.3-0.6) — молча выпадал из отчёта. Вердикт
        # утверждения остаётся в поле verdict каждого элемента, так что
        # «выдумал» и «вспомнил половину» по-прежнему различимы.
        "unsupported_claims": [
            {"claim": c["claim"], "verdict": c["verdict"],
             "reason": c["reason"], "reason_en": c["reason_en"],
             "reason_ru": c["reason_ru"], "reason_code": c["reason_code"]}
            for c in claims if c["verdict"] != "supported"
        ],
        "source_nodes": ordered,
        "source_node_ids": [s["id"] for s in ordered],
        "thresholds": {
            "support_strong": SUPPORT_STRONG, "support_weak": SUPPORT_WEAK,
            "grounded_ratio": GROUNDED_RATIO, "partial_ratio": PARTIAL_RATIO,
        },
        "answer_tokens": estimate_tokens(answer_text),
    }


# ============================================================================
# graph-first: ответ из графа без вызова LLM (ноль токенов генерации)
# ============================================================================

def graph_first(
    store: Any,
    query: str,
    coverage_threshold: float = GRAPH_FIRST_COVERAGE,
    min_weight: float = GRAPH_FIRST_WEIGHT,
    min_confidence: float = GRAPH_FIRST_CONFIDENCE,
    margin: float = GRAPH_FIRST_MARGIN,
    search: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Есть ли в графе готовый ответ — так, чтобы LLM звать не пришлось.

    Условия попадания (все сразу, иначе hit=false):
      * узел покрывает вопрос на coverage_threshold и выше (recall вопроса);
      * узел живой (не refuted/outdated/hub, TTL не истёк) и это факт/правило;
      * вес с учётом затухания >= min_weight, уверенность >= min_confidence;
      * лидер обходит второго кандидата не меньше чем в margin раз — иначе
        в графе два разных ответа, и выбирать между ними должна модель,
        а не порог.

    search — уже посчитанный store.search_budget(query) (чтобы не искать дважды).
    """
    q = str(query or "").strip()
    if not q:
        return {"hit": False, **explain("empty_query"), "answer": None}
    if search is None:
        search = store.search_budget(q)
    results = list(search.get("results") or [])
    if not results:
        return {"hit": False, **explain("nothing_found"),
                "answer": None, "candidates": 0}

    qtoks = list(dict.fromkeys(tokens(q)))
    now = _now()
    scored: List[Tuple[float, Dict[str, Any], Dict[str, Any]]] = []
    with store._lock:
        engine = store._budget_engine()
        idx = SupportIndex.of(engine)
        qmass = idx.qmass(qtoks)
        for r in results:
            n = engine.nodes.get(r["id"])
            if n is None:
                continue
            cov, matched = idx.coverage(r["id"], qtoks, qmass)
            scored.append((cov, r, {"matched": matched}))
    scored.sort(key=lambda t: -t[0])
    if not scored:
        return {"hit": False, **explain("candidates_gone"),
                "answer": None, "candidates": 0}

    cov, top, why = scored[0]
    node = engine.nodes.get(top["id"]) or store.get(top["id"]) or {}
    from .budget import _active, _decayed_weight  # локально: только тут нужны

    weight = _decayed_weight(node, now)
    conf = float(node.get("confidence", 0.5) or 0.5)
    runner_up = scored[1][0] if len(scored) > 1 else 0.0
    checks = {
        "coverage": {"value": round(cov, 3), "need": coverage_threshold,
                     "pass": cov >= coverage_threshold},
        "weight": {"value": round(weight, 3), "need": min_weight,
                   "pass": weight >= min_weight},
        "confidence": {"value": round(conf, 3), "need": min_confidence,
                       "pass": conf >= min_confidence},
        "kind": {"value": node.get("kind"), "need": "fact|rule|api",
                 "pass": node.get("kind") in ("fact", "rule", "api")},
        "active": {"value": True, "need": True, "pass": _active(node, now)},
        "margin": {"value": round(cov / runner_up, 3) if runner_up > 0 else None,
                   "need": margin,
                   "pass": runner_up <= 0.0 or cov >= runner_up * margin},
    }
    failed = [k for k, v in checks.items() if not v["pass"]]
    if failed:
        return {
            "hit": False, "answer": None,
            **explain("graph_first_thresholds", items=", ".join(failed)),
            "checks": checks, "candidates": len(scored),
            "best_node": top["id"], "best_coverage": round(cov, 3),
        }
    return {
        "hit": True,
        "answer": str(node.get("claim") or ""),
        "node_id": top["id"],
        "node": _brief(node, cov, why["matched"]),
        "checks": checks,
        "candidates": len(scored),
        "llm_calls_saved": 1,
        # Честная бухгалтерия: сэкономлено ровно столько, сколько стоило бы
        # уехать в модель — контекст из памяти (мы его измерили) плюс сам
        # ответ. Размер генерации модели заранее неизвестен, поэтому здесь
        # только нижняя граница, и она так и подписана.
        "tokens_saved_min": int(search.get("tokens_used") or 0)
        + estimate_tokens(str(node.get("claim") or "")),
        "tokens_saved_note": (
            "нижняя граница: контекст памяти "
            f"{int(search.get('tokens_used') or 0)} токенов + ответ "
            f"{estimate_tokens(str(node.get('claim') or ''))}; генерация модели "
            "не учтена (её размер заранее неизвестен)"
        ),
    }


# ============================================================================
# Append-only журнал проходов
# ============================================================================

class GroundLog:
    """Append-only JSONL: каждый проход через граф — одна строка.

    Формат строки: {ts, event, agent, session_id, query, verdict, node_ids,
    counts, answer_sha256, answer_preview}. Файл только дописывается: разбор
    «почему агент так ответил» должен опираться на запись, сделанную в тот
    момент, а не на пересобранную задним числом.
    """

    # `counter` — движение узла-счётчика: выдача номера (memory_counter_take)
    # и запись номера, занятого мимо счётчика (memory_counter_reserve); какая
    # именно — в поле `op`. В бюджет
    # обращений дирижёра (START/FINAL) не входит намеренно: это не проход через
    # граф за фактами, а служебная выдача числа.
    EVENTS = ("prepare", "ground", "answer", "add", "recent", "counter")

    # T2.10: бюджет обращений дирижёра к памяти за сессию.
    START_EVENTS = ("prepare", "recent")
    FINAL_EVENTS = ("add", "ground")

    def __init__(self, path: Union[str, Path]) -> None:
        self.path = Path(path)

    @staticmethod
    def _clip(key: str, value: Any) -> Any:
        """Длинную строку — под потолок; идентификаторы и хеши — как есть."""
        if not isinstance(value, str) or key in GROUND_LOG_KEEP_WHOLE:
            return value
        if len(value) <= GROUND_LOG_MAX_TEXT:
            return value
        return value[:GROUND_LOG_MAX_TEXT] + GROUND_LOG_TRUNC_MARK

    def _rotate_if_big(self) -> Optional[Path]:
        """Отвести разросшийся журнал в .1 и начать новый. Зовётся ПОД замком.

        Append-only это не нарушает: ни одна запись не переписывается, файл
        целиком уезжает в сторону. Храним одно поколение — журнал живёт рядом
        со стором (у нас — в git-репозитории с автопушем), и расти бесконечно
        ему нельзя. Читатель и так смотрит только хвост GROUND_LOG_MAX_TAIL.
        """
        try:
            if self.path.stat().st_size < GROUND_LOG_MAX_BYTES:
                return None
        except OSError:
            return None
        rotated = self.path.with_name(self.path.name + ".1")
        try:
            os.replace(self.path, rotated)
        except OSError:
            return None
        return rotated

    def append(self, event: str, **fields: Any) -> Dict[str, Any]:
        if event not in self.EVENTS:
            raise ValueError(f"ground_log: event должен быть из {self.EVENTS}, "
                             f"получено {event!r}")
        rec = {"ts": _iso(), "event": event}
        rec.update({k: self._clip(k, v) for k, v in fields.items() if v is not None})
        line = json.dumps(rec, ensure_ascii=False) + "\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with trace.phase("journal"), locked_file(self.path):
            self._rotate_if_big()
            with open(self.path, "a", encoding="utf-8", newline="\n") as f:
                f.write(line)
                f.flush()
        return rec

    def _tail_lines(self, max_bytes: int = GROUND_LOG_MAX_TAIL) -> List[str]:
        """Хвост журнала: журнал растёт вечно, читать его целиком нельзя."""
        if not self.path.exists():
            return []
        try:
            size = self.path.stat().st_size
            with open(self.path, "rb") as f:
                if size > max_bytes:
                    f.seek(size - max_bytes)
                    f.readline()  # первая строка обрезана посередине — выкинуть
                raw = f.read()
        except OSError:
            return []
        return raw.decode("utf-8", errors="replace").splitlines()

    def read(self, limit: int = 50, session_id: Optional[str] = None,
             event: Optional[str] = None, agent: Optional[str] = None,
             ) -> List[Dict[str, Any]]:
        """Последние записи журнала (новые в конце), с фильтрами."""
        out: List[Dict[str, Any]] = []
        for raw in self._tail_lines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue  # оборванная строка параллельного писателя — пропуск
            if not isinstance(rec, dict):
                continue
            if session_id is not None and rec.get("session_id") != session_id:
                continue
            if event is not None and rec.get("event") != event:
                continue
            if agent is not None and rec.get("agent") != agent:
                continue
            out.append(rec)
        return out[-max(1, int(limit)):] if out else []

    def find_pre_pass(self, session_id: str, ttl_seconds: Optional[float] = None,
                      now: Optional[datetime] = None, agent: Optional[str] = None,
                      ) -> Optional[Dict[str, Any]]:
        """Свежий пред-проход этой сессии или None (протух/не было).

        agent (wave2): сначала ищется пред-проход ЭТОГО агента в сессии;
        если у агента своих записей нет — последний по сессии (клиент,
        который называет агента только в memory_ground).
        ttl_seconds=None читает PRE_PASS_TTL_SECONDS в момент вызова, а не
        в момент объявления функции: иначе порог нельзя было бы поменять
        в рантайме, а значение из значения по умолчанию застывало навсегда.
        """
        if not session_id:
            return None
        ttl = PRE_PASS_TTL_SECONDS if ttl_seconds is None else float(ttl_seconds)
        now = now or _now()
        records = self.read(limit=2000, session_id=session_id)
        if agent:
            mine = [r for r in records if r.get("agent") == agent
                    and r.get("event") in ("prepare", "answer")]
            if mine:
                records = mine
        for rec in reversed(records):
            if rec.get("event") not in ("prepare", "answer"):
                continue
            ts = _parse_iso(rec.get("ts"))
            if ts is None:
                continue
            age = (now - ts).total_seconds()
            if age > ttl:
                return None  # записи идут по времени: дальше только старее
            if not (rec.get("node_ids") or []):
                # то же правило, что в SessionTracker.get (D2): последний
                # пред-проход этой сессии ничего не нашёл — значит прохода нет
                return None
            return {
                "present": True, "session_id": session_id, "ts": rec.get("ts"),
                "agent": rec.get("agent"),
                "age_seconds": round(age, 3), "tool": rec.get("tool"),
                "query": rec.get("query"), "node_ids": rec.get("node_ids") or [],
                "source": "log",
            }
        return None


def handoff_call_budget(records: List[Dict[str, Any]],
                        start_max: int = 2, final_max: int = 2) -> Dict[str, Any]:
    """T2.10: счётчик обращений дирижёра к памяти за сессию по журналу.

    Начало сессии — checkpoint (событие `prepare`) плюс не более одного
    `memory_recent` (событие `recent`); финал — один `memory_add` (событие
    `add`) плюс один `memory_ground` (событие `ground`). События `answer`
    (graph-first) в бюджет не входят: это ответ из графа, а не обращение
    дирижёра за новым проходом.
    """
    events = [str(r.get("event") or "") for r in records]
    start = sum(e in GroundLog.START_EVENTS for e in events)
    final = sum(e in GroundLog.FINAL_EVENTS for e in events)
    return {
        "start_calls": start, "start_max": int(start_max),
        "final_calls": final, "final_max": int(final_max),
        "ok": start <= int(start_max) and final <= int(final_max),
    }


class SessionTracker:
    """Пред-проходы в памяти процесса — быстрый путь для find_pre_pass.

    Журнал остаётся источником правды (переживает рестарт), но ходить в файл
    на каждый memory_ground не нужно: ответ приходит через секунды после
    подготовки, в том же процессе.
    """

    def __init__(self, capacity: int = 512) -> None:
        self.capacity = max(1, int(capacity))
        self._data: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        self._lock = threading.Lock()

    @staticmethod
    def _key(session_id: str, agent: Optional[str]) -> str:
        return f"{session_id}\x00{agent}" if agent else session_id

    def register(self, session_id: str, **fields: Any) -> None:
        """Пред-проход сессии. Несколько агентов в одной сессии (wave2):
        запись хранится и под ключом (session_id, agent), и под голым
        session_id (последний по времени) — memory_ground того же агента
        получает СВОЙ пред-проход, а не чужой, даже если prepare шли
        параллельно и перемешались."""
        if not session_id:
            return
        rec = {"ts": _iso(), **fields}
        agent = fields.get("agent")
        with self._lock:
            for key in dict.fromkeys((self._key(session_id, agent), session_id)):
                self._data[key] = rec
                self._data.move_to_end(key)
            while len(self._data) > self.capacity:
                self._data.popitem(last=False)

    def get(self, session_id: str, ttl_seconds: Optional[float] = None,
            now: Optional[datetime] = None, agent: Optional[str] = None,
            ) -> Optional[Dict[str, Any]]:
        with self._lock:
            rec = self._data.get(self._key(session_id, agent)) if agent else None
            if rec is None:
                rec = self._data.get(session_id)
        if rec is None:
            return None
        if not rec.get("node_ids"):
            # Пустой пред-проход — не проход (баг-хант 03.09, D2). Поиск,
            # который не нашёл в графе НИЧЕГО, не мог заземлить ответ: засчитав
            # его, мы выдавали бы «прошёл через граф: да» за один лишь факт
            # вызова инструмента с этим session_id.
            return None
        ts = _parse_iso(rec.get("ts"))
        if ts is None:
            return None
        ttl = PRE_PASS_TTL_SECONDS if ttl_seconds is None else float(ttl_seconds)
        age = ((now or _now()) - ts).total_seconds()
        if age > ttl:
            return None
        return {"present": True, "session_id": session_id, "ts": rec.get("ts"),
                "agent": rec.get("agent"),
                "age_seconds": round(age, 3), "tool": rec.get("tool"),
                "query": rec.get("query"), "node_ids": rec.get("node_ids") or [],
                "source": "memory"}


def answer_sha256(text: str) -> str:
    """Отпечаток ответа для журнала: сам ответ в журнал целиком не кладём."""
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()
