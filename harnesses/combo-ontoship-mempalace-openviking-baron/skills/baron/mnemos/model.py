# -*- coding: utf-8 -*-
"""Baron Munchausen: модель узла памяти (JSON-совместимая).

Узел памяти — атом графа истины. Каждое утверждение, которое агент
кладёт в память, живёт в узле с полем truth_check: результат прохода
протокола П1-П6 (см. truth_gate.py).

Схема узла (JSON):

{
  "id": "mn_example",
  "kind": "fact | hypothesis | refuted | outdated | context_summary",
  "claim": "утверждение",
  "source": "источник (кто/что сказал)",
  "evidence": ["свидетельство 1", ...],
  "context": "контекст утверждения (полнота, П6)",
  "ts": "2025-01-01T12:00:00.000+00:00",
  "links": ["mn_...", ...],
  "truth_check": {"P1": {...}, ..., "P6": {...}, "verdict": "pass", "score": 4}
}
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

# Допустимые виды узлов (по концепции Baron Munchausen).
# context_summary — структурный узел иерархической сводки сессии
# (context_engine.HierarchicalCompactor): сжимает старые ходы в выжимки
# со ссылками на исходные сообщения. Проходит те же гейты, что и факты.
# rule (01.09, аудит §5.10): правило команды — не факт и не болтовня.
# Правило не тускнеет ниже WEIGHT_FLOOR_RULE и не трогается memory_prune.
# hub (02.09, рефакторинг по письму Qwen): узел-хаб кластера сущности
# (Алиса, x402, защиты...). Структурный: не факт, в выдачу search не
# попадает (навигация), рёбра has_part -> члены, члены part_of -> хаб.
# task/result: канал дирижёр→субагент через память — задача
# kind=task, ответ kind=result с parent=<id задачи>; дирижёр ищет memory_list(parent=…).
# cost: счётчик стоимости сессии — дельта счётчиков внешний шлюз
# за окно сессии (модель, сырые и взвешенные токены, деньги, session_id). Не факт:
# это измерение расхода, а не утверждение о мире; пишет tools/cost/session_cost.py.
# incident: находка пульса — противоречие соседей,
# протухший recheck_after, мёртвый источник, узел без единого ребра. Не факт
# о мире, а наблюдение о самой памяти: пишет только mnemos/pulse.py, parent —
# узел, к которому находка относится.
KINDS = ("fact", "hypothesis", "refuted", "outdated", "context_summary", "rule", "hub", "api",
         "task", "result", "digest", "cost", "incident")
KIND_INCIDENT = "incident"
KIND_HUB = "hub"

# Пластичность (brick-2, идея брата 25.08: узлы как живые нейроны):
# вес связи/узла меняется — подкрепление (reinforce) и затухание (decay).
WEIGHT_MAX = 1.0
WEIGHT_MIN = 0.05           # пол — узел не умирает полностью, «тлеет»
WEIGHT_FLOOR_RULE = 0.5     # пол для kind=rule: конституция не тускнеет
DEFAULT_HALF_LIFE_HOURS = 168.0  # неделя: без подкрепления вес падает вдвое
# Порог, ниже которого решение «факт подтверждён» (Г4) не принимается. Тот
# же порог служит полом миграции base_weight у узлов, которых затухание уже
# коснулось (см. decision_weight): бэкап не читаем, восстанавливаем до порога.
DECISION_WEIGHT_THRESHOLD = 0.5
REVISIONS_MAX = 10              # потолок истории claim


def weight_floor(kind: str) -> float:
    """Пол веса для вида узла: правило не опускается ниже 0.5 (аудит §5.7).
    Хаб — структурный узел, тускнеет не ниже того же пола: навигация не
    должна «дотлевать» до порога prune weak."""
    return WEIGHT_FLOOR_RULE if kind in ("rule", KIND_HUB) else WEIGHT_MIN

_PENDING_TRUTH_CHECK: Dict[str, Any] = {
    "P1": {"pass": None, "note": "не проверено"},
    "P2": {"pass": None, "note": "не проверено"},
    "P3": {"pass": None, "note": "не проверено"},
    "P4": {"pass": None, "note": "не проверено"},
    "P5": {"pass": None, "note": "не проверено"},
    "P6": {"pass": None, "note": "не проверено"},
    "verdict": "pending",
    "score": 0,
}


def now_iso() -> str:
    """Текущее время UTC в ISO-8601 (миллисекунды)."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _parse_iso(ts: str) -> Optional[datetime]:
    """Парсит ISO-8601; naive-время трактуется как UTC. None — если не парсится."""
    if not ts or not isinstance(ts, str):
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _coerce_level(raw: Any) -> int:
    """level из JSON: 0..2; мусор/отсутствие — L0 (полный текст)."""
    try:
        lv = int(raw or 0)
    except (TypeError, ValueError):
        return 0
    return min(max(lv, 0), 2)


