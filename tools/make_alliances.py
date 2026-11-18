"""Mechanic "Альянсы" (docs/global_mechanics/Alliances.md): three start factions, joining only through decisions and events, the cooperation scale of an alliance,
tier spirits, puppets always in the alliance of their overlord, ideology-change events, change of a puppet's course, AI rules. Founding ("create faction") and inviting stay VANILLA buttons with our conditions;
joining by request, leaving and expelling go through decisions / events.
Values, names and texts are mostly INVENTED (docs/lore/Invented-Lore.md, section "Альянсы"); the author's rules are in docs/global_mechanics/Alliances.md.
Writes: common/scripted_triggers|scripted_effects|on_actions|ideas|decisions(+categories)|scripted_localisation/ktits_alliance*.txt, events/ktits_alliance_events.txt,
localisation ru/en ktits_alliance_l_*.yml, interface/ktits_alliance.gui|gfx + gfx/interface/ktits/ally_*.png (scale bar), common/scripted_guis/ktits_alliance.txt; patches the mod copies of
common/scripted_triggers/diplomacy_scripted_triggers.txt (join blocked, offer join with our conditions, leave / kick) and common/factions/templates/*.txt (vanilla templates invisible; our template is visible to allowed founders).
The scripted trigger ktits_ai_ally_locked is used by tools/make_focuses.py (AI weights of the politics branch).
Usage: python tools/make_alliances.py [--mod PATH]
"""
import argparse, re
from pathlib import Path
import lore_data as L

# ---------------- data (docs/global_mechanics/Alliances.md) ----------------
GROUPS = ["democratic", "theology", "neutrality", "fascism", "communism", "casuality"]
GRP_RU = {"democratic": "Демократия", "theology": "Теология", "neutrality": "Диктатура", "fascism": "Фашизм", "communism": "Коммунизм", "casuality": "Казуальность"}
# world tension (threat) thresholds by the ideology group of the alliance leader (author: democracy 40, theology 35, casuality 0; the rest invented)
TENSION = {"democratic": 0.40, "theology": 0.35, "neutrality": 0.30, "fascism": 0.20, "communism": 0.10, "casuality": 0.0}
# the scale of every new alliance (INVENTED, docs/lore/Invented-Lore.md); a lone alliance (only the leader) is dissolved after LONE_DAYS (INVENTED)
START_COOP = 20
LONE_DAYS = 60
EVENT_TXT = {   # event number -> group -> text (docs/global_mechanics/Alliances.md, section "Тексты событий по идеологиям")
    1: {  # "Стук в дверь", to the leader
        "democratic": "Посол привёз прошение, заверенное парламентом, сенатом и тремя комиссиями. Союзники соберут голосование — когда-нибудь.",
        "theology": "Делегация в белых одеждах просит принять их под общий покров веры. Советники уже ищут подходящий стих в писании.",
        "neutrality": "Генерал соседней страны лично привёз письмо и стоит у дверей, не снимая фуражки. Вопрос простой: свой он или нет.",
        "fascism": "Под окнами штаба марширует чужой оркестр. Посол требует принять их немедленно — на правах «братского народа».",
        "communism": "Товарищи из-за границы прислали телеграмму: «Готовы к мировой революции. Ждём указаний». Партком собирается на внеочередное заседание.",
        "casuality": "Посол пришёл, сел у входа и уснул. Когда проснётся — спросим, чего он хотел. Скорее всего, того же, что и мы: ничего."},
    3: {  # "Чужая среди своих", to the member that changed the ideology (text by the ideology of the alliance)
        "democratic": "На заседании союзников наш представитель впервые голосует не так, как все. Неловкая тишина длится дольше гимна.",
        "theology": "Союзные проповедники объявили наших новых правителей заблудшими. Дипломаты не знают, каяться или уходить.",
        "neutrality": "Соседние генералы перестали приглашать нашего министра на охоту. Это плохой знак.",
        "fascism": "В штабе союза наш флаг повесили вверх ногами. Говорят, случайно. Никто не верит.",
        "communism": "Товарищи по Интернационалу называют нас «уклонистами». Это слово у них звучит страшнее, чем «враг».",
        "casuality": "Мы снова начали работать — союзники смотрят на нас с ужасом, как на заболевших."},
    4: {  # "Чужой в доме", to the leader
        "democratic": "Союзник сменил курс, но формально нарушений нет. Юристы просят время на изучение вопроса — год-два.",
        "theology": "В нашем общем храме молится чужак. Старейшины требуют решения: изгнать или терпеть ради мира.",
        "neutrality": "Союзник больше не смотрит нам в глаза. Генералы предлагают простое решение — указать ему на дверь.",
        "fascism": "В строю появился тот, кто шагает не в ногу. Строй этого не прощает.",
        "communism": "В рядах Интернационала завелись ревизионисты. Партийная чистка или пролетарская терпимость?",
        "casuality": "Один из союзников вдруг начал суетиться. Это заразно — надо решать, пока остальные не проснулись."},
}
CAT_TXT = {   # description of the category "Альянс" by the ideology of the alliance
    "democratic": "Союз свободных народов: решения принимаются долго, зато все довольны процедурой.",
    "theology": "Союз единоверцев: общие молитвы, общие враги, общий взгляд на небо.",
    "neutrality": "Союз сильных рук: каждый правит у себя, но держатся вместе.",
    "fascism": "Союз марширующих: один шаг, один голос, одна цель.",
    "communism": "Союз трудящихся: общие заводы, общие лозунги, общая будущая революция.",
    "casuality": "Союз отдыхающих: никто никуда не спешит, но все почему-то вместе."}
CAT_NONE = "Своей стране вне союза одиноко: альянс можно основать кнопкой «Создать фракцию» в дипломатии (великим и средним державам), а можно попроситься в чужой, когда мир станет достаточно опасным."
# tier spirits by the cooperation scale: name, lore text [invented], research sharing bonus per member, doctrine cost factor, experience per day (author: docs table "Баффы")
TIERS = [
    ("t1", "k1", "Дружба на бумаге", "Совместное безделье", 0.0, 0.0, 0.0,
     "Союзники подписали все бумаги и теперь не знают, что с ними делать. Дружба существует, но пока только в архиве.",
     "Мы условились ничего не делать вместе, и пока это отлично получается. Договор лежит где-то под подушкой."),
    ("t2", "k2", "Общие планы", "Ленивая солидарность", 0.05, -0.05, 0.0,
     "Генштабы обменялись планами и обнаружили, что они почти одинаковые. Это радует: не придётся ничего согласовывать.",
     "Мы разделяем взгляды на безделье и иногда даже кивком это подтверждаем. Солидарность дошла до обмена зевками."),
    ("t3", "k3", "Братство по оружию", "Общий туман", 0.10, -0.10, 0.0,
     "Союзные офицеры вместе ужинают, вместе спорят о доктринах и вместе забывают, из-за чего поспорили. Знания переходят из рук в руки быстрее, чем документы.",
     "Над землями союзников стелется общий туман: в нём так уютно, что чужие знания доходят сами, без почты и курьеров."),
    ("t4", "k4", "Единый штаб", "Единое болото", 0.15, -0.15, 0.05,
     "Карты союзников сложены в одну, а генералы пьют чай из одного самовара. Учения идут как по маслу, и опыт делится на всех.",
     "Все союзники стоят по колено в одном болоте и чувствуют единство. Опыт передаётся сам собой: достаточно постоять рядом."),
]
# cooperation decisions: key, name, text (doc, with the effect added), cost PP, cooldown days, effect tag
COOP = [
    ("ktits_ally_drills", "Совместные учения", "Армии союзников выходят на общие манёвры. Шкала сотрудничества растёт на 5, армия получает 10 опыта.", 50, 120, "drills"),
    ("ktits_ally_scientists", "Обмен учёными", "Лаборатории союзников открывают двери друг для друга. Шкала сотрудничества растёт на 5, в страну приезжают 2 тысячи иностранных специалистов.", 50, 180, "scientists"),
    ("ktits_ally_fund", "Общий фонд", "Союзники складываются на общее дело. Шкала сотрудничества растёт на 10, но казна инициатора теряет 100 единиц политического веса.", 100, 365, "fund"),
    ("ktits_ally_hq", "Объединённый штаб", "Генералы союзников садятся за один стол с одной картой. Шкала сотрудничества растёт на 5, планирование ускоряется на 180 дней.", 75, 180, "hq"),
    ("ktits_ally_corridor", "Торговый коридор", "Между союзниками открывают беспошлинные пути: поезда идут без досмотра. Шкала сотрудничества растёт на 5, товары народного потребления дешевеют на 180 дней.", 75, 180, "corridor"),
    ("ktits_ally_blueprints", "Обмен чертежами", "Конструкторские бюро союзников делятся чертежами без патентов и обид. Шкала сотрудничества растёт на 5, одна технология оборудования дешевеет вдвое.", 100, 240, "blueprints"),
    ("ktits_ally_festival", "Общий праздник", "По всему альянсу отмечают день союза: парады, речи и бесплатный чай. Шкала сотрудничества растёт на 5, а стабильность у инициатора растёт на 90 дней.", 50, 365, "festival"),
]
# timed spirits of the cooperation decisions: key -> (name, text [invented], modifiers, picture)
TIMED = {
    "ktits_ally_i_hq": ("Единая карта", "Одна карта на всех, и планировщики впервые не спорят, чей красный карандаш главнее.", "planning_speed = 0.05"),
    "ktits_ally_i_corridor": ("Беспошлинные поезда", "Составы идут через границы без досмотра, и даже таможенники катаются бесплатно.", "consumer_goods_factor = -0.02"),
    "ktits_ally_i_festival": ("День союза", "Парады, речи и бесплатный чай: страна довольна и охотно прощает власти мелкие грехи.", "stability_factor = 0.03"),
    "ktits_ally_i_course": ("Новый курс на подходе", "Из столицы сюзерена прибыли советники с папками, и теперь весь аппарат учится говорить на чужом политическом языке.", None),
}
POL_SPIRITS_FILE = "common/ideas/ktits_pol_ideas.txt"

def T(s, **kw):
    for k, v in kw.items():
        s = s.replace("@" + k + "@", str(v))
    return s

def pct(v):
    return ("%.2f" % v).rstrip("0").rstrip(".") if v else "0"

# the founder of an alliance must be a major power (vanilla is_major) or have at least this many factories (INVENTED, docs/lore/Invented-Lore.md)
FOUND_FACTORIES = 30
# countries with the spirit "Вечный нейтралитет" from the start (author's rule): Figaria, Ledyshka, Aidalia
NEUTRAL_LORE = ("FIG", "LED", "ADL")
# countries with the spirit "Бакинская пороховая бочка" from the start (author's rule): Dalmiria, Rashidia, Transildavia, Macedorea (Z01-Z04) and Aragonia (Z06).
# For now the spirit works exactly like Eternal Neutrality (a placeholder for a future mechanic); both are checked through the trigger ktits_ally_barred
BAKU_LORE = ("Z01", "Z02", "Z03", "Z04", "Z06")

