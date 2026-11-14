"""Focus branch «Казуальность» in the standard (generic) national focus tree (docs/focuses/Generic-Focus-Tree.md).

 * 11 focuses in two mutually exclusive paths: «Труд» (against Casuality) and «Болото» (towards it), absolute columns x = 24 and x = 30,
   which are free in vanilla `generic_focus` (its focuses use x up to 22);
 * the block is inserted into the mod's common/national_focus/generic.txt between the markers KTITS_CASUALITY_BRANCH_BEGIN/END
   (the file is rewritten by every RandomParadox export, so the step cuts the old block and inserts it again: idempotent);
 * effects needing the mechanic (education +1, growth x0.9, neighbour -1, halved event growth, free "Дома Безделья", no split on fall,
   cheaper fight decisions, AI course) are country flags `ktits_cas_f_*` read by make_casuality.py;
 * spirits «Министерство Бодрости», «Трудовая повинность» (common/ideas/ktits_focus_ideas.txt), opinion modifier ktits_cas_embassy.
Texts and numbers: docs/focuses/Generic-Focus-Tree.md (author's table); icons, opinion value, tooltips are INVENTED (docs/lore/Invented-Lore.md).
Also builds the branch «Политический курс» (26 focuses, x = 34..64, markers KTITS_POLITICS_BRANCH_BEGIN/END, spirits ktits_pol_sp_*).
Run after make_casuality.py. Usage: python tools/make_focuses.py [--mod PATH]
"""
import argparse, re
from pathlib import Path
import lore_data as L

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
a = ap.parse_args()
M = Path(a.mod)
info = L.load_mod(M)
KAZ = {lt: t for t, lt in info["tag2lore"].items()}["CSL"]
RAPP = "ktits_cas_ai_rapprochement"
BEGIN, END = "# KTITS_CASUALITY_BRANCH_BEGIN (tools/make_focuses.py, do not edit by hand)", "# KTITS_CASUALITY_BRANCH_END"

def tt(d):   # tooltip loc keys are created by make_casuality.py (ktits_cas_tt_p10 ...)
    return "ktits_cas_tt_" + ("p%d" % d if d > 0 else "m%d" % -d)

def scale(d, t="\t\t\t"):
    return (f"{t}custom_effect_tooltip = {tt(d)}\n{t}add_to_variable = {{ var = ktits_casuality value = {d} }}\n"
            f"{t}clamp_variable = {{ var = ktits_casuality min = 0 max = 100 }}\n{t}hidden_effect = {{ ktits_casuality_update = yes }}\n")

def hidden(tip, body, t="\t\t\t"):
    return f"{t}custom_effect_tooltip = {tip}\n{t}hidden_effect = {{\n" + "".join(f"{t}\t{l}\n" for l in body) + f"{t}}}\n"

EDU_UP = [f"if = {{ limit = {{ has_idea = ktits_edu_{i} }} remove_ideas = ktits_edu_{i} add_ideas = ktits_edu_{i + 1} }}" for i in range(4, -1, -1)]
POP = lambda p: f"\t\t\tadd_popularity = {{ ideology = casuality popularity = {p} }}\n"

