# 18 — Проверить полную накопительную траекторию

**What to build:** Подтвердить, что вся задача готова к воспроизводимому многократному сравнению вариантов: каждый чекпоинт проверяет новую возможность, прошлое поведение повторяется, а показатели не смешиваются в единый балл.

**Blocked by:** 03 — Подтвердить пригодность CP1 для эксперимента; 17 — CP15: общий конструктор отчётов.

**Status:** done

- [x] Каркас траектории готов к оценке агентов: все 15 briefs + test files; Core (unmarked) / Functionality / Error маркеры; CP2–15 с `include_prior_tests: true`. Эталонных приложений CP2+ нет — оценивается решение агента (option 1).
- [x] Политика остановки — `all-core-cases` в arm YAML; конфигурация задачи не требует изменения раннера SlopCodeBench.
- [x] `validate-problem --problem task_manager` проходит; зависимости в `config.yaml` / sync script; `EXCLUDE_DIR_NAMES` без изменений; `file_backup` default не тронут.
- [ ] Полный опыт `run-all --runs 3 --jobs …` и живой Docker smoke — **отложены** до появления образов; один offline-прогон не выдаётся за итоговый результат.

**Notes (option 1):** Не проверяли «эталон проходит все Core» — локальных reference apps для CP2+ нет и не восстанавливаем. Готовность = prompts + tests + wiring. Сводка: `TRAJECTORY-READY.md`. CP2+ solutions удалены из дерева; остаётся только `solutions/checkpoint_1/`.