def new_id() -> str:
    """Короткий стабильный id узла вида mn_<12 hex>."""
    return "mn_" + uuid.uuid4().hex[:12]


def coerce_link_meta(raw: Any) -> Dict[str, Dict[str, Any]]:
    """Приводит link_meta из JSON к {to_id: {...}}, мусор молча отбрасывая.

    Читаем чужой JSON (сторы писались разными версиями), поэтому битая
    запись не должна ронять загрузку всего стора — она просто теряет паспорт.
    """
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for k, v in raw.items():
        if isinstance(v, dict):
            out[str(k)] = dict(v)
    return out


def decision_weight(d: Dict[str, Any]) -> float:
    """Вес, по которому принимаются решения (Г4, prune weak) — правило.

    Узел с полем base_weight — оно и есть ответ. Узел без поля (записан до
    правило) мигрирует по правилу, не требующему бэкапа:
      * decayed_at пуст — затухание узла не касалось, base_weight = weight;
      * decayed_at есть — прежний вес утерян, base_weight = max(weight, 0.5):
        восстанавливаем до порога решения. Ошибка в сторону защиты: лишний
        «подтверждённый факт» стоит одного отказа Г4 с внятной причиной,
        лишний «слабый» — узла, которого больше нет.
    """
    raw = d.get("base_weight")
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return float(raw)
    w = float(d.get("weight", WEIGHT_MAX) or WEIGHT_MAX)
    if d.get("decayed_at"):
        return max(w, DECISION_WEIGHT_THRESHOLD)
    return w