# id, ru name, ru desc, days, icon, x, y, prerequisite, path, extra available, reward
F = [
 ("ktits_cas_culture", "Культура труда", "Газеты, радио и школы начинают говорить о труде как о достоинстве. Работать снова становится принято.", 70, "GFX_goal_generic_production", 24, 0, None, "trud", None,
  scale(-10) + "\t\t\tadd_political_power = 50\n"),
 ("ktits_cas_schools", "Школы труда", "В школах вместо послеобеденного сна — уроки труда и дисциплины.", 70, "GFX_goal_generic_army_doctrines", 24, 1, "ktits_cas_culture", "trud", None,
  hidden("ktits_foc_tt_schools", EDU_UP + ["set_country_flag = ktits_cas_f_schools"])),
 ("ktits_cas_drain", "Осушение низин", "Государственная программа превращает топи в поля. Болото отступает.", 105, "GFX_goal_generic_construct_infrastructure", 24, 2, "ktits_cas_schools", "trud", None,
  "\t\t\tset_country_flag = ktits_cas_f_drain\n\t\t\tcustom_effect_tooltip = ktits_foc_tt_drain\n" + scale(-20)),
 ("ktits_cas_ministry", "Министерство Бодрости", "Ведомство, которое следит, чтобы никто не засыпал на рабочем месте.", 70, "GFX_goal_generic_national_unity", 24, 3, "ktits_cas_drain", "trud",
  "\t\t\tcustom_trigger_tooltip = {\n\t\t\t\ttooltip = ktits_foc_req_lt50\n\t\t\t\tcheck_variable = { var = ktits_casuality value = 50 compare = less_than }\n\t\t\t}\n",
  "\t\t\tadd_ideas = ktits_cas_sp_ministry\n\t\t\tset_country_flag = ktits_cas_f_ministry\n\t\t\tcustom_effect_tooltip = ktits_foc_tt_ministry\n"),
 ("ktits_cas_anticas", "Анти-Казуальный курс", "Страна открыто объявляет Казуальность главной угрозой. Готовится основа будущей Анти-Казуальной Лиги.", 70, "GFX_goal_generic_defence", 24, 4, "ktits_cas_ministry", "trud", None,
  "\t\t\tset_country_flag = ktits_cas_f_anticas\n\t\t\tclear_country_flag = " + RAPP + "\n\t\t\tcustom_effect_tooltip = ktits_foc_tt_anticas\n" + scale(-10)),
 ("ktits_cas_service", "Трудовая повинность", "Каждый гражданин обязан отработать на благо страны. Лень объявлена пережитком, прогульщиков отправляют в трудовые лагеря.", 35, "GFX_goal_generic_construct_mil_factory", 26, 1, "ktits_cas_culture", "trud",
  "\t\t\tOR = {\n\t\t\t\thas_country_leader_ideology = total_fascism\n\t\t\t\thas_country_leader_ideology = total_communism\n\t\t\t}\n",
  "\t\t\tadd_ideas = ktits_cas_sp_labour\n\t\t\tset_country_flag = ktits_cas_f_labour\n\t\t\tcustom_effect_tooltip = ktits_foc_tt_service\n" + scale(-15)),
 ("ktits_cas_rest", "Право на отдых", "Конституцию дополняет статья: «Никто не обязан стараться».", 70, "GFX_goal_generic_neutrality_focus", 30, 0, None, "bolot", None,
  scale(10) + POP(0.05) + "\t\t\tcustom_effect_tooltip = ktits_foc_tt_rest\n"),
 ("ktits_cas_resorts", "Болотные курорты", "В топях открываются санатории, туда едут целыми семьями.", 70, "GFX_goal_generic_construct_civ_factory", 30, 1, "ktits_cas_rest", "bolot", None,
  "\t\t\tadd_stability = 0.05\n" + scale(5) + POP(0.05)),
 ("ktits_cas_houses", "Дома Безделья по всей стране", "Сеть клубов «ничего-не-делания» покрывает каждый город.", 70, "GFX_goal_generic_propaganda", 30, 2, "ktits_cas_resorts", "bolot", None,
  "\t\t\tset_country_flag = { flag = ktits_cas_f_houses days = 180 value = 1 }\n\t\t\tcustom_effect_tooltip = ktits_foc_tt_houses\n" + POP(0.10)),
 ("ktits_cas_embassy", "Посольство в Ставке Казуала", "В Ставку Казуала отправляется посольство с дарами и просьбой о покровительстве.", 35, "GFX_goal_generic_political_pressure", 30, 3, "ktits_cas_houses", "bolot",
  f"\t\t\tcountry_exists = {KAZ}\n",
  f"\t\t\t{KAZ} = {{\n\t\t\t\tadd_opinion_modifier = {{ target = ROOT modifier = ktits_cas_embassy }}\n\t\t\t}}\n" + scale(10)),
 ("ktits_cas_wing", "Под крылом Казуалии", "Правительство готово добровольно стать частью болотного мира.", 105, "GFX_goal_generic_military_sphere", 30, 4, "ktits_cas_embassy", "bolot",
  "\t\t\tcustom_trigger_tooltip = {\n\t\t\t\ttooltip = ktits_foc_req_ge75\n\t\t\t\tcheck_variable = { var = ktits_casuality value = 75 compare = greater_than_or_equals }\n\t\t\t}\n",
  "\t\t\tset_country_flag = ktits_cas_f_wing\n\t\t\tcustom_effect_tooltip = ktits_foc_tt_wing\n" + scale(20)),
]
assert all(f[3] % 7 == 0 for f in F)
EXCL = {"ktits_cas_culture": "ktits_cas_rest", "ktits_cas_rest": "ktits_cas_culture"}
ROOT_GATE = "\t\tallow_branch = {\n\t\t\tNOT = { ktits_is_kazualia = yes }\n\t\t\tNOT = { has_country_flag = ktits_casuality_fallen }\n\t\t}\n"

