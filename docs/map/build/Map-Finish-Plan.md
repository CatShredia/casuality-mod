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
| 4 | `tools/make_countries.py` | Теги, названия, прилагательные, цвета, столицы стран из одного источника. Генерирует `countryMappings.txt` для программы и патчит мод Стартовые марионетки Бриттана (`puppet = ` для Ирракии, Иракиккистана, Цейлона в его `history/countries`, блок между маркерами `# ktits start puppets`, идемпотентно). | `docs/lore/Contries-Description.md`, `docs/map/build/Map-Build-Plan.md` раздел 6 | `common/country_tags`, `common/countries`, `localisation` |
| 5 | `tools/make_rulers.py` | Правители, идеологии, партии и персонажи по лору | `docs/lore/Contries-Description.md` (у Z01–Z06, FIG, LED, вероятно, нет данных) | `history/countries`, `common/characters` |
| 6 | `tools/set_terrain.py` | Тип местности провинций: болота, пустыня, джунгли и др. по лору (болот отдельным типом программа не даёт) | карты климата и лора | `map/definition.csv`, `map/terrain` |
| 7 | `tools/name_regions.py` | Названия стратегических районов и континентов | лор | `localisation` |
| 8 | `tools/check_mod.py` | Проверки: число провинций и штатов, провинции без штата, штаты без владельца, теги без localisation, пустые строки localisation, пикселей реки на воде | весь `Ktits` | ничего не пишет |
| 9 | `tools/post_export.py` | Запускает 1–7, затем 10–14 и 8, затем `zip_mod.py` | | |
| 10 | `tools/make_ideologies.py` | 6 групп идеологий, подтипы, интерфейс партий (docs/lore/Lore-Overview.md, раздел 3) | `tools/ideologies_data.py`, ванильные файлы игры | `common/ideologies`, `interface`, `localisation` |
| 11 | `tools/make_education.py` (+`education_mech.py`) | Образованность (6 уровней) как национальные духи, специалисты (счётчики, ежемесячный переход), две категории решений («Образование: развитие» и «Образование: упрощение»), договор о сотрудничестве (события) | лор, `INVENTED_LEVEL` | `common/ideas`, `history/countries`, `localisation` |
| 12 | `tools/make_casuality.py` | Глобальная механика «Казуальность»: шкала, ступени, решения, события, ежемесячный рост, «Зов болот», ИИ, графическая шкала (docs/global_mechanics/Casuality-Mechanic.md) | придуманные значения в самом скрипте | `common/*`, `events`, `interface`, `gfx/interface/ktits`, `localisation` |
| 12б | `tools/make_focuses.py` | Ветки фокусов «Казуальность» (11 фокусов), «Политический курс» (26) и «Образование» (13; x = 72–80) и «Экономика» (36; x = 84–108) в стандартном дереве `generic.txt`, духи, модификатор отношений (docs/focuses/Generic-Focus-Tree.md) | придуманные значки и значение отношений в самом скрипте | `common/national_focus/generic.txt`, `common/ideas`, `common/opinion_modifiers`, `localisation` |
| 12а | `tools/make_game_rules.py` | Экран правил игры: подменяет `00_game_rules.txt` копией без правил ванильных стран (`<TAG>_ai_behavior`, `*_fragmentation_status`, `quebec_colonization_status`), оставляет общие; правило мода `ktits_global_casuality` пишет `make_casuality.py` | ванильный `common/game_rules/00_game_rules.txt` | `common/game_rules/00_game_rules.txt` |
| 12в | `tools/fix_vanilla_leftovers.py` | Чистка ванильных остатков (шум в `error.log`): проверки `has_game_rule` удалённых правил заменяются на `always = yes/no` (по умолчанию правила), пустые перекрытия для `common/ai_strategy_plans/*` и ванильных решений с пограничными войнами и шаблонами фракций, строка с отсутствующим шаблоном фракции в `AST_scripted_effects.txt`, недостающие `add_namespace` в событиях, `icon` в `rpx_call_to_arms.txt`, `has_completed_focus` удалённых фокусов общего древа. Дальше обрезка всего ванильного, чего в моде нет: (а) все ванильные страновые древа фокусов (`common/national_focus/*`, кроме `generic.txt` и стилей заголовка) перекрыты пустыми файлами, `has_completed_focus`/`has_focus_tree`/`complete_/uncomplete_/unlock_national_focus` их фокусов убраны; (б) страновые файлы `common/ai_strategy/<ТЕГ>.txt` ванильных тегов пусты (папка в `replace_path`: файлы из ванили не копируются, только копии RandomParadox); (в) ссылки на несуществующие решения и миссии убираются в любой форме, в том числе многострочной (`activate_targeted_decision`, `add_days_mission_timeout`, `unlock_decision_tooltip`...), `has_decision`/`has_active_mission` становятся `always = no`; `has_faction_template` несуществующих шаблонов тоже `always = no`; (г) в ванильных `common/on_actions` убираются блоки состояний по номерам ванильной карты (`123 = { ... }` в эффектах), вызовы несуществующих событий (и строки `random_events`), блоки `<ТЕГ>_<персонаж> = { set_unit_leader_flag ... }` ванильных тегов. Разбор скобок «с учётом вложенности» (`mask/parse/cut` в скрипте), в конце печатается краткий отчёт со счётчиками. (д) `events/rpx_generic_war.txt` (события войн RandomParadox: `create_wargoal`/`declare_war_on` без обоснования) оставлен только с `add_namespace = generic_war`; ссылок на `generic_war.N` вне файла и локализации нет. (е) **Настоящая причина «войн по фану»**: `events/rpx_ideological_tension_v2.txt` (RandomParadox): событие `ideological_tension_v2.2` с `date > 1937.4.1` срабатывает по MTTH (120 дней) у любой фашистской/коммунистической страны с соседом другой идеологии, ИИ выбирает опцию и получает бесплатную `create_wargoal = annex_everything` без обоснования, затем сразу объявляет войну (так 25.4.1937 и 2.5.1937). Остальные события файла (v2.1, 2.3-2.5) выдают такие же цели с 1938-1940. Теперь файл пуст (только `add_namespace`), проверка в `check_mod`. Прочие `declare_war_on`/`create_wargoal` в моде: ванильные теги (ICE, PER, SOV, ENG...) в моде не существуют, `is_triggered_only` цепочки `compat_Generic` из пустых источников, наши Казуальные восстания и фокусы Казуалии. В `make_splits.py` дополнительно удаляются устаревшие `history/countries/Kxx - *.txt` с другим именем при сдвиге нумерации (двойной `recruit_character` у K34). Коллизий наших тегов с ванильными нет (проверка в `check_mod`) | `common/*`, `events/` |
| 13 | `tools/make_splits.py` | Выделяемые государства `K01`–`K34` больших стран: теги, ядра на штатах, заблокированные эффекты выделения (docs/countries/Splits.md) | `history/states`, карта провинций | `common/country_tags`, `common/countries`, `history/countries`, `history/states` (ядра), `localisation` |
| 13б | `tools/make_alliances.py` | Механика «Альянсы» (`docs/global_mechanics/Alliances.md`): три стартовые фракции, вступление решениями и событиями с порогами напряжённости, шкала сотрудничества и духи ступеней, марионетки в альянсе сюзерена, смена курса марионетки, ИИ; отключает ванильные «Вступить/Пригласить во фракцию» и список шаблонов фракций (правит копии `diplomacy_scripted_triggers.txt` и `common/factions/templates`); шаг `alliances` стоит после `splits` | числа и тексты в самом скрипте и в `Invented-Lore.md` | `common/scripted_*`, `on_actions`, `ideas`, `decisions`, `events`, `localisation`, патч `diplomacy_scripted_triggers.txt` и `common/factions/templates` |
| 13в | `tools/make_continuous.py` | Три непрерывных фокуса в палитре `generic_focus`: «Борьба с ленью», «Болотный покой» (Казуальность, `Casuality-Mechanic.md`), «Укрепление альянса» (`Alliances.md`); месячный эффект и on_action. После `make_alliances.py`. |
| 13г | `tools/make_debug.py` | Отладочный журнал: вставляет под флагом `ktits_debug` строки `log` в события, решения, фокусы и эффекты (последний из генераторов), пишет `ktits_dbg_*`, `on_war`/`on_declare_war`, `ktits_debug.txt`/`ktits_debug_off.txt`. Разбор: `tools/read_log.py`. См. `global_mechanics/Debug-Log.md`. |
| 14 | `tools/make_icons.py` | Иконки национальных духов (24 PNG 65×67 из `gfx_src/ideas/`): копирует в `gfx/interface/ideas/ktits_<id>.png`, пишет `interface/ktits_ideas.gfx` (`GFX_idea_ktits_<id>`), проставляет `picture = ktits_<id>` 39 духам постпроцессом по idea-файлам (идемпотентно). Последний шаг перед `check`; после отдельного запуска генераторов духов запускать заново. |
| 14a | `tools/make_pictures.py` | Картинки событий (210×120) и шапки категорий решений (420×120) из `gfx_src/pictures/`: копирует PNG в `gfx/event_pictures/` и `gfx/interface/ktits/`, пишет `interface/ktits_pictures.gfx`, заменяет `picture =` у 55 событий (`ktits_casuality`, `ktits_alliance`, `ktits_edu`, `ktits_kazualia`, `ktits_kz_out`) и у 13 категорий решений (идемпотентно). Запускать после шагов, пишущих события и категории, рядом с `make_icons.py`. |
| 13в | `tools/make_kazualia.py` | Удаление ж/д и узлов снабжения Казуалии (`map/railways.txt`, `map/supply_nodes.txt`, копия экспорта в `no_commit/temp/backup_railways/`). Механики и древо фокусов Казуалии (`docs/mechanics/Kazualia.md`, `docs/focuses/Kazualia-Focus-Tree.md`): стартовый ивент «Утро в Ставке», Внутренняя Казуальность (динамический модификатор, опоздания), Дурманище, Казуальная Вера и «Дары болот», 55 фокусов, Реформы, Бриттанское влияние, «Принять в Ставку»; шаг `kazualia` стоит после `terrain` (болотные штаты читаются из `definition.csv`) | числа и тексты в документах; придуманное помечено в скрипте | `common/national_focus/ktits_kazualia.txt`, `ideas`, `dynamic_modifiers`, `scripted_*`, `decisions`, `on_actions`, `events/ktits_kazualia_events.txt`, `localisation` |
| 13г | `tools/make_kazualia_outer.py` | Внешняя Казуальность и остальное из `docs/mechanics/Kazualia.md`: категории «Внутренняя» / «Внешняя Казуальность» со шкалами, Казуальное восстание (теги-слоты K36–K41, выбор штатов, сила, победа / поражение), страна «Наши Болота» K35 и решение СССР «Буфер на болотах», гражданская война против Казуалов, экстренные военные решения; шаг `kazouter` стоит после `kazualia`; теги K35–K41 в `04_ktits_kazualia.txt` | числа и тексты в документе; придуманное помечено в скрипте и в `docs/lore/Invented-Lore.md` | `common/country_tags/04_ktits_kazualia.txt`, `common/countries/K35–K41.txt`, `decisions/ktits_kazualia_outer_*`, `scripted_effects/ktits_kazualia_outer_effects.txt`, `scripted_guis/ktits_kazualia.txt`, `interface/ktits_kazualia.gui`, `events/ktits_kazualia_outer_events.txt`, `localisation` |

Порядок в `post_export.py`: rivers → population → states → cities → countries → ideologies → rulers → casuality → focuses → gamerules → leftovers → education → splits → terrain → regions → check → zip. Скрипт 5 (`make_rulers.py`) учитывает идеологии из `ideologies_data.py`, поэтому идёт после 10; `make_splits.py` идёт после всех, кто пишет в `history/states`.

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
