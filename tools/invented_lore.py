"""INVENTED data: everything here is NOT in docs/lore/Contries-Description.md. It was made up to fill TODO gaps and must be reviewed by the author.
A value present in docs/lore/Contries-Description.md always wins over this file (see lore_data.LORE_POP, make_rulers.RULERS).
Review list with reasons: docs/lore/Invented-Lore.md.
"""

# population in millions (docs/lore/Contries-Description.md says TODO / nothing). Hints used: analog countries, "Магнолия и Фигария почти безлюдны",
# "самое плотное население у Ирракии, Кытая и Чёрной Республики", "Челяба - промышленный гигант", "Ледышка: населения почти нет"
INVENTED_POP = {
    "ZLD": 18, "ADL": 5, "SVA": 20, "FDP": 35, "DMK": 25, "CLB": 55, "MGN": 3, "KTY": 450, "CEY": 8,
    "FIG": 2, "LED": 0.05, "Z01": 12, "Z02": 10, "Z03": 8, "Z04": 14, "Z05": 4, "Z06": 5,   # Z05 + Z06 = 9 (the old Iberadia, split into two)
}

# rulers: lore tag -> (name, ideology group, text, vanilla sub-ideology). Names follow each country's naming style from docs/lore/Contries-Description.md.
INVENTED_RULERS = {
    "IRK": ("Низам Махмуд Хайрулла-хан Лахарский", "theology", "самодержавие, марионетка Бриттана (придумано)", "theology_ideology"),
    "IRR": ("Махараджа Радж Нараян Сингх", "theology", "княжеское самодержавие, марионетка Бриттана (придумано)", "theology_ideology"),
    "MUS": ("Король Рама Чакрават Аюттарский", "neutrality", "монархия (docs/lore/Contries-Description.md: монархия и верховный правитель; имя придумано)", "despotism"),
    "TRV": ("Президент Чилл Расслабов", "democratic", "федеративная республика (придумано)", "liberalism"),
    "MGN": ("Каган Алтан-Бор Хэнтийский", "neutrality", "улусная монархия (придумано)", "despotism"),
    "KTY": ("Маршал Чжао Лун-Тай", "neutrality", "военная диктатура (придумано)", "despotism"),
    "BLK": ("Премьер Фукусава Мацуяма", "neutrality", "милитаризм (придумано)", "japan_militarism_ideology"),
    "CEY": ("Король Нанда Сурия Цейлонский", "neutrality", "марионетка Бриттана (придумано)", "despotism"),
    "Z05": ("Президент Исабель Монтеверде-Рио", "democratic", "республика с выборным президентом (придумано)", "liberalism"),
    "Z06": ("Каудильо Эмилиано Бельтран-Арагон", "fascism", "каудильизм (придумано)", "falangism"),
}

# start politics that replace the exported ones (applied by make_rulers.py after the ruling party is set): lore tag -> (last election, elections allowed, popularities)
# Z05 became a democracy: sensible democratic start like the other democracies of the mod (docs/lore/Invented-Lore.md)
INVENTED_POLITICS = {
    "Z05": ("1934.5.12", "yes", {"democratic": 47, "fascism": 12, "communism": 20, "neutrality": 21}),
}

# Z06 is the eastern part of the old Iberadia, split off AFTER the RandomParadox export by tools/make_iberia_split.py (docs/lore/Invented-Lore.md)
# new mod tag, parent mod-tag lore (Z05), colour (also in tools/rp_input/stage_04/countryMappings.txt), states of the eastern landmass are found by adjacency
SPLIT_OFF = {"lore": "Z06", "tag": "ARA", "parent_lore": "Z05", "color": (140, 40, 60), "file": "Aragonia", "english": "Aragonia"}

# terrain positions (pixel coordinates of the 4608x2816 map; a province is selected by its centroid)
NASHI_BOLOTA = {"country": "SVS", "x": (2750, 3450), "y": (850, 1200), "from": ("plains", "forest", "hills"), "to": "marsh"}
FIG_RIDGE_Y = (2270, 2370)        # Фигарийский хребет: east-west band across the southern part
FIG_JUNGLE_SOUTH_OF_Y = 2370      # "южнее хребта большие джунгли"
FIG_WEST_HILLS_X = 1100           # "на западе холмы" (north of the ridge)
CSL_CAPITAL_PIXEL = (2948, 1292)  # capitals.txt; the capital province is ringed by mountains on N, E, W (not S)

