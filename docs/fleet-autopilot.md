# Запуск автоматического benchmark fleet

`benchmark fleet` поддерживает целевое состояние в `configs/desired.yaml`: демон
сверяет его с каталогом `results/`, запускает недостающие слоты, возобновляет
оборванные прогоны и оставляет неоднозначные случаи в `ops/needs-human/`.

## 1. Подготовка

Все команды выполняйте из корня репозитория:

```bash
cd /home/user/my/harness-benchmark
docker ps
docker image ls
uv run pytest tests -q
```

Для обычных проверок и запуска benchmark используйте именно `uv run`; вручную
передавать путь к кешу не нужно. Если отдельная диагностическая команда `uv run
python -m benchmark ...` в конкретном окружении падает с `Read-only file system`
внутри `/home/user/.cache/uv`, это проблема локального кеша uv. Для разовой
диагностики можно задать временный `UV_CACHE_DIR`, но в рабочей конфигурации
сначала исправьте права/окружение кеша.

Временный обход для проверки команды:

```bash
UV_CACHE_DIR=/tmp/harness-benchmark-uv-cache \
  uv run python -m benchmark fleet plan --config configs/desired.yaml
```

Перед первым многопоточным запуском, если vendor или Docker-образы ещё не
подготовлены, выполните:

```bash
bash scripts/bootstrap_vendor.sh
docker image ls
bash scripts/build_images.sh
```

`build_images.sh` нужен только при отсутствии подходящих локальных образов или
после изменения их pin'ов. Убедитесь, что нужные credentials доступны агенту;
секреты не добавляйте в `configs/desired.yaml`.

## 2. Каталог имён и проверка конфигурации

В benchmark нет одного универсального API-списка: у каждого маршрута свой
provider. Для запуска используются имена из локального SCB-каталога, который
собирается из vendor-каталога и `configs/models/*.yaml`.

Посмотреть точные идентификаторы:

```bash
uv run python -m benchmark catalog providers
uv run python -m benchmark catalog models
```

В выводе моделей:

- `name` — значение, которое нужно писать в `desired.yaml` в поле `model`;
- `api` — внутренний/API model id из определения модели;
- `catalog_provider` — provider, записанный в определении модели;
- `routes` — фактические agent-specific маршруты, например `opencode:opencode`;
- `agents` — для каких адаптеров есть специальные настройки.

Например, `opencode_auth` — это имя credential provider (файл авторизации
OpenCode), а `x-preview-f-free` — имя модели в benchmark-каталоге. Не склеивайте
их вручную в поле `model`: в `desired.yaml` они задаются отдельно.

Если нужной модели нет в выводе, не подставляйте случайный API id прямо в
`desired.yaml`. Сначала добавьте проверенный overlay
`configs/models/<catalog-name>.yaml` с точным `internal_name` и настройками
нужного agent, затем повторите `catalog models` и `fleet validate`.

Для воспроизводимого выбора создайте профиль в `configs/profiles/`. Пути в поле
`profile` считаются относительными корню репозитория:

```yaml
id: opencode-x-preview-f-free-high
description: OpenCode Zen free route with high reasoning.
agent: opencode
provider: opencode_auth
model: x-preview-f-free
thinking: high
```

Проверьте профиль до подключения к benchmark:

```bash
uv run python -m benchmark profile list
uv run python -m benchmark profile validate \
  --config configs/profiles/opencode-x-preview-f-free-high.yaml \
  --check-credentials
```

Для нового skill-arm можно сразу проверить реальный запуск профиля:

```bash
uv run python -m benchmark profile smoke \
  --config configs/profiles/opencode-x-preview-f-free-high.yaml \
  --arm <name> --problem file_backup --checkpoints 2
```

После успешной проверки в `desired.yaml` указывайте только путь к профилю:

```yaml
defaults:
  profile: configs/profiles/opencode-x-preview-f-free-high.yaml
```

Не смешивайте `profile` с `agent`, `provider`, `model` или `thinking` в одном
блоке. Это намеренно запрещено, чтобы benchmark не выполнялся на частично
переопределённой конфигурации.

Перед запуском проверьте весь desired-конфиг:

```bash
uv run python -m benchmark fleet validate --config configs/desired.yaml
```

Проверка не вызывает модель и не делает сетевой API-запрос. Она проверяет YAML,
точные имена provider/model/agent, thinking preset, существование problem и
зарегистрированных arms. Для дополнительной проверки наличия локального файла
или переменной credentials:

```bash
uv run python -m benchmark fleet validate \
  --config configs/desired.yaml --check-credentials
```

Проверка автоматически выполняется также перед `fleet plan`, `fleet status` и
каждым reconciliation-циклом daemon. Если имя неверно, запуск завершается с
понятной ошибкой и monitor не создаётся. Наличие credentials ещё не доказывает,
что provider принимает запрос; это проверяется smoke-прогоном. Обычные команды
`run`, `run-all` и `smoke` также проверяют resolved selection до старта прогона.

## 3. Описание цели

Редактируйте только `configs/desired.yaml`. Минимальный пример:

```yaml
defaults:
  profile: configs/profiles/opencode-x-preview-f-free-high.yaml
  runs: 3
  jobs: 4
  rework_attempts: 2
  transient_retries: 0

experiments:
  - id: tm-opencode-x-preview-high
    problem: task_manager
    arms: [baseline, python-harness]
    runs: 3
```

`id`, `problem`, `arms`, `agent`, `provider`, `model`, `thinking`, параметры
повторов и параллелизма образуют идентичность прогона. После изменения модели,
провайдера или задачи создавайте новый `experiments[].id`; не пытайтесь
продолжить старый эксперимент с другой конфигурацией.

