"""Custom ideologies of the mod (docs/lore/Lore-Overview.md section 3). Lore (docs/lore/Contries-Description.md) names the 7 ideologies and 5 special sub-ideologies;
everything else here (groups, keys, colors, texts, effects) is INVENTED and must be reviewed (docs/lore/Invented-Lore.md).

Structure: the 4 vanilla groups stay, with extra sub-ideologies; 2 own groups (casuality, theology) are added.
Shared by make_ideologies.py and make_rulers.py.
"""

GROUP_ORDER = ("democratic", "fascism", "communism", "neutrality", "casuality", "theology")
NEW_GROUPS = ("casuality", "theology")

# group -> {key: (russian name, english name, russian description)}; keys that are new sub-ideologies of vanilla groups
CUSTOM_SUBTYPES = {
    "democratic": {"technodemocracy": ("Технодемократия", "Technodemocracy",
                   "Демократия, где решения опираются на научные советы и экспертов. Лор: Северная Ассамблея.")},
    "communism": {"total_communism": ("Тотальный Коммунизм", "Total Communism",
                  "Коммунизм без остатка: государство и партия охватывают всю жизнь общества. Заготовка, страны пока нет.")},
    "fascism": {"total_fascism": ("Тотальный Фашизм", "Total Fascism",
                "Предельная форма фашизма: вся жизнь подчинена вождю и партии. Заготовка, страны пока нет."),
                "integralism": ("Интегрализм", "Integralism",
                "Государство как единый организм с порядком, иерархией и очками интеграции земель. Лор: Дмитровское Княжество.")},
    "neutrality": {"meritocracy": ("Меритократия", "Meritocracy",
                   "Власть по заслугам и мандатам: выше тот, кто заработал голоса и должности. Лор: Федерация Депутатов."),
                   "technocracy": ("Технократия", "Technocracy",
                   "Власть инженеров и учёных; главное мерило - технический индекс. Лор: Челяба."),
                   "steppe_khanate": ("Степной ханизм", "Steppe Khanate",
                   "Хан над кланами, торговля и караванные пути вместо государства-аппарата. Лор: Сарайкумское Ханство.")},
    # own groups: one sub-ideology each (same key as the group would clash in HOI4 loc, so sub keys are *_ideology)
    "casuality": {"casuality_ideology": ("Казуальность", "Casuality",
                  "Умение ничего не делать и получать от жизни всё. Идеология и образ жизни Казуалии.")},
    "theology": {"theology_ideology": ("Теология", "Theology",
                 "Власть, основанная на вере и духовенстве. Привязка к Иракиккистану и Ирракии придумана.")},
}

# own groups: key -> (adjective ru, noun ru, desc ru, adjective en, noun en, color rgb)
NEW_GROUP_INFO = {
    "casuality": ("Казуальная", "Казуальность", "Расслабленное государство", "Casual", "Casuality", (60, 180, 75)),
    "theology": ("Теократическая", "Теология", "Религиозное государство", "Theocratic", "Theology", (212, 175, 55)),
}

# names of vanilla groups in Russian (vanilla ru loc may be absent for some languages; only used for new keys)
GROUP_RU = {"democratic": "Демократия", "communism": "Коммунизм", "fascism": "Фашизм", "neutrality": "Нейтралитет"}