blk = BEGIN + "\n"
for fid, ru, _d, days, icon, x, y, pre, path, av, rew in F:
    blk += f"\n\tfocus = {{\n\t\tid = {fid}\n\t\ticon = {icon}\n"
    if pre: blk += f"\t\tprerequisite = {{ focus = {pre} }}\n"
    if fid in EXCL: blk += f"\t\tmutually_exclusive = {{ focus = {EXCL[fid]} }}\n" + ROOT_GATE
    blk += f"\t\tx = {x}\n\t\ty = {y}\n\t\tcost = {days // 7}\n\t\tsearch_filters = {{ FOCUS_FILTER_POLITICAL }}\n"
    if av: blk += "\t\tavailable = {\n" + av + "\t\t}\n"
    blk += "\t\tcancel_if_invalid = no\n\t\tcontinue_if_invalid = yes\n"
    # AI: course "Сближение" takes the path «Болото», "Борьба" (no flag) the path «Труд»
    gate = f"NOT = {{ has_country_flag = {RAPP} }}" if path == "bolot" else f"has_country_flag = {RAPP}"
    blk += f"\t\tai_will_do = {{\n\t\t\tfactor = {1 if fid == 'ktits_cas_service' else 5}\n\t\t\tmodifier = {{\n\t\t\t\tfactor = 0\n\t\t\t\t{gate}\n\t\t\t}}\n\t\t}}\n"
    blk += "\t\tcompletion_reward = {\n" + rew + "\t\t}\n\t}\n"
blk += "\n" + END + "\n"

g = M / "common/national_focus/generic.txt"
txt = g.read_text(encoding="utf-8", newline="")          # keep BOM and line endings of the exported file
nl = "\r\n" if "\r\n" in txt else "\n"
txt = re.sub(r"\r?\n?" + re.escape(BEGIN) + r".*?" + re.escape(END) + r"\r?\n?", "", txt, flags=re.S)
k = txt.rindex("}")                                         # closing brace of focus_tree
txt = txt[:k].rstrip() + nl + nl + blk.replace("\n", nl) + nl + txt[k:]
g.write_text(txt, encoding="utf-8", newline="")

def w(rel, text):
    p = M / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding="utf-8", newline="\n")

def idea(name, stab):
    return (f"\t\t{name} = {{\n\t\t\tpicture = ktits_casuality\n\t\t\tallowed = {{ always = no }}\n\t\t\tallowed_civil_war = {{ always = yes }}\n"
            f"\t\t\tremoval_cost = -1\n\t\t\tmodifier = {{\n\t\t\t\tstability_factor = {stab}\n\t\t\t}}\n\t\t}}\n")
w("common/ideas/ktits_focus_ideas.txt", "ideas = {\n\tcountry = {\n" + idea("ktits_cas_sp_ministry", 0.05) + idea("ktits_cas_sp_labour", -0.05) + "\t}\n}\n")
w("common/opinion_modifiers/ktits_opinion_modifiers.txt", "opinion_modifiers = {\n\n\t# focus «Посольство в Ставке Казуала»: opinion of Kazualia about the country (value INVENTED)\n\tktits_cas_embassy = {\n\t\tvalue = 40\n\t\tmonths = 24\n\t}\n}\n")

