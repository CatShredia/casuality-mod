# HOI4 Agent Tools и HOI4 Live Tools (klimPaskov)

Дата: 2026-11-10. Сведения со страниц GitHub и каталога https://clauderules.net/mcp/io-github-klimpaskov-hoi4-agent-tools. Код не запускался, установка не проверялась. Неподтверждённое помечено [uncertain].

Это два связанных проекта одного автора:
- **HOI4 Agent Tools** создаёт и проверяет файлы мода (игру не запускает).
- **HOI4 Live Tools** запускает игру и читает её состояние.

## 1. HOI4 Agent Tools

Репозиторий: https://github.com/klimPaskov/hoi4-agent-tools

- MCP-сервер на Node.js 22.19+ или 24, пакет npm `hoi4-agent-tools` (версия 4.6.2), лицензия Apache-2.0.
- 639 коммитов, 10 звёзд, 1 форк, 6 открытых issues. Дата последнего коммита и поддерживаемая версия HOI4 не указаны [uncertain].
- Установка: `npm install --global hoi4-agent-tools`, затем `hoi4-agent-tools-setup --print-client-config`; для Claude Code также `claude mcp add hoi4-agent-tools -- npx -y hoi4-agent-tools@4.6.2`. Нужна установленная игра (ваниль, арт, шрифты).
- Базовые инструменты занимают около 8 000 токенов контекста (по описанию автора).
- Игру не запускает.

### Инструменты (39 по таблицам на странице `docs/tools.md`)

- Справочники и проверка: `reference_context`, `reference_search`, `reference_read`, `source_lookup`, `script_validate`, `error_log`, `explain_error`, `mod_health`, `script_guard`, `compat_check`, `mod_index` (в том числе свободный ID), `localisation_inspect`, `idea_inspect`, `system_inspect`, `unit_inspect`, `asset_inspect`, `skill`.
- Запись: `localisation_write`, `focus_rewrite`, `gui_rewrite`, `map_rewrite`.
- Просмотр и превью: `focus_inspect/render`, `gui_inspect/render`, `event_inspect/render`, `tech_inspect/render`.
- ИИ: `probability_inspect`, `probability_analyze` (веса `ai_will_do`, MTTH, `random_list`).
- Тесты и влияние: `impact_inspect`, `decision_inspect`, `mechanic_test`, `package_check`, `scenario_test`, `job_inspect`, `job_cancel`.

### Профиль `map` (важно для нашей карты)

- `hoi4.map_inspect`: поиск провинций, штатов и регионов по имени, ID или координатам; проверка проблем карты и ссылок в скриптах; рендер слоя, плитки или области.
- `hoi4.map_rewrite`: строит мир по референсному изображению или геомодели либо редактирует провинции, штаты, регионы и снабжение. Параметры: `preview`, массив `operations`. Пример: `{"kind":"create_world","reference":{"imagePath":"references/world.png"}}`.
- Какие именно файлы создаёт `create_world` (`provinces.bmp`, `definition.csv`, штаты, реки, `heightmap`), на странице не сказано [uncertain]. Пересечение с RandomParadox и нашими скриптами надо проверять на тестовой копии мода.

## 2. HOI4 Live Tools

Репозиторий: https://github.com/klimPaskov/HOI4-Live-Tools

- MCP-сервер, который запускает игру, загружает сохранение, вызывает события, отвечает на окна, пропускает время и читает `error.log`. Лицензия Apache-2.0 (компоненты Clausewitz-MCP: MIT). 334 коммита, 3 звезды, 1 форк. Дата последнего коммита не указана.
- **Поддерживаемая версия: HOI4 1.19.4.1**, как и у нас (билд f584 указан для macOS). Python-пакет на Windows протестирован на 1.19.4.1.
- Версии на странице расходятся (1.2.0 в таблице статуса, 1.4.0 в разделе загрузок).
- Автор прямо пишет, что прохождение тестов не равно работе в живой игре; полная кампания не принята ни на одном рантайме.

### Как читает игру

| Платформа | Способ |
|---|---|
| Windows (Python-пакет, стабильный) | Консоль игры в тестовом режиме `HOI4_LIVE_MODE=test`, логи `error.log` и `game.log`, текстовые сохранения, скриншоты и OCR (нужен английский компонент Windows OCR) |
| Linux x86_64, macOS Apple silicon (Rust, экспериментально) | Чтение памяти процесса игры без паузы и скриншотов |
| Windows нативный адаптер | Не завершён |

В кампанейском режиме консоль, события и эффекты недоступны.

### Инструменты

- Тест мода (Windows): `hoi4_smoke_namespace`, `hoi4_check_trigger`, `hoi4_check_focus`, `hoi4_sweep_loc`, `hoi4_eval_effect`, `hoi4_fire_event`.
- Запуск: `hoi4_prepare`, `hoi4_launch`, `hoi4_shutdown`.
- Игра через интерфейс: около 104 инструментов (Linux) и 120 (macOS); на Windows нативного адаптера нет.
- Клики и ввод: есть (размещение строительства, ввод ID области). Полный список в `docs/tools.md` [uncertain].

### Требования для Windows

Windows 10/11, HOI4 из Steam в оконном или безрамочном режиме, масштаб интерфейса 1, Python 3.9+, английский компонент Windows OCR. Установка: распаковать zip и запустить `python install.py` (создаёт окружение в `%LOCALAPPDATA%` и регистрирует сервер в Claude Code, Codex, Cursor и OpenCode).

## Оценка для проекта Ktits

- **Live Tools** ближе всего к вопросу «Claude смотрит данные из игры» и совпадает с нашей версией 1.19.4.1. На Windows это консоль, логи, текстовые сохранения, скриншоты и OCR, то есть то, что мы обсуждали как методы 2, 3 и 4 в `hoi4-live-data-research.md`, но уже собранное. Минусы: проект молодой (3 звезды), версии противоречат друг другу, чтение памяти на Windows не готово, а консольный режим отключает достижения и Ironman.
- **Agent Tools** пригодится для проверки скриптов, локализации, ИИ-весов и истории штатов; профиль `map` надо сравнить с нашими скриптами на копии мода.
- Не ставить в основную среду до проверки: перед установкой просмотреть `install.py` и список записываемых путей (Live Tools пишет в `%LOCALAPPDATA%` и регистрирует сервер в клиентах).

## Что проверить дальше

1. Прочитать `docs/tools.md` Live Tools и найти команды для камеры и скриншотов (переход к провинции, масштаб).
2. На копии мода запустить `hoi4.map_inspect` и `hoi4.map_rewrite` с `preview: true`.
3. Проверить, снимает ли Live Tools скриншоты и в каком разрешении.

Связано: `hoi4-live-data-research.md`, `hoi4-mcp-cpntodd.md`.
