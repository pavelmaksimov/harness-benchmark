# -*- coding: utf-8 -*-
"""Baron Munchausen: гейты качества памяти (Г1-Г5), импортируемый модуль.

Контракт — из gates_research.md, §7. Пять гейтов поверх truth-gate П1-П6:

  Г1 CONFIDENCE-GATE   — «уверенность автора»: зыбкие формулировки не
                         попадают в память как факты (verimem: abstention).
  Г2 STALENESS-GATE    — «свежесть»: volatile-темы (курс/статус/версия…)
                         стареют за 7 дней vs 365 для стабильных; на чтении
                         — recency-конфликты и вес узла.
  Г3 SOURCE-TRUST-GATE — «доверие к источнику»: градация A/B/C + отказ в
                         наследовании доверия по ссылкам (усиление П2).
  Г4 CONSISTENCY-GATE  — «противоречия и дубликаты»: Jaccard-сходство с
                         памятью: дубликат → reject; конфликт с фактом
                         веса >= 0.5 → reject (кроме явного kind=refuted).
  Г5 RELEVANCE-GATE    — «релевантность на чтении»: шум не идёт в контекст
                         агента (порог по покрытию токенов запроса).

Пайплайн (как в research):
  ЗАПИСЬ  run_write_gates(node, registry, now)  — Г1 -> Г3 -> Г4 -> Г2
  ЧТЕНИЕ  run_read_gates(candidates, query)     — Г2 -> Г5

Философия: жёсткий reject только когда запись вредит памяти; в спорных
случаях — flag («понизить статус»), а не выбросить знание.

Только stdlib. Логика идентична demo_gates.py (19/19 кейсов зелёные).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from . import i18n
from .model import DECISION_WEIGHT_THRESHOLD, decision_weight

# --- общие помощники -----------------------------------------------------------

STOPWORDS = {
    "что", "это", "как", "так", "вот", "ещё", "уже", "был", "была", "было",
    "были", "будет", "будут", "очень", "просто", "который", "которая",
    "которые", "такой", "такая", "такие", "сам", "сама", "сами", "всего",
    "только", "тоже", "даже", "здесь", "там", "тут", "потом", "потому",
    "поэтому", "например", "какой", "какая", "какие", "свой", "своя", "свои",
}

_RE_NONWORD = re.compile(r"[^\w\s$%]")
_RE_DIGIT = re.compile(r"\d")


def _tokens(text: str) -> List[str]:
    """Нормализация: lower, пунктуация вон, стоп-слова вон.

    Слова >=3 симв.; числовые токены >=2 цифр сохраняются — для памяти
    фактов цифры (курс, версии, суммы) важнее слов."""
    t = _RE_NONWORD.sub(" ", str(text or "").lower())
    return [
        w for w in t.split()
        if (len(w) >= 3 or (len(w) >= 2 and w.isdigit())) and w not in STOPWORDS
    ]


def _jaccard(a: List[str], b: List[str]) -> float:
    """Jaccard-сходство наборов токенов (0..1)."""
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb)


def _parse_ts(ts: Any) -> Optional[datetime]:
    """ISO-8601 -> datetime (UTC). None — не парсится."""
    if not isinstance(ts, str) or not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _now(ctx: Optional[Dict[str, Any]]) -> datetime:
    return (ctx or {}).get("now") or datetime.now(timezone.utc)


@dataclass
class GateResult:
    """Результат гейта: pass | reject | flag + причина на человеческом языке.

    правило: причина хранится на двух языках. `reason` — то, что видит клиент:
    English по умолчанию, русский при BARON_LANG=ru. `reason_en`/`reason_ru`
    остаются рядом для тех, кто разбирает причину сам (сервер вытаскивает из
    неё id узла-дубликата регуляркой, и язык на это не влияет).
    """

    verdict: str            # "pass" | "reject" | "flag"
    reason_en: str
    reason_ru: str = ""

    @property
    def reason(self) -> str:
        return i18n.pick(self.reason_en, self.reason_ru or self.reason_en)

    @property
    def ok(self) -> bool:
        return self.verdict == "pass"


def ok(reason_en: str, reason_ru: str = "") -> GateResult:
    return GateResult("pass", reason_en, reason_ru)


def reject(reason_en: str, reason_ru: str = "") -> GateResult:
    return GateResult("reject", reason_en, reason_ru)


def flag(reason_en: str, reason_ru: str = "") -> GateResult:
    return GateResult("flag", reason_en, reason_ru)


# ============================================================================
# Г1 CONFIDENCE-GATE — «уверенность автора записи»
# ============================================================================

HEDGE_MARKERS = (
    "наверное", "наверно", "кажется", "возможно", "вероятно", "похоже",
    "вроде", "вроде бы", "думаю", "полагаю", "не уверен", "не уверена",
    "вряд ли", "как будто", "якобы", "предположительно", "примерно", "может",
    "probably", "maybe", "i think", "i guess", "not sure", "possibly",
    "perhaps", "seems", "apparently", "supposedly",
)
CERTAINTY_MARKERS = (
    "точно", "факт", "подтверждено", "подтверждён", "гарантированно",
    "измерено", "проверено", "100%", "certainly", "definitely", "confirmed",
    "verified", "measured", "checked",
)

CONF_PASS = 0.50   # факт допустим
CONF_MIN = 0.30    # ниже — вон из фактов


def _conf_pass(value: Any) -> float:
    """Порог Г1 «факт допустим»: доза Л1 или штатная константа.

    Дозы R4 §6.1: A 0.50 (как всегда), B1 0.35, B2/B3/Bblind 0.20. Порог ниже
    CONF_MIN осмыслен и допустим: он схлопывает полосу flag ([CONF_MIN,
    conf_pass)) в пустую, то есть «сомнительное, но не зыбкое» перестаёт
    понижаться до гипотезы. Отказ ниже CONF_MIN порогом при этом не снимается
    — это делает отдельный флаг trip_mode (reject -> flag), и разделение
    намеренное: ослабить строгость и отменить отказ — два разных решения.

    Значение вне [0, 1] игнорируется молча: доза приходит из тега узла, и
    мусор в теге не должен ронять запись.
    """
    if value is None:
        return CONF_PASS
    try:
        conf_pass = float(value)
    except (TypeError, ValueError):
        return CONF_PASS
    if conf_pass < 0.0 or conf_pass > 1.0:
        return CONF_PASS
    return conf_pass


def check_confidence(node: Dict[str, Any], ctx: Optional[Dict[str, Any]] = None) -> GateResult:
    """Г1: уверенность автора. Что фильтрует: «наверное-факты».

    Эвристика: явное поле confidence (0..1) — берём как есть; иначе база
    0.75, минус маркеры неуверенности (-> 0.35), минус отсутствие источника
    (-> 0.25), плюс маркеры подтверждения (-> 0.85).
    Факт с conf < 0.30 -> reject; 0.30..0.50 -> flag (понизить до hypothesis);
    hypothesis пропускается всегда (низкая уверенность — его природа).
    """
    claim = str(node.get("claim") or "")
    kind = str(node.get("kind") or "fact")
    src = str(node.get("source") or "")
    # TS.2 / R4 §3 Л1: порог «факт допустим» дозозависим. Вне песочницы ctx
    # пустой и работает штатная константа — основной граф не меняется.
    conf_pass = _conf_pass((ctx or {}).get("conf_pass"))

    conf = node.get("confidence")
    if conf is None:
        conf = 0.75
        hedges = [h for h in HEDGE_MARKERS if h in claim.lower()]
        if hedges:
            conf = min(conf, 0.35)
        if any(m in claim.lower() for m in CERTAINTY_MARKERS):
            conf = max(conf, 0.85)
        if not src.strip():
            conf = min(conf, 0.25)
    else:
        try:
            conf = float(conf)
        except (TypeError, ValueError):
            conf = 0.0

    if kind == "hypothesis":
        return ok(
            f"kind=hypothesis — low confidence is acceptable (conf={conf:.2f})",
            f"kind=hypothesis — низкая уверенность допустима (conf={conf:.2f})",
        )
    if conf < CONF_MIN:
        detail_en = detail_ru = ""
        hedges = [h for h in HEDGE_MARKERS if h in claim.lower()]
        if hedges:
            detail_en = f"; hedging markers: {', '.join(hedges[:3])}"
            detail_ru = f"; маркеры неуверенности: {', '.join(hedges[:3])}"
        if not src.strip():
            detail_en += "; no source"
            detail_ru += "; нет источника"
        return reject(
            f"confidence {conf:.2f} < {CONF_MIN:.2f} — too shaky for a fact{detail_en}",
            f"уверенность {conf:.2f} < {CONF_MIN:.2f} — слишком зыбкое для факта{detail_ru}",
        )
    if conf < conf_pass:
        return flag(
            f"confidence {conf:.2f} in [{CONF_MIN:.2f}, {conf_pass:.2f}) — "
            f"store as hypothesis, not as a fact",
            f"уверенность {conf:.2f} в [{CONF_MIN:.2f}, {conf_pass:.2f}) — "
            f"сохранить как hypothesis, а не факт",
        )
    return ok(f"confidence {conf:.2f} >= {conf_pass:.2f} — the fact is admissible",
              f"уверенность {conf:.2f} >= {conf_pass:.2f} — факт допустим")


# ============================================================================
# Г2 STALENESS-GATE — «свежесть / устаревание»
# ============================================================================

VOLATILE_LEXICON = (
    "курс", "цена", "ценник", "статус", "баланс", "версия", "погода",
    "онлайн", "offline", "доступ", "занят", "свободен", "аптайм", "uptime",
    "price", "status", "balance", "version", "online", "капитализация",
)
VOLATILE_MAX_AGE_DAYS = 7
STABLE_MAX_AGE_DAYS = 365


def check_staleness(node: Dict[str, Any], ctx: Optional[Dict[str, Any]] = None) -> GateResult:
    """Г2: свежесть/устаревание. Что фильтрует: устаревшие данные.

    На записи: у volatile-тем лимит возраста 7 дней, у стабильных — 365
    (расширение П1). На чтении: recency-конфликт — если по той же теме есть
    более свежая запись с другим содержанием, старый узел помечается
    outdated (flag); вес ниже порога тоже отсекается.
    """
    ts = node.get("ts")
    dt = _parse_ts(ts)
    if dt is None:
        return reject("ts is missing or not ISO-8601 — freshness cannot be checked",
                      "ts отсутствует или не ISO-8601 — свежесть не проверить")
    now = _now(ctx)
    claim_l = str(node.get("claim") or "").lower()

    volatile = any(w in claim_l for w in VOLATILE_LEXICON)
    max_age = timedelta(days=VOLATILE_MAX_AGE_DAYS if volatile else STABLE_MAX_AGE_DAYS)
    age = now - dt
    if age > max_age:
        tag_en = "a volatile topic (rate/status/version…)" if volatile else "an ordinary topic"
        tag_ru = "volatile-тема (курс/статус/версия…)" if volatile else "обычная тема"
        return reject(
            f"age {age.days} d > the {max_age.days} d limit for {tag_en} — "
            f"the data is stale",
            f"возраст {age.days} дн > лимита {max_age.days} дн для {tag_ru} — "
            f"данные устарели",
        )

    # recency-конфликт: та же тема, более свежая запись с другим содержанием
    subject = " ".join(_tokens(str(node.get("claim") or ""))[:2])
    newer = (ctx or {}).get("subjects") or {}
    if subject and subject in newer:
        nv = newer[subject]
        nv_dt = _parse_ts(nv.get("ts"))
        if nv_dt and nv_dt > dt and str(nv.get("claim") or "") != str(node.get("claim") or ""):
            return flag(
                f"a fresher entry on the topic «{subject}» exists "
                f"({str(nv.get('claim'))[:36]}…) — mark the old node as outdated",
                f"есть более свежая запись по теме «{subject}» "
                f"({str(nv.get('claim'))[:36]}…) — старый узел помечать как outdated",
            )

    kind_en = "volatile topic" if volatile else "stable topic"
    kind_ru = "volatile-тема" if volatile else "стабильная тема"
    return ok(f"age {age.days} d <= {max_age.days} d ({kind_en}) — fresh",
              f"возраст {age.days} дн <= {max_age.days} дн ({kind_ru}) — свежо")


# ============================================================================
# Г3 SOURCE-TRUST-GATE — «доверие к источнику»
# ============================================================================

TIER_A_MARKERS = (
    "отчёт", "отчет", "офиц", "документ", "док.", "таблиц", "лог", "измер",
    "протокол", "спецификац", "данные сенсора", "метрики", "report",
    "document", "official", "log", "measured", "spec", "metrics", "api ",
)
TIER_C_MARKERS = (
    "слух", "кто-то", "говорят", "интернет", "chatgpt", "не помню", "в чате",
    "слышал", "сплетни", "не уверен", "rumor", "someone", "heard",
    "internet", "i don't remember", "где-то прочитал", "кажется из разговора",
)


def _source_tier(source: str) -> tuple:
    """(tier, why_en, why_ru) — класс источника и объяснение на двух языках."""
    s = (source or "").lower().strip()
    if not s:
        return "C", "empty source", "пустой источник"
    if any(m in s for m in TIER_A_MARKERS):
        return "A", f"trusted class: «{s[:44]}»", f"доверенный класс: «{s[:44]}»"
    if any(m in s for m in TIER_C_MARKERS):
        return "C", f"unverifiable class: «{s[:44]}»", f"непроверяемый класс: «{s[:44]}»"
    return "B", f"ordinary source: «{s[:44]}»", f"обычный источник: «{s[:44]}»"


def check_source_trust(node: Dict[str, Any], ctx: Optional[Dict[str, Any]] = None) -> GateResult:
    """Г3: доверие к источнику. Что фильтрует: факты «из слухов».

    Градация источника A (0.9) / B (0.6) / C (0.15). Факт из C -> reject;
    hypothesis из C -> flag. Наследование недоверия: ссылка на факт из
    ненадёжного источника -> reject. Усиливает П2 (там только «непустой»).
    """
    tier, why_en, why_ru = _source_tier(str(node.get("source") or ""))
    kind = str(node.get("kind") or "fact")

    for link in node.get("links") or []:
        target = ((ctx or {}).get("registry") or {}).get(link)
        if isinstance(target, dict):
            ttier = _source_tier(str(target.get("source") or ""))[0]
            if ttier == "C" and str(target.get("kind") or "") == "fact":
                return reject(
                    f"link {link} points at a fact from an untrusted source (C) — "
                    f"trust is not inherited through links",
                    f"ссылка {link} ведёт на факт из ненадёжного источника (C) — "
                    f"доверие по ссылкам не наследуется",
                )

    if tier == "C":
        if kind == "fact":
            return reject(
                f"fact from an untrusted source ({why_en}) — store it as a hypothesis",
                f"факт из ненадёжного источника ({why_ru}) — сохраните как hypothesis",
            )
        return flag(
            f"hypothesis from an untrusted source — acceptable ({why_en})",
            f"hypothesis из ненадёжного источника — допустимо ({why_ru})",
        )
    return ok(f"source of class {tier}: {why_en}", f"источник класса {tier}: {why_ru}")


# ============================================================================
# Г4 CONSISTENCY-GATE — «противоречия и дубликаты»
# ============================================================================

DUP_THRESHOLD = 0.55            # Jaccard >= — это дубликат, а не новая память
CONTRADICTION_THRESHOLD = 0.30  # Jaccard >= и разная полярность — конфликт
NEG_PATTERNS = (
    "не ", "нет", "никогда", "отсутствует", "недоступн", "не работает",
    "не было", "не вырос", "упал", "сломан", "потерян", "no ", "not ",
    "never", "unavailable", "down", "offline", "failed", "без ",
)


def _has_negation(claim: str) -> bool:
    c = " " + str(claim or "").lower() + " "
    return any(p in c for p in NEG_PATTERNS)


# -- значимые различия (фикс 01.09) -----------------------------------------
# Jaccard по словам не отличает «премию я бы хотел…» ×208 (настоящий дубль)
# от «CRV long -> reject» / «SKR long -> approve» (разные решения, общий
# шаблон). На коротких claim'ах шаблон даёт сходство 0.67-0.90, и голый порог
# 0.55 зарубил бы ВСЕ различающиеся только числом или тикером факты —
# проверено на tests/test_server.py::test_memory_search_topk_limit, где
# 5 разных замеров латентности схлопнулись в 1.
# Поэтому дубликат = высокое сходство И совпадающий «значимый набор»:
# числа и тикеры/аббревиатуры. Даты и время из набора исключены осознанно:
# один и тот же вердикт по той же монете, повторённый через час, — это
# подкрепление, а не новая память (ровно то, что просит Г4 в тексте reject).
_RE_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}:\d{2}(?::\d{2})?\b")
_RE_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_RE_TICKER = re.compile(r"\b[A-ZА-Я][A-ZА-Я0-9]{1,11}\b")


# Слова-решения: смена вердикта по тому же предмету — это НОВАЯ память,
# а не копия. Без них «CRV long -> approve» схлопывалось с «CRV long ->
# reject» (одинаковые числа и тикеры, высокое сходство), и агент читал бы
# устаревшее решение как актуальное.
DECISION_MARKERS = (
    "approve", "reject", "одобр", "отклон", "да", "нет", "long", "short",
    "buy", "sell", "лонг", "шорт", "покуп", "прода", "pass", "fail",
    "вход", "выход", "халт", "halt", "стоп", "hold",
)


def _salient(claim: str) -> set:
    """«О чём именно» утверждение: числа, тикеры и принятые решения.

    Даты и время исключены: повтор того же вердикта через час — это
    подкрепление, а не новая память.
    """
    text = _RE_DATE.sub(" ", str(claim or ""))
    nums = set()
    for raw in _RE_NUMBER.findall(text):
        n = raw.replace(",", ".")
        if "." in n:
            n = n.rstrip("0").rstrip(".")
        nums.add(n or "0")
    low = text.lower()
    decisions = {m for m in DECISION_MARKERS if m in low}
    return nums | set(_RE_TICKER.findall(text)) | decisions


def _content_tokens(claim: str) -> List[str]:
    """Токены claim'а БЕЗ дат и времени — для сверки содержания (Г4).

    Алиса зашивает timestamp в сам текст («Вердикт Алиса 2026-09-01
    02:05:23: CRV long -> reject»). Дата — метаданные узла (поле ts), а не
    содержание, но в Jaccard она давала до 6 различающихся токенов и роняла
    сходство одинаковых вердиктов с 0.9 до 0.33 — дубликаты проскакивали.
    """
    return _tokens(_RE_DATE.sub(" ", str(claim or "")))


# ---------------------------------------------------------------------------
# Эпизодические записи: снимок момента, а не утверждение о мире.
#
# Замер 2026-09-09 (Baron-Psychonaut, сутки): 1495 узлов не записано, из них
# 1486 — отказ Г4 «противоречит подтверждённому факту». Отвергались записи
# вида «[BARON:paper] balance() -> ok» и «решение #6: open SOL — объём упал
# до 10», а «подтверждённым фактом» выступало СОБСТВЕННОЕ прошлое решение
# того же психонавта из другого прогона.
#
# Механизм: полярность Г4 — лексическая. NEG_PATTERNS ловит «упал», «без »,
# «не » — обычные слова рыночной прозы, а не логическое отрицание. Хватает,
# чтобы у двух записей полярность разошлась; шаблонный префикс даёт Jaccard
# выше порога 0.30 — и запись момента объявляется спором о факте.
#
# Спорить о факте могут только длящиеся утверждения. Снимок момента (цена в
# 02:31, ответ инструмента, решение в цикле 6) не противоречит другому
# снимку: это два разных момента. Такие узлы помечены видом (cost, incident,
# result, task, digest — по KINDS они и заведены как «не факт о мире») либо
# тегом момента, и Г4 их больше не сталкивает лбами.
#
# Дубликаты у эпизодических узлов остаются жёсткими: 607 повторов
# «positions() -> ok» за те же сутки корректно схлопнулись в один узел, и
# терять это схлопывание нельзя.
EPISODIC_KINDS = frozenset({"cost", "incident", "result", "task", "digest"})
# Теги-признаки момента. `world_state` сюда НЕ входит, хотя выглядит подходяще:
# это тег-маршрутизатор из mnemos/budget.py, его ставит ensure_router_tag по
# умолчанию, и на боевом сторе он висит на 2836 узлах из 2911 (97%). Взять его
# признаком эпизода значит выключить Г4 почти всем — проверено: с ним
# «порт 8765 не слушает 127.0.0.1» переставал спорить с «порт 8765 слушает
# только 127.0.0.1». Признак должен ставить пишущий осознанно, а не роутер.
EPISODIC_TAGS = frozenset({"decision", "observation", "snapshot", "episode"})
# Префиксы тегов, которые сами по себе означают запись момента: ответ
# конкретного инструмента (tool:balance) и запись конкретного прогона
# (run:psychonaut-1788912999). Оба ставит автор записи, а не сервер.
EPISODIC_TAG_PREFIXES = ("tool:", "run:", "cycle:")


def _is_episodic(node: Dict[str, Any]) -> bool:
    """Узел — запись момента, а не длящееся утверждение о мире?"""
    if str(node.get("kind") or "") in EPISODIC_KINDS:
        return True
    tags = node.get("tags") or ()
    if isinstance(tags, str):
        tags = (tags,)
    for raw in tags:
        t = str(raw).strip().lower()
        if t in EPISODIC_TAGS or t.startswith(EPISODIC_TAG_PREFIXES):
            return True
    return False


def check_consistency(node: Dict[str, Any], ctx: Optional[Dict[str, Any]] = None) -> GateResult:
    """Г4: противоречия и дубликаты. Что фильтрует: копии и конфликты с памятью.

    Сверка нового claim со всеми узлами (Jaccard — лексический прокси
    семантики; в проде — эмбеддинги): сходство >= 0.55 и та же полярность
    -> дубликат: reject; сходство >= 0.30 и разная полярность -> конфликт
    (против факта веса >= 0.5 — reject, кроме явного kind=refuted+evidence;
    против слабого узла — flag). Расширяет П4 (там только links->refuted).

    Конфликт считается только между длящимися утверждениями: эпизодическая
    запись (снимок момента — см. _is_episodic) ни с чем не спорит, а
    дубликаты у неё проверяются как обычно.
    """
    claim = str(node.get("claim") or "")
    tn = _content_tokens(claim)
    sn = _salient(claim)
    existing = (ctx or {}).get("nodes") or []

    conflicts: List[tuple] = []
    episodic_new = _is_episodic(node)
    session_id = str(node.get("session_id") or "")
    for other in existing:
        if other.get("id") == node.get("id"):
            continue
        # T2.9: узлы одной сессии нити содержат общие шаблонные токены. Сверять
        # их между собой нельзя — иначе шаблонная запись/хвост отвергает соседний
        # элемент того же memory_add. Смысловую сверку ведём только с чужими сессиями.
        if session_id and str(other.get("session_id") or "") == session_id:
            continue
        other_claim = str(other.get("claim") or "")
        to = _content_tokens(other_claim)
        j = _jaccard(tn, to)
        neg_diff = _has_negation(claim) != _has_negation(other_claim)
        # дубликат — то же содержание, та же полярность И те же числа/тикеры
        if j >= DUP_THRESHOLD and not neg_diff and sn == _salient(other_claim):
            return reject(
                f"duplicate of node {other.get('id')} (similarity {j:.0%}, "
                f"«{str(other.get('claim'))[:30]}…») — reinforce the existing "
                f"node instead of breeding a copy",
                f"дубликат узла {other.get('id')} (сходство {j:.0%}, "
                f"«{str(other.get('claim'))[:30]}…») — подкрепите существующий узел, "
                f"а не плодите копию",
            )
        # противоречие — общая тема, но противоположная полярность.
        # Спорить могут только длящиеся утверждения: снимок момента не
        # противоречит ни факту, ни другому снимку (см. _is_episodic).
        # Полярность из проверки дубликата НЕ убираем: «positions() -> ok» и
        # «positions() не отвечает» — разные сведения, а не копия.
        if j >= CONTRADICTION_THRESHOLD and neg_diff \
                and not episodic_new and not _is_episodic(other):
            conflicts.append((other, j))

    for other, j in conflicts:
        # правило: спор решает вес решения (base_weight), а не затухающий
        # weight поиска — иначе массовый decay молча разоружает гейт:
        # все факты становятся «слабыми», и с любым из них можно спорить.
        weight = decision_weight(other)
        if other.get("kind") == "fact" and weight >= DECISION_WEIGHT_THRESHOLD:
            if node.get("kind") != "refuted" or not (node.get("evidence") or []):
                return reject(
                    f"contradicts the confirmed fact {other.get('id')} "
                    f"(weight {weight:.2f}, similarity {j:.0%}) — to store it pass "
                    f"kind=refuted + evidence",
                    f"противоречит подтверждённому факту {other.get('id')} "
                    f"(вес {weight:.2f}, сходство {j:.0%}) — для записи укажите "
                    f"kind=refuted + evidence",
                )
            return ok(
                f"filed as an explicit refutation (kind=refuted + evidence) — "
                f"the conflict is resolved, node {other.get('id')} becomes refuted",
                f"оформлено как явное опровержение (kind=refuted + evidence) — "
                f"конфликт разрешён, узел {other.get('id')} станет refuted",
            )
        return flag(
            f"contradiction with {other.get('id')} (similarity {j:.0%}), but that node "
            f"is weak (weight {weight:.2f}) — the new node's weight is lowered",
            f"противоречие с {other.get('id')} (сходство {j:.0%}), но тот узел "
            f"слабый (вес {weight:.2f}) — вес нового узла снижается",
        )
    return ok(f"no contradictions or duplicates against {len(existing)} node(s)",
              f"противоречий и дубликатов с {len(existing)} узлом(ами) не найдено")


# ============================================================================
# Г5 RELEVANCE-GATE — «релевантность чтения»
# ============================================================================

RELEVANCE_THRESHOLD = 2.0
CLAIM_HIT_WEIGHT = 3.0
CONTEXT_HIT_WEIGHT = 1.5
SOURCE_HIT_WEIGHT = 1.0


def check_relevance(node: Dict[str, Any], ctx: Optional[Dict[str, Any]] = None) -> GateResult:
    """Г5: релевантность на чтении. Что фильтрует: шум в контексте агента.

    score = 3.0*попаданий токенов запроса в claim + 1.5*в context +
    1.0*в source; ниже порога — не отдавать агенту. Лексический прокси
    косинуса (в проде с эмбеддингами — прямой порог по косинусу ~0.5).
    """
    query = str((ctx or {}).get("query") or "")
    qt = _tokens(query)
    if not qt:
        return reject("empty query — relevance cannot be determined",
                      "пустой запрос — релевантность не определить")
    threshold = float((ctx or {}).get("threshold", RELEVANCE_THRESHOLD))

    claim_l = str(node.get("claim") or "").lower()
    ctx_l = str(node.get("context") or "").lower()
    src_l = str(node.get("source") or "").lower()

    score = (
        CLAIM_HIT_WEIGHT * sum(1 for t in qt if t in claim_l)
        + CONTEXT_HIT_WEIGHT * sum(1 for t in qt if t in ctx_l)
        + SOURCE_HIT_WEIGHT * sum(1 for t in qt if t in src_l)
    )
    if score < threshold:
        return reject(
            f"relevance {score:.1f} < {threshold} for query «{query}» — "
            f"the node is nearly off-topic, keep the agent's context clean",
            f"релевантность {score:.1f} < {threshold} по запросу «{query}» — "
            f"узел почти не по теме, не засорять контекст агента",
        )
    return ok(f"relevance {score:.1f} >= {threshold} — the node goes into the agent's context",
              f"релевантность {score:.1f} >= {threshold} — узел идёт в контекст агента")


# ============================================================================
# Пайплайны: запись и чтение (gates_research.md, §7)
# ============================================================================


def _soften(res: GateResult, gate: str) -> GateResult:
    """reject -> flag с сохранением причины (TS.2 / R4 §3 Л1).

    Формулировка причины не выбрасывается, а дополняется пометкой режима:
    сервер восстанавливает id узла-дубликата регуляркой по тексту причины
    (server._first_node_id), и потерять текст значит потерять подкрепление.
    """
    if res.verdict != "reject":
        return res
    return flag(f"[trip_mode {gate}] {res.reason_en}",
                f"[trip_mode {gate}] {res.reason_ru or res.reason_en}")


def run_write_gates(
    node: Dict[str, Any],
    registry: Optional[Dict[str, Any]] = None,
    now: Optional[datetime] = None,
    existing: Optional[List[Dict[str, Any]]] = None,
    trip_mode: bool = False,
    conf_pass: Optional[float] = None,
    all_gates_flag: bool = False,
) -> GateResult:
    """Полный проход гейтов записи: Г1 -> Г3 -> Г4 -> Г2 (порядок из research).

    - registry: id -> узел (для наследования доверия по ссылкам, Г3);
    - existing: список узлов памяти для сверки на дубликаты/противоречия (Г4);
      по умолчанию — значения registry;
    - now: фиксированное «сейчас» (детерминизм тестов/гейтов).

    Режим трипа (TS.2, R4 §3 Л1 — ослабление точности верхних приоров):
    - conf_pass: порог Г1 по дозе (A 0.50, B1 0.35, B2/B3/Bblind 0.20);
    - trip_mode: reject от Г1 и Г3 превращается в flag — хеджированное
      предположение и догадка без источника записываются помеченными, а не
      отбрасываются. Г4 (дубликат) и Г2 (разбираемое время) остаются жёсткими;
    - all_gates_flag: то же для ВСЕХ гейтов записи (доза за потолком, рука B3).

    Смягчённый вердикт НЕ замыкает пайплайн: проверка идёт до конца, и если
    дальше найдётся жёсткий reject, вернётся он. Иначе рука, ослабившая только
    верхние приоры, переставала бы проверять дубликаты ровно на тех записях,
    ради которых трип и затеян, — то есть B2 вела бы себя как B3.

    Все три параметра по умолчанию выключены: без них поведение побайтово
    прежнее, и основной граф режимом трипа не затрагивается. Решение о том,
    что узел относится к песочнице, принимает вызывающий, а не гейты.

    Возвращает первый непройденный результат (reject/flag) или pass.
    """
    ctx: Dict[str, Any] = {}
    if now is not None:
        ctx["now"] = now
    if conf_pass is not None:
        ctx["conf_pass"] = conf_pass
    soft_conf = trip_mode or all_gates_flag
    # Первый непройденный результат по-прежнему выигрывает — НО смягчённый
    # (reject -> flag) не имеет права коротко замкнуть пайплайн: иначе рука,
    # которая ослабила только Г1, на хеджированных claim'ах вообще перестаёт
    # проверять дубликаты и ведёт себя как рука за потолком. Разница между
    # дозами исчезла бы ровно на тех записях, ради которых трип и затеян.
    softened: Optional[GateResult] = None

    def _step(res: GateResult, gate: str, soft: bool) -> Optional[GateResult]:
        """Вернуть вердикт, который надо отдать сразу, либо None — идём дальше."""
        nonlocal softened
        if res.verdict == "pass":
            return None
        if res.verdict == "flag":
            softened = softened or res
            return None
        if soft:
            softened = softened or _soften(res, gate)
            return None
        return res

    out = _step(check_confidence(node, ctx), "Г1", soft_conf)
    if out is not None:
        return out
    # Г3 смягчается вместе с Г1: оба гейта — про «верхние приоры» (насколько
    # автор уверен и насколько доверенный источник), и это ровно то, что
    # ослабляет доза по R4 §3 Л1. Догадка без источника — законный продукт
    # трипа: брифинг прямо просит формулировать догадки, которые нечем
    # обосновать (R4 §4.1). Г4 (дубликат) и Г2 (разбираемое время) остаются
    # жёсткими: они не про уверенность, а про структуру графа, и смягчает их
    # только доза за потолком.
    out = _step(check_source_trust(node, {"registry": registry or {}, **ctx}),
                "Г3", soft_conf)
    if out is not None:
        return out
    out = _step(check_consistency(
        node,
        {"nodes": existing if existing is not None else list((registry or {}).values())},
    ), "Г4", all_gates_flag)
    if out is not None:
        return out
    out = _step(check_staleness(node, ctx), "Г2", all_gates_flag)
    if out is not None:
        return out
    return softened or ok("all write gates passed", "все гейты записи пройдены")


def _is_self_history(node: Dict[str, Any], agent: str, scope_tag: Optional[str]) -> bool:
    """Узел — собственная история агента? (TS.5 / R4 §3 Л3.)

    Своя история — это узел с тегом `agent:<self>` либо запись сессии (тег
    `session`). scope_tag сужает запрет до одной нити: без него запрет
    накрыл бы весь граф, а «распад самомодели» задуман только в песочнице.
    """
    tags = node.get("tags") or []
    if scope_tag is not None and scope_tag not in tags:
        return False
    if f"agent:{agent}" in tags:
        return True
    if "session" in tags:
        return str(node.get("agent") or "") == agent
    return str(node.get("agent") or "") == agent and "thread_head" not in tags


def run_read_gates(
    candidates: List[Dict[str, Any]],
    query: str,
    threshold: Optional[float] = None,
    now: Optional[datetime] = None,
    hide_self: Optional[str] = None,
    hide_scope: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Полный проход гейтов чтения: Г2 (свежесть) -> Г5 (релевантность).

    hide_self (TS.5, R4 §3 Л3): имя агента, чью собственную историю в трипе
    видеть нельзя. hide_scope — тег нити, которым запрет ограничен (обычно
    `thread:sandbox`): вне этой нити агент свою историю видит как обычно, и
    выученное не теряется — запрет действует только в фазе трипа.

    Возвращает кандидатов, достойных контекста агента (reject — вон).
    """
    out: List[Dict[str, Any]] = []
    for node in candidates:
        if hide_self and _is_self_history(node, hide_self, hide_scope):
            continue
        ctx: Dict[str, Any] = {"query": query}
        if now is not None:
            ctx["now"] = now
        res = check_staleness(node, ctx)
        if res.verdict == "reject":
            continue
        rctx: Dict[str, Any] = {"query": query}
        if threshold is not None:
            rctx["threshold"] = threshold
        if now is not None:
            rctx["now"] = now
        if check_relevance(node, rctx).verdict == "reject":
            continue
        out.append(node)
    return out


