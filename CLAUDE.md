# CLAUDE.md

Мод для Hearts of Iron IV «Казуальность»: полная замена мира (свой материк, страны, идеологии, механики).
Название мода: Ktits, версия 0.1.0 (в программу вводить имя без слэша на конце).
Целевая версия игры: Operation Postern v1.19.4.1.99a5 (f584).

## Документы (`docs/`)
Путеводитель по папкам: `docs/Guide.md`. Старые версии (до перестройки): `no_commit/legacy_docs/`.
- `countries/Country-Template.md` — шаблон описания страны и чек-лист.
- `lore/Contries-Description.md` — главный документ лора. При расхождениях прав он.
- `map/Geography.md` — выписка географии из `lore/Contries-Description.md`. Менять вместе с `lore/Contries-Description.md`.
- `map/Map-Sketch.svg` — схематичная карта (не в масштабе, ≈97 км² на единицу SVG). `map/Map-Sketch-legacy.svg` — старая версия, не трогать.
- `map/build/Map-Build-Plan.md` — план сборки первоначальной карты мода.
- `map/build/Video-RandomParadox-Notes.md`, `map/build/RandomParadox-Guide.md`, `map/build/RP-Stages.md` — сборка карты через RandomParadox, поэтапно (в `map/build/RP-Stages.md` — файлы для загрузки и проверка каждого этапа).

- `map/build/Map-Finish-Plan.md` — план и таблица скриптов `tools/` (порядок в `post_export.py`).
- `lore/Invented-Lore.md` — всё, что придумано автоматически (нужна проверка автором).
- `lore/Lore-Overview.md` — сводный лор и таблица идеологий.
- `global_mechanics/Casuality-Mechanic.md` — механика «Казуальность» (числа и решения).
- `global_mechanics/Casuality-Testing.md` — команды консоли и сценарии проверки «Казуальности» в игре.
- `global_mechanics/Education.md` — образованность населения.
- `countries/Big-Countries.md` — крупные страны и их части.
- `focuses/Generic-Focus-Tree.md` — стандартное древо фокусов (пока ветка «Казуальность»).
- `countries/Splits.md` — выделяемые государства `K01`–`K35` больших стран (выделение заблокировано).

## Служебное (`no_commit/`, в git не попадает)
- `no_commit/guide_for_ai/` — черновик инструкций по моддингу HOI4 (выписки с вики, есть пометки [uncertain]). Сверять с ванильными файлами 1.19.
- `no_commit/temp/` — временные файлы: скрипты правок, скриншоты проверки, промежуточные данные. Всё временное класть только сюда.

## Правила
- Отвечать на русском, кратко.
- Не коммитить и не пушить без просьбы. Сообщения коммитов — на английском, только что изменилось.
- Не додумывать лор: всё придуманное самостоятельно явно перечислять в ответе; спорное — вопросом.
- Правки географии вносить согласованно в `lore/Contries-Description.md`, `map/Geography.md` и `map/Map-Sketch.svg`.
- `lore/Contries-Description.md` использует CRLF; сохранять окончания строк файла.
- Ветки фокусов в документах (`docs/focuses/`) обязательно показывать и графически — схемой mermaid (`flowchart TD`) в том же md: узел = фокус, стрелка = предпосылка, взаимоисключающие фокусы связывать пунктиром с подписью.
- Технические факты о моддинге без подтверждения помечать [uncertain], ключи и эффекты не выдумывать.
- Проверка SVG: `python -m http.server` в `docs/` + скриншот Playwright в `no_commit/temp/`; после проверки остановить сервер и удалить `.playwright-mcp/`.