# ---- Z01..Z05 "заготовки" (docs/lore/Contries-Description.md gives only the placeholder; the Balkan-like belt of 5 small countries) ----
# Names, capitals, cities and naming styles are INVENTED: each country is a blend of several real-world cultures.
INVENTED_COUNTRIES = {
    "Z01": {"name": "Дальмирия", "style": "z01_adria", "capital": "Вельград-Маре",
            "cities": ["Сан-Дубров", "Кастель-Нова", "Ново-Бари", "Лубляна-Кара", "Поречье", "Спалатро"]},      # славяно-итальянская
    "Z02": {"name": "Рашидия", "style": "z02_ottoslav", "capital": "Шахр-Беград",
            "cities": ["Кара-Сараево", "Мостар-Кала", "Ново-Пазар-Хан", "Скопье-Шахр", "Тетовабад", "Нишкент"]},  # турецко-арабско-славянская
    "Z03": {"name": "Трансильдавия", "style": "z03_carpath", "capital": "Дракуленград",
            "cities": ["Клуж-Вар", "Тимишбург", "Сибиу-Кент", "Орадеа", "Брашовар", "Фэгэрашка"]},               # румыно-венгро-немецкая
    "Z04": {"name": "Македорея", "style": "z04_hellenic", "capital": "Фессалиополь",
            "cities": ["Афинополь", "Коринф-Хан", "Патрас-Нова", "Лариссград", "Янинакала", "Тривизонд"]},        # греко-кавказско-византийская
    "Z05": {"name": "Иберадия", "style": "z05_iberia", "capital": "Сан-Мадриго",
            "cities": ["Альсевилья", "Валенсария", "Барселуна", "Толедо-Нова", "Гранадир"]},     # испано-мавро-латиноамериканская (западная часть, полуостров южнее Соевой)
    "Z06": {"name": "Арагония", "style": "z06_aragon", "capital": "Сарагоса-Кала",
            "cities": ["Уэска-Мар", "Теруэльград", "Калатаюд", "Монсон-Нова", "Тарасона-Кала", "Бельчите"]},    # восточная часть бывшей Иберадии, у Тямовского рейха
}
INVENTED_STYLES = {
    "z01_adria": (["Бело", "Сан", "Порто", "Кастель", "Ново", "Лидо", "Мали", "Вело", "Рива", "Бук", "Дубро", "Мар"],
                  ["град", "ница", "поре", "ано", "елло", "ово", "ето", "ичи", "ена", "аро"]),
    "z02_ottoslav": (["Кара", "Ак", "Ново", "Шах", "Паша", "Султан", "Дервиш", "Мост", "Баш", "Яни", "Чарши", "Хан"],
                     ["кент", "бад", "кала", "ица", "ово", "хисар", "шахр", "чай", "гюль", "овац"]),
    "z03_carpath": (["Клуж", "Сибу", "Тимиш", "Брашо", "Арад", "Вар", "Зала", "Нэсэуд", "Моцы", "Хунед", "Дьер", "Кронен"],
                    ["вар", "бург", "ешти", "ара", "иу", "бая", "кент", "штадт", "оара", "ень"]),
    "z04_hellenic": (["Афин", "Корин", "Ларис", "Патр", "Спар", "Элев", "Тривиз", "Кала", "Янин", "Аргос", "Месо", "Ново"],
                     ["ополь", "ида", "ика", "ини", "ос", "кала", "ианти", "хори", "аки", "ата"]),
    "z05_iberia": (["Аль", "Валь", "Сан", "Санта", "Толе", "Гран", "Кастель", "Вилья", "Монте", "Ла", "Рио", "Пуэр"],
                   ["севилья", "ада", "ария", "уна", "дор", "оса", "брава", "лона", "мора", "кала", "дира"]),
    "z06_aragon": (["Уэс", "Терув", "Калата", "Бильби", "Таразо", "Монс", "Хака", "Фрага", "Борха", "Альби", "Ла", "Сан"],
                   ["ка", "юд", "ель", "ара", "он", "оса", "дира", "монте", "вилья", "хар"]),
}