ru, en = [], []
def add(k, r, e=None):
    ru.append((k, r)); en.append((k, e or L.translit(r)))
for fid, n, d, *_ in F:
    add(fid, n); add(fid + "_desc", d)
add("ktits_cas_sp_ministry", "Министерство Бодрости"); add("ktits_cas_sp_ministry_desc", "Чиновники в бодрых жилетах ходят по цехам и громко здороваются с каждым, кто закрыл глаза. Страна не то чтобы проснулась, но спать теперь неудобно.")
add("ktits_cas_sp_labour", "Трудовая повинность"); add("ktits_cas_sp_labour_desc", "Работать обязан каждый, даже тот, кто давно прикинулся мебелью. Народ трудится, косо смотрит на указ и вздыхает так, что слышно в соседней стране.")
add("ktits_cas_embassy", "Посольство в Ставке Казуала")
for k, r, e in [
    ("ktits_foc_tt_schools", "Образование повышается на 1 уровень (не выше 5). Рост Казуальности в месяц умножается на §G0,9§!.", "Education rises by 1 level (max 5). Monthly Casuality growth is multiplied by §G0.9§!."),
    ("ktits_foc_req_lt50", "Казуальность меньше §Y50§! (сейчас [?ktits_casuality|0])", "Casuality below §Y50§! (now [?ktits_casuality|0])"),
    ("ktits_foc_req_ge75", "Казуальность не меньше §Y75§! (сейчас [?ktits_casuality|0])", "Casuality at least §Y75§! (now [?ktits_casuality|0])"),
    ("ktits_foc_tt_drain", "Рост Казуальности от соседства с Казуалией: §G-1§! в месяц.", "Casuality growth from neighbouring Kazualia: §G-1§! per month."),
    ("ktits_foc_tt_ministry", "Рост Казуальности от событий вдвое меньше (с округлением вниз).", "Casuality growth from events is halved (rounded down)."),
    ("ktits_foc_tt_anticas", "ИИ страны всегда на курсе «Борьба»; курс «Сближение» отключается.", "The AI always follows the course of fighting; rapprochement is switched off."),
    ("ktits_foc_tt_service", "Решения борьбы с Казуальностью дешевле на §G10 %§!.", "Fight decisions are §G10%§! cheaper."),
    ("ktits_foc_tt_rest", "Открывает решения поддержки Казуальности.", "Unlocks the decisions that support Casuality."),
    ("ktits_foc_tt_houses", "Решение «Дома Безделья» доступно без перезарядки в течение 180 дней.", "The decision \"Doma Bezdelya\" has no cooldown for 180 days."),
    ("ktits_foc_tt_wing", "При переходе в Казуальность страна сохраняет промышленность и не распадается на части.", "On falling into Casuality the country keeps its industry and does not break apart."),
]:
    ru.append((k, r)); en.append((k, e))
L.write_yml(str(M / "localisation/russian/ktits_focuses_l_russian.yml"), "russian", ru)
L.write_yml(str(M / "localisation/english/ktits_focuses_l_english.yml"), "english", en)
print(f"focus branch written: {len(F)} focuses into {g.name}, 2 spirits, 1 opinion modifier")

# ======================= branch «Политический курс» (docs/focuses/Generic-Focus-Tree.md) =======================
# 26 focuses: root, 5 mutually exclusive paths (popularity -> coming to power -> subtype), reset focus.
# Columns x >= 34 (vanilla generic uses x <= 22, the Casuality branch x = 24..30). Subtypes are set with set_country_leader_ideology,
# their bonuses are national spirits ktits_pol_sp_* (common/ideas/ktits_pol_ideas.txt), removed by the reset focus.
PBEGIN, PEND = "# KTITS_POLITICS_BRANCH_BEGIN (tools/make_focuses.py, do not edit by hand)", "# KTITS_POLITICS_BRANCH_END"
P_ROOT = "ktits_pol_root"
P_CHANGE = "ktits_pol_change"
P_CD = "ktits_pol_change_cd"
POP_NEED = "0.39"   # popularity >= 40 % is written as `> 0.39` (vanilla form: `democratic > 0.39`)