def build(M, lore2tag):
    KAZ = lore2tag["CSL"]
    out = {}
    def w(rel, text):
        out[rel] = text

    # ---------------- scripted triggers ----------------
    tr = "# docs/global_mechanics/Alliances.md. Generated by tools/make_alliances.py\n"
    tr += "# world tension (threat 0..1) needed to join an alliance, by the ideology group of the alliance leader; scope = the leader\nktits_ally_tension_ok = {\n\tOR = {\n"
    for g in GROUPS:
        tr += ("\t\thas_government = casuality\n" if g == "casuality" else f"\t\tAND = {{\n\t\t\thas_government = {g}\n\t\t\tNOT = {{ threat < {TENSION[g]:.2f} }}\n\t\t}}\n")
    tr += "\t}\n}\n\n"
    tr += "# ROOT and FROM have the same ruling ideology group (subtypes of one group count as one ideology)\nktits_ally_group_match = {\n\tOR = {\n"
    for g in GROUPS:
        tr += f"\t\tAND = {{\n\t\t\thas_government = {g}\n\t\t\tFROM = {{ has_government = {g} }}\n\t\t}}\n"
    tr += "\t}\n}\n\n"
    tr += "# ROOT = the alliance leader that invites, FROM = the candidate: the candidate is at war with a country that is at war with ROOT too (invitation across ideologies)\nktits_ally_common_enemy = {\n\tany_country = {\n\t\thas_war_with = ROOT\n\t\thas_war_with = FROM\n\t}\n}\n\n"
    tr += "# author's rule: a country with the ruling ideology Casuality never joins an alliance whose leader is not Casuality. ROOT = the leader, FROM = the candidate\nktits_ally_kaz_ok = {\n\tOR = {\n\t\thas_government = casuality\n\t\tFROM = { NOT = { has_government = casuality } }\n\t}\n}\n\n"
    tr += "# scope = a member: it rules with Casuality and the leader of its alliance does not (author's rule, applies to puppets too; checked by ktits_ally_purge_kaz)\nktits_ally_kaz_excluded = {\n\thas_government = casuality\n\tis_in_faction = yes\n\tis_faction_leader = no\n\tany_allied_country = {\n\t\tis_faction_leader = yes\n\t\tNOT = { has_government = casuality }\n\t}\n}\n\n"
    tr += "# ROOT = the leader, FROM = the invited country: the same ideology group or a common enemy\nktits_ally_invite_match = {\n\tktits_ally_kaz_ok = yes\n\tOR = {\n\t\tktits_ally_group_match = yes\n\t\tktits_ally_common_enemy = yes\n\t}\n}\n\n"
    tr += "# any scope = a country: a spirit that bars founding, requesting, accepting and being invited to an alliance (Eternal Neutrality and, for now identical to it, Baku Powder Keg)\nktits_ally_barred = {\n\tOR = {\n\t\thas_idea = ktits_eternal_neutrality\n\t\thas_idea = ktits_baku_powder_keg\n\t}\n}\n\n"
    tr += ("# scope = a member that joined an alliance of ANOTHER ideology group through the common-enemy rule (flag ktits_ally_war_guest): the leader of its alliance is still at war with a country that is at war with the member\n"
           "# (inside any_country PREV = the leader, PREV.PREV = the member). When this stops being true the flag is cleared by ktits_ally_check_ideology and the ideology check applies again\n"
           "ktits_ally_war_guest_ok = {\n\tany_allied_country = {\n\t\tis_faction_leader = yes\n\t\tany_country = {\n\t\t\thas_war_with = PREV\n\t\t\thas_war_with = PREV.PREV\n\t\t}\n\t}\n}\n\n")
    tr += ("# scope = the founder: a major power or a medium one (at least %d factories), outside any alliance, not a subject, without Eternal Neutrality or Baku Powder Keg. The vanilla template ktits_alliance_template is visible only when it holds, so the vanilla button \"create faction\" works only for allowed founders\nktits_ally_can_found = {\n\tcustom_trigger_tooltip = {\n\t\ttooltip = ktits_ally_can_found_tt\n\t\tOR = {\n\t\t\tis_major = yes\n\t\t\tnum_of_factories > %d\n\t\t}\n\t}\n"
           "\tis_in_faction = no\n\tis_subject = no\n\tNOT = { ktits_ally_barred = yes }\n\t# an AI alliance dissolved as lone cannot be founded again for a year (a human can)\n\tOR = {\n\t\tis_ai = no\n\t\tNOT = { has_country_flag = ktits_ally_lone_fail }\n\t}\n}\n\n" % (FOUND_FACTORIES, FOUND_FACTORIES - 1))
    tr += "# ROOT (overlord) and FROM (its subject) have different ruling ideology groups\nktits_ally_course_needed = {\n\tOR = {\n"
    for g in GROUPS:
        tr += f"\t\tAND = {{\n\t\t\thas_government = {g}\n\t\t\tFROM = {{ NOT = {{ has_government = {g} }} }}\n\t\t}}\n"
    tr += "\t}\n}\n\n"
    tr += "# the leader of my alliance rules with another ideology group than I do (me = a member)\nktits_ally_has_foreign_leader = {\n\tOR = {\n"
    for g in GROUPS:
        tr += f"\t\tAND = {{\n\t\t\thas_government = {g}\n\t\t\tany_allied_country = {{\n\t\t\t\tis_faction_leader = yes\n\t\t\t\tNOT = {{ has_government = {g} }}\n\t\t\t}}\n\t\t}}\n"
    tr += "\t}\n}\n\n"
    for g in GROUPS:
        tr += (f"# the alliance of the country (own or as a member) is led by a ruler of the group {g}\nktits_ally_lead_{g} = {{\n\tOR = {{\n"
               f"\t\tAND = {{\n\t\t\tis_faction_leader = yes\n\t\t\thas_government = {g}\n\t\t}}\n"
               f"\t\tany_allied_country = {{\n\t\t\tis_faction_leader = yes\n\t\t\thas_government = {g}\n\t\t}}\n\t}}\n}}\n\n")
    tr += "# a leader of the same ideology group as mine already exists (the AI then asks to join instead of founding)\nktits_ally_same_group_leader_exists = {\n\tOR = {\n"
    for g in GROUPS:
        tr += f"\t\tAND = {{\n\t\t\thas_government = {g}\n\t\t\tany_country = {{\n\t\t\t\tis_faction_leader = yes\n\t\t\t\thas_government = {g}\n\t\t\t}}\n\t\t}}\n"
    tr += "\t}\n}\n\n"
    tr += ("# author's rule: an AI country in an alliance with at least one independent member does not change its ideology (used in the AI weights of tools/make_focuses.py)\n"
           "ktits_ai_ally_locked = {\n\tis_in_faction = yes\n\tany_allied_country = { is_subject = no }\n}\n\n")
    tr += f"# the alliance of Kazualia (leader or member): the scale is always 100, cooperation decisions are not needed\nktits_ally_in_kaz = {{\n\tOR = {{\n\t\tktits_is_kazualia = yes\n\t\tis_in_faction_with = {KAZ}\n\t}}\n}}\n"
    w("common/scripted_triggers/ktits_alliance_triggers.txt", tr)

    # ---------------- scripted effects ----------------
    spirits = ["ktits_ally_t%d" % i for i in range(1, 5)] + ["ktits_ally_k%d" % i for i in range(1, 5)]
    ef = "# docs/global_mechanics/Alliances.md. Generated by tools/make_alliances.py. Scripted effects have no parameters here (a parametrised call broke loading before), so every delta has its own effect.\n\n"
    ef += "# scope = any country: removes the cooperation tier spirits\nktits_ally_clear_spirits = {\n"
    for s in spirits:
        ef += f"\tif = {{ limit = {{ has_idea = {s} }} remove_ideas = {s} }}\n"
    ef += "}\n\n"
    ef += ("# scope = a member; ktits_ally_tier (1..4) and ktits_ally_kz (1 = the alliance of Kazualia) were set by the leader\nktits_ally_apply = {\n\tktits_ally_clear_spirits = yes\n")
    for i in range(1, 5):
        ef += (f"\tif = {{\n\t\tlimit = {{ check_variable = {{ var = ktits_ally_tier value = {i} compare = equals }} }}\n"
               f"\t\tif = {{\n\t\t\tlimit = {{ check_variable = {{ var = ktits_ally_kz value = 1 compare = equals }} }}\n\t\t\tadd_ideas = ktits_ally_k{i}\n\t\t}}\n"
               f"\t\telse = {{ add_ideas = ktits_ally_t{i} }}\n\t}}\n")
    ef += "}\n\n"
    ef += ("# scope = the LEADER of an alliance: clamps the scale (Kazualia: always 100), gives every member (the leader included) the tier spirit and the value for the category text\n"
           "ktits_ally_update = {\n\tif = {\n\t\tlimit = { ktits_is_kazualia = yes }\n\t\tset_variable = { var = ktits_alliance_coop value = 100 }\n\t}\n"
           "\tclamp_variable = { var = ktits_alliance_coop min = 0 max = 100 }\n"
           "\tset_temp_variable = { ktits_ally_t_coop = ktits_alliance_coop }\n\tset_temp_variable = { ktits_ally_t_tier = 1 }\n\tset_temp_variable = { ktits_ally_t_kz = 0 }\n"
           "\tif = { limit = { ktits_is_kazualia = yes } set_temp_variable = { ktits_ally_t_kz = 1 } }\n")
    for i, lo in ((2, 25), (3, 50), (4, 75)):
        ef += f"\tif = {{\n\t\tlimit = {{ check_variable = {{ var = ktits_alliance_coop value = {lo} compare = greater_than_or_equals }} }}\n\t\tset_temp_variable = {{ ktits_ally_t_tier = {i} }}\n\t}}\n"
    own = ("set_variable = { var = ktits_ally_view value = ktits_ally_t_coop }\n\t\tset_variable = { var = ktits_ally_tier value = ktits_ally_t_tier }\n"
           "\t\tset_variable = { var = ktits_ally_kz value = ktits_ally_t_kz }\n\t\tktits_ally_apply = yes\n")
    ef += "\t" + own.replace("\n\t\t", "\n\t")
    ef += "\tevery_faction_member = {\n\t\t" + own + "\t}\n}\n\n"
    ef += "# leader scope: scale changes. Every positive change also marks the alliance as active this month (no cooling)\n"
    for name, d, busy in (("p5", 5, True), ("p10", 10, True), ("m5", -5, False), ("m20", -20, False)):
        ef += (f"ktits_ally_coop_{name} = {{\n\tadd_to_variable = {{ var = ktits_alliance_coop value = {d} }}\n"
               + ("\tset_country_flag = ktits_ally_busy\n" if busy else "") + "\tktits_ally_update = yes\n}\n\n")
    ef += "# scope = a member (the leader too): the same changes on the leader of my alliance\n"
    for name in ("p5", "p10"):
        ef += (f"ktits_ally_member_coop_{name} = {{\n\tif = {{\n\t\tlimit = {{ is_faction_leader = yes }}\n\t\tktits_ally_coop_{name} = yes\n\t}}\n"
               f"\telse = {{\n\t\tevery_other_country = {{\n\t\t\tlimit = {{\n\t\t\t\tis_faction_leader = yes\n\t\t\t\tis_in_faction_with = PREV\n\t\t\t}}\n\t\t\tktits_ally_coop_{name} = yes\n\t\t}}\n\t}}\n}}\n\n")
    ef += ("# scope = a member that leaves or is expelled for a change of ideology: the leader forgets one member, so the monthly check does not take the author's -5\n"
           "ktits_ally_forget_member = {\n\tevery_other_country = {\n\t\tlimit = {\n\t\t\tis_faction_leader = yes\n\t\t\tis_in_faction_with = PREV\n\t\t}\n\t\tadd_to_variable = { var = ktits_ally_size value = -1 }\n\t}\n}\n\n")
    ef += "# scope = any country at the start of the game: no alliance exists at the start (author's decision), all are founded with the vanilla button. Here: spirits of neutral and powder-keg countries, subject sync, purge of barred\nktits_ally_start = {\n"
    for lt in NEUTRAL_LORE:
        t = lore2tag.get(lt)
        if t:
            ef += f"\tif = {{\n\t\tlimit = {{ country_exists = {t} }}\n\t\t{t} = {{\n\t\t\tadd_ideas = ktits_eternal_neutrality\n\t\t}}\n\t}}\n"
    for lt in BAKU_LORE:
        t = lore2tag.get(lt)
        if t:
            ef += f"\tif = {{\n\t\tlimit = {{ country_exists = {t} }}\n\t\t{t} = {{\n\t\t\tadd_ideas = ktits_baku_powder_keg\n\t\t}}\n\t}}\n"
    ef += "\tevery_country = {\n\t\tktits_ally_allow_found = yes\n\t\tktits_ally_purge_barred = yes\n\t\tktits_ally_purge_kaz = yes\n\t\tktits_ally_sync_subjects = yes\n\t}\n}\n\n"
    ef += "# scope = any country: the engine rule can_create_factions is off by default (vanilla gives it with spirits and focuses removed from the mod); every country gets it, who may found is decided by the template trigger ktits_ally_can_found. Monthly too: released countries appear later\nktits_ally_allow_found = {\n\tset_rule = {\n\t\tcan_create_factions = yes\n\t}\n}\n\n"
    ef += ("# scope = an overlord: its subjects are always in its alliance (author's rule). Scope inside: the subject, PREV = the overlord. Subjects cannot leave (the diplomacy trigger is blocked), the monthly check repairs the rest\n"
           "ktits_ally_sync_subjects = {\n\tevery_subject_country = {\n\t\tif = {\n\t\t\tlimit = {\n\t\t\t\tPREV = { is_in_faction = no }\n\t\t\t\tis_in_faction = yes\n\t\t\t}\n\t\t\tleave_faction = yes\n\t\t}\n"
           "\t\tif = {\n\t\t\tlimit = {\n\t\t\t\tPREV = { is_in_faction = yes }\n\t\t\t\tNOT = { is_in_faction_with = PREV }\n\t\t\t}\n\t\t\tif = {\n\t\t\t\tlimit = { is_in_faction = yes }\n\t\t\t\tleave_faction = yes\n\t\t\t}\n"
           "\t\t\tif = {\n\t\t\t\tlimit = {\n\t\t\t\t\tNOT = { ktits_ally_barred = yes }\n\t\t\t\t\t# author's rule: a Casuality subject does not enter the alliance of a non-Casuality overlord\n\t\t\t\t\tOR = {\n\t\t\t\t\t\tNOT = { has_government = casuality }\n\t\t\t\t\t\tPREV = { has_government = casuality }\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t\tPREV = { add_to_faction = PREV }\n\t\t\t}\n\t\t}\n\t}\n}\n\n")
    ef += ("# scope = any country: a country with Eternal Neutrality or Baku Powder Keg is never a member of an alliance (the engine puts subjects into the faction of the overlord by itself, so the check runs on startup and monthly)\n"
           "ktits_ally_purge_barred = {\n\tif = {\n\t\tlimit = {\n\t\t\tktits_ally_barred = yes\n\t\t\tis_in_faction = yes\n\t\t\tis_faction_leader = no\n\t\t}\n\t\tktits_ally_forget_member = yes\n\t\tleave_faction = yes\n\t}\n}\n\n")
    ef += ("# scope = any country: author's rule, a country that rules with Casuality is never a member of an alliance led by a non-Casuality leader (an exception to \"subjects are always in the alliance of the overlord\"): leaves, also after a change of ideology to Casuality\n"
           "ktits_ally_purge_kaz = {\n\tif = {\n\t\tlimit = { ktits_ally_kaz_excluded = yes }\n\t\tktits_ally_forget_member = yes\n\t\tktits_ally_news_leave = yes\n\t\tleave_faction = yes\n\t}\n}\n\n")
    ef += ("# scope = a member: a ruling ideology group that differs from the leader's -> the event \"Чужая среди своих\" (once per difference; the flag is dropped when the groups match again or the country leaves).\n"
           "# A guest of the common-enemy rule (flag ktits_ally_war_guest, set on joining across ideologies) is skipped while the shared war lasts; the flag is cleared first when the war is over or the country left\n"
           "ktits_ally_check_ideology = {\n\tif = {\n\t\tlimit = {\n\t\t\thas_country_flag = ktits_ally_war_guest\n\t\t\tOR = {\n\t\t\t\tis_in_faction = no\n\t\t\t\tNOT = { ktits_ally_war_guest_ok = yes }\n\t\t\t}\n\t\t}\n\t\tclr_country_flag = ktits_ally_war_guest\n\t}\n"
           "\tif = {\n\t\tlimit = {\n\t\t\tis_in_faction = yes\n\t\t\tis_faction_leader = no\n\t\t\tNOT = { has_country_flag = ktits_ally_alien }\n\t\t\tNOT = { has_country_flag = ktits_ally_war_guest }\n\t\t\tktits_ally_has_foreign_leader = yes\n\t\t}\n"
           "\t\tset_country_flag = ktits_ally_alien\n\t\tcountry_event = { id = ktits_alliance.3 }\n\t}\n"
           "\tif = {\n\t\tlimit = {\n\t\t\thas_country_flag = ktits_ally_alien\n\t\t\tOR = {\n\t\t\t\tis_in_faction = no\n\t\t\t\tNOT = { ktits_ally_has_foreign_leader = yes }\n\t\t\t}\n\t\t}\n\t\tclr_country_flag = ktits_ally_alien\n\t}\n}\n\n")
    ef += ("# scope = the leader, once a month. Members beyond the leader +1 each; a common war +2; no war and no cooperation decision -1; a member lost without the ideology flow -5 each. Kazualia: always 100\n"
           "ktits_ally_leader_monthly = {\n\tset_variable = { var = ktits_ally_n value = 0 }\n\tevery_faction_member = {\n\t\tlimit = { is_faction_leader = no }\n\t\tPREV = { add_to_variable = { var = ktits_ally_n value = 1 } }\n\t}\n"
           "\tif = {\n\t\tlimit = { NOT = { ktits_is_kazualia = yes } }\n"
           "\t\tif = {\n\t\t\tlimit = { check_variable = { var = ktits_ally_n value = ktits_ally_size compare = less_than } }\n"
           "\t\t\tset_variable = { var = ktits_ally_d value = ktits_ally_size }\n\t\t\tsubtract_from_variable = { var = ktits_ally_d value = ktits_ally_n }\n\t\t\tmultiply_variable = { var = ktits_ally_d value = -5 }\n"
           "\t\t\tadd_to_variable = { var = ktits_alliance_coop value = ktits_ally_d }\n\t\t}\n"
           "\t\tadd_to_variable = { var = ktits_alliance_coop value = ktits_ally_n }\n"
           "\t\tif = {\n\t\t\tlimit = { has_war = yes }\n\t\t\tif = {\n\t\t\t\tlimit = { any_allied_country = { has_war_together_with = PREV } }\n\t\t\t\tadd_to_variable = { var = ktits_alliance_coop value = 2 }\n\t\t\t}\n\t\t}\n"
           "\t\telse = {\n\t\t\tif = {\n\t\t\t\tlimit = { NOT = { has_country_flag = ktits_ally_busy } }\n\t\t\t\tadd_to_variable = { var = ktits_alliance_coop value = -1 }\n\t\t\t}\n\t\t}\n\t}\n"
           "\tclr_country_flag = ktits_ally_busy\n\tset_variable = { var = ktits_ally_size value = ktits_ally_n }\n\tktits_ally_update = yes\n}\n\n")
    ef += ("# on_monthly, scope = every country\nktits_ally_monthly = {\n\tktits_ally_allow_found = yes\n\tktits_ally_purge_barred = yes\n\tktits_ally_purge_kaz = yes\n\tktits_ally_sync_subjects = yes\n\tktits_ally_check_ideology = yes\n"
           "\t# a former leader: the scale is not its own any more\n\tif = {\n\t\tlimit = {\n\t\t\thas_country_flag = ktits_ally_keeper\n\t\t\tis_faction_leader = no\n\t\t}\n"
           "\t\tclr_country_flag = ktits_ally_keeper\n\t\tset_variable = { var = ktits_alliance_coop value = 0 }\n\t\tset_variable = { var = ktits_ally_size value = 0 }\n\t}\n"
           "\tif = {\n\t\tlimit = {\n\t\t\tis_faction_leader = yes\n\t\t\thas_country_flag = ktits_ally_keeper\n\t\t}\n\t\tktits_ally_leader_monthly = yes\n\t}\n"
           "\tif = {\n\t\tlimit = { is_in_faction = no }\n\t\tktits_ally_clear_spirits = yes\n\t\tset_variable = { var = ktits_ally_view value = 0 }\n\t}\n}\n\n")
    # puppet course change: runs in the puppet at the end of the 90 days
    pol = Path(M / POL_SPIRITS_FILE)
    pol_sp = sorted(set(re.findall(r"(?m)^\t\t(ktits_pol_sp_\w+) = \{", pol.read_text(encoding="utf-8")))) if pol.exists() else []
    ef += "# scope = the puppet (event ktits_alliance.5): the party of the overlord's ideology group comes to power, popularity +40 %, stability -10 %; the Political Course branch of the generic tree is reset\nktits_ally_course_apply = {\n"
    for g in GROUPS:
        ef += (f"\tif = {{\n\t\tlimit = {{ any_other_country = {{ has_subject = ROOT has_government = {g} }} }}\n"
               f"\t\tadd_popularity = {{ ideology = {g} popularity = 0.4 }}\n\t\tset_politics = {{ ruling_party = {g} }}\n\t}}\n")
    ef += "\tadd_stability = -0.10\n\tif = {\n\t\tlimit = { has_focus_tree = generic_focus }\n"
    for s in pol_sp:
        ef += f"\t\tif = {{ limit = {{ has_idea = {s} }} remove_ideas = {s} }}\n"
    ef += "\t\tuncomplete_national_focus = {\n\t\t\tfocus = ktits_pol_root\n\t\t\tuncomplete_children = yes\n\t\t}\n\t}\n}\n"
    ef += ("\n# scope = a country that has just joined: the other members get the news (FROM = the newcomer)\nktits_ally_news_join = {\n\tevery_other_country = {\n\t\tlimit = { is_in_faction_with = PREV }\n\t\tcountry_event = { id = ktits_alliance.8 }\n\t}\n}\n"
           "\n# scope = a member that leaves (before leave_faction): the other members get the news (FROM = the leaver)\nktits_ally_news_leave = {\n\tevery_other_country = {\n\t\tlimit = { is_in_faction_with = PREV }\n\t\tcountry_event = { id = ktits_alliance.9 }\n\t}\n}\n")
    ef += "\n" + """# scope = the LEADER of an alliance that has just been taken over (no flag ktits_ally_keeper, but its members were counted before): the scale passes from the copy ktits_ally_view (last month), no -5 for the members counted by the old leader
ktits_ally_leader_changed = {
	set_country_flag = ktits_ally_keeper
	set_variable = { var = ktits_ally_n value = 0 }
	every_faction_member = {
		limit = { is_faction_leader = no }
		set_country_flag = ktits_ally_member
		PREV = { add_to_variable = { var = ktits_ally_n value = 1 } }
	}
	set_variable = { var = ktits_alliance_coop value = ktits_ally_view }
	set_variable = { var = ktits_ally_size value = ktits_ally_n }
	every_faction_member = {
		country_event = { id = ktits_alliance.6 }
	}
}

# scope = the leader of a NEW alliance (founded with the vanilla button): the scale starts at the start value, the timer of a lone alliance starts
ktits_ally_new_alliance = {
	set_country_flag = ktits_ally_keeper
	set_country_flag = ktits_ally_lone_armed
	set_country_flag = { flag = ktits_ally_lone_wait value = 1 days = LONE_DAYS }
	set_variable = { var = ktits_alliance_coop value = START_COOP }
	set_variable = { var = ktits_ally_size value = 0 }
	ktits_ally_update = yes
}

# scope = a member found in the faction without the flag ktits_ally_member (joined by the vanilla invitation or by the request decision), PREV = the leader
# +5 to the scale; the first member gives the founder the event "Альянс основан", the next ones the news "Новый союзник" to everybody; a guest of another ideology group (not a puppet) gets the common-enemy flag
ktits_ally_newcomer = {
	set_country_flag = ktits_ally_member
	if = {
		limit = {
			is_subject = no
			ktits_ally_has_foreign_leader = yes
		}
		set_country_flag = ktits_ally_war_guest
	}
	PREV = { ktits_ally_coop_p5 = yes }
	if = {
		limit = { PREV = { check_variable = { var = ktits_ally_size value = 0 compare = equals } } }
		PREV = { country_event = { id = ktits_alliance.14 } }
	}
	else = {
		ktits_ally_news_join = yes
	}
	PREV = { add_to_variable = { var = ktits_ally_size value = 1 } }
}

# scope = the leader that dissolves its alliance: spirits, flags and variables are cleaned, then dismantle_faction
ktits_ally_dissolve = {
	every_faction_member = {
		ktits_ally_clear_spirits = yes
		set_variable = { var = ktits_ally_view value = 0 }
		clr_country_flag = ktits_ally_member
		clr_country_flag = ktits_ally_alien
		clr_country_flag = ktits_ally_war_guest
	}
	clr_country_flag = ktits_ally_keeper
	clr_country_flag = ktits_ally_lone_armed
	clr_country_flag = ktits_ally_lone_wait
	set_variable = { var = ktits_alliance_coop value = 0 }
	set_variable = { var = ktits_ally_size value = 0 }
	dismantle_faction = yes
}

# scope = the leader: the scale fell to 0, the alliance dissolves itself; every member gets the event (event 15)
ktits_ally_dissolve_zero = {
	every_faction_member = {
		country_event = { id = ktits_alliance.15 }
	}
	ktits_ally_dissolve = yes
}

# scope = the leader: nobody joined for LONE_DAYS days, the alliance dissolves; the leader gets the event (event 16); a dissolved AI alliance cannot be founded again for a year
ktits_ally_dissolve_lone = {
	country_event = { id = ktits_alliance.16 }
	set_country_flag = { flag = ktits_ally_lone_fail value = 1 days = 365 }
	ktits_ally_dissolve = yes
}

# on_daily, scope = every country. The leader: a new alliance (founded with the vanilla button) or a taken-over one, newcomers, a lone alliance scale 0 (Kazualia is fixed at 100).
# Everybody: the flag ktits_ally_member (= counted by the leader) is dropped when the country left or leads
ktits_ally_track = {
	if = {
		limit = { is_faction_leader = yes }
		if = {
			limit = { NOT = { has_country_flag = ktits_ally_keeper } }
			if = {
				limit = {
					OR = {
						has_country_flag = ktits_ally_member
						any_other_country = {
							is_in_faction_with = ROOT
							has_country_flag = ktits_ally_member
						}
					}
				}
				ktits_ally_leader_changed = yes
			}
			else = {
				ktits_ally_new_alliance = yes
			}
		}
		every_faction_member = {
			limit = {
				is_faction_leader = no
				NOT = { has_country_flag = ktits_ally_member }
			}
			ktits_ally_newcomer = yes
		}
		if = {
			limit = {
				NOT = { num_faction_members > 1 }
			}
			if = {
				limit = { NOT = { has_country_flag = ktits_ally_lone_armed } }
				set_country_flag = ktits_ally_lone_armed
				set_country_flag = { flag = ktits_ally_lone_wait value = 1 days = LONE_DAYS }
			}
			else_if = {
				limit = { NOT = { has_country_flag = ktits_ally_lone_wait } }
				ktits_ally_dissolve_lone = yes
			}
		}
		else = {
			clr_country_flag = ktits_ally_lone_armed
			clr_country_flag = ktits_ally_lone_wait
		}
		if = {
			limit = {
				has_country_flag = ktits_ally_keeper
				NOT = { ktits_is_kazualia = yes }
				check_variable = { var = ktits_alliance_coop value = 1 compare = less_than }
			}
			ktits_ally_dissolve_zero = yes
		}
	}
	if = {
		limit = {
			has_country_flag = ktits_ally_member
			OR = {
				is_in_faction = no
				is_faction_leader = yes
			}
		}
		clr_country_flag = ktits_ally_member
	}
}
""".replace("LONE_DAYS", str(LONE_DAYS)).replace("START_COOP", str(START_COOP))
    w("common/scripted_effects/ktits_alliance_effects.txt", ef)

    # ---------------- on_actions ----------------
    w("common/factions/templates/ktits_alliance_templates.txt",
      "# template of every Ktits alliance. Start alliances are made by script; the VANILLA button \"create faction\" offers it only to an allowed founder (ktits_ally_can_found); the name is typed by the player\n"
      "ktits_alliance_template = {\n\tname = ktits_alliance_template_name\n\tmanifest = faction_manifest_strength_in_unity\n\tcan_leader_join_other_factions = no\n\ticon = GFX_faction_logo_generic\n"
      "\tvisible = {\n\t\tktits_ally_can_found = yes\n\t}\n\tavailable = {\n\t\talways = yes\n\t}\n\tgoals = {\n\t\tfaction_goal_a_military_base\n\t}\n}\n")

    w("common/on_actions/ktits_alliance_on_actions.txt",
      "on_actions = {\n\ton_startup = {\n\t\t# no country scope on startup: random_country gives one, the effect addresses the start leaders by tag and loops over all countries itself\n\t\teffect = {\n\t\t\trandom_country = {\n\t\t\t\tktits_ally_start = yes\n\t\t\t}\n\t\t}\n\t}\n"
      "\ton_monthly = {\n\t\teffect = {\n\t\t\tktits_ally_monthly = yes\n\t\t}\n\t}\n\ton_daily = {\n\t\teffect = {\n\t\t\tktits_ally_track = yes\n\t\t}\n\t}\n}\n")

    # ---------------- ideas ----------------
    idea = "# cooperation tiers (docs/global_mechanics/Alliances.md) and timed spirits of the cooperation decisions\nideas = {\n\tcountry = {\n"
    for t, k, n, kn, rs, dc, xp, d, kd in TIERS:
        for key in (f"ktits_ally_{t}", f"ktits_ally_{k}"):
            mod = ""
            if rs:
                mod += f"\t\t\t\tresearch_sharing_per_country_bonus = {pct(rs)}\n"
                for dk in ("land", "naval", "air"):
                    mod += f"\t\t\t\t{dk}_doctrine_cost_factor = {pct(dc)}\n"
            if xp:
                for ek in ("army", "navy", "air"):
                    mod += f"\t\t\t\texperience_gain_{ek} = {pct(xp)}\n"
            idea += (f"\t\t{key} = {{\n\t\t\tpicture = generic_research_bonus\n\t\t\tallowed = {{ always = no }}\n\t\t\tallowed_civil_war = {{ always = yes }}\n\t\t\tremoval_cost = -1\n"
                     f"\t\t\tmodifier = {{\n{mod}\t\t\t}}\n\t\t}}\n")
    for key, (n, d, mod) in TIMED.items():
        idea += (f"\t\t{key} = {{\n\t\t\tpicture = generic_research_bonus\n\t\t\tallowed = {{ always = no }}\n\t\t\tallowed_civil_war = {{ always = yes }}\n\t\t\tremoval_cost = -1\n"
                 f"\t\t\tmodifier = {{\n" + (f"\t\t\t\t{mod}\n" if mod else "") + "\t\t\t}\n\t\t}\n")
    idea += "\t}\n}\n"
    w("common/ideas/ktits_alliance_ideas.txt", idea)
    w("common/ideas/ktits_neutrality_ideas.txt", "# national spirit \"Вечный нейтралитет\" (author's rule): no founding of and no joining to alliances (the decisions check it)\nideas = {\n\tcountry = {\n\t\tktits_eternal_neutrality = {\n\t\t\tpicture = generic_neutrality_drift_bonus\n\t\t\tallowed = {\n\t\t\t\talways = no\n\t\t\t}\n\t\t\tremoval_cost = -1\n\t\t\tmodifier = {\n\t\t\t\tcustom_modifier_tooltip = ktits_eternal_neutrality_tt\n\t\t\t}\n\t\t}\n\t\t# national spirit Baku Powder Keg (author rule): for now works exactly like Eternal Neutrality, a placeholder for a future mechanic (the triggers check ktits_ally_barred)\n\t\tktits_baku_powder_keg = {\n\t\t\tpicture = generic_guerilla_warfare\n\t\t\tallowed = {\n\t\t\t\talways = no\n\t\t\t}\n\t\t\tremoval_cost = -1\n\t\t\tmodifier = {\n\t\t\t\tcustom_modifier_tooltip = ktits_baku_powder_keg_tt\n\t\t\t}\n\t\t}\n\t}\n}\n")
    # (the opinion modifier ktits_ally_insult was removed with the refusal events)
    pass

    # ---------------- decisions ----------------
    w("common/decisions/categories/ktits_alliance_categories.txt",
      "ktits_alliance_category = {\n\ticon = generic_propaganda\n\tpicture = GFX_decision_cat_picture_ktits_casuality\n\tscripted_gui = ktits_alliance_ui\n\tvisible = {\n\t\talways = yes\n\t}\n}\n")
    d = "ktits_alliance_category = {\n\n"
    d += T("""	ktits_ally_request = {
		icon = generic_propaganda
		visible = {
			is_in_faction = no
			is_subject = no
			NOT = { ktits_ally_barred = yes }
		}
		target_root_trigger = {
			is_in_faction = no
			is_subject = no
			NOT = { ktits_ally_barred = yes }
		}
		target_trigger = {
			FROM = {
				is_faction_leader = yes
			}
			ktits_ally_group_match = yes
		}
		available = {
			NOT = { has_country_flag = ktits_ally_refused }
			custom_trigger_tooltip = {
				tooltip = ktits_ally_tension_tt
				FROM = { ktits_ally_tension_ok = yes }
			}
		}
		cost = 50
		days_re_enable = 90
		fire_only_once = no
		complete_effect = {
			FROM = {
				country_event = { id = ktits_alliance.1 }
			}
		}
		ai_will_do = {
			base = 0
			modifier = {
				add = 6
				has_opinion = { target = FROM value > -1 }
				NOT = { has_war_with = FROM }
				NOT = { FROM = { any_allied_country = { has_war_with = ROOT } } }
			}
		}
	}

	ktits_ally_course = {
		icon = generic_propaganda
		visible = {
			NOT = { ktits_is_kazualia = yes }
		}
		target_root_trigger = {
			NOT = { ktits_is_kazualia = yes }
			any_subject_country = { always = yes }
		}
		target_trigger = {
			FROM = {
				is_subject_of = ROOT
				NOT = { has_idea = ktits_ally_i_course }
			}
			ktits_ally_course_needed = yes
		}
		cost = 75
		days_re_enable = 180
		fire_only_once = no
		complete_effect = {
			FROM = {
				add_timed_idea = { idea = ktits_ally_i_course days = 90 }
				country_event = { id = ktits_alliance.5 days = 90 }
			}
		}
		ai_will_do = {
			base = 5
			modifier = {
				factor = 0
				has_political_power < 100
			}
		}
	}

""")
    effects = {
        "drills": "\t\t\tarmy_experience = 10\n",
        "scientists": "\t\t\tcustom_effect_tooltip = ktits_ally_tt_for2\n\t\t\thidden_effect = {\n\t\t\t\tadd_to_variable = { var = ktits_spec_foreign value = 2 }\n\t\t\t\tktits_education_update = yes\n\t\t\t}\n",
        "fund": "\t\t\tadd_political_power = -100\n",
        "hq": "\t\t\tadd_timed_idea = { idea = ktits_ally_i_hq days = 180 }\n",
        "corridor": "\t\t\tadd_timed_idea = { idea = ktits_ally_i_corridor days = 180 }\n",
        "blueprints": "\t\t\tadd_tech_bonus = {\n\t\t\t\tname = ktits_ally_blueprints\n\t\t\t\tbonus = 0.5\n\t\t\t\tuses = 1\n\t\t\t\tcategory = infantry_weapons\n\t\t\t\tcategory = artillery\n\t\t\t\tcategory = armor\n\t\t\t}\n",
        "festival": "\t\t\tadd_timed_idea = { idea = ktits_ally_i_festival days = 90 }\n",
    }
    d += ("\tktits_ally_leave = {\n\t\ticon = generic_propaganda\n\t\tvisible = {\n\t\t\tis_in_faction = yes\n\t\t\tis_faction_leader = no\n\t\t\tis_subject = no\n\t\t}\n\t\tavailable = {\n\t\t\tis_in_faction = yes\n\t\t\tis_faction_leader = no\n\t\t\tis_subject = no\n\t\t}\n"
          "\t\tcost = 25\n\t\tdays_re_enable = 30\n\t\tfire_only_once = no\n\t\tcomplete_effect = {\n\t\t\tktits_ally_news_leave = yes\n\t\t\tleave_faction = yes\n\t\t}\n\t\tai_will_do = {\n\t\t\tbase = 0\n\t\t\tmodifier = {\n\t\t\t\tadd = 2\n\t\t\t\thas_country_flag = ktits_ally_alien\n\t\t\t}\n\t\t}\n\t}\n\n")
    for key, name, txt, cost, cd, tag in COOP:
        delta = "p10" if tag == "fund" else "p5"
        d += (f"\t{key} = {{\n\t\ticon = generic_propaganda\n\t\tvisible = {{\n\t\t\tis_in_faction = yes\n\t\t\tNOT = {{ ktits_ally_in_kaz = yes }}\n\t\t}}\n"
              f"\t\tavailable = {{\n\t\t\tis_in_faction = yes\n\t\t\tnum_faction_members > 1\n\t\t}}\n\t\tcost = {cost}\n\t\tdays_re_enable = {cd}\n\t\tfire_only_once = no\n\t\tcomplete_effect = {{\n"
              f"\t\t\tcustom_effect_tooltip = ktits_ally_tt_{delta}\n\t\t\thidden_effect = {{ ktits_ally_member_coop_{delta} = yes }}\n{effects[tag]}\t\t}}\n"
              f"\t\tai_will_do = {{\n\t\t\tbase = 3\n\t\t\tmodifier = {{\n\t\t\t\tfactor = 0\n\t\t\t\tcheck_variable = {{ var = ktits_ally_view value = 75 compare = greater_than_or_equals }}\n\t\t\t}}\n"
              f"\t\t\tmodifier = {{\n\t\t\t\tfactor = 0\n\t\t\t\thas_political_power < {cost + 25}\n\t\t\t}}\n\t\t}}\n\t}}\n\n")
    d += "}\n"
    w("common/decisions/ktits_alliance.txt", d)

    # ---------------- scripted localisation (category text by the alliance ideology) ----------------
    sl = "# docs/global_mechanics/Alliances.md, section \"Описание альянса\". Scope = the country that looks at the category\ndefined_text = {\n\tname = GetKtitsAllyDesc\n"
    for g in GROUPS:
        sl += f"\ttext = {{\n\t\ttrigger = {{ ktits_ally_lead_{g} = yes }}\n\t\tlocalization_key = ktits_ally_desc_{g}\n\t}}\n"
    sl += "\ttext = {\n\t\tlocalization_key = ktits_ally_desc_none\n\t}\n}\n"
    w("common/scripted_localisation/ktits_alliance_loc.txt", sl)

    # ---------------- events ----------------
    pic = "GFX_report_event_ktits_casuality"
    def descs(n, own_group):
        s = ""
        for g in GROUPS:
            cond = (f"has_government = {g}" if own_group else f"any_other_country = {{ is_faction_leader = yes is_in_faction_with = ROOT has_government = {g} }}")
            s += f"\tdesc = {{\n\t\ttext = ktits_alliance.{n}.d_{g}\n\t\ttrigger = {{ {cond} }}\n\t}}\n"
        return s + f"\tdesc = {{\n\t\ttext = ktits_alliance.{n}.d\n\t}}\n"
    ev = "add_namespace = ktits_alliance\n\n"
    ev += (f"# FROM = the country that asks for membership\ncountry_event = {{\n\tid = ktits_alliance.1\n\ttitle = ktits_alliance.1.t\n{descs(1, True)}\tpicture = {pic}\n\tis_triggered_only = yes\n\tfire_only_once = no\n\n"
           "\toption = {\n\t\tname = ktits_alliance.1.a\n\t\tai_chance = {\n\t\t\tbase = 100\n\t\t\tmodifier = {\n\t\t\t\tfactor = 0\n\t\t\t\tOR = {\n\t\t\t\t\thas_war_with = FROM\n\t\t\t\t\tany_allied_country = { has_war_with = FROM }\n\t\t\t\t\thas_opinion = { target = FROM value < 0 }\n\t\t\t\t}\n\t\t\t}\n\t\t}\n"
           "\t\tif = {\n\t\t\tlimit = { FROM = { is_in_faction = no } }\n\t\t\tadd_to_faction = FROM\n\t\t}\n\t}\n"
           "\toption = {\n\t\tname = ktits_alliance.1.b\n\t\tai_chance = {\n\t\t\tbase = 0\n\t\t\tmodifier = {\n\t\t\t\tadd = 100\n\t\t\t\tOR = {\n\t\t\t\t\thas_war_with = FROM\n\t\t\t\t\tany_allied_country = { has_war_with = FROM }\n\t\t\t\t\thas_opinion = { target = FROM value < 0 }\n\t\t\t\t}\n\t\t\t}\n\t\t}\n"
           "\t\tFROM = {\n\t\t\tset_country_flag = { flag = ktits_ally_refused value = 1 days = 180 }\n\t\t}\n\t}\n}\n\n")
    ev += (f"# a member's ruling ideology group differs from the leader's (puppets cannot leave)\ncountry_event = {{\n\tid = ktits_alliance.3\n\ttitle = ktits_alliance.3.t\n{descs(3, False)}\tpicture = {pic}\n\tis_triggered_only = yes\n\tfire_only_once = no\n\n"
           "\toption = {\n\t\tname = ktits_alliance.3.a\n\t\ttrigger = { is_subject = no }\n\t\tai_chance = {\n\t\t\tbase = 50\n\t\t}\n\t\tktits_ally_forget_member = yes\n\t\tclr_country_flag = ktits_ally_alien\n\t\tktits_ally_news_leave = yes\n\t\tleave_faction = yes\n\t}\n"
           "\toption = {\n\t\tname = ktits_alliance.3.b\n\t\tai_chance = {\n\t\t\tbase = 50\n\t\t}\n\t\tevery_other_country = {\n\t\t\tlimit = {\n\t\t\t\tis_faction_leader = yes\n\t\t\t\tis_in_faction_with = PREV\n\t\t\t}\n\t\t\tcountry_event = { id = ktits_alliance.4 }\n\t\t}\n\t}\n}\n\n")
    ev += (f"# FROM = the member that changed the ideology and stayed\ncountry_event = {{\n\tid = ktits_alliance.4\n\ttitle = ktits_alliance.4.t\n{descs(4, True)}\tpicture = {pic}\n\tis_triggered_only = yes\n\tfire_only_once = no\n\n"
           "\toption = {\n\t\tname = ktits_alliance.4.a\n\t\ttrigger = { FROM = { is_subject = no } }\n\t\tai_chance = {\n\t\t\tbase = 50\n\t\t}\n\t\tadd_to_variable = { var = ktits_ally_size value = -1 }\n\t\tFROM = { clr_country_flag = ktits_ally_alien }\n\t\tFROM = { country_event = { id = ktits_alliance.11 } }\n\t}\n"
           "\toption = {\n\t\tname = ktits_alliance.4.b\n\t\tai_chance = {\n\t\t\tbase = 50\n\t\t}\n\t\tktits_ally_coop_m20 = yes\n\t}\n}\n\n")
    ev += (f"# the end of the change of course of a puppet (decision ktits_ally_course): ROOT = the puppet\ncountry_event = {{\n\tid = ktits_alliance.5\n\ttitle = ktits_alliance.5.t\n\tdesc = ktits_alliance.5.d\n\tpicture = {pic}\n\tis_triggered_only = yes\n\tfire_only_once = no\n\n"
           "\ttrigger = {\n\t\tis_subject = yes\n\t}\n\n\timmediate = {\n\t\thidden_effect = {\n\t\t\tktits_ally_course_apply = yes\n\t\t}\n\t}\n\n"
           "\toption = {\n\t\tname = ktits_alliance.5.a\n\t\tcustom_effect_tooltip = ktits_ally_tt_course\n\t}\n}\n")
    ev += (f"\n# a new leader of the alliance (the monthly check); FROM = the new leader, ROOT = every member including the leader\ncountry_event = {{\n\tid = ktits_alliance.6\n\ttitle = ktits_alliance.6.t\n"
           f"\tdesc = {{\n\t\ttext = ktits_alliance.6.d_leader\n\t\ttrigger = {{ is_faction_leader = yes }}\n\t}}\n\tdesc = {{\n\t\ttext = ktits_alliance.6.d\n\t\ttrigger = {{ is_faction_leader = no }}\n\t}}\n"
           f"\tpicture = {pic}\n\tis_triggered_only = yes\n\tfire_only_once = no\n\n\toption = {{\n\t\tname = ktits_alliance.6.a\n\t\ttrigger = {{ is_faction_leader = yes }}\n\t}}\n"
           "\toption = {\n\t\tname = ktits_alliance.6.b\n\t\ttrigger = { is_faction_leader = no }\n\t}\n}\n")
    ev += (f"\n# news for the members: FROM joined the alliance\ncountry_event = {{\n\tid = ktits_alliance.8\n\ttitle = ktits_alliance.8.t\n\tdesc = ktits_alliance.8.d\n\tpicture = {pic}\n\tis_triggered_only = yes\n\tfire_only_once = no\n\n\toption = {{\n\t\tname = ktits_alliance.8.a\n\t}}\n}}\n")
    ev += (f"\n# news for the members: FROM left the alliance\ncountry_event = {{\n\tid = ktits_alliance.9\n\ttitle = ktits_alliance.9.t\n\tdesc = ktits_alliance.9.d\n\tpicture = {pic}\n\tis_triggered_only = yes\n\tfire_only_once = no\n\n\toption = {{\n\t\tname = ktits_alliance.9.a\n\t}}\n}}\n")
    ev += ("\n# hidden: ROOT = the country the leader expels (event 4): the news to the members, then it leaves\ncountry_event = {\n\tid = ktits_alliance.11\n\thidden = yes\n\tis_triggered_only = yes\n\tfire_only_once = no\n\n\timmediate = {\n\t\tif = {\n\t\t\tlimit = { is_in_faction = yes }\n\t\t\tevery_other_country = {\n\t\t\t\tlimit = {\n\t\t\t\t\tis_in_faction_with = PREV\n\t\t\t\t\tis_faction_leader = no\n\t\t\t\t}\n\t\t\t\tcountry_event = { id = ktits_alliance.12 }\n\t\t\t}\n\t\t\tleave_faction = yes\n\t\t}\n\t}\n}\n")
    ev += (f"\n# news for the members: FROM was expelled by the leader\ncountry_event = {{\n\tid = ktits_alliance.12\n\ttitle = ktits_alliance.12.t\n\tdesc = ktits_alliance.12.d\n\tpicture = {pic}\n\tis_triggered_only = yes\n\tfire_only_once = no\n\n\toption = {{\n\t\tname = ktits_alliance.12.a\n\t}}\n}}\n")
    ev += (f"\n# news for the founder: the first member joined the new alliance (daily check ktits_ally_track); ROOT = the founder, FROM = the first member\ncountry_event = {{\n\tid = ktits_alliance.14\n\ttitle = ktits_alliance.14.t\n\tdesc = ktits_alliance.14.d\n\tpicture = {pic}\n\tis_triggered_only = yes\n\tfire_only_once = no\n\n\toption = {{\n\t\tname = ktits_alliance.14.a\n\t}}\n}}\n")
    ev += (f"\n# the scale fell to 0, the alliance dissolved itself; ROOT = every member including the leader\ncountry_event = {{\n\tid = ktits_alliance.15\n\ttitle = ktits_alliance.15.t\n\tdesc = ktits_alliance.15.d\n\tpicture = {pic}\n\tis_triggered_only = yes\n\tfire_only_once = no\n\n\toption = {{\n\t\tname = ktits_alliance.15.a\n\t}}\n}}\n")
    ev += (f"\n# nobody joined for {LONE_DAYS} days, the lone alliance dissolved; ROOT = the leader\ncountry_event = {{\n\tid = ktits_alliance.16\n\ttitle = ktits_alliance.16.t\n\tdesc = ktits_alliance.16.d\n\tpicture = {pic}\n\tis_triggered_only = yes\n\tfire_only_once = no\n\n\toption = {{\n\t\tname = ktits_alliance.16.a\n\t}}\n}}\n")
    w("events/ktits_alliance_events.txt", ev)

    # ---------------- localisation ----------------
    ru, en = [], []
    def add(k, r, e=None):
        ru.append((k, r)); en.append((k, e if e is not None else L.translit(r)))
    for g in GROUPS:
        add(f"ktits_ally_desc_{g}", CAT_TXT[g])
    add("ktits_ally_desc_none", CAT_NONE)
    add("ktits_alliance_category", "Альянс")
    add("ktits_alliance_category_desc", "Союзники делают вместе то, что не получается поодиночке, и меряют дружбу шкалой. [GetKtitsAllyDesc]", "Allies do together what cannot be done alone and measure friendship with a scale. [GetKtitsAllyDesc]")
    add("ktits_alliance_template_name", "Альянс", "Alliance")
    for t, k, n, kn, rs, dc, xp, dd, kd in TIERS:
        add(f"ktits_ally_{t}", n); add(f"ktits_ally_{t}_desc", dd)
        add(f"ktits_ally_{k}", kn); add(f"ktits_ally_{k}_desc", kd)
    for key, (n, dd, mod) in TIMED.items():
        add(key, n); add(key + "_desc", dd)
    add("ktits_ally_can_found_tt", "Страна великая или средняя держава: не менее 30 фабрик (военных и гражданских вместе)", "The country is a major or a medium power: at least 30 factories (military and civilian together)")
    add("ktits_ally_invite_match_tt", "Та же идеологическая группа или общий враг: приглашаемая страна воюет хотя бы с одной страной, которая воюет с лидером альянса", "The same ideology group or a common enemy: the invited country is at war with a country that is at war with the alliance leader")
    add("ktits_ally_request", "Просить о вступлении: [FROM.GetName]", "Request to join: [FROM.GetName]")
    add("ktits_ally_request_desc", "Посол с папкой документов отправляется к лидеру альянса. Просьбу можно подать, когда мир достаточно опасен для одиночек. Если лидер откажет, повторить просьбу можно будет только через полгода.")
    add("ktits_ally_course", "Сменить курс марионетки: [FROM.GetName]", "Change the puppet's course: [FROM.GetName]")
    add("ktits_ally_course_desc", "Сюзерен присылает советников, и через три месяца у марионетки правит партия сюзеренской идеологии. Стабильность падает, а политический курс страны придётся выбирать заново.")
    for key, name, txt, cost, cd, tag in COOP:
        add(key, name); add(key + "_desc", txt)
    add("ktits_ally_tension_tt", "Мировая напряжённость не ниже порога идеологии альянса (демократия 40 %, теология 35 %, диктатура 30 %, фашизм 20 %, коммунизм 10 %, Казуальность любая)",
        "World tension is at least the threshold of the alliance ideology (democracy 40%, theology 35%, dictatorship 30%, fascism 20%, communism 10%, Casuality any)")
    add("ktits_ally_tt_p5", "Шкала сотрудничества альянса: §G+5§!", "Alliance cooperation: §G+5§!")
    add("ktits_ally_tt_p10", "Шкала сотрудничества альянса: §G+10§!", "Alliance cooperation: §G+10§!")
    add("ktits_ally_tt_for2", "Иностранные специалисты: §G+2§! тыс.", "Foreign specialists: §G+2§! k")
    add("ktits_ally_tt_course", "Правящей станет партия идеологии сюзерена, её популярность вырастет на 40 %, стабильность упадёт на 10 %, ветка «Политический курс» начнётся заново.",
        "The party of the overlord's ideology comes to power, its popularity grows by 40%, stability falls by 10%, the Political Course branch starts again.")
    add("ktits_ally_diplo_blocked", "Вступить в альянс можно только через решения категории «Альянс».", "Alliances are joined only through the decisions of the category \"Alliance\".")
    add("ktits_ally_puppet_leave", "Марионетка не может выйти из альянса своего сюзерена.", "A puppet cannot leave the alliance of its overlord.")
    add("ktits_ally_puppet_kick", "Марионетку нельзя исключить из альянса её сюзерена.", "A puppet cannot be expelled from the alliance of its overlord.")
    titles = {1: "Стук в дверь", 3: "Чужая среди своих", 4: "Чужой в доме", 5: "Новый курс"}
    for n, t in titles.items():
        add(f"ktits_alliance.{n}.t", t)
    for n in (1, 3, 4):
        for g in GROUPS:
            add(f"ktits_alliance.{n}.d_{g}", EVENT_TXT[n][g])
    add("ktits_alliance.1.d", "У дверей штаба альянса стоит чья-то делегация и просит принять её в союз. Мир становится опаснее, и одиночкам в нём неуютно.")
    add("ktits_alliance.3.d", "Правящая партия сменилась, и союзники смотрят на нас иначе: теперь мы думаем и голосуем не так, как они.")
    add("ktits_alliance.4.d", "Один из союзников сменил политический курс и остался в альянсе. Остальным предстоит решить, что с этим делать.")
    add("ktits_alliance.5.d", "Советники сюзерена закончили работу: в столице сменилась власть, а прежние партии учатся говорить о политике по-новому. Народу сообщили, что так и было задумано.")
    add("ktits_alliance.1.a", "Принять в альянс"); add("ktits_alliance.1.b", "Отказать")
    add("ktits_alliance.3.a", "Выйти из альянса"); add("ktits_alliance.3.b", "Остаться")
    add("ktits_alliance.4.a", "Исключить из альянса"); add("ktits_alliance.4.b", "Терпеть (шкала сотрудничества -20)")
    add("ktits_alliance.5.a", "Привыкать к новому курсу")
    add("ktits_alliance.6.t", "Смена караула")
    add("ktits_alliance.6.d", "Знамя альянса перешло к стране [FROM.GetName]. Папки с договорами перевезли в новую столицу, печати переделали за ночь. Союзники спорят только о том, кому теперь звонить первым.")
    add("ktits_alliance.6.d_leader", "Прежний лидер больше не ведёт союзников, и все взгляды обратились к нам. Архив альянса, его долги и обещания теперь наши. Шкала сотрудничества перешла вместе с ними.")
    add("ktits_alliance.6.a", "Принять командование")
    add("ktits_alliance.6.b", "Присягнуть новому лидеру")
    add("ktits_alliance.8.t", "Новый союзник")
    add("ktits_alliance.8.d", "[FROM.GetName] вступила в наш альянс. На общей карте прибавился ещё один флажок, а в штабе — ещё один стул, на котором пока никто не знает, как сидеть.")
    add("ktits_alliance.8.a", "Добро пожаловать")
    add("ktits_alliance.9.t", "Союзник ушёл")
    add("ktits_alliance.9.d", "[FROM.GetName] покинула наш альянс. Флажок с общей карты сняли аккуратно, чтобы не порвать: вдруг ещё вернётся.")
    add("ktits_alliance.9.a", "Скатертью дорога")
    add("ktits_alliance.12.t", "Изгнание из альянса")
    add("ktits_alliance.12.d", "Лидер альянса исключил страну [FROM.GetName] из союза. Её посол собрал вещи под молчаливые взгляды остальных; никто не решился спросить, кто будет следующим.")
    add("ktits_alliance.12.a", "Так ей и надо")
    add("ktits_ally_leave", "Покинуть альянс")
    add("ktits_ally_leave_desc", "Союз больше не нужен или стал в тягость. Страна забирает свой флажок с общей карты и уходит; союзники узнают об этом из газет. Шкала сотрудничества альянса падает на 5.")
    add("ktits_ally_leave_by_decision", "Выйти из альянса можно только решением «Покинуть альянс».", "An alliance can be left only with the decision \"Leave the alliance\".")
    add("ktits_eternal_neutrality", "Вечный нейтралитет")
    add("ktits_eternal_neutrality_desc", "Наша конституция начинается словами «Мы ни с кем не дружим против кого-то». Дипломаты обучены отвечать на любое приглашение одной фразой, и союзники давно перестали спрашивать.")
    add("ktits_eternal_neutrality_tt", "Нельзя основать альянс и вступить в альянс.", "Cannot found or join an alliance.")
    add("ktits_baku_powder_keg", "Бакинская пороховая бочка")
    add("ktits_baku_powder_keg_desc", "Каждый сосед уверен, что нефть и перевалы этой земли принадлежат ему по праву, и у каждого в сейфе лежит карта с красной линией. Дипломаты ходят по краю бочки с порохом, а в союзы вступают шёпотом: любое неосторожное рукопожатие может стать искрой.")
    add("ktits_baku_powder_keg_tt", "Пока действует так же, как «Вечный нейтралитет»: нельзя основать альянс и вступить в альянс (заглушка будущей механики).", "For now works like Eternal Neutrality: cannot found or join an alliance (a placeholder for a future mechanic).")
    add("ktits_alliance.14.t", "Альянс основан")
    add("ktits_alliance.14.d", "[FROM.GetName] вступила в наш новый альянс. Пустой зал заседаний наконец-то занят, печать поставлена, а значит, мы больше не одиночки с красивым названием. Во главе стоим мы: кто основал, тот и держит перо.")
    add("ktits_alliance.14.a", "За новый союз")
    add("ktits_alliance.15.t", "Самороспуск альянса")
    add("ktits_alliance.15.d", "Шкала сотрудничества опустилась до нуля, и союзники вдруг обнаружили, что давно не помнят, зачем собирались. Договоры сложили в архив, флажки сняли с общей карты, чай допили в тишине. Каждый теперь сам по себе, и никто не в обиде: обижаться тоже было лень.")
    add("ktits_alliance.15.a", "Разойтись по домам")
    add("ktits_alliance.16.t", "Пустой альянс")
    add("ktits_alliance.16.d", "Два месяца подряд в зале заседаний стояли пустые стулья, а послы соседей вежливо смотрели в сторону. Союз без союзников не союз, а канцелярия. Печать сняли со стола и убрали в сундук до лучших времён.")
    add("ktits_alliance.16.a", "Что ж, обойдёмся")
    add("ktits_ally_bar_label", "Сотрудничество альянса: [?ktits_ally_view|0] / 100", "Alliance cooperation: [?ktits_ally_view|0] / 100")
    add("ktits_ally_bar_tt", "Каждое деление - 5 пунктов шкалы. Цвет деления - ступень: серый 0-24 «Дружба на бумаге», голубой 25-49 «Общие планы», синий 50-74 «Братство по оружию», золотой 75-100 «Единый штаб». На нуле альянс распускается сам.",
        "Each segment is 5 points of the scale. Colour = tier: grey 0-24, light blue 25-49, blue 50-74, gold 75-100. At zero the alliance dissolves itself.")
    for v in (25, 50, 75):
        add(f"ktits_ally_bar_thr_{v}", str(v))
    # English of the options with numbers keep readable text
    en_over = {"ktits_alliance.4.b": "Tolerate (cooperation -20)"}
    en = [(k, en_over.get(k, v)) for k, v in en]
    out["__loc__"] = (ru, en)
    return out

