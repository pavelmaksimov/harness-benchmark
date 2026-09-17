"""Индекс кандидатов подстрочного поиска (R12-10).

Задача. И `Store.search`, и `BudgetSearch.candidates` спрашивают у графа одно
и то же: «в каких узлах строка запроса встречается как подстрока склеенного
текста (blob)». До 10.09 ответ считался линейным проходом по всем узлам —
`q in blob` для каждого. На 8203 узлах (9.1 МБ блоба) это 18 мс на запрос,
на 100k — секунды.

Идея. Держим обратный индекс «слово блоба -> id узлов» и по запросу отдаём
НАДМНОЖЕСТВО подходящих узлов; окончательную проверку `q in blob` делает
вызывающий по этому надмножеству. Значит выдача побайтово та же, что у
линейного прохода, — индекс только сокращает число проверок.

Почему надмножество честное. Запрос режется на слова тем же алфавитом, что и
блоб. Слово запроса называется «якорным», если внутри запроса у него с обеих
сторон стоит не-словарный символ (или граница запроса не по букве): тогда в
блобе оно обязано встретиться ЦЕЛЫМ словом, и достаточно взять узлы из его
корзины. Крайние слова запроса якорными не считаются: «ыручк» — кусок слова
«выручка», целым словом его в блобе нет. Если якорных слов нет вовсе (обычный
случай однословного запроса), берём самое длинное слово и обходим СЛОВАРЬ
(44 тыс. строк, 1.3 мс), а не блобы (9 МБ) — узлы собираем из корзин слов,
содержащих кусок. Короче трёх символов кусок не сужает ничего: возвращаем
None, и вызывающий честно делает линейный проход.

Файл на диске (`<стор>.index.json`, только stdlib) — кэш старта, а не
источник истины: при несовпадении паспорта (число узлов, подпись снимка,
позиция журнала) индекс собирается заново из блобов. Корзины хранятся
строками номеров и разбираются лениво, по обращению: старт не платит за
разбор 431 тыс. постингов, если запрос трогает десяток слов.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Union

logger = logging.getLogger("mnemos.search_index")

SCHEMA = 1
# Алфавит слова: буквы (кириллица/латиница), цифры, подчёркивание. Всё
# остальное — разделитель, как и в блобе (blob уже в нижнем регистре).
_WORD_RE = re.compile(r"[0-9a-zа-яё_]+")
# Кусок короче этого словарь не сужает (слишком много слов его содержат).
MIN_SCAN_LEN = 3
# Слова длиннее не индексируем целиком (base64/хеши раздувают словарь):
# такой запрос уйдёт по общему пути (линейный проход) и останется верным.
MAX_TOKEN_LEN = 64


def words(text: str) -> Set[str]:
    """Слова блоба (уникальные, не длиннее MAX_TOKEN_LEN)."""
    return {w for w in _WORD_RE.findall(text) if len(w) <= MAX_TOKEN_LEN}


def anchored_tokens(query_low: str) -> List[str]:
    """Слова запроса, которые в блобе обязаны быть целыми словами.

    Крайнее слово якорное только если запрос с этой стороны обрывается не
    буквой: «» -> «d», «109» якорные, «выручк» — нет.
    """
    out: List[str] = []
    for m in _WORD_RE.finditer(query_low):
        left_ok = m.start() > 0
        right_ok = m.end() < len(query_low)
        if left_ok and right_ok and len(m.group(0)) <= MAX_TOKEN_LEN:
            out.append(m.group(0))
    return out


class SubstringIndex:
    """Обратный индекс «слово -> id узлов» с ленивым разбором корзин."""

    def __init__(self) -> None:
        self._post: Dict[str, Union[str, Set[str]]] = {}
        self._ids: List[str] = []          # таблица id для ленивых корзин
        self.dirty = False
        self.meta: Dict[str, Any] = {}

    # -- содержимое --------------------------------------------------------
    def __len__(self) -> int:
        return len(self._post)

    def _bucket(self, tok: str) -> Optional[Set[str]]:
        """Корзина слова; строку из файла разбираем при первом обращении."""
        raw = self._post.get(tok)
        if raw is None:
            return None
        if isinstance(raw, str):
            ids = self._ids
            try:
                bucket = {ids[int(i)] for i in raw.split()}
            except (ValueError, IndexError):  # битый файл — слово теряем
                bucket = set()
            self._post[tok] = bucket
            return bucket
        return raw

    def add(self, nid: str, blob: str) -> None:
        for tok in words(blob):
            bucket = self._bucket(tok)
            if bucket is None:
                self._post[tok] = {nid}
            else:
                bucket.add(nid)
        self.dirty = True

    def remove(self, nid: str, blob: str) -> None:
        """Убрать узел. blob — тот, по которому узел был проиндексирован."""
        for tok in words(blob):
            bucket = self._bucket(tok)
            if bucket is None:
                continue
            bucket.discard(nid)
            if not bucket:
                del self._post[tok]
        self.dirty = True

    def build(self, blobs: Dict[str, str]) -> None:
        self._post = {}
        self._ids = []
        post: Dict[str, Set[str]] = {}
        for nid, blob in blobs.items():
            for tok in words(blob):
                bucket = post.get(tok)
                if bucket is None:
                    post[tok] = {nid}
                else:
                    bucket.add(nid)
        self._post = dict(post)
        self.dirty = True

    # -- запрос ------------------------------------------------------------
    def candidates(self, query_low: str, max_hits: Optional[int] = None) -> Optional[Set[str]]:
        """Надмножество узлов, где query_low МОЖЕТ встретиться подстрокой.

        None — «сузить не смогла, делай полный проход»: запрос без слов, из
        одного слишком короткого куска, или кандидатов набралось больше
        max_hits (кусок вроде «прав» лежит в половине графа — собирать из него
        множество дороже, чем пройти блобы подряд).
        """
        anchored = anchored_tokens(query_low)
        if anchored:
            # пересечение корзин, начиная с самой маленькой
            buckets: List[Set[str]] = []
            for tok in set(anchored):
                bucket = self._bucket(tok)
                if not bucket:
                    return set()  # слова нет ни в одном узле — и подстроки нет
                buckets.append(bucket)
            buckets.sort(key=len)
            if max_hits is not None and len(buckets[0]) > max_hits:
                # самая маленькая корзина и та шире порога: пересечение будет
                # стоить как проход по блобам — пусть его делает вызывающий
                return None
            out = set(buckets[0])
            for bucket in buckets[1:]:
                out &= bucket
                if not out:
                    break
            return out
        toks = [w for w in _WORD_RE.findall(query_low) if len(w) >= MIN_SCAN_LEN]
        if not toks:
            return None
        piece = max(toks, key=len)
        matched = [w for w in self._post if piece in w]
        buckets = [b for b in (self._bucket(w) for w in matched) if b]
        if max_hits is not None and sum(len(b) for b in buckets) > max_hits:
            # кусок лежит в половине графа: объединять корзины дороже, чем
            # пройти блобы подряд (счёт по длинам — до сборки множества)
            return None
        out: Set[str] = set()
        for bucket in buckets:
            out |= bucket
        return out

    # -- файл рядом со стором ---------------------------------------------
    @staticmethod
    def path_for(store_path: Union[str, Path]) -> Path:
        p = Path(store_path)
        return p.with_name(p.name + ".index.json")

    def load(self, path: Path, meta: Dict[str, Any]) -> bool:
        """Поднять индекс из файла, если паспорт совпал. True — подняли."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return False
        if not isinstance(data, dict) or data.get("schema") != SCHEMA:
            return False
        if data.get("meta") != meta:
            return False
        post = data.get("post")
        ids = data.get("ids")
        if not isinstance(post, dict) or not isinstance(ids, list):
            return False
        self._post = post
        self._ids = [str(i) for i in ids]
        self.meta = dict(meta)
        self.dirty = False
        return True

    def save(self, path: Path, meta: Dict[str, Any]) -> bool:
        """Сохранить индекс атомарно (tmp + rename). Ошибки — не фатальны:
        файл всего лишь кэш старта."""
        ids: List[str] = []
        pos: Dict[str, int] = {}
        post: Dict[str, str] = {}
        for tok in list(self._post):
            bucket = self._bucket(tok)
            if not bucket:
                continue
            nums = []
            for nid in bucket:
                i = pos.get(nid)
                if i is None:
                    i = pos[nid] = len(ids)
                    ids.append(nid)
                nums.append(i)
            post[tok] = " ".join(str(i) for i in sorted(nums))
        payload = {"schema": SCHEMA, "meta": meta, "ids": ids, "post": post}
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
                os.replace(tmp, path)
            except BaseException:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise
        except OSError as exc:
            logger.warning("индекс поиска не сохранён (%s): %s", path, exc)
            return False
        self.meta = dict(meta)
        self.dirty = False
        return True


def verify(query_low: str, ids: Iterable[str], blobs: Dict[str, str]) -> List[str]:
    """Оставить из кандидатов те узлы, где подстрока действительно есть."""
    return [nid for nid in ids if query_low in blobs.get(nid, "")]