# key, ideology group, ru genitive, x of the path column, pop (ru, desc, icon), come (ru, desc, icon),
# subtypes [(id suffix, ru, desc, ideology key, x, icon, modifiers)]
PATHS = [
 ("dem", "democratic", "демократии", 37,
  ("Голос народа", "Разрешены партии, газеты и собрания.", "GFX_goal_support_democracy"),
  ("Свободные выборы", "Страна идёт на честные выборы.", "GFX_goal_generic_improve_relations"),
  [("liberal", "Либеральная республика", "Свобода рынка и слова прежде всего.", "liberalism", 34, "GFX_goal_generic_trade", {"consumer_goods_factor": -0.05}),
   ("socdem", "Социал-демократия", "Сильное государство заботится о каждом.", "socialism", 36, "GFX_goal_generic_construct_civ_factory", {"stability_factor": 0.10}),
   ("conserv", "Консервативный центр", "Традиции и осторожные реформы.", "conservatism", 38, "GFX_goal_generic_national_unity", {"war_support_factor": 0.05, "stability_factor": 0.05}),
   ("techdem", "Технодемократия", "Голосование через машины, решения по расчётам.", "technodemocracy", 40, "GFX_goal_generic_scientific_exchange", {"research_speed_factor": 0.05})]),
 ("com", "communism", "коммунизма", 44,
  ("Красный рассвет", "Рабочие кружки выходят из подполья.", "GFX_goal_support_communism"),
  ("Власть советов", "Советы рабочих берут власть в столице.", "GFX_goal_generic_soviet_construction"),
  [("lenin", "Ленинский путь", "Умеренный путь: власть советов без чисток.", "leninism", 43, "GFX_goal_generic_production", {"stability_factor": 0.10, "industrial_capacity_factory": 0.05}),
   ("totcom", "Тотальный коммунизм", "Всё во имя партии, ничего вне партии.", "total_communism", 45, "GFX_goal_generic_war_with_comintern", {"war_support_factor": 0.10, "stability_factor": -0.05})]),
 ("fas", "fascism", "фашизма", 50,
  ("Сильная рука", "Ветераны и националисты требуют порядка.", "GFX_goal_support_fascism"),
  ("Марш на столицу", "Колонны сторонников входят в столицу, правительство уходит в отставку.", "GFX_goal_generic_occupy_start_war"),
  [("natstate", "Национальное государство", "Нация превыше всего, но без тотального контроля.", "fascism_ideology", 48, "GFX_goal_generic_construct_mil_factory", {"stability_factor": 0.10, "production_speed_arms_factory_factor": 0.05}),
   ("totfas", "Тотальный фашизм", "Государство контролирует каждую сторону жизни.", "total_fascism", 50, "GFX_goal_generic_major_war", {"war_support_factor": 0.15, "stability_factor": -0.05}),
   ("integral", "Интегрализм", "Нация, вера и традиция как единое целое.", "integralism", 52, "GFX_goal_generic_fortify_city", {"stability_factor": 0.05, "war_support_factor": 0.05})]),
 ("neu", "neutrality", "нейтральных", 58,
  ("Порядок прежде всего", "Страна устала от партий и лозунгов.", "GFX_goal_generic_neutrality_focus"),
  ("Правительство спасения", "Власть переходит к беспартийному кабинету.", "GFX_goal_generic_defence"),
  [("merit", "Меритократия", "Должности получают лучшие по экзаменам.", "meritocracy", 55, "GFX_goal_generic_intelligence_exchange", {"research_speed_factor": 0.05}),
   ("technoc", "Технократия", "Страной управляют инженеры и учёные.", "technocracy", 57, "GFX_goal_generic_construction", {"production_speed_buildings_factor": 0.05}),
   ("steppe", "Степной ханизм", "Власть хана, совет родов и кочевая конница.", "steppe_khanate", 59, "GFX_goal_generic_cavalry", {"conscription_factor": 0.05}),
   ("despot", "Самодержавие", "Вся власть в руках одного правителя.", "despotism", 61, "GFX_goal_generic_demand_territory", {"stability_factor": 0.10, "political_power_gain": -0.05})]),
 ("the", "theology", "теологии", 64,
  ("Глас веры", "Проповедники собирают площади.", "GFX_goal_generic_propaganda"),
  ("Совет духовенства", "Совет духовенства становится высшей властью.", "GFX_goal_generic_political_pressure"),
  [("theocr", "Теократия", "Закон и вера становятся одним.", "theology_ideology", 64, "GFX_goal_generic_secret_weapon", {"stability_factor": 0.15})]),
]
BONUS = {"consumer_goods_factor": "товары народного потребления", "stability_factor": "стабильность", "war_support_factor": "поддержка войны",
         "research_speed_factor": "скорость исследований", "industrial_capacity_factory": "выпуск фабрик", "production_speed_arms_factory_factor": "скорость постройки военных фабрик",
         "production_speed_buildings_factor": "скорость строительства", "conscription_factor": "пополнение (призыв)", "political_power_gain": "прирост политической власти"}
