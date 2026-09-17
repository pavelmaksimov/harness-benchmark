# memory-stack — четыре памяти в одной упряжке

> **Класс:** Memory (combo bundle: ontoship + mempalace + openviking + baron) · **Контроль:** baseline (внутри класса — supermemory.md)  
> **Идеальная дистанция:** 14 CP RealWorld (межчекпоинтная память — только марафон)  
> **Проблема:** realworld · **Эксперимент:** `realworld-combo-memory-stack-opencode-glm53flash-high-20260916` (opencode, glm-5.3-flash, z.ai, high)  
> **Итог прогона:** 14/14 CP, 26/26 Core, 0 реворков, 0 инфра-сбоев, 456 шагов, 159.2 мин, $0.00.

## Кто есть кто в упряжке

Ни одной системе не нужен API-ключ: эмбеддинги OpenViking — локальный GGUF (bge-small-zh-v1.5) на
хост-сервере `ops/openviking-host-server` (:8790, hostnet), MemPalace работает в `--no-llm` режиме,
Baron и OntoShip — чистый stdlib. Tool-CLI ставятся эфемерно через `uvx` (кэш контейнера), в
workspace живут только **данные** памяти.

| Система | Роль (наблюдалась) | Хранилище | Запись | Поиск |
|---|---|---|---|---|
| **Baron** | Оперативный реестр правил: атомарные claim'ы с kind/tags | `.baron/nodes.json` (52 ноды: 32 rule, 15 fact, 3 outdated, 1 incident) + свой сервер на случайном порту | `memory_add`, `memory_checkpoint` | `memory_search` (substring) |
| **MemPalace** | Нарративный журнал: заметка на CP, шахта вербатим-кусков в palace | `.mempalace/` (14 заметок + palace, 1.5 МБ) | `mine` + write заметки | `search` (ONNX-эмбеддинги, локально) |
| **OntoShip (gitmark)** | Человеческая документация проекта: kb/ с frontmatter (node_type/status/links) | `kb/` — 12 md (2 decisions + 9 reference-контрактов + README) + индекс `.gitmark/` (1.8 МБ) | write/edit в kb/ + `index`/`lint` | `search` + перечитывание файлов |
| **OpenViking** | Серверная семантическая память: те же заметки уходят в `viking://resources/notes/` | workspace `.openviking/notes/` (14) + хост-сервер (вектора 680 КБ) | `add-resource --wait` | `find` (векторный, score 0.48–0.64) |

Всего за прогон: **40 md-заметок** написано агентом (14+14+12), **306 bash-команд** тронули память
(Baron 140, MemPalace 75, OpenViking 60, OntoShip 31) — ≈22 на чекпоинт, ~43% всех tool-вызовов.
Это верхняя оценка налога: многие команды совмещают setup+recall+journal в одну строку.

## Как они работали вместе: цикл чекпоинта

Цикл сложился сам, без подсказки в промпте, и повторялся из CP в CP (reasoning CP9):

> «1. Start the baron server + checkpoint (memory_checkpoint). 2. **Recall**: baron memory_search,
> mempalace search, ontoship gitmark search, openviking find — before implementing. 3. Explore…
> 4. Implement… 5. Verify with tests. 6. **Journal**: mempalace notes, KB update, baron memory_add,
> openviking add-resource.»

Две развилки на чекпоинт: **recall fan-out** на старте (4 поиска параллельно по всем системам) и
**journal fan-out** в конце (4 записи). Разделение труда сложилось такое: Baron — «что нельзя
нарушить» (правила контрактов), MemPalace — «что я решил и почему» (хронология), kb/ — «как
устроен API» (справочник, который читают при имплементации), OpenViking — «то же, но с векторным
поиском на будущее».

## Переиспользование: доказательства

1. **Baron отдаёт чужие чекпоинты.** CP2 `memory_search "login token invalid auth"` →
   `hits: 4`, среди них правило JWT из CP1 («HS256, sub=user.id …»). Пик — CP9/CP10 по 5 хитов.
2. **MemPalace — самый надёжный recall: хиты в 12/13 поисков** (единственный пустой — CP1, дворец
   только что создан). Каждый CP с CP2 находил заметки предыдущих.
3. **kb/reference/articles-contract.md перечитан в CP5, 6, 7, 8, 9, 10 (×2), 11** — живой контракт
   API, по которому писались endpoint'ы. Всего 24 перечитывания kb/ через read tool в 12 CP.
4. **Системы сшиваются между собой**: в заметке OpenViking CP9 записан операционный урок про Baron
   («stale servers hold 8765/8766 with foreign /tmp stores; use 8767») — память одной системы
   хранит знания о другой. Baron с тех пор поднимался на случайном порту каждый CP.
5. **Жизненный цикл знаний**: 3 ноды Baron в kind=outdated — агент помечал протухшие факты, а не
   копил свалку. Reasoning-события упоминают все 4 системы постоянно (122–193 на систему за прогон).

## След в коде (снапшот CP14)

```
kb/                                .mempalace/               .openviking/            .baron/
  decisions/cp1-stack-and-layout.md  notes/2026-09-16-cp1..14  notes/cp1..cp14.md      nodes.json (52)
  decisions/cp2-auth-design.md       palace/, config/          ovcli.conf              ground_log.jsonl
  reference/{auth,articles,comments, tags-contract}.md         (сервер: resources/     export-queue, index
  profiles,feed,error-envelope,                                  notes/ + vectordb)     .json
  registration,user-update}.md
```

Рост по CP: Baron 48K→176K, MemPalace 664K→1.5МБ, kb 28K→64K, индекс gitmark 156K→1.8МБ. Ровный
линейный рост без скачков — память не раздувалась к финалу. Из метрик_LOC_ всё это вычтено
(`EXCLUDE_DIR_NAMES`: `.gitmark`, `.mempalace`, `.baron`, `.openviking`).

## Трения

- **Baron** требует управления сервером: рестарт каждый CP, конфликты портов, «чужие» /tmp-сторы —
  ~60% его 140 вызовов это lifecycle, а не память. Самая дорогая в обслуживании система стека.
- **OpenViking find** возвращает мусор из системных корней `viking://user/...` в топ-5 (score
  0.49–0.64) — заметки агента пробиваются выше только с CP4. `ov read` использован лишь 1 раз:
  основную работу сделал workspace-экземпляр заметок, сервер остался «страховым» поиском.
- Ни одна система не заблокировала решение: 0 реворков за 14 CP.

## Вердикт

Стек работает и работает **согласованно**: сложился чёткий цикл recall→implement→journal с
разделением ролей, все четыре хранилища росли линейно, recall подтверждён хитами и перечитываниями.
Цена — ощутимый налог tool-вызовов (~22/CP) и эксплуатация Baron-сервера. Одиночкам из стека:
MemPalace — лучший recall/простота, Baron — лучший формат правил, OpenViking — единственный
настоящий векторный поиск (нужен, когда заметок станет сотни), OntoShip — лучший «человеческий»
след для чтения людьми. N=1: это один прогон, не наука, но вектор виден.

---
*Источники:* `results/<exp>/combo-.../run_1/scb/realworld/checkpoint_*/{agent/messages.jsonl, snapshot/{kb,.mempalace,.openviking,.baron}}`,
`metrics/run.json`, `ops/openviking-host-server/data-realworld-memory-stack/`, скиллы в `harnesses/*/skill/SKILL.md`.
Классификация вызовов: скрипты в `memory/.tmp/analyze_*.py`.