def block_end(text, start):
    """index after the brace that closes the block whose '{' is the first one after `start`"""
    i = text.index("{", start); depth = 0
    for j in range(i, len(text)):
        if text[j] == "{": depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0: return j + 1
    raise ValueError("unbalanced braces")

def replace_block(text, key, new):
    m = re.search(r"(?m)^[ \t]*" + re.escape(key) + r"\s*=\s*\{", text)
    if not m: return text, False
    return text[:m.start()] + new + text[block_end(text, m.start()):], True

DIPLO = {
    "DIPLOMACY_JOIN_FACTION_ENABLE_TRIGGER": "custom_trigger_tooltip = {\n\t\ttooltip = ktits_ally_diplo_blocked\n\t\talways = no\n\t}",
    # the vanilla button "Пригласить в альянс" (this = the inviter, FROM = the invited): the leader invites a free independent country of the same ideology group or with a common enemy, if the world tension allows; the vanilla AI acceptance stays
    "DIPLOMACY_OFFER_JOIN_FACTION_ENABLE_TRIGGER": ("is_faction_leader = yes\n\tFROM = {\n\t\tis_in_faction = no\n\t\tis_subject = no\n\t\tNOT = { ktits_ally_barred = yes }\n\t}\n"
                                                    "\tcustom_trigger_tooltip = {\n\t\ttooltip = ktits_ally_tension_tt\n\t\tktits_ally_tension_ok = yes\n\t}\n"
                                                    "\tcustom_trigger_tooltip = {\n\t\ttooltip = ktits_ally_invite_match_tt\n\t\tktits_ally_invite_match = yes\n\t}"),
    "DIPLOMACY_LEAVE_FACTION_ENABLE_TRIGGER": ("if = {\n\t\tlimit = {\n\t\t\thas_game_rule = {\n\t\t\t\trule = allow_leave_faction\n\t\t\t\toption = BLOCKED\n\t\t\t}\n\t\t}\n\t\tcustom_trigger_tooltip = {\n\t\t\ttooltip = RULE_ALLOW_LEAVE_FACTION_BLOCKED_TOOLTIP\n\t\t\talways = no\n\t\t}\n\t}\n"
                                               "\tif = {\n\t\tlimit = { is_subject = yes }\n\t\tcustom_trigger_tooltip = {\n\t\t\ttooltip = ktits_ally_puppet_leave\n\t\t\talways = no\n\t\t}\n\t}\n"
                                               "\tcustom_trigger_tooltip = {\n\t\ttooltip = ktits_ally_leave_by_decision\n\t\talways = no\n\t}"),
    "DIPLOMACY_KICK_FROM_FACTION_ENABLE_TRIGGER": ("if = {\n\t\tlimit = {\n\t\t\thas_game_rule = {\n\t\t\t\trule = allow_kick_faction\n\t\t\t\toption = BLOCKED\n\t\t\t}\n\t\t}\n\t\tcustom_trigger_tooltip = {\n\t\t\ttooltip = RULE_KICK_FROM_FACTION_BLOCKED_TOOLTIP\n\t\t\talways = no\n\t\t}\n\t}\n"
                                                 "\tif = {\n\t\tlimit = { FROM = { is_subject = yes } }\n\t\tcustom_trigger_tooltip = {\n\t\t\ttooltip = ktits_ally_puppet_kick\n\t\t\talways = no\n\t\t}\n\t}"),
}

