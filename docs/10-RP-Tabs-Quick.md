# Краткая инструкция по вкладкам RandomParadox

Файлы лежат в `no_commit/temp/rp_input/` (копии в `tools/rp_input/`). Файл перетаскивается в окно программы, принимает его та вкладка, которая сейчас открыта. Проект не сохраняем и не загружаем: всё в одной сессии (вылет при загрузке, см. `no_commit/rp_notes/`).

Перед началом: запустить `RandomParadox_bigstack.exe`. В логе должны быть пути `C:/Users/catsh/...`, а не `C:/Users/user/...`.

| Вкладка | Что делать | Файл |
|---|---|---|
| Configure | Имя мода `Ktits`, пути, Validate | нет |
| Land Tabs | Land Input, разметить 3 цвета (180;250;180 valley, 220;200;200 mountains, 255;255;255 peaks), Analyse Input, затем Heightmap: Generate from Landform Input. Проверить, что Фигария и острова не слиплись | `stage_01/land.png` |
| Climate Tabs, Climate Input | Режим «Use Climate Input Map», цвета распознаются сами | `stage_02/climate.png` |
| Climate Tabs, River | Открыть подвкладку River и перетащить файл. Кнопки Generate не нажимать | `stage_03/rivers.png` |
| Civilisation | Topography, Development, Population. Culture и Locations загрузить нельзя | `stage_03b/topography.png`, `development.png`, `population.png` |
| Areas | Provinces и регионы: Generate. Цель около 6 000 провинций суши | нет |
| Strategic Regions | Generate | нет |
| Countries | Режим solid. Сначала `countryMappings.txt`, затем `countries.png`. Затем Generate state data, Generate country data | `stage_04/countryMappings.txt`, `stage_04/countries.png` |
| Finalise | Export Complete mod | нет |

Проверки:
- файл принят: нет Unclassified (кроме 3 цветов Land) и ошибок в логе;
- после Areas: в логе нет «Invalid weighted center», программа не вылетела;
- после экспорта: папка `...\mod\Ktits` обновилась, в `history\countries` есть CSL, SVS, BRT, FIG, LED.

Названия вкладок и кнопок взяты из скриншотов и справки [uncertain].
