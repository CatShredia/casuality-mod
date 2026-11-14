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
import education_mech as E

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

# (education +1 level was replaced by specialists: Школы труда gives own +30, tools/education_mech.py)
_UNUSED_EDU_UP = [f"if = {{ limit = {{ has_idea = ktits_edu_{i} }} remove_ideas = ktits_edu_{i} add_ideas = ktits_edu_{i + 1} }}" for i in range(4, -1, -1)]
POP = lambda p: f"\t\t\tadd_popularity = {{ ideology = casuality popularity = {p} }}\n"

# id, ru name, ru desc, days, icon, x, y, prerequisite, path, extra available, reward
F = [
 ("ktits_cas_culture", "Культура труда", "Газеты, радио и школы начинают говорить о труде как о достоинстве. Работать снова становится принято.", 70, "GFX_goal_generic_production", 24, 0, None, "trud", None,
  scale(-10) + "\t\t\tadd_political_power = 50\n"),
 ("ktits_cas_schools", "Школы труда", "В школах вместо послеобеденного сна — уроки труда и дисциплины.", 70, "GFX_goal_generic_army_doctrines", 24, 1, "ktits_cas_culture", "trud", None,
  E.spec(own=30) + hidden("ktits_foc_tt_schools", ["set_country_flag = ktits_cas_f_schools"])),
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
w("common/opinion_modifiers/ktits_opinion_modifiers.txt", "opinion_modifiers = {\n\n\t# focus «Посольство в Ставке Казуала»: opinion of Kazualia about the country (value INVENTED)\n\tktits_cas_embassy = {\n\t\tvalue = 40\n\t\tmonths = 24\n\t}\n\n\t# focus «Иностранные инвестиции»: opinion of the neighbours about the country (value 10 by the author)\n\tktits_eco_investment = {\n\t\tvalue = 10\n\t\tmonths = 24\n\t}\n}\n")

ru, en = [], []
def add(k, r, e=None):
    ru.append((k, r)); en.append((k, e or L.translit(r)))
for fid, n, d, *_ in F:
    add(fid, n); add(fid + "_desc", d)
add("ktits_cas_sp_ministry", "Министерство Бодрости"); add("ktits_cas_sp_ministry_desc", "Чиновники в бодрых жилетах ходят по цехам и громко здороваются с каждым, кто закрыл глаза. Страна не то чтобы проснулась, но спать теперь неудобно.")
add("ktits_cas_sp_labour", "Трудовая повинность"); add("ktits_cas_sp_labour_desc", "Работать обязан каждый, даже тот, кто давно прикинулся мебелью. Народ трудится, косо смотрит на указ и вздыхает так, что слышно в соседней стране.")
add("ktits_cas_embassy", "Посольство в Ставке Казуала"); add("ktits_eco_investment", "Иностранные инвестиции")
for k, r, e in [
    ("ktits_foc_tt_schools", "Рост Казуальности в месяц умножается на §G0,9§!.", "Monthly Casuality growth is multiplied by §G0.9§!."),
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

# ======================= branch «Образование» (docs/focuses/Generic-Focus-Tree.md) =======================
# 13 focuses, columns x >= 68 (vanilla <= 22, Casuality 24..30, Politics 34..64). Effects: specialists counters (tools/education_mech.py);
# flags ktits_edu_f_* are read by ktits_education_monthly / the decisions; not for Kazualia and its puppets (allow_branch of the root).
EBEGIN, EEND = "# KTITS_EDUCATION_BRANCH_BEGIN (tools/make_focuses.py, do not edit by hand)", "# KTITS_EDUCATION_BRANCH_END"
EDU_GATE = ("\t\tallow_branch = {\n\t\t\tNOT = { ktits_is_kazualia = yes }\n\t\t\tNOT = { is_puppet_of = " + KAZ + " }\n"
            "\t\t\tNOT = { has_country_flag = ktits_casuality_fallen }\n\t\t}\n")
SPRIT = ("ktits_edu_sp_workers", "Рабочие факультеты", "Днём станок, вечером лекция: к концу смены рабочие знают и как точить деталь, и почему она не точится. Брака меньше, а лекторов не хватает.", "production_factory_efficiency_gain_factor", 0.03)
SPRIT2 = ("ktits_edu_sp_academy", "Академия наук", "Лучшие умы собраны под одной крышей и спорят там так громко, что окрестные улицы слышат формулы. Открытия делаются быстрее, чайник кипит дольше.", "research_speed_factor", 0.03)
LVL3 = ("\t\t\tcustom_trigger_tooltip = {\n\t\t\t\ttooltip = ktits_edu_req_lvl3\n\t\t\t\tOR = {\n\t\t\t\t\thas_idea = ktits_edu_3\n\t\t\t\t\thas_idea = ktits_edu_4\n\t\t\t\t\thas_idea = ktits_edu_5\n\t\t\t\t}\n\t\t\t}\n")
BIGAV = "\t\t\tcustom_trigger_tooltip = {\n\t\t\t\ttooltip = ktits_edu_req_big\n\t\t\t\tktits_is_big_country = yes\n\t\t\t}\n"   # "Импорт умов": big countries only
INST = "\t\t\tset_country_flag = ktits_edu_f_inst\n\t\t\tcustom_effect_tooltip = ktits_edu_tt_inst\n"
CITIZEN = ("\t\t\tcustom_effect_tooltip = ktits_edu_tt_citizen\n\t\t\thidden_effect = {\n\t\t\t\tset_variable = { var = ktits_edu_m value = ktits_spec_foreign }\n"
           "\t\t\t\tdivide_variable = { var = ktits_edu_m value = 3 }\n\t\t\t\tround_variable = ktits_edu_m\n\t\t\t\tadd_to_variable = { var = ktits_spec_own value = ktits_edu_m }\n"
           "\t\t\t\tmultiply_variable = { var = ktits_edu_m value = -1 }\n\t\t\t\tadd_to_variable = { var = ktits_spec_foreign value = ktits_edu_m }\n\t\t\t\tktits_education_update = yes\n\t\t\t}\n")
def idea_mod(sp):
    return (f"\t\t{sp[0]} = {{\n\t\t\tpicture = generic_research_bonus\n\t\t\tallowed = {{ always = no }}\n\t\t\tallowed_civil_war = {{ always = yes }}\n"
            f"\t\t\tremoval_cost = -1\n\t\t\tmodifier = {{\n\t\t\t\t{sp[3]} = {sp[4]}\n\t\t\t}}\n\t\t}}\n")
# id, ru, desc, days, icon, x, y, prerequisite(s), exclusive, available, reward, ai
EF = [
 ("ktits_edu_root", "Народное просвещение", "Правительство признаёт: страна, которая не умеет читать, не умеет и строить.", 70, "GFX_goal_generic_intelligence_exchange", 76, 0, [], [], "", E.spec(own=5) + "\t\t\tadd_political_power = 25\n", "\t\t\tfactor = 3\n"),
 ("ktits_edu_own", "Своими силами", "Решено не надеяться на чужаков: учителей и инженеров вырастим сами.", 70, "GFX_goal_generic_army_doctrines", 72, 1, ["ktits_edu_root"], ["ktits_edu_imp"], "",
  "\t\t\tset_country_flag = ktits_edu_f_self\n\t\t\tcustom_effect_tooltip = ktits_edu_tt_self\n", "\t\t\tfactor = 3\n"),
 ("ktits_edu_rural", "Сельские школы", "В каждой деревне - школа с печкой и одним учителем на все классы.", 70, "GFX_goal_generic_construct_civilian", 72, 2, ["ktits_edu_own"], [], "", E.spec(own=10), "\t\t\tfactor = 2\n"),
 ("ktits_edu_workers", "Рабочие факультеты", "Рабочих учат прямо при заводах: днём станок, вечером лекция.", 70, "GFX_goal_generic_production", 72, 3, ["ktits_edu_rural"], [], "",
  E.spec(own=10) + "\t\t\tadd_ideas = ktits_edu_sp_workers\n", "\t\t\tfactor = 2\n"),
 ("ktits_edu_inst", "Учительские институты", "Учителя теперь готовят учителей: образование растёт само.", 105, "GFX_goal_generic_propaganda", 72, 4, ["ktits_edu_workers"], [], "", INST, "\t\t\tfactor = 2\n"),
 ("ktits_edu_imp", "Импорт умов", "Если своих мастеров нет, их можно пригласить. Двери для чужих учёных открыты только у крупных держав: малым странам не хватит ни денег, ни громких имён.", 70, "GFX_goal_generic_positive_trade_relations", 80, 1, ["ktits_edu_root"], ["ktits_edu_own"], BIGAV,
  "\t\t\tset_country_flag = ktits_edu_f_import\n\t\t\tcustom_effect_tooltip = ktits_edu_tt_import\n\t\t\thidden_effect = { ktits_education_costs = yes }\n", "\t\t\tfactor = 2\n"),
 ("ktits_edu_open", "Открытые границы для учёных", "Учёным из любой страны - визы без очереди и квартиры в столице.", 70, "GFX_goal_generic_improve_relations", 80, 2, ["ktits_edu_imp"], [], "", E.spec(foreign=15), "\t\t\tfactor = 2\n"),
 ("ktits_edu_mentor", "Наставник в каждом цеху", "Каждый приезжий специалист берёт учеников.", 70, "GFX_goal_generic_national_unity", 80, 3, ["ktits_edu_open"], [], "",
  "\t\t\tset_country_flag = ktits_edu_f_mentor\n\t\t\tcustom_effect_tooltip = ktits_edu_tt_mentor_focus\n", "\t\t\tfactor = 2\n"),
 ("ktits_edu_citizen", "Гражданство за знания", "Иностранцам, отработавшим пять лет, дают гражданство.", 105, "GFX_goal_generic_alliance", 80, 4, ["ktits_edu_mentor"], [], "", CITIZEN, "\t\t\tfactor = 2\n"),
 ("ktits_edu_univ", "Университеты", "В крупных городах открываются университеты.", 105, "GFX_goal_generic_scientific_exchange", 76, 3, ["ktits_edu_rural", "ktits_edu_open"], [], "", E.spec(own=20), "\t\t\tfactor = 3\n"),
 ("ktits_edu_academy", "Академия наук", "Лучшие умы страны собраны под одной крышей.", 105, "GFX_goal_generic_secret_weapon", 76, 4, ["ktits_edu_univ"], [], "",
  E.spec(own=20) + "\t\t\tadd_ideas = ktits_edu_sp_academy\n", "\t\t\tfactor = 3\n"),
 ("ktits_edu_society", "Общество знаний", "Знание становится главной ценностью страны.", 140, "GFX_goal_generic_radar", 76, 5, ["ktits_edu_academy"], [], LVL3, E.spec(own=30), "\t\t\tfactor = 3\n"),
 ("ktits_edu_cure", "Лекарство от лени", "Учёные доказывают: Казуальность - болезнь, и от неё есть лечение.", 70, "GFX_goal_generic_dangerous_deal", 78, 4, ["ktits_edu_univ"], [], "",
  scale(-10) + "\t\t\tset_country_flag = ktits_cas_f_cure\n\t\t\tcustom_effect_tooltip = ktits_foc_tt_cure\n",
  "\t\t\tfactor = 3\n\t\t\tmodifier = {\n\t\t\t\tfactor = 0.2\n\t\t\t\tcheck_variable = { var = ktits_casuality value = 10 compare = less_than }\n\t\t\t}\n"),
]
assert len(EF) == 13 and all(f[3] % 7 == 0 for f in EF)
eblk = EBEGIN + "\n"
el, ee = [], []
for fid, ru_, desc, days, icon, x, y, pre, excl, av, rew, ai in EF:
    eblk += pfocus(fid, icon, x, y, days, pre or None, excl or None, av or None, ai, rew)
    el += [(fid, ru_), (fid + "_desc", desc)]
eblk = eblk.replace("\t\tx = 76\n\t\ty = 0\n", EDU_GATE + "\t\tx = 76\n\t\ty = 0\n", 1)   # allow_branch of the root only
eblk += "\n" + EEND + "\n"
txt = g.read_text(encoding="utf-8", newline="")
nl = "\r\n" if "\r\n" in txt else "\n"
txt = re.sub(r"\r?\n?" + re.escape(EBEGIN) + r".*?" + re.escape(EEND) + r"\r?\n?", "", txt, flags=re.S)
k = txt.rindex("}")
txt = txt[:k].rstrip() + nl + nl + eblk.replace("\n", nl) + nl + txt[k:]
g.write_text(txt, encoding="utf-8", newline="")
w("common/ideas/ktits_edu_focus_ideas.txt", "ideas = {\n\tcountry = {\n" + idea_mod(SPRIT) + idea_mod(SPRIT2) + "\t}\n}\n")
for sp in (SPRIT, SPRIT2):
    el += [(sp[0], "Образование: " + sp[1]), (sp[0] + "_desc", sp[2])]
ru_e = [
    ("ktits_edu_req_lvl3", "Образованность не ниже уровня §Y3§! («Развивающееся общество»)", "Education at least level §Y3§!"),
    ("ktits_edu_tt_self", "Решения упрощения отнимают вдвое меньше наших специалистов.", "Simplification decisions cost half as many own specialists."),
    ("ktits_edu_tt_import", "Открываются решения привлечения специалистов («Приют для беглых умов», «Наставничество», «Договор о сотрудничестве»). «Приют» и «Наставничество» дешевле на §G25 %§!.", "Attraction decisions open (refuge, mentorship, cooperation treaty). Refuge and mentorship are §G25%§! cheaper."),
    ("ktits_edu_tt_mentor_focus", "Иностранные специалисты становятся нашими по §G8 %§! в месяц вместо 5 % (навсегда).", "§G8%§! of foreign specialists a month become own instead of 5% (permanent)."),
    ("ktits_edu_tt_inst", "Наших специалистов §G+1§! тыс. в месяц навсегда.", "Own specialists §G+1§! k a month, permanently."),
    ("ktits_edu_tt_citizen", "Треть иностранных специалистов сразу становится нашими.", "A third of the foreign specialists become own at once."),
    ("ktits_foc_tt_cure", "Рост Казуальности в месяц умножается на §G0,9§! (вместе с «Школами труда»: ×0,81).", "Monthly Casuality growth is multiplied by §G0.9§! (with the labour schools: x0.81)."),
]
for k_, r_, e_ in ru_e:
    el.append((k_, r_)); ee.append((k_, e_))
el_en = {k_: L.translit(v_) for k_, v_ in el}
el_en.update(dict(ee))
L.write_yml(str(M / "localisation/russian/ktits_edu_focus_l_russian.yml"), "russian", el)
L.write_yml(str(M / "localisation/english/ktits_edu_focus_l_english.yml"), "english", list(el_en.items()))
print(f"education branch written: {len(EF)} focuses, 2 spirits")

# ======================= branch «Экономика» (docs/focuses/Generic-Focus-Tree.md) =======================
# 36 focuses, columns x = 84..108 (vanilla <= 22, Casuality 24..30, Politics 34..64, Education 72..80). Open to every country (Kazualia too).
# Factories / slots / infrastructure / dockyards / resources are hidden_effect blocks over random_owned_controlled_state (vanilla pattern of
# common/national_focus/generic.txt) with a custom_effect_tooltip; percent modifiers are national spirits ktits_eco_sp_* (common/ideas/ktits_eco_ideas.txt).
XBEGIN, XEND = "# KTITS_ECONOMY_BRANCH_BEGIN (tools/make_focuses.py, do not edit by hand)", "# KTITS_ECONOMY_BRANCH_END"
TTL = {}   # tooltip loc: key -> (ru, en)
def ttl(key, ru_, en_): TTL[key] = (ru_, en_)
def hid(tip, body, t="\t\t\t"):
    return f"{t}custom_effect_tooltip = {tip}\n{t}hidden_effect = {{\n" + "".join(f"{t}\t{l}\n" for l in body) + f"{t}}}\n"
def in_states(n, lines, limit="impassable = no"):
    return [f"random_owned_controlled_state = {{ limit = {{ {limit} }} " + " ".join(lines) + " }" for _ in range(n)]
def civ(n):
    ttl(f"ktits_eco_tt_civ{n}", f"Гражданских фабрик: §G+{n}§! (в случайном штате)", f"Civilian factories: §G+{n}§! (in a random state)")
    return hid(f"ktits_eco_tt_civ{n}", in_states(1, [f"add_extra_state_shared_building_slots = {n}", f"add_building_construction = {{ type = industrial_complex level = {n} instant_build = yes }}"]))
def mil(n):
    ttl(f"ktits_eco_tt_mil{n}", f"Военных фабрик: §G+{n}§! (в случайном штате)", f"Military factories: §G+{n}§! (in a random state)")
    return hid(f"ktits_eco_tt_mil{n}", in_states(1, [f"add_extra_state_shared_building_slots = {n}", f"add_building_construction = {{ type = arms_factory level = {n} instant_build = yes }}"]))
def dock(n):
    ttl(f"ktits_eco_tt_dock{n}", f"Верфей: §G+{n}§! (в случайном прибрежном штате)", f"Dockyards: §G+{n}§! (in a random coastal state)")
    return hid(f"ktits_eco_tt_dock{n}", in_states(1, [f"add_extra_state_shared_building_slots = {n}", f"add_building_construction = {{ type = dockyard level = {n} instant_build = yes }}"], "is_coastal = yes"))
def slots(n, st):
    ttl(f"ktits_eco_tt_slots{n}_{st}", f"Слотов строительства: §G+{n}§! в каждом из {st} случайных штатов", f"Building slots: §G+{n}§! in each of {st} random states")
    return hid(f"ktits_eco_tt_slots{n}_{st}", in_states(st, [f"add_extra_state_shared_building_slots = {n}"]))
def capslots(n):
    ttl(f"ktits_eco_tt_cap{n}", f"Слотов строительства в столице: §G+{n}§!", f"Building slots in the capital: §G+{n}§!")
    return hid(f"ktits_eco_tt_cap{n}", [f"capital_scope = {{ add_extra_state_shared_building_slots = {n} }}"])
def infra(st):
    ttl(f"ktits_eco_tt_infra{st}", f"Инфраструктура: §G+1§! уровень в {st} штатах", f"Infrastructure: §G+1§! level in {st} states")
    return hid(f"ktits_eco_tt_infra{st}", in_states(st, ["add_building_construction = { type = infrastructure level = 1 instant_build = yes }"],
                                                    "impassable = no free_building_slots = { building = infrastructure size > 0 }"))
def resrc(pairs, key):
    return hid(key, in_states(1, [f"add_resource = {{ type = {t_} amount = {n_} show_state_in_tooltip = no }}" for t_, n_ in pairs]))
def sp(name): return f"\t\t\tadd_ideas = ktits_eco_sp_{name}\n"
def stab(v): return f"\t\t\tadd_stability = {v}\n"
def pp(v): return f"\t\t\tadd_political_power = {v}\n"

# spirits: name -> (ru, lore desc [INVENTED], idea picture, modifiers)
SPX = {
 "root": ("Экономический курс", "Министры составили программу на сорок страниц, из которых работает последняя. Товаров на прилавках стало чуть меньше: бумаги на планы ушло много.", "generic_economic_recovery", {"consumer_goods_factor": -0.02}),
 "devalue": ("Девальвация валюты", "Деньги дешевеют быстрее, чем их успевают печатать. Соседи в восторге от наших цен, свои только вздыхают над кошельком.", "generic_devalue_currency", {"resource_trade_cost_bonus_per_factory": 1, "consumer_goods_factor": -0.03}),
 "crash": ("Последствия девальвации", "Вчерашние сбережения сегодня стоят буханку хлеба. Люди ходят по лавкам с кошельком в одной руке и калькулятором в другой.", "generic_economic_crisis", {"stability_factor": -0.05}),
 "export": ("Экспортный рывок", "Порты загружены, склады пусты, а строители работают в три смены: заказы из-за границы не ждут.", "generic_economic_increase", {"production_speed_buildings_factor": 0.05}),
 "settle": ("Рабочие посёлки", "Одинаковые дома стоят ровными рядами, и в каждом живёт будущий призывник, который точно знает, где его улица.", "generic_build_infrastructure", {"conscription_factor": 0.02}),
 "base": ("Расширение ресурсной базы", "Опись недр составлена и подшита в папку. Добыча растёт не потому, что руды стало больше, а потому, что её наконец сосчитали.", "generic_exploit_mines", {"local_resources_factor": 0.05}),
 "reserve": ("Стратегический резерв", "На складах лежит всё, что понадобится в войну, и немного того, что не понадобится никогда. Снабженцы спят спокойно.", "generic_fuel_reserves", {"local_resources_factor": 0.05, "supply_consumption_factor": -0.05}),
 "plan": ("Плановая экономика", "Каждый гвоздь учтён, каждая лопата внесена в таблицу. Правда, гвоздей иногда меньше, чем строчек в таблице.", "generic_central_management", {"production_speed_buildings_factor": 0.10, "consumer_goods_factor": 0.05}),
 "gosplan": ("Госплан", "Комитет плановиков заседает днём и ночью и рисует на карте стрелки, по которым ездят настоящие грузовики.", "generic_central_management", {"production_factory_efficiency_gain_factor": 0.05}),
 "second": ("Вторая пятилетка", "Новый план перекрывает прежний, а прежний ещё не закончен. Прорабы привыкли и строят одновременно оба.", "generic_build_infrastructure", {"production_speed_buildings_factor": 0.05}),
 "heavy": ("Тяжёлая промышленность", "Станки теперь важнее ботинок. Ботинки, впрочем, тоже когда-нибудь выпустят, по плану.", "generic_improved_industries", {"consumer_goods_factor": 0.02}),
 "collective": ("Коллективные хозяйства", "Тракторы общие, лозунги общие, урожай общий, и только жалобы почему-то у каждого свои.", "generic_agrarian_reform", {"conscription_factor": 0.03}),
 "stakhanov": ("Стахановское движение", "Передовики выполняют норму за полсмены и обедают остаток дня. Остальные стараются не отставать, но получается не у всех.", "generic_economic_increase", {"production_factory_max_efficiency_factor": 0.05}),
 "electro": ("Электрификация страны", "Лампочка в каждой избе светит тускло, зато ярче любых докладов. В лабораториях тоже стало светлее.", "generic_research_bonus", {"research_speed_factor": 0.03}),
 "market": ("Рыночная экономика", "Цены меняются каждый день, и все сразу становятся экономистами. Лавки открываются, государство только следит за правилами.", "generic_foreign_capital", {"consumer_goods_factor": -0.05, "production_speed_buildings_factor": 0.05}),
 "banks": ("Частные банки", "Банкиры дают ссуду любому, у кого есть идея и залог, а залогом нередко служит сама идея. Стройки идут бойко.", "generic_foreign_capital", {"production_speed_buildings_factor": 0.05}),
 "tax": ("Налоговые льготы", "Новое предприятие пять лет не платит налогов, а потом внезапно закрывается и открывается под другим названием.", "generic_economic_recovery", {"consumer_goods_factor": -0.03}),
 "boom": ("Потребительский бум", "Полки ломятся от товаров, люди покупают в кредит то, что им совсем не нужно. Зато настроение отличное.", "generic_goods_red_bonus", {"consumer_goods_factor": 0.02}),
 "trade": ("Торговые компании", "Караваны компаний ходят по всему материку, и каждый купец знает, где дешевле. Фабрикам теперь выгоднее менять товар на сырьё.", "generic_foreign_capital", {"resource_trade_cost_bonus_per_factory": 1}),
 "rail": ("Железные дороги", "Поезда ходят почти по расписанию, а те, что не по расписанию, зато доставляют грузы быстрее, чем их ждут.", "generic_build_infrastructure", {"supply_consumption_factor": -0.05}),
}
ICO = {"cap": "GFX_goal_generic_construct_civ_factory", "mil": "GFX_goal_generic_construct_mil_factory", "inf": "GFX_goal_generic_construct_infrastructure",
       "tr": "GFX_goal_generic_trade", "pr": "GFX_goal_generic_production", "co": "GFX_goal_generic_construction"}
OPIN = hid("ktits_eco_tt_opinion", ["every_neighbor_country = { add_opinion_modifier = { target = ROOT modifier = ktits_eco_investment } }"])
GEO = resrc([("steel", 4), ("aluminium", 2)], "ktits_eco_tt_geo")
SWAMP = resrc([("oil", 4)], "ktits_eco_tt_swamp")
ttl("ktits_eco_tt_opinion", "Отношения соседей со страной: §G+10§!", "Neighbours' opinion of the country: §G+10§!")
ttl("ktits_eco_tt_dry", "Рост Казуальности от популярности Казуальности: §G-1§! в месяц (если у партии не меньше 10 %).", "Casuality growth from the casuality party: §G-1§! per month (if the party has 10% or more).")
ttl("ktits_eco_tt_swamp", "§G+4§! нефти в случайном штате.", "§G+4§! oil in a random state.")
ttl("ktits_eco_tt_geo", "§G+4§! стали и §G+2§! алюминия в случайном штате.", "§G+4§! steel and §G+2§! aluminium in a random state.")
ttl("ktits_eco_tt_crash_off", "Снимает штраф от девальвации валюты.", "Removes the devaluation penalty.")

# id suffix, ru, desc, days, icon, x, y, prerequisites (list of OR-groups; groups are ANDed), exclusive, reward, ai
X = [
 ("root", "Экономический курс", "Министры спорят, как поднимать хозяйство страны, и садятся писать программу.", 70, ICO["pr"], 100, 0, [], [], pp(50) + sp("root"), "\t\t\tfactor = 5\n"),
 # finance
 ("dev", "Девальвация валюты", "Национальная валюта резко дешевеет. Товары страны дешевле для соседей, а сбережения граждан тают.", 35, "GFX_goal_generic_dangerous_deal", 84, 1, [["root"]], [],
  sp("devalue") + "\t\t\tadd_timed_idea = { idea = ktits_eco_sp_crash days = 180 }\n", "\t\t\tfactor = 1\n\t\t\tmodifier = {\n\t\t\t\tfactor = 0\n\t\t\t\thas_stability < 0.55\n\t\t\t}\n"),
 ("export", "Экспортный рывок", "Дешёвая валюта превращается в заказы из-за границы.", 70, ICO["tr"], 84, 2, [["dev"]], [], civ(1) + sp("export"), "\t\t\tfactor = 2\n"),
 ("gold", "Золотой запас", "Выручку от экспорта переплавляют в слитки и прячут в подвалы Центробанка.", 70, "GFX_goal_generic_scientific_exchange", 84, 3, [["export"]], [],
  pp(100) + stab(0.05) + "\t\t\tcustom_effect_tooltip = ktits_eco_tt_crash_off\n\t\t\thidden_effect = {\n\t\t\t\tif = {\n\t\t\t\t\tlimit = { has_idea = ktits_eco_sp_crash }\n\t\t\t\t\tremove_ideas = ktits_eco_sp_crash\n\t\t\t\t}\n\t\t\t}\n", "\t\t\tfactor = 2\n"),
 # housing
 ("house", "Жилищная программа", "Государство обещает каждой семье крышу над головой.", 70, ICO["co"], 88, 1, [["root"]], [], stab(0.05) + slots(1, 2), "\t\t\tfactor = 3\n"),
 ("settle", "Рабочие посёлки", "Рядом с заводами вырастают посёлки из одинаковых домов.", 70, "GFX_goal_generic_construct_civilian", 88, 2, [["house"]], [], civ(1) + sp("settle"), "\t\t\tfactor = 3\n"),
 ("quarters", "Городские кварталы", "Старые трущобы сносят, на их месте строят кварталы с водопроводом.", 70, ICO["cap"], 88, 3, [["settle"]], [], capslots(2) + stab(0.05), "\t\t\tfactor = 3\n"),
 ("dry", "Сухие дома", "Новые дома ставят на сваях и подсыпке: болотная сырость больше не проникает в жильё.", 70, "GFX_goal_generic_fortify_city", 88, 4, [["quarters"]], [],
  scale(-5) + "\t\t\tset_country_flag = ktits_cas_f_dry\n\t\t\tcustom_effect_tooltip = ktits_eco_tt_dry\n", "\t\t\tfactor = 1\n"),
 # resources
 ("base", "Расширение ресурсной базы", "Страна составляет опись всего, что лежит в её недрах.", 70, "GFX_goal_generic_oil_refinery", 92, 1, [["root"]], [], sp("base"), "\t\t\tfactor = 3\n"),
 ("geo", "Геологоразведка", "Экспедиции геологов уходят в горы и пустоши.", 70, "GFX_goal_generic_secret_weapon", 92, 2, [["base"]], [], GEO, "\t\t\tfactor = 3\n"),
 ("swamp", "Добыча в болотах", "Торф, болотная руда и газ: топи тоже могут кормить страну.", 70, "GFX_goal_generic_construct_infrastructure", 92, 3, [["geo"]], [], SWAMP + scale(5), "\t\t\tfactor = 1\n"),
 ("reserve", "Стратегический резерв", "Склады ресурсов на случай войны или кризиса.", 70, "GFX_goal_generic_construct_military", 92, 4, [["swamp"]], [], sp("reserve"), "\t\t\tfactor = 2\n"),
 # planned economy
 ("plan", "Плановая экономика", "Государство само решает, что, где и сколько производить.", 70, "GFX_goal_generic_soviet_construction", 98, 1, [["root"]], ["market"], sp("plan"),
  "\t\t\tfactor = 1\n\t\t\tmodifier = {\n\t\t\t\tfactor = 4\n\t\t\t\tOR = {\n\t\t\t\t\thas_government = communism\n\t\t\t\t\thas_government = fascism\n\t\t\t\t}\n\t\t\t}\n"),
 ("gosplan", "Госплан", "Комитет плановиков расписывает выпуск каждой фабрики на годы вперёд.", 70, "GFX_goal_generic_political_pressure", 98, 2, [["plan"]], [], pp(50) + sp("gosplan"), "\t\t\tfactor = 3\n"),
 ("five1", "Первая пятилетка", "План на пять лет: заводы, электростанции, каналы.", 105, ICO["cap"], 98, 3, [["gosplan"]], [], civ(2), "\t\t\tfactor = 3\n"),
 ("heavy", "Тяжёлая промышленность", "Сталь и станки важнее одежды и мебели.", 70, ICO["mil"], 96, 4, [["five1"]], [], mil(2) + sp("heavy"), "\t\t\tfactor = 2\n"),
 ("collect", "Коллективные хозяйства", "Крестьян объединяют в хозяйства с общими тракторами.", 70, "GFX_goal_generic_construct_civilian", 100, 4, [["five1"]], [], sp("collective") + stab(-0.05), "\t\t\tfactor = 2\n"),
 ("five2", "Вторая пятилетка", "Новый план ещё больше прежнего.", 105, ICO["cap"], 98, 5, [["heavy", "collect"]], [], civ(2) + sp("second"), "\t\t\tfactor = 3\n"),
 ("stakh", "Стахановское движение", "Передовиков, перевыполняющих норму, ставят в пример всей стране.", 70, ICO["pr"], 96, 6, [["five2"]], [], scale(-10) + sp("stakhanov"), "\t\t\tfactor = 2\n"),
 ("order", "Оборонный заказ", "Часть плана отдаётся армии.", 70, "GFX_goal_generic_army_tanks", 100, 6, [["five2"]], [], mil(2), "\t\t\tfactor = 2\n"),
 ("electro", "Электрификация страны", "Провода тянут в каждую деревню.", 70, "GFX_goal_generic_radar", 98, 7, [["stakh", "order"]], [], slots(1, 3) + sp("electro"), "\t\t\tfactor = 2\n"),
 ("great", "Великие стройки", "Каналы, плотины и города в пустых местах.", 105, ICO["co"], 98, 8, [["electro"]], [], civ(3) + stab(-0.05), "\t\t\tfactor = 2\n"),
 # market economy
 ("market", "Рыночная экономика", "Цены и выпуск решает рынок, государство только следит за правилами.", 70, "GFX_goal_generic_positive_trade_relations", 106, 1, [["root"]], ["plan"], sp("market"),
  "\t\t\tfactor = 2\n\t\t\tmodifier = {\n\t\t\t\tfactor = 0.25\n\t\t\t\tOR = {\n\t\t\t\t\thas_government = communism\n\t\t\t\t\thas_government = fascism\n\t\t\t\t}\n\t\t\t}\n"),
 ("free", "Свободный рынок", "Отменены ценовые ограничения, лавки и мастерские открываются без разрешений.", 70, ICO["tr"], 106, 2, [["market"]], [], civ(1) + stab(0.03), "\t\t\tfactor = 3\n"),
 ("banks", "Частные банки", "Банки дают ссуды всем, у кого есть идея и залог.", 70, "GFX_goal_generic_improve_relations", 106, 3, [["free"]], [], pp(50) + sp("banks"), "\t\t\tfactor = 3\n"),
 ("stock", "Биржа", "В столице открывается фондовая биржа.", 70, ICO["cap"], 104, 4, [["banks"]], [], civ(2), "\t\t\tfactor = 2\n"),
 ("tax", "Налоговые льготы", "Новым предприятиям — несколько лет без налогов.", 70, "GFX_goal_generic_construction2", 108, 4, [["banks"]], [], sp("tax"), "\t\t\tfactor = 2\n"),
 ("invest", "Иностранные инвестиции", "Иностранные компании строят заводы в стране.", 105, "GFX_goal_generic_alliance", 106, 5, [["stock", "tax"]], [], civ(2) + OPIN, "\t\t\tfactor = 3\n"),
 ("boom", "Потребительский бум", "Магазины полны, люди покупают в кредит.", 70, "GFX_goal_generic_production2", 104, 6, [["invest"]], [], stab(0.05) + sp("boom"), "\t\t\tfactor = 2\n"),
 ("yards", "Частные верфи", "Судостроение отдают частным владельцам.", 70, "GFX_goal_generic_construct_naval_dockyard", 108, 6, [["invest"]], [], dock(2), "\t\t\tfactor = 2\n"),
 ("firms", "Торговые компании", "Крупные компании возят товары по всему материку.", 70, "GFX_goal_generic_trade", 106, 7, [["boom", "yards"]], [], sp("trade") + pp(50), "\t\t\tfactor = 2\n"),
 ("flower", "Деловой расцвет", "Страна — один из деловых центров материка.", 105, ICO["co"], 106, 8, [["firms"]], [], civ(3) + scale(-5), "\t\t\tfactor = 2\n"),
 # common finale
 ("road", "Дорожная сеть", "Шоссе связывают все крупные города.", 70, "GFX_goal_generic_construct_infrastructure", 102, 10, [["great", "flower", "quarters"]], [], infra(4), "\t\t\tfactor = 3\n"),
 ("rail", "Железные дороги", "Новые линии и вокзалы.", 70, "GFX_goal_generic_army_motorized", 102, 11, [["road"]], [], infra(4) + sp("rail"), "\t\t\tfactor = 3\n"),
 ("belt", "Промышленный пояс", "Вдоль железных дорог вырастает пояс заводов.", 105, ICO["mil"], 100, 12, [["rail"], ["reserve"]], [], civ(2) + mil(2), "\t\t\tfactor = 3\n"),
 ("bureau", "Научно-промышленные бюро", "Учёные работают прямо при заводах.", 70, "GFX_goal_generic_scientific_exchange", 100, 13, [["belt"]], [],
  "\t\t\tadd_research_slot = 1\n" + E.spec(own=15), "\t\t\tfactor = 3\n"),
]
assert len(X) == 36 and all(f[3] % 7 == 0 for f in X)
XID = lambda k: "ktits_eco_" + k
xblk = XBEGIN + "\n"
xl = []
for k, ru_, desc, days, icon, x, y, pre, excl, rew, ai in X:
    s_ = f"\n\tfocus = {{\n\t\tid = {XID(k)}\n\t\ticon = {icon}\n"
    for grp in pre:
        s_ += "\t\tprerequisite = { " + " ".join(f"focus = {XID(p)}" for p in grp) + " }\n"
    if excl: s_ += "\t\tmutually_exclusive = { " + " ".join(f"focus = {XID(p)}" for p in excl) + " }\n"
    s_ += f"\t\tx = {x}\n\t\ty = {y}\n\t\tcost = {days // 7}\n\t\tsearch_filters = {{ FOCUS_FILTER_INDUSTRY }}\n" + CONT
    s_ += "\t\tai_will_do = {\n" + ai + "\t\t}\n\t\tcompletion_reward = {\n" + rew + "\t\t}\n\t}\n"
    xblk += s_
    xl += [(XID(k), ru_), (XID(k) + "_desc", desc)]
xblk += "\n" + XEND + "\n"
txt = g.read_text(encoding="utf-8", newline="")
nl = "\r\n" if "\r\n" in txt else "\n"
txt = re.sub(r"\r?\n?" + re.escape(XBEGIN) + r".*?" + re.escape(XEND) + r"\r?\n?", "", txt, flags=re.S)
k_ = txt.rindex("}")
txt = txt[:k_].rstrip() + nl + nl + xblk.replace("\n", nl) + nl + txt[k_:]
g.write_text(txt, encoding="utf-8", newline="")
def xidea(name, v):
    body = "".join(f"\t\t\t\t{k} = {x:g}\n" for k, x in v[3].items())
    return (f"\t\tktits_eco_sp_{name} = {{\n\t\t\tpicture = {v[2]}\n\t\t\tallowed = {{ always = no }}\n\t\t\tallowed_civil_war = {{ always = yes }}\n"
            f"\t\t\tremoval_cost = -1\n\t\t\tmodifier = {{\n{body}\t\t\t}}\n\t\t}}\n")
w("common/ideas/ktits_eco_ideas.txt", "ideas = {\n\tcountry = {\n" + "".join(xidea(n, v) for n, v in SPX.items()) + "\t}\n}\n")
for n, v in SPX.items():
    xl += [(f"ktits_eco_sp_{n}", v[0]), (f"ktits_eco_sp_{n}_desc", v[1])]
xl_en = {k: L.translit(v) for k, v in xl}
for k, (r_, e_) in TTL.items():
    xl.append((k, r_)); xl_en[k] = e_
L.write_yml(str(M / "localisation/russian/ktits_eco_l_russian.yml"), "russian", xl)
L.write_yml(str(M / "localisation/english/ktits_eco_l_english.yml"), "english", list(xl_en.items()))
print(f"economy branch written: {len(X)} focuses, {len(SPX)} spirits")
