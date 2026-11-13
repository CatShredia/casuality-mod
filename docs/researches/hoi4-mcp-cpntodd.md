# HOI4-MCP (cpntodd)

Источник: https://github.com/cpntodd/HOI4-MCP. Дата: 2026-11-10. Сведения взяты со страницы README, код не запускался и не проверялся. Неподтверждённое помечено [uncertain].

## Что это

Локальный MCP-сервер на Python для моддинга HOI4. 19 инструментов, лицензия GPL-3.0, статус «pre-release» (интерфейсы могут меняться), 22 коммита, 11 звёзд, 1 форк. Дату последнего коммита страница не показывает [uncertain]. Заявленная версия игры: Vanilla 1.19.x.

## Инструменты

- Проект: `get_mod_index`, `search_mod`, `get_next_id`, `check_id_exists`, `set_mod_path`.
- Проверка и отладка: `validate_syntax` (Clausewitz), `get_latest_errors` (разбор `error.log`), `fuzzy_edit`, `get_loop_status`, `get_server_info`.
- Ваниль и карта: `lookup_vanilla` (база SQLite из установленной игры), `generate_province_rgb`.
- Правила: `skill`, `get_learned_rules`, `record_mistake`, `resolve_mistake`, `export_learned_rules`, `import_learned_rules`, `session_review`.
- Ресурсы: `mod://descriptor`, `logs://error_latest`.

## Источники данных

- Логи: да, `error.log`.
- Файлы мода и установленная игра: да (`index-vanilla`).
- Сохранения, память процесса, консоль, скриншоты: нет. «Память» в проекте означает локальную базу правил `~/.hoi4_mcp/learned_rules.db`.

## Установка (по README)

Python 3.10+, `python -m pip install -e .` в папке `hoi4-mcp-server`, затем `index-vanilla --vanilla-path "..."`, настройка `.vscode/mcp.json` (для Claude Code аналог: `.mcp.json` или `claude mcp add`) [uncertain].

## Польза для проекта Ktits

Живые данные из игры он не читает, поэтому на вопрос «смотреть информацию напрямую из HOI4» отвечает только логами ошибок.

- Может помочь: `validate_syntax` (проверка файлов мода до запуска игры), `lookup_vanilla` (вместо grep по ванили), частично `get_latest_errors`.
- Не поможет: реки, карта, RandomParadox и Python-скрипты по изображениям.
- Минусы: схемы 19 инструментов занимают контекст каждой сессии, установка и индексация ванили, проект предрелизный, отзывов нет.

## Решение

Не ставить сейчас. Вернуться к нему, когда начнётся массовая запись файлов мода (`make_countries.py`, `make_rulers.py`, `history/states`, localisation): проверить на одном файле. Перед установкой просмотреть код (зависимости, что пишет на диск).

Связано: `hoi4-live-data-research.md`.