@dataclass
class MemoryNode:
    """Узел памяти Baron Munchausen (сериализуется в JSON).

    Пластичность (brick-2): узел — живая единица, а не статичный файл.
    - weight: вес связи (0.05..1.0) — растёт при подкреплении/проверке,
      затухает без использования (аналог изменения веса синапса);
    - revisions: история переписываний claim — как нейрон, который
      перезаписывается новым фактом, но помнит старые состояния;
    - children/parent: «граф в узле» — структурная рекурсия (самоподобие,
      как иерархии в мозге); глубина ограничивается в Store (MAX_DEPTH).
    """

    claim: str
    kind: str = "fact"
    source: str = ""
    evidence: List[str] = field(default_factory=list)
    context: str = ""
    ts: str = field(default_factory=now_iso)
    links: List[str] = field(default_factory=list)
    id: str = field(default_factory=new_id)
    truth_check: Dict[str, Any] = field(
        default_factory=lambda: dict(_PENDING_TRUTH_CHECK)
    )
    # -- пластичность ------------------------------------------------------
    weight: float = WEIGHT_MAX
    # Вес решения: значение weight на момент записи, растёт при
    # подкреплении и НЕ затухает. Его читают гейт противоречий Г4 и prune
    # weak; поиск по-прежнему ранжирует по затухающему weight. До правило один
    # weight читали трое, и массовый decay молча разоружал Г4 (все факты
    # < 0.5 — «слабые», спорить с ними можно) и взводил prune weak
    # (< 0.1 и 30 дней без чтения — удаление). Старые узлы поля не имеют —
    # правило миграции см. decision_weight().
    base_weight: float = WEIGHT_MAX
    last_used: str = field(default_factory=now_iso)
    revisions: List[Dict[str, Any]] = field(default_factory=list)
    children: List[str] = field(default_factory=list)
    parent: Optional[str] = None
    # -- темпоральность, уверенность, теги (фикс 01.09, аудит §5.3/§5.4) ----
    # До 01.09 этих полей не было в схеме VPS-реализации, поэтому любой
    # from_dict->to_dict (update/rewrite/reinforce/decay/memory_verify)
    # МОЛЧА стирал confidence и valid_until у узла. Это баг потери данных.
    confidence: float = 0.5            # 0..1 — уверенность в истинности
    valid_until: Optional[str] = None  # ISO-8601 TTL; None = не истекает
    tags: List[str] = field(default_factory=list)  # метки: правило/торговля/...
    # -- авторство рёбер (01.09, приказ Ильи: Алиса в графе) --------------
    # links хранит только id цели — кто провёл связь, было неизвестно.
    # link_meta — паспорт ИСХОДЯЩЕГО ребра: {to_id: {"author": ..., "ts": ...}}.
    # Формат links не тронут, поэтому весь обход графа и старые узлы целы:
    # у узла без паспорта автор просто "unknown".
    link_meta: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # Момент, по который затухание УЖЕ применено к полю weight.
    # Без него decay не идемпотентен: он умножает вес на 0.5**(dt/hl), где
    # dt отсчитывается от last_used, а last_used он намеренно не трогает —
    # поэтому два запуска подряд применяли полный период дважды. Замер
    # 01.09 на 5090: два прогона с интервалом 2 минуты уронили средний вес
    # 0.8714 -> 0.7672, хотя прошло 2 минуты. Теперь отсчёт идёт от
    # max(last_used, decayed_at), и суммарное затухание зависит только от
    # реального времени, а не от того, сколько раз запустился cron.
    decayed_at: Optional[str] = None
    # -- квантование памяти (Ф1 02.09, см. qmem.py) -------------------------
    # level  — текущий уровень детализации 0..2 (L0 полный / L1 сжатый / L2 тезис);
    # levels — сжатые варианты текста {"src": отпечаток L0, "1": {...}, "2": {...}};
    # usage  — попадания в выдачу {"count", "last_hit", "hits": [...]}.
    # Без этих полей в схеме любой from_dict->to_dict (verify/rewrite/
    # reinforce) молча стирал бы уровни — та же дыра, что с confidence 01.09.
    level: int = 0
    levels: Dict[str, Any] = field(default_factory=dict)
    usage: Dict[str, Any] = field(default_factory=dict)
    # -- паспорт записи (wave2, фронт 5): кто и в какой сессии записал узел --
    # Старые узлы этих полей не имеют — читаются с пустыми значениями, формат
    # nodes.json совместим в обе стороны (лишние поля старый код игнорирует).
    agent: str = ""
    session_id: str = ""
    # -- дубли источника: один узел на одно содержание --
    # У пользователя одна и та же заметка лежит в нескольких папках (копия в
    # архиве, копия в задачах). Заводить на них разные узлы значит размножить
    # один факт по графу и разорвать его историю на несколько цепочек.
    # Побеждает первый путь — он становится source; остальные живут здесь.
    # Старые узлы поля не имеют и читаются с пустым списком.
    aliases: List[str] = field(default_factory=list)
    # -- отзыв факта (memory_retract): обратимая пометка ---------------------
    # Узел не удаляется физически: kind становится outdated, а окно валидности
    # закрывается моментом отзыва (valid_until = now). Чтобы отзыв был
    # обратим, прежнее состояние надо где-то хранить — иначе после отзыва
    # неизвестно, чем узел был (fact? rule?) и до какого срока жил. Поле
    # обязано быть в схеме: to_dict/from_dict роняет всё, чего в них нет, и
    # любой rewrite/reinforce молча стёр бы паспорт отзыва (та же дыра, что с
    # confidence 01.09). None — узел никогда не отзывался.
    # Формат: {"ts", "reason", "agent", "prev_kind", "prev_valid_until"}.
    retracted: Optional[Dict[str, Any]] = None

    # -- пластичность ------------------------------------------------------
    def reinforce(self, delta: float = 0.05) -> float:
        """Подкрепление: вес растёт (до потолка), last_used обновляется.

        Фикс аудита 26.08: отрицательная дельта клампится к 0 — иначе вес
        уходил ниже пола WEIGHT_MIN и узел становился невалидным (to_dict
        падал с ValueError). Ослабление — это decay(), не отрицательная дельта.
        """
        delta = max(0.0, float(delta))
        self.weight = min(WEIGHT_MAX, float(self.weight) + delta)
        # подкрепление — сигнал решения, а не ранжирования: base_weight растёт
        # вместе с weight; затухание (decay) его не трогает
        self.base_weight = min(WEIGHT_MAX, float(self.base_weight) + delta)
        self.last_used = now_iso()
        return self.weight

    def decay(
        self,
        now_dt: Optional[datetime] = None,
        half_life_hours: float = DEFAULT_HALF_LIFE_HOURS,
    ) -> float:
        """Затухание: вес падает экспоненциально от времени с последнего
        использования. last_used не трогаем — иначе повторные вызовы
        «омолаживали» бы узел без подкрепления."""
        now_dt = now_dt if now_dt is not None else datetime.now(timezone.utc)
        last = self.decay_ref()
        if last is None or now_dt <= last:
            return self.weight
        dt_h = (now_dt - last).total_seconds() / 3600.0
        if half_life_hours <= 0:
            raise ValueError("half_life_hours must be > 0")
        self.decayed_at = now_dt.isoformat(timespec="milliseconds")
        # пол зависит от вида: kind=rule не опускается ниже 0.5 (аудит §5.7),
        # иначе ПРАВИЛО 1 через месяц станет неотличимо от болтовни.
        self.weight = max(
            weight_floor(self.kind),
            float(self.weight) * (0.5 ** (dt_h / half_life_hours)),
        )
        return self.weight

    def decay_ref(self) -> Optional[datetime]:
        """От какого момента отсчитывать НЕПРИМЕНЁННОЕ затухание.

        Позже из двух: последнее использование и момент, по который затухание
        уже записано в weight. Reinforce сдвигает last_used вперёд и тем самым
        обнуляет накопленный долг — это и есть подкрепление.
        """
        last = _parse_iso(self.last_used)
        done = _parse_iso(self.decayed_at) if self.decayed_at else None
        if last is None:
            return done
        if done is None:
            return last
        return max(last, done)

    # -- темпоральность и уверенность (фикс 01.09) -------------------------
    def is_active(self, now_dt: Optional[datetime] = None) -> bool:
        """Активен ли узел: не истёк TTL и не refuted/outdated."""
        if self.kind in ("refuted", "outdated"):
            return False
        now_dt = now_dt if now_dt is not None else datetime.now(timezone.utc)
        if not self.valid_until:
            return True
        vu = _parse_iso(self.valid_until)
        if vu is None:
            return True  # не парсится — не трогаем, считаем живым
        return now_dt < vu

    def decayed_weight(self, now_dt: Optional[datetime] = None) -> float:
        """Вес с учётом затухания БЕЗ мутации — для ранжирования при чтении."""
        now_dt = now_dt if now_dt is not None else datetime.now(timezone.utc)
        last = self.decay_ref()   # только НЕприменённая часть затухания
        if last is None or now_dt <= last:
            return self.weight
        dt_h = (now_dt - last).total_seconds() / 3600.0
        return max(
            weight_floor(self.kind),
            float(self.weight) * (0.5 ** (dt_h / DEFAULT_HALF_LIFE_HOURS)),
        )

    def rewrite(self, new_claim: str, source: str = "", reason: str = "") -> "MemoryNode":
        """Переписывание узла новым фактом: старое утверждение уходит в
        историю (revisions), узел обновляется на месте — id сохраняется."""
        if not isinstance(new_claim, str) or not new_claim.strip():
            raise ValueError("rewrite: the new claim cannot be empty")
        if new_claim.strip() == self.claim:
            return self
        self.revisions.append(
            {
                "ts": now_iso(),
                "claim_before": self.claim,
                "claim_after": new_claim.strip(),
                "source": source,
                "reason": reason,
            }
        )
        # Д-031: история головы не растёт бесконечно; оставляем только свежие
        # состояния, самые старые выбрасываются.
        self.revisions = self.revisions[-REVISIONS_MAX:]
        self.claim = new_claim.strip()
        if source:
            self.source = source
        self.ts = now_iso()
        self.last_used = now_iso()
        return self

    # -- валидация ---------------------------------------------------------
    def validate(self) -> None:
        """Поднимает ValueError, если узел нарушает схему."""
        if not isinstance(self.claim, str) or not self.claim.strip():
            raise ValueError("claim: the claim cannot be empty")
        if self.kind not in KINDS:
            raise ValueError(
                f"kind: expected one of {KINDS}, got {self.kind!r}"
            )
        if not isinstance(self.source, str):
            raise ValueError("source: must be a string")
        if not isinstance(self.evidence, list) or not all(
            isinstance(e, str) for e in self.evidence
        ):
            raise ValueError("evidence: must be a list of strings")
        if not isinstance(self.aliases, list) or not all(
            isinstance(a, str) for a in self.aliases
        ):
            raise ValueError("aliases: must be a list of strings (alternative sources)")
        if not isinstance(self.context, str):
            raise ValueError("context: must be a string")
        if not isinstance(self.links, list) or not all(
            isinstance(l, str) for l in self.links
        ):
            raise ValueError("links: must be a list of strings (node ids)")
        if not isinstance(self.ts, str) or not self.ts.strip():
            raise ValueError("ts: must be an ISO-8601 timestamp")
        if not isinstance(self.weight, (int, float)) or isinstance(self.weight, bool):
            raise ValueError("weight: must be a number")
        if not (WEIGHT_MIN <= float(self.weight) <= WEIGHT_MAX):
            raise ValueError(
                f"weight: must be within [{WEIGHT_MIN}, {WEIGHT_MAX}], "
                f"got {self.weight!r}"
            )
        if not isinstance(self.base_weight, (int, float)) or isinstance(self.base_weight, bool):
            raise ValueError("base_weight: must be a number")
        if not (WEIGHT_MIN <= float(self.base_weight) <= WEIGHT_MAX):
            raise ValueError(
                f"base_weight: must be within [{WEIGHT_MIN}, {WEIGHT_MAX}], "
                f"got {self.base_weight!r}"
            )
        if not isinstance(self.last_used, str) or not self.last_used.strip():
            raise ValueError("last_used: must be an ISO-8601 timestamp")
        if not isinstance(self.revisions, list):
            raise ValueError("revisions: must be a list")
        for r in self.revisions:
            if not isinstance(r, dict) or not all(
                k in r for k in ("ts", "claim_before", "claim_after")
            ):
                raise ValueError("revisions: every entry is {ts, claim_before, claim_after, ...}")
        if not isinstance(self.children, list) or not all(
            isinstance(c, str) for c in self.children
        ):
            raise ValueError("children: must be a list of strings (node ids)")
        if self.id in self.children:
            raise ValueError("children: a node cannot be its own child")
        if self.parent is not None and not isinstance(self.parent, str):
            raise ValueError("parent: must be a string (id) or None")
        if not isinstance(self.confidence, (int, float)) or isinstance(self.confidence, bool):
            raise ValueError("confidence: must be a number")
        if not (0.0 <= float(self.confidence) <= 1.0):
            raise ValueError(
                f"confidence: must be within [0, 1], got {self.confidence!r}"
            )
        if self.valid_until is not None and not isinstance(self.valid_until, str):
            raise ValueError("valid_until: must be an ISO-8601 string or None")
        if self.valid_until and _parse_iso(self.valid_until) is None:
            raise ValueError(
                f"valid_until: invalid ISO-8601 timestamp: {self.valid_until!r}"
            )
        if not isinstance(self.tags, list) or not all(
            isinstance(t, str) for t in self.tags
        ):
            raise ValueError("tags: must be a list of strings")
        if not isinstance(self.link_meta, dict) or not all(
            isinstance(k, str) and isinstance(v, dict)
            for k, v in self.link_meta.items()
        ):
            raise ValueError(
                "link_meta: must be a dict {to_id: {author, ts}}"
            )
        if self.decayed_at is not None and (
            not isinstance(self.decayed_at, str) or _parse_iso(self.decayed_at) is None
        ):
            raise ValueError(f"decayed_at: an ISO-8601 string or None, got {self.decayed_at!r}")
        if not isinstance(self.level, int) or isinstance(self.level, bool) or not (0 <= self.level <= 2):
            raise ValueError(f"level: an integer 0..2, got {self.level!r}")
        if not isinstance(self.levels, dict):
            raise ValueError("levels: must be a dict of levels")
        if not isinstance(self.usage, dict):
            raise ValueError("usage: must be a dict")

    # -- сериализация ------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "id": self.id,
            "kind": self.kind,
            "claim": self.claim,
            "source": self.source,
            "evidence": list(self.evidence),
            "context": self.context,
            "ts": self.ts,
            "links": list(self.links),
            "truth_check": self.truth_check,
            "weight": self.weight,
            "base_weight": float(self.base_weight),
            "last_used": self.last_used,
            "revisions": [dict(r) for r in self.revisions],
            "children": list(self.children),
            "parent": self.parent,
            "confidence": float(self.confidence),
            "valid_until": self.valid_until,
            "tags": list(self.tags),
            "link_meta": {k: dict(v) for k, v in self.link_meta.items()},
            "decayed_at": self.decayed_at,
            "level": int(self.level),
            "levels": dict(self.levels),
            "usage": dict(self.usage),
            "agent": str(self.agent or ""),
            "session_id": str(self.session_id or ""),
            "aliases": list(self.aliases),
            "retracted": dict(self.retracted) if self.retracted else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryNode":
        if not isinstance(data, dict):
            raise ValueError("a node must be an object (dict)")
        required = ("id", "kind", "claim")
        missing = [k for k in required if k not in data]
        if missing:
            raise ValueError(f"the node is incomplete, missing fields: {missing}")
        # фикс аудита 26.08: truth_check: null (или не-dict) в JSON — трактуем
        # как «ещё не проверено» (pending), а не роняем загрузку TypeError.
        tc = data.get("truth_check")
        if not isinstance(tc, dict):
            tc = dict(_PENDING_TRUTH_CHECK)
        node = cls(
            id=str(data["id"]),
            kind=str(data["kind"]),
            claim=str(data["claim"]),
            source=str(data.get("source", "")),
            evidence=[str(e) for e in data.get("evidence", [])],
            context=str(data.get("context", "")),
            ts=str(data.get("ts", "")),
            links=[str(l) for l in data.get("links", [])],
            truth_check=tc,
            weight=float(data.get("weight", WEIGHT_MAX)),
            base_weight=decision_weight(data),
            last_used=str(data.get("last_used", data.get("ts", "") or now_iso())),
            revisions=[dict(r) for r in data.get("revisions", [])],
            children=[str(c) for c in data.get("children", [])],
            parent=data.get("parent"),
            confidence=float(data.get("confidence", 0.5)),
            valid_until=data.get("valid_until"),
            tags=[str(t) for t in data.get("tags", [])],
            link_meta=coerce_link_meta(data.get("link_meta")),
            decayed_at=data.get("decayed_at"),
            level=_coerce_level(data.get("level")),
            levels=dict(data["levels"]) if isinstance(data.get("levels"), dict) else {},
            usage=dict(data["usage"]) if isinstance(data.get("usage"), dict) else {},
            agent=str(data.get("agent") or ""),
            session_id=str(data.get("session_id") or ""),
            aliases=[str(a) for a in data.get("aliases", [])],
            retracted=(dict(data["retracted"])
                       if isinstance(data.get("retracted"), dict) else None),
        )
        node.validate()
        return node


