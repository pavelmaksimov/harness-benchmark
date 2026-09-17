# -*- coding: utf-8 -*-
"""Одна деградация полос на всех потребителей шлюза.

Замер 09.09 вскрыл не единичный баг, а класс отказа: бесплатная полоса
отвечает 429 («daily token budget … resets at 00:00 UTC») или 503, запасная одна
и тоже мёртвая — и тик кончается строкой в чужом журнале и ничем больше.
Оператор отдал 3 поста вместо ~41, и никто этого не увидел до утра.

Починку сделали внутри вызывающем модуле. Ровно те же вызовы шлюза живут у
публикатора, у сводок tg-stream и у планировщика оркестратора — со своей
обвязкой у каждого. Второй такой список полос разъехался бы с первым в первую
же неделю, поэтому цепочка, распознавание отказа, пауза при поминутном лимите и
журнал причины живут здесь, а потребители остаются тонкими.

Что тут есть и чего нет:

* `ask()` — один вопрос, цепочка полос, `None`, если не ответила ни одна.
  Причина отказа каждой полосы называется вслух — молчаливый `None` выше по
  стеку и есть разница между починкой за минуту и за вечер.
* `SilenceGuard` — сторож «молчаливая смерть тика»: тик, где полосы дали ноль
  ответов, пишет строку причины и узел `kind=incident`, но не чаще раза в час.
  Отметка о последнем узле лежит **файлом**: каждый тик — отдельный процесс, и
  счётчик в памяти процесса ограничивал бы ровно ничего.
* Сети сверх запроса к шлюзу тут нет, памяти — тоже: узел пишет тот, кто передал
  `mem_add`. Модуль ничего не знает про вызывающие подсистемы и очередь.

Платные полосы в цепочку не попадают ни в каком порядке: вне торговли они
закрыты правилом проекта, и запасной путь не должен открывать их заново.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

#: Hub на удалённый хост (через туннель — localhost). Умеет **только** `/v1/responses`
#: (OpenAI Responses API); `/v1/chat/completions` он не маршрутизирует.
HUB = "http://localhost:8790/v1/responses"

#: Полоса по умолчанию — псевдоним, а не имя модели: раскрывает его шлюз, и
#: модель меняется правкой `routes.json`, а не этого файла.
DEFAULT_MODEL = "shine-cheap"

#: Запасные полосы. Замер 2026-09-10 (удалённый хост, один и тот же короткий промпт):
#: `shine-cheap` → 429 «daily token budget … exhausted»; `gemma-2-9b-it`
#: (LM Studio) → 503/500/таймаут. Живыми ответили `shine-light`,
#: `cohere/north-mini-code:free` и `nvidia/nemotron-3-super-120b-a12b:free`.
FALLBACKS: Tuple[str, ...] = ("shine-light", "cohere/north-mini-code:free",
                              "nvidia/nemotron-3-super-120b-a12b:free",
                              "gemma-2-9b-it")

#: Коды, при которых имеет смысл сменить полосу: полоса закрыта, а не запрос
#: плох. 403/404 здесь потому, что незнакомый шлюзу псевдоним выглядит именно
#: так — это тоже «полосы нет». На 400 полоса не меняется: плохой запрос
#: останется плохим и на второй модели, а перебор потратит вторую квоту.
SWITCHABLE: Tuple[int, ...] = (403, 404, 429, 502, 503)

#: Псевдокод «полоса ответила, но текста не отдала». Это свойство полосы
#: (модель проедает лимит рассуждением и до текста не доходит), а не случайность:
#: повтор того же промпта на ней даст то же самое — берём следующую.
EMPTY = "empty"

#: Поминутный лимит (OTPM/TPM) — единственный отказ, который проходит сам:
#: минута кончится, и полоса снова живая. Суточный бюджет так не проходит,
#: поэтому паузу даёт только поминутный, и распознаётся он по тексту отказа.
OTPM = re.compile(r"per[-\s]?min|/\s?min\b|\botpm\b|\btpm\b|rate[-\s]?limit",
                  re.I)
#: Не пауза «на всякий случай», а по замеру Groq: окно лимита — минута,
#: и ждать её целиком дороже, чем взять следующую полосу. Ждём один раз.
OTPM_PAUSE_S = float(os.environ.get("SHINE_BAND_OTPM_PAUSE_S", "8"))

#: Суточный бюджет паузой не лечится — по этим словам полоса выбывает сразу.
DAILY = re.compile(r"daily|resets at|per[-\s]?day|суточн", re.I)


class BandError(RuntimeError):
    """Ни одна полоса не ответила, а вызывающий просил падать."""


def is_switchable(code: Any) -> bool:
    """Стоит ли пробовать следующую полосу.

    Код бывает строкой (`"429"` в теле ошибки шлюза) — тогда прямое сравнение с
    числами `SWITCHABLE` молча ложно, и полоса не меняется.
    """
    if code == EMPTY:
        return True
    if isinstance(code, str) and code.strip().isdigit():
        code = int(code.strip())
    return code in SWITCHABLE


def needs_pause(code: Any, note: str) -> bool:
    """Отказ, который пройдёт сам через минуту (поминутный лимит), а не суточный."""
    if code != 429 and str(code).strip() != "429":
        return False
    return bool(OTPM.search(note or "")) and not DAILY.search(note or "")


def extract_text(body: Dict[str, Any]) -> str:
    """Текст ответа Responses API. Блоки reasoning пропускаются."""
    parts: List[str] = []
    for item in body.get("output") or []:
        if item.get("type") != "message":
            continue
        for chunk in item.get("content") or []:
            if chunk.get("type") in ("output_text", "text"):
                parts.append(chunk.get("text") or "")
    return "\n".join(p for p in parts if p).strip()


def ask_one(prompt: str, model: str, hub: str = HUB,
            max_output_tokens: int = 4000, timeout: float = 180.0,
            reasoning: Optional[str] = None, *,
            source: str = "service",
            lane: str = "") -> Tuple[Optional[str], Optional[Any], str]:
    """Ответ одной полосы: (текст, код отказа, пояснение).

    `reasoning="low"` придерживает рассуждение: у полос с жёстким лимитом вывода
    модель иначе проедает весь лимит на reasoning и до текста не доходит —
    снаружи это выглядит как «полоса недоступна».

    `X-Shine-Source` обязателен: кто не назвался, для хаба ручная сессия, а не
    служба, — он не гадает.
    """
    payload: Dict[str, Any] = {"model": model, "input": prompt,
                               "max_output_tokens": max_output_tokens}
    if reasoning:
        payload["reasoning"] = {"effort": reasoning}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json", "X-Shine-Source": source}
    if lane:
        headers["X-Shine-Lane"] = lane
    req = urllib.request.Request(hub, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        return None, exc.code, f"hub HTTP {exc.code}: {detail}"
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return None, None, f"hub недоступен: {exc}"
    if body.get("error"):                    # hub отвечает 200 с телом ошибки
        err = body["error"]
        return None, err.get("code"), f"hub: {err.get('message')}"
    text = extract_text(body)
    if not text:
        # Ответ без блока message: полоса работает и деньги потрачены, но до
        # текста модель не дошла. Отсюда явный разбор status/incomplete_details.
        reason = ((body.get("incomplete_details") or {}).get("reason")
                  or body.get("status") or "ответ без текста")
        return None, EMPTY, f"пустой ответ ({reason}); лимит вывода {max_output_tokens}"
    return text, None, ""


def ask_verbose(prompt: str, *, model: str = DEFAULT_MODEL, hub: str = HUB,
                max_output_tokens: int = 4000, timeout: float = 180.0,
                reasoning: Optional[str] = None,
                fallbacks: Sequence[str] = FALLBACKS,
                accept: Optional[Callable[[str], bool]] = None,
                source: str = "service", lane: str = "",
                one: Optional[Callable[..., Tuple[Optional[str], Optional[Any], str]]] = None,
                sleep: Callable[[float], None] = time.sleep,
                ) -> Tuple[Optional[str], List[str]]:
    """Цепочка полос: (текст, причины отказа по полосам).

    Причины возвращаются всегда, в том числе при успехе с третьей попытки:
    сторож молчаливого тика и журнал прогона хотят знать, кто отказал и почему,
    а не только итог.
    """
    call = one or ask_one
    reasons: List[str] = []
    for candidate in (model, *fallbacks):
        for attempt in (1, 2):
            text, code, note = call(prompt, candidate, hub, max_output_tokens,
                                    timeout, reasoning)
            if text or attempt == 2 or not needs_pause(code, note):
                break
            # Поминутный лимит: окно кончится само, и это единственный отказ,
            # который стоит переждать на той же полосе, а не менять её.
            reasons.append(f"{candidate}: поминутный лимит, пауза "
                           f"{OTPM_PAUSE_S:.0f} с — {note[:120]}")
            _say(reasons[-1])
            sleep(OTPM_PAUSE_S)
        if text and (accept is None or accept(text)):
            return text, reasons
        if text:
            # Ответ есть, но требованию вызывающего не отвечает — почти всегда
            # это длина. Повтор того же промпта на той же полосе даст то же
            # самое: тот же случай, что и закрытая полоса, — берём следующую.
            reasons.append(f"{candidate}: ответ не прошёл требование вызывающего "
                           f"({len(text)} знаков)")
            _say(f"полоса {candidate} отдала негодный ответ ({len(text)} знаков) "
                 f"— пробую следующую")
            continue
        reasons.append(f"{candidate}: {note}")
        if not is_switchable(code):
            break
        _say(f"полоса {candidate} закрыта ({note[:120]}) — пробую следующую")
    return None, reasons


def ask(prompt: str, *, raise_on_error: bool = False, **kw) -> Optional[str]:
    """Один вопрос — один ответ. `None`, если не ответила ни одна полоса."""
    text, reasons = ask_verbose(prompt, **kw)
    if text:
        return text
    last = reasons[-1] if reasons else ""
    if raise_on_error:
        raise BandError(last or "полоса не ответила")
    _say(f"полоса не ответила — {last or 'причина неизвестна'}")
    return None


def _say(line: str) -> None:
    print(line, file=sys.stderr)


# --------------------------------------------------------------------------- #
# Сторож: молчаливая смерть тика
# --------------------------------------------------------------------------- #
#: Куда кладётся отметка о последнем узле. Каждый тик — отдельный процесс,
#: поэтому «не чаще раза в час» может держаться только файлом.
STATE_DIR = Path(os.environ.get("SHINE_BAND_STATE_DIR",
                                str(Path.home() / ".shine" / "bands")))
#: Час — не круглое число, а шаг тиков: оператор постит раз в 35 минут,
#: публикатор — раз в час. Узел на каждый тик засыпал бы граф копиями одного факта.
INCIDENT_EVERY_S = float(os.environ.get("SHINE_BAND_INCIDENT_EVERY_S", "3600"))

INCIDENT_TAGS = ("bands", "degradation", "thread:shinemnemos", "visibility:private")


class SilenceGuard:
    """Тик, где полосы дали ноль ответов, обязан сказать это вслух.

    `mem_add(claim=…, kind=…, source=…, tags=…, context=…)` передаёт вызывающий:
    у вызывающих подсистем клиенты памяти разные, а модуль про них
    не знает. Без `mem_add` сторож всё равно пишет строку причины — журнал
    службы есть у всех, а память бывает недоступна ровно тогда, когда всё лежит.
    """

    def __init__(self, component: str, *,
                 mem_add: Optional[Callable[..., Any]] = None,
                 every_s: float = INCIDENT_EVERY_S,
                 state_dir: Optional[Path] = None,
                 now: Callable[[], float] = time.time) -> None:
        self.component = component
        self.mem_add = mem_add
        self.every_s = every_s
        self.state_dir = Path(state_dir) if state_dir else STATE_DIR
        self.now = now

    @property
    def state_path(self) -> Path:
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", self.component) or "band"
        return self.state_dir / f"silence-{safe}.json"

    def _last(self) -> float:
        try:
            return float(json.loads(self.state_path.read_text("utf-8"))["ts"])
        except (OSError, ValueError, KeyError, TypeError):
            return 0.0

    def _stamp(self, ts: float) -> None:
        try:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(json.dumps({"ts": ts}), "utf-8")
        except OSError as exc:                # диск только для темпа узлов
            _say(f"сторож полос: не смог записать отметку ({exc})")

    def due(self) -> bool:
        """Пора ли писать узел: прошло ли `every_s` с прошлого."""
        return (self.now() - self._last()) >= self.every_s

    def silent_tick(self, reasons: Sequence[str], *, detail: str = "") -> bool:
        """Тик кончился ничем. Возвращает True, если узел записан.

        Строка причины пишется **всегда**: она стоит ноль и без неё в журнале
        остаётся только тишина. Узел — не чаще раза в час.
        """
        why = "; ".join(r for r in reasons if r) or "причина не названа"
        _say(f"[{self.component}] тик без ответа полос: {why}")
        if not self.due():
            return False
        claim = (f"{self.component}: тик кончился без единого ответа полос — "
                 f"{why[:600]}")
        ts = self.now()
        try:
            if self.mem_add is not None:
                self.mem_add(claim=claim, kind="incident",
                             source=f"mnemos/bands.py: сторож молчаливого тика "
                                    f"({self.component})",
                             tags=list(INCIDENT_TAGS) + [f"component:{self.component}"],
                             context=detail)
        except Exception as exc:              # noqa: BLE001 — память не должна ронять тик
            _say(f"сторож полос: узел не записан ({exc})")
            return False
        self._stamp(ts)
        return self.mem_add is not None
