# Как дать Claude доступ к данным из HOI4: методы и сложность

Дата: 2026-11-10. Сделано тремя субагентами (Haiku), чтение и веб-поиск. Часть источников (вики по консоли и логированию) не открылась, поэтому пункты с [uncertain] не подтверждены.

## Сводная таблица

| № | Метод | Что видит Claude | Сложность | Время | Главный минус |
|---|---|---|---|---|---|
| 1 | Читать `logs/game.log`, `error.log`, `system.log` | Ошибки мода и скриптов, старт игры, дата | Низкая | уже работает | В `game.log` сейчас только старт игры |
| 2 | Мод пишет состояние в лог (`log = "..."` в `on_action`) + скрипт-наблюдатель | Всё, что видят скрипты: страны, переменные, события | Низкая–средняя | 1–2 дня | Ежедневные хуки тормозят игру; сброс буфера лога не подтверждён [uncertain] |
| 3 | Скриншоты окна и OCR | Видимое на экране | Низкая–средняя | 1–3 дня | DirectX-окно может давать чёрный кадр; помогает оконный режим [uncertain] |
| 4 | Чтение сохранений через MCP-сервер (Python + `mcp`) | Состояние стран, провинций, даты | Высокая | 3–5 дней | Сейвы бинарные (`HOI4bin5`); парсеры требуют токены, автор их не публикует [uncertain]; вариант `save_as_binary=no` не подтверждён [uncertain] |
| 5 | Чтение памяти процесса | Любые внутренние значения | Очень высокая | от 1–2 недель | Адреса ломаются при патчах; риск для Steam; не рекомендуется |
| 6 | DLL-хуки | Как память + вызовы функций | Очень высокая | недели | Запрет правки exe для модов [uncertain]; не рекомендуется |
| 7 | Консольные команды (`-debug`) | Дампы ИИ, гарнизонов в лог | Средняя | — | Имена команд не подтверждены; ручной ввод |

## Факты о локальной машине (папка `Documents/Paradox Interactive/Hearts of Iron IV`)

- `logs/`: `game.log` (490 Б, только старт), `error.log` (18 КБ), `system.log`, `system_debug.log`, `setup.log`, `memory.log`, `graphics.log`; пустые `ai.log`, `executed_commands.log` и др. Строки вида `[ЧЧ:ММ:СС][дата]: текст`.
- `crashes/`: около 16 папок `hoi4_YYYYMMDD_HHMMSS` с 03.11.
- `save games/`: 163 файла, около 12 ГБ; заголовок `HOI4bin5` (бинарный).
- `settings.txt`: `save_as_binary=yes`, `autosave="MONTHLY"`, `debug_saves=0`.

## Готовые инструменты (сохранения)

- rakaly/hoi4save (Rust, plaintext+binary), rakaly/jomini (Rust, парсер Clausewitz): активность не проверена [uncertain].
- hoi4.py (Python, PyPI `hoi4-py`): по одному источнику 2022 год, вероятно устарел [uncertain].
- pdx-tools: веб-приложение, для HOI4 «melt only» [uncertain].
- 2048Israel/hoi4-claude (PR #5, `hoi4_save.py`): Python-ридер, не проверен [uncertain].
- Готового MCP для чтения сейвов HOI4 не найдено; есть MCP для скриптов модов (`106-paradox-script-mcp`, RHoiScribe).
- Свой MCP-сервер: Python, SDK `mcp` (FastMCP), stdio, `claude mcp add` или `.mcp.json`; инструменты `get_latest_save`, `read_save`, `get_country`; оценка 150–250 строк, 1–2 дня, плюс до 2 дней на устойчивость.

## Рекомендация

1. Сразу: метод 1 (логи).
2. Следующий шаг: метод 2 (мод пишет в лог раз в месяц + `tools/read_game_log.py`). Начать с одной тестовой строки `log = "..."` и проверки, что она появляется в `game.log`.
3. По необходимости: метод 3 (авто-скриншоты), метод 4 (сейвы; сначала проверить текстовый режим сохранения).
4. Не делать: методы 5 и 6.

## Источники (из отчётов агентов)

- https://hoi4.paradoxwikis.com/On_actions, https://hoi4.paradoxwikis.com/Scripted_GUI_modding (не открывались)
- https://github.com/rakaly/hoi4save, https://github.com/rakaly/jomini, https://github.com/samirelanduk/hoi4.py, https://github.com/pdx-tools/pdx-tools
- https://admin-forum.paradoxplaza.com/forum/threads/getting-live-statistics-about-a-running-game.1564674
- https://hoi4commands.com/command/help