# --- R12-8: сканер переклассификации kind (только чтение) ------------------
#
# Пользователь задачи: смена kind массово — по явному запросу. Функции
# ниже — ЧИСТЫЙ read-only классификатор для отчёта сканера, они НИЧЕГО не
# пишут и не вызываются автоматически при memory_add/memory_rewrite. Само
# применение — отдельная ручная команда из отчёта research/mnemos/.

_TRANSPORT_ERROR_RE = re.compile(
    r"\b(402|403|404|408|409|429|500|502|503|504)\b|"
    r"nxdomain|connection refused|timeout|таймаут|тайм-аут|"
    r"payment required|not found|forbidden|bad gateway"
    , re.IGNORECASE,
)

_LANGBENCH_RE = re.compile(r"\blangbench\b", re.IGNORECASE)
_VAULT_DUMP_RE = re.compile(
    r"\bvault\b.*(дамп|dump|снапшот|snapshot)|"
    r"(дамп|dump|снапшот|snapshot).*\bvault\b",
    re.IGNORECASE,
)


def suggest_kind_hypothesis_to_incident(node: Dict[str, Any]) -> bool:
    """kind=hypothesis узел описывает транспортную ошибку (402/404/…) -> incident?

    Эвристика для отчёта сканера R12-8. True не значит «переписать»: решение
    и правку узла делает пользователь."""
    if str(node.get("kind") or "") != "hypothesis":
        return False
    claim = str(node.get("claim") or node.get("text") or "")
    return bool(_TRANSPORT_ERROR_RE.search(claim))


def suggest_kind_rule_out(node: Dict[str, Any]) -> Optional[str]:
    """kind=rule узел — на самом деле langbench-замер или дамп vault?

    Возвращает предлагаемый новый kind ('fact' для замера, None если правило
    настоящее) — тоже только для отчёта, без записи."""
    if str(node.get("kind") or "") != "rule":
        return None
    claim = str(node.get("claim") or node.get("text") or "")
    if _LANGBENCH_RE.search(claim):
        return "fact"
    if _VAULT_DUMP_RE.search(claim):
        return "fact"
    return None