BONUS_EN = {"consumer_goods_factor": "consumer goods", "stability_factor": "stability", "war_support_factor": "war support", "research_speed_factor": "research speed",
            "industrial_capacity_factory": "factory output", "production_speed_arms_factory_factor": "military factory construction speed",
            "production_speed_buildings_factor": "construction speed", "conscription_factor": "replenishment (conscription)", "political_power_gain": "political power gain"}
CONT = "\t\tcancel_if_invalid = no\n\t\tcontinue_if_invalid = yes\n"
SUB_IDS, SPIRITS = [], []
# INVENTED lore texts of the subtype spirits (docs/lore/Invented-Lore.md)
SP_TXT = {
    "liberal": "Рынок свободен, пресса свободна, только прилавки иногда пустеют: свободу ведь не купишь, зато за неё не берут пошлину.",
    "socdem": "Государство заботливо подтыкает каждому одеяло и выдаёт пособие на чай. Граждане довольны и немного разбалованы.",
    "conserv": "Как дедушка говорил, так и делаем, а чуть что - собираем комиссию. Перемены допускаются, но очень медленно и с поклоном традиции.",
    "techdem": "Любой спор решается голосованием через машину, а машина решает, чьё голосование считать. Учёные в восторге, остальные не в курсе.",
    "lenin": "Советы заседают допоздна, чистки отложены до лучших времён, а лозунги висят ровно. Строим светлое будущее без лишней нервотрёпки.",
    "totcom": "Всё общее, включая зубные щётки и мнения. Партия знает лучше, поэтому спорить с ней вредно для здоровья и репутации.",
    "natstate": "Нация превыше всего, и об этом напоминают на каждом углу. Заводы дымят в строю, но личная жизнь пока остаётся личной.",
    "totfas": "Государство смотрит в каждое окно и одобряет только строй. Все маршируют, даже те, кто просто шёл в магазин.",
    "integral": "Нация, вера и традиция слиты в один пирог, который режет только староста. Сытно, чинно и немного душно.",
    "merit": "Должность получает тот, кто лучше сдал экзамен, а не тот, у кого дядя в канцелярии. Дядьки, разумеется, учатся наперегонки.",
    "technoc": "Страной правят инженеры, и каждая реформа сопровождается чертежом. Дороги стали ровнее, а споров почти нет: чертёж не обсуждают.",
    "steppe": "Хан сидит на ковре, совет родов шумит, а конница уже в седле. Законы устные, но запоминаются отлично.",
    "despot": "Вся власть у одного человека, а остальным остаётся ему кивать. Тишина в стране такая, что слышно, как правитель ест.",
    "theocr": "Закон и молитва слились настолько, что налоги платят с поклоном. Порядок крепок, ведь спорить со святым себе дороже.",
}
pl, pe = [], []   # loc ru entries, en overrides

