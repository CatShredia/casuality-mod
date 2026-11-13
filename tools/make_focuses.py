"""Focus branch «Казуальность» in the standard (generic) national focus tree (docs/focuses/Generic-Focus-Tree.md).

 * 11 focuses in two mutually exclusive paths: «Труд» (against Casuality) and «Болото» (towards it), absolute columns x = 24 and x = 30,
   which are free in vanilla `generic_focus` (its focuses use x up to 22);
 * the block is inserted into the mod's common/national_focus/generic.txt between the markers KTITS_CASUALITY_BRANCH_BEGIN/END
   (the file is rewritten by every RandomParadox export, so the step cuts the old block and inserts it again: idempotent);
 * effects needing the mechanic (education +1, growth x0.9, neighbour -1, halved event growth, free "Дома Безделья", no split on fall,
   cheaper fight decisions, AI course) are country flags `ktits_cas_f_*` read by make_casuality.py;
 * spirits «Министерство Бодрости», «Трудовая повинность» (common/ideas/ktits_focus_ideas.txt), opinion modifier ktits_cas_embassy.
Texts and numbers: docs/focuses/Generic-Focus-Tree.md (author's table); icons, opinion value, tooltips are INVENTED (docs/lore/Invented-Lore.md).
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
add("ktits_cas_sp_ministry", "Министерство Бодрости"); add("ktits_cas_sp_ministry_desc", "Ведомство следит, чтобы никто не засыпал на рабочем месте: стабильность выше, а события Казуальности подталкивают шкалу вдвое слабее.")
add("ktits_cas_sp_labour", "Трудовая повинность"); add("ktits_cas_sp_labour_desc", "Работать обязан каждый. Решения борьбы с Казуальностью дешевле на 10 %, но стабильность страдает.")
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
