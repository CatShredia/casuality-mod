# Краткая инструкция по вкладкам RandomParadox

Файлы лежат в `no_commit/temp/rp_input/` (копии в `tools/rp_input/`). Файл перетаскивается в окно программы, принимает его та вкладка, которая сейчас открыта. Проект не сохраняем и не загружаем: всё в одной сессии (вылет при загрузке, см. `no_commit/rp_notes/`).

Перед началом: запустить `RandomParadox_bigstack.exe`. В логе должны быть пути `C:/Users/catsh/...`, а не `C:/Users/user/...`.

| Вкладка | Что делать | Файл |
|---|---|---|
| Configure | Имя мода `Ktits`, пути, Validate | нет |
| Land Tabs | Land Input (режим Landform), все 10 цветов распознаются сами, ручная разметка не нужна; Analyse Input, затем Heightmap: Generate from Landform Input. Проверить, что Фигария и острова не слиплись | `stage_01/land.png` |
| Climate Tabs, Climate Input | Режим «Use Climate Input Map», цвета распознаются сами | `stage_02/climate.png` |
| Climate Tabs, River | Открыть подвкладку River и перетащить файл. Кнопки Generate не нажимать | `stage_03/rivers.png` |
| Civilisation | Topography, Development, Population. Culture и Locations загрузить нельзя | `stage_03b/topography.png`, `development.png`, `population.png` |
| Areas | Density: Generate Density from Climate. Segments: Target Land Regions 650, Target Sea Regions 240, Generate Segments. Provinces: Land Factor 8 (не влияет), Sea Factor 0.65, Density Effects 0.55, Min Province Size 355, Max Province Count 20000, Generate Provinces. Результат в таблице ниже | нет |
| Strategic Regions | Generate | нет |
| Countries | Режим solid. Сначала `countryMappings.txt`, затем `countries.png`. Затем Generate state data, Generate country data | `stage_04/countryMappings.txt`, `stage_04/countries.png` |
| Finalise | Export Complete mod | нет |

Проверки:
- файл принят: нет Unclassified и ошибок в логе;
- после Areas: в логе нет «Invalid weighted center», программа не вылетела;
- после экспорта: папка `...\mod\Ktits` обновилась, в `history\countries` есть CSL, SVS, BRT, FIG, LED.

Названия вкладок и кнопок взяты из скриншотов и справки [uncertain].

Вкладка Areas → Provinces, поля со скрина 11 (10.11.2026):

| Поле | Значение | Влияет на результат |
|---|---|---|
| Land Factor | 8.000000 | нет |
| Sea Factor | 0.650000 | да, определяет море |
| Density Effects | 0.550000 | нет |
| Min Province Size | 355 | да, определяет сушу |
| Max Province Count | 20000 | только как потолок |
| Current Provinces | 8136 | результат: суша 6 176, море 1 960 |

Результат Areas → Provinces (скрин 11, 10.11.2026): всего 8 136 провинций, Current Provinces 8136; суша 6 176 (около 9,0 на штат при 683 штатах, ваниль 9,5), море 1 960 (ваниль 3 133), медианная сухопутная провинция 633 пикселя. Считалось по `Maps/areas/provinces.png` и `land.png`.

Что влияет на число провинций (проверено прогонами):
- Min Province Size определяет сушу: «Total desired» обратно пропорционально ему (20 → 214 567, 10 → 428 005, 570 → 10 216, 355 → 13 658). Итог меньше желаемого: программа убирает мелкие провинции.
- Sea Factor определяет море: 1.0 → около 3 000, 0.65 → 1 960, не зависит от Min Province Size.
- Land Factor (4, 5, 6, 8) и Density Effects (0.5–0.65) на число не влияют.
- Если желаемое число больше Max Province Count, программа обрезает итог пропорционально, и море почти исчезает (307 провинций): потолок ставить заведомо выше.