def pfocus(fid, icon, x, y, days, pre, excl, avail, ai, reward, gate=False):
    s = f"\n\tfocus = {{\n\t\tid = {fid}\n\t\ticon = {icon}\n"
    if pre: s += "\t\tprerequisite = { " + " ".join(f"focus = {p}" for p in pre) + " }\n"
    if excl: s += "\t\tmutually_exclusive = { " + " ".join(f"focus = {p}" for p in excl) + " }\n"
    if gate: s += ROOT_GATE
    s += f"\t\tx = {x}\n\t\ty = {y}\n\t\tcost = {days // 7}\n\t\tsearch_filters = {{ FOCUS_FILTER_POLITICAL }}\n"
    if avail: s += "\t\tavailable = {\n" + avail + "\t\t}\n"
    s += CONT + "\t\tai_will_do = {\n" + ai + "\t\t}\n\t\tcompletion_reward = {\n" + reward + "\t\t}\n\t}\n"
    return s

pblk = PBEGIN + "\n"
pblk += pfocus(P_ROOT, "GFX_goal_generic_political_pressure", 50, 0, 70, None, None, None, "\t\t\tfactor = 1\n", "\t\t\tadd_political_power = 75\n", gate=True)
pl += [(P_ROOT, "Политический курс"), (P_ROOT + "_desc", "Страна устала от неопределённости: пора решить, по какому пути она пойдёт.")]
pops = [f"ktits_pol_{p[0]}_pop" for p in PATHS]
for key, grp, gen, cx, (pn, pd, pic), (cn, cd, cic), subs in PATHS:
    pid, cid = f"ktits_pol_{key}_pop", f"ktits_pol_{key}_come"
    pblk += pfocus(pid, pic, cx, 1, 70, [P_ROOT], [o for o in pops if o != pid], None,
                   f"\t\t\tfactor = 3\n\t\t\tmodifier = {{\n\t\t\t\tfactor = 4\n\t\t\t\thas_government = {grp}\n\t\t\t}}\n",
                   f"\t\t\tadd_popularity = {{ ideology = {grp} popularity = 0.15 }}\n")
    need = f"\t\t\tcustom_trigger_tooltip = {{\n\t\t\t\ttooltip = ktits_pol_req_{grp}\n\t\t\t\t{grp} > {POP_NEED}\n\t\t\t}}\n"
    rew = (f"\t\t\tif = {{\n\t\t\t\tlimit = {{ has_government = {grp} }}\n\t\t\t\tadd_stability = 0.10\n\t\t\t}}\n\t\t\telse = {{\n"
           f"\t\t\t\tset_politics = {{\n\t\t\t\t\truling_party = {grp}\n\t\t\t\t\telections_allowed = yes\n\t\t\t\t}}\n\t\t\t}}\n")
    pblk += pfocus(cid, cic, cx, 2, 70, [pid], None, need, "\t\t\tfactor = 5\n", rew)
    pl += [(pid, pn), (pid + "_desc", pd), (cid, cn), (cid + "_desc", cd), (f"ktits_pol_req_{grp}", f"Популярность {gen} не ниже §Y40 %§!")]
    pe.append((f"ktits_pol_req_{grp}", f"Popularity of {grp} at least §Y40%§!"))
    sids = [f"ktits_pol_{key}_{s[0]}" for s in subs]
    for s, sid in zip(subs, sids):
        _, sn, sd, ide, sx, sic, mods = s
        sp = f"ktits_pol_sp_{s[0]}"
        SUB_IDS.append(sid); SPIRITS.append((sp, sn, mods, ide))
        rew = f"\t\t\thidden_effect = {{ set_country_leader_ideology = {ide} }}\n\t\t\tcustom_effect_tooltip = ktits_pol_tt_{s[0]}\n\t\t\tadd_ideas = {sp}\n"
        if ide == "theology_ideology": rew += scale(-10)
        pblk += pfocus(sid, sic, sx, 3, 70, [cid], [o for o in sids if o != sid], None, "\t\t\tfactor = 2\n", rew)
        pl += [(sid, sn), (sid + "_desc", sd), (f"ktits_pol_tt_{s[0]}", f"Правитель страны получает подтип идеологии «{sn}»"),
               (sp, sn), (sp + "_desc", SP_TXT[s[0]])]
        pe += [(f"ktits_pol_tt_{s[0]}", f"The ruler gets the ideology subtype \"{L.translit(sn)}\""),
               (sp + "_desc", L.translit(SP_TXT[s[0]]))]