def patch_diplomacy(M):
    """join (request) is blocked for everybody, offer join has our conditions; leave / kick are blocked for puppets (ROOT = the acting country, FROM = the target)"""
    p = M / "common/scripted_triggers/diplomacy_scripted_triggers.txt"
    if not p.exists(): return []
    raw = p.read_bytes(); crlf = b"\r\n" in raw
    text = raw.decode("utf-8-sig").replace("\r\n", "\n")
    done = []
    for key, body in DIPLO.items():
        text, ok = replace_block(text, key, f"{key} = {{\n\t{body}\n}}")
        if ok: done.append(key)
    if crlf: text = text.replace("\n", "\r\n")
    p.write_bytes(("﻿" if raw.startswith(b"\xef\xbb\xbf") else "").encode() + text.encode("utf-8"))
    return done

VANILLA_TEMPLATES = Path("D:/SteamLibrary/steamapps/common/Hearts of Iron IV/common/factions/templates")

def patch_templates(M):
    """every vanilla faction template becomes invisible: the list of templates of the vanilla "create faction" action is empty (scripts create factions from the template by name).
    A template WITHOUT a visible block is visible and available to everybody (vanilla allies.txt, axis.txt, unique_minor_factions.txt ... have none), so vanilla files absent from the mod
    are copied into it first and a visible block = always no is added to every template that lacks one"""
    n = 0
    d = M / "common/factions/templates"
    if VANILLA_TEMPLATES.exists():
        for v in sorted(VANILLA_TEMPLATES.glob("*.txt")):
            if not (d / v.name).exists(): (d / v.name).write_bytes(v.read_bytes())
    for p in sorted(d.glob("*.txt")):
        if p.name == "ktits_alliance_templates.txt": continue   # ours: visible to allowed founders
        raw = p.read_bytes(); text = raw.decode("utf-8-sig"); orig = text
        pos = 0
        while True:
            m = re.compile(r"(?m)^([ \t]*)visible\s*=\s*\{").search(text, pos)
            if not m: break
            e = block_end(text, m.start())
            new = f"{m.group(1)}visible = {{\n{m.group(1)}\talways = no # Ktits: factions are made by decisions (tools/make_alliances.py)\n{m.group(1)}}}"
            text = text[:m.start()] + new + text[e:]
            pos = m.start() + len(new); n += 1
        # templates without a visible block (top level `name = {`): the block is added right after the opening line
        out = []; pos = 0
        for m in re.finditer(r"(?m)^([A-Za-z_]\w*)\s*=\s*\{[^\n]*\n", text):
            if m.start() < pos: continue
            e = block_end(text, m.start())
            body = text[m.end():e]
            out.append(text[pos:m.end()])
            if not re.search(r"(?m)^[ \t]*visible\s*=\s*\{", body):
                out.append("\tvisible = {\n\t\talways = no # Ktits: factions are made by decisions (tools/make_alliances.py)\n\t}\n"); n += 1
            out.append(body); pos = e
        out.append(text[pos:]); text = "".join(out)
        if text != orig:
            p.write_bytes((b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b"") + text.encode("utf-8"))
    return n