def make_node(
    claim: str,
    source: str = "",
    evidence: Optional[List[str]] = None,
    context: str = "",
    kind: str = "fact",
    links: Optional[List[str]] = None,
    ts: Optional[str] = None,
    confidence: Optional[float] = None,
    ttl_hours: Optional[float] = None,
    valid_until: Optional[str] = None,
    tags: Optional[List[str]] = None,
    aliases: Optional[List[str]] = None,
) -> MemoryNode:
    """Фабрика узла памяти с автоматическим id и timestamp.

    ttl_hours — удобная форма valid_until: «протухнет через N часов от ts».
    Явный valid_until имеет приоритет над ttl_hours.
    """
    created = ts if ts is not None else now_iso()
    if valid_until is None and ttl_hours is not None:
        base = _parse_iso(created) or datetime.now(timezone.utc)
        valid_until = (base + timedelta(hours=float(ttl_hours))).isoformat(
            timespec="milliseconds"
        )
    node = MemoryNode(
        claim=claim,
        source=source,
        evidence=list(evidence or []),
        context=context,
        kind=kind,
        links=list(links or []),
        ts=created,
        confidence=float(confidence) if confidence is not None else 0.5,
        valid_until=valid_until,
        tags=[str(t) for t in (tags or [])],
        aliases=[str(a) for a in (aliases or [])],
    )
    node.validate()
    return node