# reset focus: removes the spirits itself (on_uncomplete is documented only in the effect docs, not seen in a vanilla focus file)
rm = "".join(f"\t\t\t\tif = {{ limit = {{ has_idea = {sp} }} remove_ideas = {sp} }}\n" for sp, *_ in SPIRITS)
rew = (f"\t\t\tadd_political_power = -100\n\t\t\tadd_stability = -0.10\n\t\t\tset_country_flag = {{ flag = {P_CD} days = 365 value = 1 }}\n"
       f"\t\t\tcustom_effect_tooltip = ktits_pol_tt_reset\n\t\t\thidden_effect = {{\n{rm}\t\t\t}}\n"
       f"\t\t\tuncomplete_national_focus = {{\n\t\t\t\tfocus = {P_ROOT}\n\t\t\t\tuncomplete_children = yes\n\t\t\t}}\n")
avail = f"\t\t\thas_war = no\n\t\t\tNOT = {{ has_country_flag = {P_CD} }}\n"
ai = "\t\t\tfactor = 0\n\t\t\tmodifier = {\n\t\t\t\tadd = 1\n\t\t\t\thas_stability < 0.40\n\t\t\t}\n"
pblk += pfocus(P_CHANGE, "GFX_goal_generic_dangerous_deal", 50, 5, 70, SUB_IDS, None, avail, ai, rew)
pl += [(P_CHANGE, "Народ голосует за перемены"), (P_CHANGE + "_desc", "Улицы требуют другого будущего. Правительство объявляет, что прежний курс исчерпан, и страна снова выбирает путь."),
       ("ktits_pol_tt_reset", "Снимает выполнение со всей ветки «Политический курс» и её духи; ветку можно пройти заново. Смена курса закрыта на 365 дней.")]
pe.append(("ktits_pol_tt_reset", "Resets the whole Political Course branch and removes its spirits; the branch can be taken again. Changing course is locked for 365 days."))
pblk += "\n" + PEND + "\n"

txt = g.read_text(encoding="utf-8", newline="")
nl = "\r\n" if "\r\n" in txt else "\n"
txt = re.sub(r"\r?\n?" + re.escape(PBEGIN) + r".*?" + re.escape(PEND) + r"\r?\n?", "", txt, flags=re.S)
k = txt.rindex("}")
txt = txt[:k].rstrip() + nl + nl + pblk.replace("\n", nl) + nl + txt[k:]
g.write_text(txt, encoding="utf-8", newline="")

def pidea(name, mods):
    body = "".join(f"\t\t\t\t{k} = {v:g}\n" for k, v in mods.items())
    return (f"\t\t{name} = {{\n\t\t\tpicture = ktits_casuality\n\t\t\tallowed = {{ always = no }}\n\t\t\tallowed_civil_war = {{ always = yes }}\n"
            f"\t\t\tremoval_cost = -1\n\t\t\tmodifier = {{\n{body}\t\t\t}}\n\t\t}}\n")
w("common/ideas/ktits_pol_ideas.txt", "ideas = {\n\tcountry = {\n" + "".join(pidea(sp, m) for sp, _n, m, _i in SPIRITS) + "\t}\n}\n")
pl_en = {k: L.translit(v) for k, v in pl}
pl_en.update(dict(pe))
L.write_yml(str(M / "localisation/russian/ktits_pol_l_russian.yml"), "russian", pl)
L.write_yml(str(M / "localisation/english/ktits_pol_l_english.yml"), "english", list(pl_en.items()))
print(f"politics branch written: {len(SUB_IDS) + 12} focuses, {len(SPIRITS)} spirits")
