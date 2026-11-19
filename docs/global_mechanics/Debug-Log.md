# Отладочный журнал механик

Строки пишутся эффектом `log` в `game.log` только при глобальном флаге `ktits_debug`. Генерирует `tools/make_debug.py` (последний из генераторов, шаг `debug` в `post_export.py`); читает `tools/read_log.py`. Ничего из этого не проверено в игре [uncertain].

## Как включить
- Консоль (`~`): `effect ktits_dbg_on` (выключить: `effect ktits_dbg_off`) [uncertain: синтаксис `effect` по `console_commands_documentation.md`: «`<tag> scripted_effect_name`», тег может быть обязателен].
- Или файлом: `run ktits_debug.txt` / `run ktits_debug_off.txt`. Файлы лежат в корне мода (`mod/Ktits/`) [uncertain: откуда `run` берёт файл; в документации только «runs the specified file with list of commands». Если не находит — скопировать файлы в корень игры или в `Documents/Paradox Interactive/Hearts of Iron IV/`]. В файлах строка консольной команды, не эффект.
- Автовключение с начала игры: `python tools/make_debug.py --auto-on` (в `post_export` не передаётся; по умолчанию выключено).
- Флаг глобальный и сохраняется в сейве.

## Формат
`[время][дата]: KTITS:<РАЗДЕЛ>:<ТЕГ>:<СОБЫТИЕ> ключ=значение ...` — одна строка. Дату и время добавляет сама игра. Префикс без квадратных скобок: `[` в строках `log` открывает команду локализации, `|` задаёт категорию лога [uncertain: оба по документации эффекта `log`]. Значения переменных подставляются как `[?var]`.

| Раздел | Что пишется |
|---|---|
| `KAZ` | ежемесячно: Вера и прирост, внутр. К., внешняя К., прогресс реформ, уровень Бриттанского духа, флаги пути (`MONTH`); `START` (ядра на Наших Болотах), `DURMANISCHE_GRANTED`, `RIOT_EVENT_FIRED` |
| `FOC` | `DONE <фокус>` в наградах; `LATE_SCHEDULED` (опоздание: событие и окно в днях; «пришло» видно по `EVT FIRE` этого события) |
| `DEC` | `DONE <решение> cost=...` в `complete_effect` решений Казуалии, Казуальности, образования, альянсов |
| `EVT` | `FIRE <id>` в `immediate` каждого события мода (в т. ч. скрытых) |
| `OUT` | `REBEL_START` / `CIVWAR_START` (слот Kxx, плановые штаты и дивизии), `RESULT_WIN` / `RESULT_LOSE` (в т. ч. «Отрезвление»), `BUFFER_K35_CREATED`; «Принять в Ставку» и экстренные решения — в `DEC` |
| `CAS` | `MONTH` (шкала, прирост, соседи-марионетки, сосед Казуалии, ступень, образование) только при шкале > 0; `TIER` смена ступени |
| `EDU` | `MONTH` специалисты (только > 0), `LEVEL` смена уровня, `COOP_ACCEPT` / `COOP_REFUSE` договоры |
| `ALLY` | `CREATED`, `JOINED`, `LEFT_OR_EXCLUDED`, `EXPELLED_BARRED`, `EXPELLED_CASUALITY_IDEOLOGY`, `DISSOLVED*`, `COOP` (изменение шкалы), `MONTH` |
| `CONT` | `ON` / `OFF` фокуса, `MONTH` активные непрерывные фокусы |
| `WAR` | `DECLARE target=... wargoal_code=0/1/2` (0 = цели войны нет), `WAR_ENTERED` (`on_declare_war`, `on_war` из ванили; ROOT = объявляющий, FROM = цель) |
| `SYS` | включение и выключение |

Примеры:
```
KTITS:KAZ:SCU:MONTH faith=34 faith_gain=3.2 inner=52 outer=4 reform=0 britt=1 path_ref=1 ...
KTITS:FOC:SCU:DONE ktits_kaz_g_quiet inner=52
KTITS:DEC:SCU:DONE ktits_kaz_gift_guns cost=15 scale=52
KTITS:CAS:FAR:MONTH scale=12 growth=3 puppet_neighbours=0 next_to_kaz=1 tier=1 edu=0
KTITS:WAR:GER:DECLARE target=POL wargoal_code=0
```
Цена `cost=[?var]` подставляется, если цена в решении переменная; `expr` — если выражение. Код цели войны использует `has_wargoal_against` и `has_war_with_wargoal_against` [uncertain: что они возвращают в момент `on_declare_war`].

## Разбор
```
python tools/read_log.py [--log game.log] [--mod PATH] [--out PATH] [--stuck 6] [--top 10]
```
Отчёт `no_commit/temp/ktits_report.md` (+ `ktits_scale.png`, `ktits_kaz.png`, если установлен matplotlib): хронология по разделам; таблицы Казуалии (Вера, К., реформы по месяцам) и шкалы стран по месяцам (топ по максимуму); ступени; альянсы; войны с целью; выбор из `error.log` по `ktits_`/`K3x`. Блок «Подозрительно»: шкала 100 больше N месяцев или не меняется, Вера не растёт 3+ месяца, прирост Веры 0, решения и фокусы, ни разу не сработавшие, опоздание без события, восстание без итога больше года, война без цели, шкала сотрудничества не меняется год.

## Проверка Казуалии
Команды консоли и сценарии: `Casuality-Testing.md`; список проверяемого: разделы «Реализация» в `docs/mechanics/Kazualia.md` (раздел «Реализация») и `docs/focuses/Kazualia-Focus-Tree.md`. Не копируется сюда.

Сценарий 1, игра за Казуалию: включить флаг, играть 2–3 года, брать решения «Дары болот», фокусы, «Принять в Ставку»; для быстрого прохождения `pp 999`, `Casuality-Testing.md` (ускорение шкалы). Затем `read_log.py`.

Сценарий 2, `observe`: `observe`, включить флаг, скорость 5 на 2–3 года; смотреть в отчёте шкалы стран, ступени, альянсы, войны без цели, восстания. Казуалия под ИИ мало что решает сама: решения и фокусы почти не сработают, это ожидаемо; её шкалы и фоновые механики проверяются.

После 3 лет игры: `python tools/read_log.py`, открыть отчёт, приложить `error.log`.

## Пересборка
Журнал вставляется в сгенерированные файлы, поэтому после перегенерации любого из `make_casuality/education/alliances/continuous/kazualia/kazualia_outer` нужно снова запустить `python tools/make_debug.py` (в `post_export` он уже стоит после них). Строки идемпотентны: старые вставки снимаются перед новыми. Чтобы выпустить мод без журнала, пропустить шаг `--skip debug`: вставок не будет вовсе.