def strip_rp_factions(M):
    """RandomParadox puts start factions into history/countries (create_faction_from_template + add_to_faction) and adds
    events/rpx_faction_alignment.txt (mean_time_to_happen events that put countries into factions). Only the three start alliances
    of the author exist, joining only through decisions: the history lines are removed, the event file keeps only its namespace"""
    n = 0
    pat = re.compile(r"(?m)^(create_faction_from_template|add_to_faction)\s*=\s*\S+[ \t]*\r?\n")
    for f in sorted((M / "history/countries").glob("*.txt")):
        raw = f.read_bytes(); bom = raw.startswith(b"\xef\xbb\xbf")
        text = raw.decode("utf-8-sig"); new, k = pat.subn("", text)
        if k:
            f.write_bytes((b"\xef\xbb\xbf" if bom else b"") + new.encode("utf-8")); n += k
    ev = M / "events/rpx_faction_alignment.txt"
    stub = "# Ktits: RandomParadox faction alignment events removed, alliances only through decisions (tools/make_alliances.py)\nadd_namespace = faction_alignment\n"
    ev_done = False
    if ev.exists() and ev.read_text(encoding="utf-8-sig") != stub:
        ev.write_text(stub, encoding="utf-8"); ev_done = True
    # the event faction_alignment.6 ("Growing Threat" chain, fired by faction_alignment.* with days = 1) came only from this file; its texts are removed too
    nloc = 0
    for f in sorted((M / "localisation").glob("*/faction_alignment_*.yml")):
        f.unlink(); nloc += 1
    return n, ev_done, nloc

