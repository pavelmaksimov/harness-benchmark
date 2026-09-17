# -*- coding: utf-8 -*-
"""Срез графа под один ход с квотой токенов на узел (R10 §2, T10.4).

Перенесено из research/r10/r10lib.py (GraphSlicer). Что здесь живёт:

  * Quota / SliceResult — что случилось с каждым узлом при сборке среза;
  * node_render_full / node_render_compress / node_render_ref — три ступени
    потери: целиком -> сжато (заголовок + якоря) -> ссылка;
  * GraphSlicer — раздача бюджета B по узлам-кандидатам.

Формула квоты:
    w_i     = rank_i^alpha * fresh_i^beta * role_i
    share_i = w_i / sum(w)
    quota_i = clamp(B * share_i, q_min, q_max)

Политика квот (R10, policybench, 20 задач на снимке живого графа):
  равная делёжка при top_k=30 и B=2200 оставляет узлу-ответу ~90 токенов —
  узел в срезе есть, а его якоря (пути к файлам, D-NNN, mn_id, числа) при
  сжатии выпадают: все якоря доживали до текста лишь в 0.05 задач. Пол
  TARGET_FLOOR=0.5 — половина бюджета отдаётся верхним N_TARGETS узлам вне
  конкурса — поднял долю задач со всеми якорями до 0.40-0.45 при том же
  бюджете (якорей в тексте 0.38 -> 0.65). Пол 0.7 уже топит соседей
  (узел-цель в срезе 0.8 -> 0.6). Поэтому 0.5 — умолчание модуля.

Правила (kind=rule) получают квоту вне конкурса и не выбрасываются, но
и не съедают срез: не больше MAX_RULES штук и не больше RULE_SHARE_CAP
бюджета (замер R10: без потолка одно правило брало 2169 из 2200 токенов).
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .budget import BudgetSearch, estimate_tokens, is_volatile
from .model import DEFAULT_HALF_LIFE_HOURS, _parse_iso

# --- умолчания политики (R10 policybench, B=2200) ----------------------------
DEFAULT_BUDGET = 2200
TARGET_FLOOR = 0.5      # доля бюджета верхним N_TARGETS узлам вне конкурса
N_TARGETS = 2
MAX_SHARE_MIN = 0.35    # ни один узел не берёт больше max_share бюджета
RULE_FLOOR = 220
MAX_RULES = 2
RULE_SHARE_CAP = 0.25

ROLE_W = {
    "rule": 4.0,        # правило-конституция: не выбрасывается никогда
    "target": 3.0,      # прямое попадание в запрос хода
    "state": 2.5,       # состояние задачи: уже пробовал, отвергнутые ветки
    "neighbour": 1.0,   # сосед по ребру
    "background": 0.4,  # фон
}

_FACT_RE = re.compile(r"(?:mn_[0-9a-f]{6,}|D-\d{2,3}|OD-\d+|T[A-Z]?\.?\d+|\d[\d\s.,%$]*|"
                      r"[A-Za-z_][A-Za-z0-9_./-]*\.(?:py|md|json|sh|toml|plist)|"
                      r"[A-Za-z][A-Za-z0-9_]{3,}\(\)?)")


def toks(text: Any) -> int:
    """Тот же счётчик, что в mnemos.budget (RU ~2.6 симв/токен)."""
    return estimate_tokens(str(text or ""))


def max_share_for(target_floor: float) -> float:
    """Потолок доли на узел, согласованный с полом: пол на N_TARGETS=2 узла
    по target_floor/2 каждому должен помещаться под потолок."""
    return max(MAX_SHARE_MIN, target_floor / 2 + 0.05)


@dataclass
class Quota:
    """Что случилось с одним узлом при сборке среза."""
    nid: str
    rank: float
    fresh: float
    role: str
    role_w: float
    weight: float
    quota: int
    spent: int
    action: str          # full | compress | ref | drop
    kind: str = ""


@dataclass
class SliceResult:
    text: str
    quotas: List[Quota]
    tokens: int
    build_ms: float
    picked: List[str]
    dropped: List[str]
    retrieved: List[str] = field(default_factory=list)


def _fresh(node: Dict[str, Any], now: datetime, half_life_h: float = DEFAULT_HALF_LIFE_HOURS) -> float:
    ts = _parse_iso(node.get("ts"))
    if not ts:
        return 0.5
    age_h = max(0.0, (now - ts).total_seconds() / 3600.0)
    return 0.5 ** (age_h / max(1.0, half_life_h))


def node_render_full(n: Dict[str, Any]) -> str:
    parts = [f"[{n.get('id')}] ({n.get('kind')}) {n.get('claim')}"]
    ctx = (n.get("context") or "").strip()
    if ctx:
        parts.append(ctx)
    src = (n.get("source") or "").strip()
    if src:
        parts.append(f"источник: {src}")
    tags = n.get("tags") or []
    if tags:
        parts.append("теги: " + ", ".join(str(t) for t in tags[:12]))
    return "\n".join(parts)


def node_render_compress(n: Dict[str, Any], quota: int) -> str:
    """Сжатие под квоту: заголовок целиком + предложения по порядку, пока
    лезут, + якорные факты из невлезшего хвоста (id, номера решений, пути,
    числа — то же, что бережёт truth-gate). Проза выбрасывается первой."""
    head = f"[{n.get('id')}] ({n.get('kind')}) {n.get('claim')}"
    if toks(head) >= quota:
        return head[: max(40, int(quota * 2.6))]
    body = (n.get("context") or "")
    out = [head]
    left = quota - toks(head)
    sents = [s.strip() for s in re.split(r"(?<=[.!?…])\s+|\n+", body) if s.strip()]
    picked: List[str] = []
    for s in sents:
        t = toks(s)
        if t <= left:
            picked.append(s)
            left -= t
        else:
            break
    if picked:
        out.append(" ".join(picked))
    rest = " ".join(sents[len(picked):])
    if rest and left > 8:
        anchors: List[str] = []
        seen = set()
        for m in _FACT_RE.finditer(rest):
            a = m.group(0).strip(" .,;")
            if len(a) < 2 or a.lower() in seen:
                continue
            seen.add(a.lower())
            if toks(a) + 1 > left:
                break
            left -= toks(a) + 1
            anchors.append(a)
        if anchors:
            out.append("якоря: " + " · ".join(anchors[:40]))
    return "\n".join(out)


def node_render_ref(n: Dict[str, Any]) -> str:
    claim = str(n.get("claim") or "")[:120]
    return f"[{n.get('id')}] ({n.get('kind')}) {claim} … ← открыть по требованию"


class GraphSlicer:
    """Сборка среза графа под ОДИН ход, с квотой токенов на узел.

    Переполнение: full -> compress -> ref -> drop, по возрастанию потери.
    target_floor — политика квот T10.4 (см. шапку модуля): верхние n_targets
    узла-кандидата получают не меньше B*target_floor/n_targets каждый.
    """

    def __init__(self, nodes: Dict[str, Dict[str, Any]], budget: int = DEFAULT_BUDGET,
                 alpha: float = 1.0, beta: float = 0.35,
                 q_min: int = 40, q_max: int = 420, top_k: int = 30,
                 max_share: Optional[float] = None, rule_floor: int = RULE_FLOOR,
                 max_rules: int = MAX_RULES, rule_share_cap: float = RULE_SHARE_CAP,
                 target_floor: float = TARGET_FLOOR, n_targets: int = N_TARGETS,
                 engine: Optional[BudgetSearch] = None):
        self.nodes = nodes
        self.engine = engine or BudgetSearch(nodes)
        self.budget = budget
        self.alpha = alpha
        self.beta = beta
        self.q_min = q_min
        self.q_max = q_max
        self.top_k = top_k
        self.target_floor = float(target_floor or 0.0)
        self.n_targets = max(1, int(n_targets))
        # Ни один узел не забирает больше max_share бюджета — включая правило
        # («правило не режется» здесь = «правило не ВЫБРАСЫВАЕТСЯ»).
        self.max_share = float(max_share) if max_share else max_share_for(self.target_floor)
        self.rule_floor = rule_floor
        # Правила ведут в ранге при любом запросе (budget.RULE_RANK_LEAD); для
        # среза под ход это гибельно — потолок на число и долю правил.
        self.max_rules = max_rules
        self.rule_share_cap = rule_share_cap

    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[Tuple[str, float]]:
        r = self.engine.search(query, top_k=top_k or self.top_k, token_budget=10 ** 7,
                               expand=True)
        out = []
        for item in r.get("results", []):
            nid = item.get("id") or item.get("node", {}).get("id")
            if nid:
                out.append((nid, float(item.get("score") or 0.0)))
        return out

    def target_quota(self, budget: Optional[int] = None) -> int:
        """Сколько токенов гарантирует пол одному узлу-цели."""
        B = int(budget or self.budget)
        return int(B * self.target_floor / self.n_targets) if self.target_floor else 0

    def build(self, query: str, forced: Optional[Dict[str, str]] = None,
              budget: Optional[int] = None, top_k: Optional[int] = None) -> SliceResult:
        """forced: {node_id: role} — узлы, которые обязаны быть в срезе
        (состояние хода, правила задачи). Остальное добирает поиск."""
        t0 = time.perf_counter()
        B = int(budget or self.budget)
        now = datetime.now(timezone.utc)
        forced = dict(forced or {})

        cand: Dict[str, str] = {}
        for nid, role in forced.items():
            if nid in self.nodes:
                cand[nid] = role
        ranks: Dict[str, float] = {}
        for nid, sc in self.retrieve(query, top_k=top_k):
            ranks[nid] = sc
            # T10.5: служебный летучий узел (счётчик решений
            # mn_example и т.п.) имеет kind=rule и роутер sys_cmd, поэтому
            # лидировал в ранге на ЛЮБОМ запросе и занимал одно из двух мест
            # правила в срезе. Содержания для хода в нём нет — вон из выдачи.
            # Явный forced его пропускает: спросили именно счётчик — покажем.
            if nid not in forced and is_volatile(self.nodes.get(nid) or {}):
                continue
            cand.setdefault(nid, "target")
        top = ranks.values()
        rmax = max(top) if top else 1.0
        for nid in cand:
            if nid not in ranks:
                ranks[nid] = rmax  # forced идёт по верхнему рангу
            if self.nodes[nid].get("kind") == "rule":
                cand[nid] = "rule"
        rule_ids = sorted((i for i in cand if cand[i] == "rule"),
                          key=lambda i: -ranks.get(i, 0.0))
        for nid in rule_ids[self.max_rules:]:
            cand[nid] = "background"

        ws: Dict[str, float] = {}
        fr: Dict[str, float] = {}
        for nid, role in cand.items():
            n = self.nodes[nid]
            rank = (ranks.get(nid, 0.0) / rmax) if rmax > 0 else 0.0
            f = _fresh(n, now)
            fr[nid] = f
            ws[nid] = max(1e-6, (max(rank, 1e-3) ** self.alpha) * (max(f, 1e-3) ** self.beta)
                          * ROLE_W.get(role, 1.0))
        total_w = sum(ws.values()) or 1.0

        # порядок раздачи: правила, потом по весу
        order = sorted(cand, key=lambda i: (cand[i] != "rule", -ws[i]))
        top_targets = [i for i in order if cand[i] != "rule"][: self.n_targets]
        floor_q = self.target_quota(B)
        quotas: List[Quota] = []
        chunks: List[str] = []
        left = B
        rule_left = int(B * self.rule_share_cap)
        for nid in order:
            n = self.nodes[nid]
            role = cand[nid]
            q = int(max(self.q_min, min(self.q_max, B * ws[nid] / total_w)))
            need = toks(node_render_full(n))
            if role == "rule":
                q = max(q, self.rule_floor)     # правило не выбрасывается
                q = min(q, max(self.q_min, rule_left))  # но и не съедает срез
            if floor_q and nid in top_targets:
                q = max(q, floor_q)             # пол на узел-цель (T10.4)
            q = int(min(q, B * self.max_share))
            if left <= 0:
                quotas.append(Quota(nid, ranks.get(nid, 0.0), fr[nid], role, ROLE_W.get(role, 1.0),
                                    ws[nid], q, 0, "drop", n.get("kind", "")))
                continue
            q = min(q, left)
            if need <= q:
                body, action, spent = node_render_full(n), "full", need
            elif q >= self.q_min:
                body = node_render_compress(n, q)
                action, spent = "compress", toks(body)
            else:
                body = node_render_ref(n)
                action, spent = "ref", toks(body)
            if spent > left:
                body = node_render_ref(n)
                action, spent = "ref", toks(body)
                if spent > left:
                    quotas.append(Quota(nid, ranks.get(nid, 0.0), fr[nid], role,
                                        ROLE_W.get(role, 1.0), ws[nid], q, 0, "drop",
                                        n.get("kind", "")))
                    continue
            left -= spent
            if role == "rule":
                rule_left -= spent
            chunks.append(body)
            quotas.append(Quota(nid, ranks.get(nid, 0.0), fr[nid], role, ROLE_W.get(role, 1.0),
                                ws[nid], q, spent, action, n.get("kind", "")))
        text = "\n\n".join(chunks)
        ms = (time.perf_counter() - t0) * 1000.0
        res = SliceResult(text=text, quotas=quotas, tokens=toks(text), build_ms=ms,
                          picked=[q.nid for q in quotas if q.action != "drop"],
                          dropped=[q.nid for q in quotas if q.action == "drop"])
        res.retrieved = list(ranks)
        return res


def norm_txt(s: Any) -> str:
    """Нормализация для проверки «якорь дожил до текста среза»."""
    s = str(s or "").lower().replace("ё", "е")
    return re.sub(r"[^0-9a-zа-я_./:-]+", " ", s)


def anchors_survived(text: str, anchors: List[str]) -> List[str]:
    st = norm_txt(text)
    return [a for a in anchors if norm_txt(a).strip() in st]
