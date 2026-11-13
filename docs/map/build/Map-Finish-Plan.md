# План доводки карты (ветка `sprint-03-map-sprints`; продолжено в `sprint-04-global-mechanics`)

Цель: закончить работу с RandomParadox и довести мод Ktits до играбельной карты скриптами. Ветка создана от `main` (d0cfa6f).

## Исходное состояние (экспорт 10.11.2026, 18:10; историческая справка)

- 8 200 провинций (`map/definition.csv`), суша 6 176, море 1 960 (по `provinces.png`).
- 683 штата, 28 тегов стран, провинций на штат около 9,0.
- Реки: в `rivers.bmp` около 3 000 пикселей против около 90 000 в ваниле (38 истоков против 317). После `paint_rivers.py` по `check_mod.py`: 20 783 пикселя реки, 105 истоков.
- Названия штатов и стран программа даёт по своему генератору, не по лору.

## Главное правило

Программа при каждом экспорте перезаписывает папку `Ktits`. Поэтому все правки после экспорта делают скрипты, которые можно перезапускать, а не ручные правки. Единая точка входа: `tools/post_export.py` запускает все шаги по порядку и в конце делает zip.

## Скрипты

| № | Скрипт | Что делает | Берёт данные из | Пишет в мод |
|---|---|---|---|---|
| 1 | `tools/paint_rivers.py` | Дорисовывает наши реки в `rivers.bmp` линиями 1 пиксель, индексы палитры: 0 исток, 1 и 2 слияния, 3…11 ширина. Рисует только по суше (в файле суша 255, вода 254) | `tools/rp_input/stage_03/rivers.png` | `map/rivers.bmp` |
| 2 | `tools/make_state_names.py` | Названия штатов по лору. Формирует `states.txt` для программы (`r;g;b;название;население`) или сразу `localisation/*/state_names_l_*.yml` (`STATE_n`) | `Maps/areas/stateInputs.txt`, `countries.png`, лор в `docs/lore/Contries-Description.md` | `localisation`, при желании `states.txt` |
| 3 | `tools/make_city_names.py` | Названия городов и очков победы (`VICTORY_POINTS_<id провинции>`), по лору и по положению на карте | `history/states` (список VP), лор | `localisation` |
| 4 | `tools/make_countries.py` | Теги, названия, прилагательные, цвета, столицы стран из одного источника. Генерирует `countryMappings.txt` для программы и патчит мод | `docs/lore/Contries-Description.md`, `docs/map/build/Map-Build-Plan.md` раздел 6 | `common/country_tags`, `common/countries`, `localisation` |
| 5 | `tools/make_rulers.py` | Правители, идеологии, партии и персонажи по лору | `docs/lore/Contries-Description.md` (у Z01–Z05, FIG, LED, вероятно, нет данных) | `history/countries`, `common/characters` |
| 6 | `tools/set_terrain.py` | Тип местности провинций: болота, пустыня, джунгли и др. по лору (болот отдельным типом программа не даёт) | карты климата и лора | `map/definition.csv`, `map/terrain` |
| 7 | `tools/name_regions.py` | Названия стратегических районов и континентов | лор | `localisation` |
| 8 | `tools/check_mod.py` | Проверки: число провинций и штатов, провинции без штата, штаты без владельца, теги без localisation, пустые строки localisation, пикселей реки на воде | весь `Ktits` | ничего не пишет |
| 9 | `tools/post_export.py` | Запускает 1–7, затем 10–14 и 8, затем `zip_mod.py` | | |
| 10 | `tools/make_ideologies.py` | 6 групп идеологий, подтипы, интерфейс партий (docs/lore/Lore-Overview.md, раздел 3) | `tools/ideologies_data.py`, ванильные файлы игры | `common/ideologies`, `interface`, `localisation` |
| 11 | `tools/make_education.py` | Образованность (6 уровней) как национальные духи | лор, `INVENTED_LEVEL` | `common/ideas`, `history/countries`, `localisation` |
| 12 | `tools/make_casuality.py` | Глобальная механика «Казуальность»: шкала, ступени, решения, события, ежемесячный рост, «Зов болот», ИИ, графическая шкала (docs/global_mechanics/Casuality-Mechanic.md) | придуманные значения в самом скрипте | `common/*`, `events`, `interface`, `gfx/interface/ktits`, `localisation` |
| 12а | `tools/make_game_rules.py` | Экран правил игры: подменяет `00_game_rules.txt` копией без правил ванильных стран (`<TAG>_ai_behavior`, `*_fragmentation_status`, `quebec_colonization_status`), оставляет общие; правило мода `ktits_global_casuality` пишет `make_casuality.py` | ванильный `common/game_rules/00_game_rules.txt` | `common/game_rules/00_game_rules.txt` |
| 13 | `tools/make_splits.py` | Выделяемые государства `K01`–`K35` больших стран: теги, ядра на штатах, заблокированные эффекты выделения (docs/countries/Splits.md) | `history/states`, карта провинций | `common/country_tags`, `common/countries`, `history/countries`, `history/states` (ядра), `localisation` |

Порядок в `post_export.py`: rivers → population → states → cities → countries → ideologies → rulers → casuality → gamerules → education → splits → terrain → regions → check → zip. Скрипт 5 (`make_rulers.py`) учитывает идеологии из `ideologies_data.py`, поэтому идёт после 10; `make_splits.py` идёт после всех, кто пишет в `history/states`.

## Порядок и зависимости

1. Скрипт 4 (`make_countries.py`): всё остальное опирается на теги и названия стран.
2. Скрипты 2 и 3 (названия штатов и городов) после 4.
3. Скрипт 5 (правители, идеологии) после 4.
4. Скрипт 1 (реки) независим от остальных, его можно делать параллельно с 4. Проверка в игре: видны ли реки, виден ли ширина по индексам.
5. Скрипты 6 и 7 после того, как лор по местности и районам станет точным.
6. Скрипт 8 пишем одновременно с 1, чтобы проверять результат сразу.

## Что нужно от вас по лору (скрипты не выдумывают)

- Названия штатов и городов: есть ли в `docs/lore/Contries-Description.md` список областей и городов по странам. Для штатов, которых в лоре нет, нужен выбор: «Страна + номер», генератор по стилю страны или оставить как есть.
- Правители, идеологии, партии для всех 28 стран (где данных нет, спросить).
- Порядок названия: на каком языке локализация (ru, en или оба).

## Открытые вопросы

- Вариант названий штатов вне лора (пока не выбран).
- Нужны ли именно наши 38 рек или достаточно «больше, чем сделала программа».
- Правила соединения пикселей реки в HOI4 (диагонали, слияния) проверить запуском игры [uncertain].
- Проверить, что правки файлов мода после экспорта не ломают загрузку игры [uncertain].
- Остальное из прошлых этапов: рост территории Фигарии до около 15 100 тыс. км² (сейчас около 12 883), обновление `docs/lore/Contries-Description.md`, `map/Geography.md` и `map/Map-Sketch.svg` по новой географии, удаление `fwg.data` и `fwg.data.bak`.

## Проверка результата

После каждого скрипта: `check_mod.py`, затем запуск игры с одним модом Ktits, начало партии, просмотр `error.log`. Реки смотреть вблизи камеры.