Для нового source-only harness добавьте карточку в `harnesses`:

```yaml
harnesses:
  my-new-tool:
    source: "https://github.com/org/my-tool tag v1.2.3"
    install: "uv tool install my-tool==1.2.3"
    expect:
      - "my-tool-docs/"
```

Сначала изучите инструмент вручную, затем добавьте arm, выполните pin и smoke.
Полный чеклист находится в [harness-onboarding.md](harness-onboarding.md).

Имена агента, провайдера и модели должны быть точными. Опечатка не исправляется
автоматически и не подбирается «по похожему имени»:

- неподдерживаемый `agent` отклоняется wrapper'ом;
- неизвестные `provider` и `model` отклоняются каталогом SCB с сообщением об
  ошибке;
- отсутствие credentials — отдельная credential error;
- при запуске через fleet ошибка выбора может выглядеть как повторные попытки
  или тикет, поэтому проверяйте `fleet-monitor.log` и исправляйте
  `desired.yaml`, а для изменения идентичности используйте новый `id`.

Для OpenCode указывайте `provider`, `model` и `thinking` совместимые с overlay в
`configs/models/`. Для `low`, `high` или `max` у модели должны быть именованные
variants.

## 4. Проверка без запуска

Сначала посмотрите, что fleet собирается делать:

```bash
uv run python -m benchmark fleet plan --config configs/desired.yaml
uv run python -m benchmark fleet status --config configs/desired.yaml
```

`plan` показывает действия по каждой ячейке, а `status` — текущее состояние
слотов. На этом шаге не запускаются агент, Docker или модель.

Для одной пробной reconcile-итерации используйте:

```bash
uv run python -m benchmark fleet --once --config configs/desired.yaml
```

Она запускает недостающую работу и завершается. Второй fleet блокируется
файлом `results/.fleet.lock`, второй monitor того же эксперимента —
`results/<experiment>/.monitor.lock`.

## 5. Постоянный запуск

### Вручную в терминале

```bash
uv run python -m benchmark fleet --config configs/desired.yaml
```

Демон будет периодически сверять цель и запускать только недостающие слоты.
Увеличение `runs` добавляет новые `run_N`; существующие результаты не удаляются.

### Через user systemd

Установите unit из репозитория:

```bash
mkdir -p ~/.config/systemd/user
cp systemd/harness-benchmark-fleet.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now harness-benchmark-fleet.service
```

Чтобы сервис продолжал работать после выхода из SSH или графической сессии:

```bash
loginctl enable-linger "$USER"
```

Проверка и логи:

```bash
systemctl --user status harness-benchmark-fleet.service
journalctl --user -u harness-benchmark-fleet.service -f
```

Не запускайте одновременно ручной демон и systemd-unit: lock защищает от
дублей, но один режим проще контролировать.

## 6. Контроль прогресса и результаты

Периодически проверяйте:

```bash
uv run python -m benchmark fleet status --config configs/desired.yaml
uv run python -m benchmark fleet plan --config configs/desired.yaml
```

Основные артефакты:

- `results/<experiment>/<arm>/run_N/state.json` — жизненный цикл слота;
- `results/<experiment>/<arm>/run_N/metrics/run.json` — итоговые метрики;
- `results/<experiment>/comparison.{txt,json}` — сравнение завершённых прогонов;
- `results/<experiment>/fleet-monitor.log` — лог monitor;
- `ops/needs-human/*.md` — тикеты, требующие решения человека.

Уведомления Hermes — информационные: в конце каждого сообщения есть пометка,
что действий не требуется, и read-only команды для проверки состояния:
`fleet status`, `fleet plan`, `systemctl --user status
harness-benchmark-fleet.service` и `pgrep -af
'monitor_benchmark.py|benchmark.scb_main'`. Hermes не должен автоматически
запускать benchmark, менять `desired.yaml` или исправлять тикеты.

Красный checkpoint сначала триажьте по `benchmark-failure-triage`: setup/import
ERROR и `infrastructure_failure` не являются автоматически ошибкой модели.
Логи SCB могут отставать; сверяйте файлы на диске, `state.json` и живость
контейнера, а не только хвост лога. Не удаляйте `/tmp/tmp*` во время прогона.

## 7. Smoke и onboarding

Для каждого нового или изменённого skill-arm обязателен smoke до полного run:

```bash
uv run python -m benchmark smoke --arm <name> --problem file_backup \
  --checkpoints 2 \
  --agent opencode --provider opencode_auth \
  --model x-preview-f-free --thinking high
```

После изменения `harnesses/<name>/skill/` снова выполните pin и smoke этого же
arm. Не используйте старый `SMOKE.json`: он привязан к содержимому harness.

Source-only onboarding выполняется только при явно заданном
`HB_FLEET_ONBOARD_COMMAND`. Если команда не задана, fleet создаёт тикет в
`ops/needs-human/`, а не вызывает модель самовольно. После ручного исправления
установите в front matter тикета `resolved: true` и повторите `plan`.

## 8. Остановка и завершение

После того как `status` показывает, что все ячейки завершены, проверьте наличие
`metrics/run.json` и `reports/<experiment>/comparison.json`.

Остановить user-unit можно так:

```bash
systemctl --user disable --now harness-benchmark-fleet.service
```

Остановка демона не удаляет результаты. Если запуск был прерван, перед новым
стартом проверьте `pgrep -af scb_main`, `docker ps` и незавершённые `run_N`, чтобы
не получить параллельный фантомный слот.