def write_bar(M):
    '''scale bar over the category "Альянс" (same technique as the Casuality and Education bars: scripted GUI of the decision category, 20 segments of 5 points shown by the variable ktits_ally_view 0..100;
    segment colour = tier of the scale: 0-24 grey, 25-49 light blue, 50-74 blue, 75-100 gold; thresholds 25, 50, 75 are written under the bar)'''
    from PIL import Image, ImageDraw
    N, SW, SH, GAP, BX = 20, 22, 14, 1, 14
    art = M / "gfx/interface/ktits"; art.mkdir(parents=True, exist_ok=True)
    bw = N * (SW + GAP) + 6
    fr = Image.new("RGB", (bw, SH + 8), (25, 28, 36)); ImageDraw.Draw(fr).rectangle([0, 0, fr.width - 1, fr.height - 1], outline=(200, 190, 150)); fr.save(art / "ally_bar_frame.png")
    cols = [(140, 140, 140), (110, 190, 235), (50, 100, 215), (235, 190, 50)]
    for i, c in enumerate(cols, 1):
        im = Image.new("RGB", (SW, SH), c); ImageDraw.Draw(im).rectangle([0, 0, SW - 1, SH - 1], outline=tuple(int(v * 0.6) for v in c)); im.save(art / f"ally_seg_{i}.png")
    sprites = [("GFX_ktits_ally_bar_frame", "ally_bar_frame.png")] + [(f"GFX_ktits_ally_seg_{i}", f"ally_seg_{i}.png") for i in range(1, 5)]
    (M / "interface").mkdir(parents=True, exist_ok=True)
    (M / "interface/ktits_alliance.gfx").write_text("spriteTypes = {\n" + "".join(f'\tspriteType = {{\n\t\tname = "{n}"\n\t\ttexturefile = "gfx/interface/ktits/{fn}"\n\t}}\n' for n, fn in sprites) + "}\n", encoding="utf-8", newline="\n")
    (M / "common/scripted_guis").mkdir(parents=True, exist_ok=True)
    (M / "common/scripted_guis/ktits_alliance.txt").write_text("scripted_gui = {\n\n\tktits_alliance_ui = {\n\t\tcontext_type = decision_category\n\t\twindow_name = \"ktits_alliance_ui_window\"\n\n\t\ttriggers = {\n" + "".join(
        f"\t\t\tktits_ally_seg_{i}_visible = {{\n\t\t\t\tcheck_variable = {{ var = ktits_ally_view value = {i * 5} compare = greater_than_or_equals }}\n\t\t\t}}\n" for i in range(1, N + 1)) + "\t\t}\n\t}\n}\n", encoding="utf-8", newline="\n")
    g = "guiTypes = {\n\n\tcontainerWindowType = {\n\t\tname = \"ktits_alliance_ui_window\"\n\t\tposition = { x = 0 y = 0 }\n\t\tsize = { width = 100% height = 64 }\n\t\tclipping = no\n\n"
    g += f"\t\tinstantTextBoxType = {{\n\t\t\tname = \"ktits_ally_label\"\n\t\t\tposition = {{ x = {BX} y = 2 }}\n\t\t\tfont = \"hoi_16mbs\"\n\t\t\ttext = \"ktits_ally_bar_label\"\n\t\t\tformat = left\n\t\t\tmaxHeight = 18\n\t\t\tmaxwidth = 470\n\t\t}}\n\n"
    g += f"\t\ticonType = {{\n\t\t\tname = \"ktits_ally_frame\"\n\t\t\tspriteType = \"GFX_ktits_ally_bar_frame\"\n\t\t\tposition = {{ x = {BX} y = 22 }}\n\t\t\tpdx_tooltip = \"ktits_ally_bar_tt\"\n\t\t}}\n\n"
    for i in range(1, N + 1):
        g += f"\t\ticonType = {{\n\t\t\tname = \"ktits_ally_seg_{i}\"\n\t\t\tspriteType = \"GFX_ktits_ally_seg_{(i - 1) // 5 + 1}\"\n\t\t\tposition = {{ x = {BX + 3 + (i - 1) * (SW + GAP)} y = 25 }}\n\t\t}}\n"
    for v in (25, 50, 75):
        g += f"\t\tinstantTextBoxType = {{\n\t\t\tname = \"ktits_ally_thr_{v}\"\n\t\t\tposition = {{ x = {BX + 3 + (v // 5) * (SW + GAP) - 15} y = 42 }}\n\t\t\tfont = \"hoi_16mbs\"\n\t\t\ttext = \"ktits_ally_bar_thr_{v}\"\n\t\t\tformat = center\n\t\t\tmaxHeight = 16\n\t\t\tmaxwidth = 30\n\t\t}}\n"
    (M / "interface/ktits_alliance.gui").write_text(g + "\t}\n}\n", encoding="utf-8", newline="\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", default=L.DEFAULT_MOD)
    a = ap.parse_args()
    M = Path(a.mod)
    info = L.load_mod(M)
    lore2tag = {lt: t for t, lt in info["tag2lore"].items()}
    out = build(M, lore2tag)
    ru, en = out.pop("__loc__")
    for rel, text in out.items():
        p = M / rel; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")
    L.write_yml(str(M / "localisation/russian/ktits_alliance_l_russian.yml"), "russian", ru)
    L.write_yml(str(M / "localisation/english/ktits_alliance_l_english.yml"), "english", en)
    for old in ("common/scripted_diplomatic_actions/ktits_alliance_actions.txt", "common/opinion_modifiers/ktits_alliance_opinion.txt"):
        if (M / old).exists(): (M / old).unlink()
    write_bar(M)
    done = patch_diplomacy(M)
    nt = patch_templates(M)
    nh, nev, nloc = strip_rp_factions(M)
    print(f"alliances: RandomParadox faction lines removed from history: {nh}; faction alignment events neutralised: {nev}; faction_alignment loc files removed: {nloc}")
    print(f"alliances: {len(out)} script files, {len(ru)} loc keys; diplomacy triggers patched: {len(done)}/{len(DIPLO)}; faction template visible blocks set to always = no: {nt}")

if __name__ == "__main__":
    main()
