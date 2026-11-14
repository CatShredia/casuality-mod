"""Specialists mechanic (docs/global_mechanics/Education.md): text generators shared by make_education.py (effects, decisions, loc)
and make_focuses.py (branch "Образование"). Counters (thousands): ktits_spec_own, ktits_spec_foreign. All numbers are INVENTED
(docs/lore/Invented-Lore.md) except the author's rules listed in the doc."""

THRESH = [0, 10, 30, 60, 100, 150]          # own specialists that give level 0..5
OWN_TT = [1, 5, 10, 15, 20, 30, -3, -5, -10, -20]
FOR_TT = [5, 10, 15]
RAPP = "ktits_cas_ai_rapprochement"
CAT_DEV, CAT_SIMP = "ktits_education_dev_category", "ktits_education_simp_category"   # two categories: development (+) and simplification (-)
MARK_UP, MARK_DOWN = "§G+§! ", "§R−§! "   # vanilla localisation has no ▲/▼ glyphs: coloured plus / minus (U+2212)
NLN = chr(92) + "n"
# text icons that exist in vanilla (interface/texticons.gfx, used in vanilla localisation): research, manpower, right arrow
CAT_DEV_DESC = ("Образованность народа держится на специалистах. Приезжие понемногу перенимают местные порядки и становятся нашими, а учёные-одиночки умнее не делают никого."
                + NLN + "£research_icon£ Наши специалисты: [?ktits_spec_own|0] тыс."
                + NLN + "£manpower_texticon£ Иностранные специалисты: [?ktits_spec_foreign|0] тыс."
                + NLN + "£right_arrow£ До следующего уровня: [?ktits_spec_next|0] тыс.")
CAT_SIMP_DESC = ("Простое решение всегда рядом: быстро получить людей и власть ценой знаний. Каждое такое решение отнимает наших специалистов, а выучить их заново дольше, чем отменить учебный год."
                 + NLN + "£research_icon£ Наши специалисты: [?ktits_spec_own|0] тыс.")

# attraction decisions: key, ru name, ru description, cost PP, cooldown days (the cooperation treaty is a separate targeted decision COOP)
ATTRACT = [
    ("ktits_edu_attr_1", "Приют для беглых умов", "Страна принимает учёных, бегущих от войны и Казуальности. Они приезжают с чемоданами формул и без лишних вопросов.", 75, 180),
    ("ktits_edu_attr_2", "Наставничество", "Каждый приезжий специалист обязан взять учеников. Ученики сначала пугаются, потом привыкают, а потом сами начинают учить.", 100, 365),
]
COOP = ("ktits_edu_coop", "Договор о сотрудничестве", "Министры просвещения двух стран подписывают договор: лаборатории открывают двери, учёные едут в обе стороны. Подписать должны оба министра, а второй может и не захотеть.", 100, 180)
# simplification decisions: key, ru name, ru description, cooldown days (0 = once), own lost (full, halved after "Своими силами")
SIMP = [
    ("ktits_edu_simp_1", "Студентов — на поля", "Учебный год отменяется, студенты едут на уборку урожая. Урожай собран, конспекты утеряны.", 90, 5, 3),
    ("ktits_edu_simp_2", "Школы — под склады", "Здания школ отдают под нужды армии и промышленности. Парты сдвинули к стене, в классах теперь ящики.", 180, 10, 5),
    ("ktits_edu_simp_3", "Сожжение книг", "Лишние знания объявлены вредными. Иностранные специалисты в ужасе уезжают, оставив после себя только пустые лаборатории.", 0, 20, 10),
]
SP_WARE = ("ktits_edu_sp_warehouses", "Школы под склады", "Парты в коридорах, ящики в классах, а дети учатся читать по накладным. Армии хорошо, учителям не очень.", 0.03)


def tt_key(kind, d):
    return f"ktits_edu_tt_{kind}_" + (f"p{d}" if d > 0 else f"m{-d}")


def spec(own=0, foreign=0, t="\t\t\t"):
    """effect text: tooltip(s) 'Наши специалисты: +N' and a hidden change of the counters with the level update"""
    s = ""
    if own:
        s += f"{t}custom_effect_tooltip = {tt_key('own', own)}\n"
    if foreign:
        s += f"{t}custom_effect_tooltip = {tt_key('for', foreign)}\n"
    s += f"{t}hidden_effect = {{\n"
    if own:
        s += f"{t}\tadd_to_variable = {{ var = ktits_spec_own value = {own} }}\n"
    if foreign:
        s += f"{t}\tadd_to_variable = {{ var = ktits_spec_foreign value = {foreign} }}\n"
    s += f"{t}\tktits_education_update = yes\n{t}}}\n"
    return s


def tt_loc():
    """(key, ru, en) of the tooltips of specialist changes"""
    out = []
    for d in OWN_TT:
        col = "§G+%d§!" % d if d > 0 else "§R%d§!" % d
        out.append((tt_key("own", d), f"Наши специалисты: {col} тыс.", f"Own specialists: {col} k"))
    for d in FOR_TT:
        out.append((tt_key("for", d), f"Иностранные специалисты: §G+{d}§! тыс.", f"Foreign specialists: §G+{d}§! k"))
    return out


def effects_text(KAZ):
    th = THRESH
    own_chain = "".join(f"\tif = {{\n\t\tlimit = {{ has_idea = ktits_edu_{i} }}\n\t\tset_variable = {{ var = ktits_spec_own value = {th[i]} }}\n\t}}\n" for i in range(6))
    lvl = "".join(f"\tif = {{\n\t\tlimit = {{ check_variable = {{ var = ktits_spec_own value = {th[i]} compare = greater_than_or_equals }} }}\n\t\tset_variable = {{ var = ktits_edu_t value = {i} }}\n\t}}\n" for i in range(1, 6))
    nxt = f"\tset_variable = {{ var = ktits_spec_next value = 0 }}\n" + "".join(
        f"\tif = {{\n\t\tlimit = {{ check_variable = {{ var = ktits_edu_t value = {i} compare = equals }} }}\n\t\tset_variable = {{ var = ktits_spec_next value = ktits_spec_own }}\n"
        f"\t\tmultiply_variable = {{ var = ktits_spec_next value = -1 }}\n\t\tadd_to_variable = {{ var = ktits_spec_next value = {th[i + 1]} }}\n\t}}\n" for i in range(5))
    rm = "".join(f"\tif = {{\n\t\tlimit = {{\n\t\t\thas_idea = ktits_edu_{i}\n\t\t\tNOT = {{ check_variable = {{ var = ktits_edu_t value = {i} compare = equals }} }}\n\t\t}}\n\t\tremove_ideas = ktits_edu_{i}\n\t}}\n" for i in range(6))
    ad = "".join(f"\tif = {{\n\t\tlimit = {{\n\t\t\tcheck_variable = {{ var = ktits_edu_t value = {i} compare = equals }}\n\t\t\tNOT = {{ has_idea = ktits_edu_{i} }}\n\t\t}}\n\t\tadd_ideas = ktits_edu_{i}\n\t}}\n" for i in range(6))
    rnd = "".join(f"\t\t1 = {{ set_variable = {{ var = ktits_spec_foreign value = {n} }} }}\n" for n in range(11))
    base = [d[3] for d in ATTRACT]
    costs = "".join(f"\tset_variable = {{ var = ktits_edu_cost_{i + 1} value = {c} }}\n" for i, c in enumerate(base))
    disc = "".join(f"\t\tmultiply_variable = {{ var = ktits_edu_cost_{i + 1} value = 0.75 }}\n\t\tround_variable = ktits_edu_cost_{i + 1}\n" for i in range(len(base)))
    return f"""# specialists (docs/global_mechanics/Education.md); generated by tools/make_education.py, do not edit by hand
# counters in thousands: ktits_spec_own, ktits_spec_foreign; ktits_spec_next = own specialists missing for the next level (0 at level 5); level thresholds {th}
ktits_education_update = {{
	# Kazualia and its puppets: no specialists, level 0 (author's rule)
	if = {{
		limit = {{
			OR = {{
				ktits_is_kazualia = yes
				is_puppet_of = {KAZ}
			}}
		}}
		set_variable = {{ var = ktits_spec_own value = 0 }}
		set_variable = {{ var = ktits_spec_foreign value = 0 }}
	}}
	clamp_variable = {{ var = ktits_spec_own min = 0 max = 99999 }}
	clamp_variable = {{ var = ktits_spec_foreign min = 0 max = 99999 }}
	set_variable = {{ var = ktits_edu_t value = 0 }}
{lvl}{nxt}{rm}{ad}}}

# start of the game: own = threshold of the level spirit from history, foreign = random 0..10
ktits_education_start = {{
{own_chain}	random_list = {{
{rnd}	}}
	ktits_education_update = yes
}}

# costs of the attraction decisions: -25 % after the focus "Импорт умов"
ktits_education_costs = {{
{costs}	if = {{
		limit = {{ has_country_flag = ktits_edu_f_import }}
{disc}	}}
}}

# monthly: 5 % of foreign (at least 1) become own (8 % after the focus, 10 % during the decision; maximum), swamp -1, institutes +1
ktits_education_monthly = {{
	if = {{
		limit = {{
			OR = {{
				ktits_is_kazualia = yes
				is_puppet_of = {KAZ}
			}}
		}}
		ktits_education_update = yes
	}}
	else = {{
		set_variable = {{ var = ktits_edu_rate value = 5 }}
		if = {{
			limit = {{ has_country_flag = ktits_edu_f_mentor }}
			set_variable = {{ var = ktits_edu_rate value = 8 }}
		}}
		if = {{
			limit = {{ has_country_flag = ktits_edu_mentor_dec }}
			set_variable = {{ var = ktits_edu_rate value = 10 }}
		}}
		if = {{
			limit = {{ check_variable = {{ var = ktits_spec_foreign value = 0 compare = greater_than }} }}
			set_variable = {{ var = ktits_edu_m value = ktits_spec_foreign }}
			multiply_variable = {{ var = ktits_edu_m value = ktits_edu_rate }}
			divide_variable = {{ var = ktits_edu_m value = 100 }}
			round_variable = ktits_edu_m
			clamp_variable = {{ var = ktits_edu_m min = 1 max = 99999 }}
			add_to_variable = {{ var = ktits_spec_own value = ktits_edu_m }}
			multiply_variable = {{ var = ktits_edu_m value = -1 }}
			add_to_variable = {{ var = ktits_spec_foreign value = ktits_edu_m }}
		}}
		if = {{
			limit = {{
				OR = {{
					has_idea = ktits_cas_3
					has_idea = ktits_cas_4
					has_idea = ktits_cas_5
				}}
			}}
			add_to_variable = {{ var = ktits_spec_own value = -1 }}
		}}
		if = {{
			limit = {{ has_country_flag = ktits_edu_f_inst }}
			add_to_variable = {{ var = ktits_spec_own value = 1 }}
		}}
		ktits_education_update = yes
	}}
	ktits_education_costs = yes
}}
"""


def decisions_text(KAZ):
    lim_att = ("\t\t\tcustom_trigger_tooltip = {\n\t\t\t\ttooltip = ktits_edu_tt_kaz\n\t\t\t\tNOT = { ktits_is_kazualia = yes }\n"
               f"\t\t\t\tNOT = {{ is_puppet_of = {KAZ} }}\n\t\t\t}}\n")
    big = ("\t\t\tcustom_trigger_tooltip = {\n\t\t\t\ttooltip = ktits_edu_req_big\n\t\t\t\tktits_is_big_country = yes\n\t\t\t}\n"
           "\t\t\thas_completed_focus = ktits_edu_imp\n")
    conds = {
        "ktits_edu_attr_1": ("\t\t\tcustom_trigger_tooltip = {\n\t\t\t\ttooltip = ktits_edu_req_refuge\n\t\t\t\tany_neighbor_country = {\n\t\t\t\t\tOR = {\n\t\t\t\t\t\thas_war = yes\n"
                             "\t\t\t\t\t\thas_idea = ktits_cas_3\n\t\t\t\t\t\thas_idea = ktits_cas_4\n\t\t\t\t\t\thas_idea = ktits_cas_5\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t}\n"),
        "ktits_edu_attr_2": ("\t\t\tcustom_trigger_tooltip = {\n\t\t\t\ttooltip = ktits_edu_req_for10\n\t\t\t\tcheck_variable = { var = ktits_spec_foreign value = 10 compare = greater_than_or_equals }\n\t\t\t}\n"
                             "\t\t\tNOT = { has_country_flag = ktits_edu_mentor_dec }\n"),
    }
    eff = {
        "ktits_edu_attr_1": spec(0, 15),
        "ktits_edu_attr_2": "\t\t\tcustom_effect_tooltip = ktits_edu_tt_mentor\n\t\t\tset_country_flag = { flag = ktits_edu_mentor_dec days = 180 value = 1 }\n",
    }
    d = f"{CAT_DEV} = {{\n"
    for i, (k, _n, _d, _c, cd) in enumerate(ATTRACT):
        d += f"""
\t{k} = {{
\t\ticon = generic_research
\t\tavailable = {{
{lim_att}{big}{conds[k]}\t\t}}
\t\tcost = ktits_edu_cost_{i + 1}
\t\tdays_re_enable = {cd}
\t\tfire_only_once = no
\t\tcomplete_effect = {{
{eff[k]}\t\t}}
\t\tai_will_do = {{
\t\t\tbase = 2
\t\t\tmodifier = {{ factor = 0 has_country_flag = {RAPP} }}
\t\t\tmodifier = {{ factor = 0 check_variable = {{ var = ktits_spec_foreign value = 30 compare = greater_than }} }}
\t\t}}
\t}}
"""
    # targeted decision: cooperation treaty (docs/global_mechanics/Education.md); the target answers with the event ktits_edu.1 (events/ktits_education_events.txt)
    ck, _cn, _cd, ccost, ccd = COOP
    d += f"""
\t{ck} = {{
\t\ticon = generic_research
\t\tavailable = {{
{lim_att}{big}\t\t}}
\t\ttarget_trigger = {{
\t\t\tFROM = {{
\t\t\t\texists = yes
\t\t\t\tNOT = {{ original_tag = ROOT }}
\t\t\t\tNOT = {{ has_war_with = ROOT }}
\t\t\t\tNOT = {{ ktits_is_kazualia = yes }}
\t\t\t\tNOT = {{ is_puppet_of = {KAZ} }}
\t\t\t\tNOT = {{ has_country_flag = ktits_edu_coop_target }}
\t\t\t\tOR = {{
\t\t\t\t\thas_idea = ktits_edu_2
\t\t\t\t\thas_idea = ktits_edu_3
\t\t\t\t\thas_idea = ktits_edu_4
\t\t\t\t\thas_idea = ktits_edu_5
\t\t\t\t}}
\t\t\t}}
\t\t}}
\t\tcost = {ccost}
\t\tdays_re_enable = {ccd}
\t\tfire_only_once = no
\t\tcomplete_effect = {{
\t\t\tcustom_effect_tooltip = ktits_edu_tt_coop
\t\t\tFROM = {{
\t\t\t\tset_country_flag = {{ flag = ktits_edu_coop_target days = 365 value = 1 }}
\t\t\t\tcountry_event = {{ id = ktits_edu.1 }}
\t\t\t}}
\t\t}}
\t\tai_will_do = {{
\t\t\tbase = 3
\t\t\tmodifier = {{ factor = 0 has_country_flag = {RAPP} }}
\t\t\tmodifier = {{ factor = 0 check_variable = {{ var = ktits_spec_foreign value = 30 compare = greater_than }} }}
\t\t}}
\t}}
""" + "}\n\n" + f"{CAT_SIMP} = {{\n"
    for k, _n, _d, cd, full, half in SIMP:
        hid = (f"\t\t\thidden_effect = {{\n\t\t\t\tif = {{\n\t\t\t\t\tlimit = {{ has_country_flag = ktits_edu_f_self }}\n\t\t\t\t\tadd_to_variable = {{ var = ktits_spec_own value = -{half} }}\n\t\t\t\t}}\n"
               f"\t\t\t\telse = {{\n\t\t\t\t\tadd_to_variable = {{ var = ktits_spec_own value = -{full} }}\n\t\t\t\t}}\n")
        if k == "ktits_edu_simp_3":
            hid += "\t\t\t\tset_variable = { var = ktits_spec_foreign value = 0 }\n"
        hid += "\t\t\t\tktits_education_update = yes\n\t\t\t}\n"
        e = f"\t\t\tcustom_effect_tooltip = ktits_edu_tt_{k}\n" + hid
        if k == "ktits_edu_simp_1":
            e += "\t\t\tadd_political_power = 50\n"
        if k == "ktits_edu_simp_2":
            e += f"\t\t\tadd_timed_idea = {{ idea = {SP_WARE[0]} days = 180 }}\n"
        if k == "ktits_edu_simp_3":
            e += "\t\t\tadd_war_support = 0.10\n\t\t\tadd_stability = -0.05\n"
            av = ("\t\t\tcustom_trigger_tooltip = {\n\t\t\t\ttooltip = ktits_edu_req_totalitarian\n\t\t\t\tOR = {\n\t\t\t\t\thas_country_leader_ideology = total_fascism\n"
                  "\t\t\t\t\thas_country_leader_ideology = total_communism\n\t\t\t\t}\n\t\t\t}\n")
            ai = "\t\t\tbase = 0\n\t\t\tmodifier = { add = 1 has_war = yes }\n"
        else:
            av = f"\t\t\tcustom_trigger_tooltip = {{\n\t\t\t\ttooltip = ktits_edu_req_own{full}\n\t\t\t\tcheck_variable = {{ var = ktits_spec_own value = {full} compare = greater_than_or_equals }}\n\t\t\t}}\n"
            ai = (f"\t\t\tbase = 0\n\t\t\tmodifier = {{ add = 1 has_country_flag = {RAPP} }}\n" if k == "ktits_edu_simp_1" else "\t\t\tbase = 0\n")
        re_en = f"\t\tdays_re_enable = {cd}\n" if cd else ""
        once = "yes" if k == "ktits_edu_simp_3" else "no"
        d += f"""
	{k} = {{
		icon = generic_research
		available = {{
{av}		}}
{re_en}		fire_only_once = {once}
		complete_effect = {{
{e}		}}
		ai_will_do = {{
{ai}		}}
	}}
"""
    return d + "}\n"


def loc_entries():
    """(key, ru, en or None) of the category, decisions, requirements, tooltips and the spirit of the decisions"""
    L = [(CAT_DEV, "Образование: развитие", "Education: development"), (CAT_DEV + "_desc", CAT_DEV_DESC, None),
         (CAT_SIMP, "Образование: упрощение", "Education: simplification"), (CAT_SIMP + "_desc", CAT_SIMP_DESC, None)]
    for k, n, d, *_ in ATTRACT + [COOP]:
        L += [(k, MARK_UP + n, None), (k + "_desc", d, None)]
    for k, n, d, *_ in SIMP:
        L += [(k, MARK_DOWN + n, None), (k + "_desc", d, None)]
    L += [
        ("ktits_edu_tt_kaz", "Ставке Казуала специалисты не нужны", "Kazual's Stavka needs no specialists"),
        ("ktits_edu_req_big", "Крупная страна (та, у которой есть выделяемые государства)", "A big country (one with releasable states)"),
        ("ktits_edu_tt_coop", "Выбранной стране уйдёт предложение о сотрудничестве. Если она согласится: у нас иностранных специалистов §G+15§! тыс., у неё §G+5§! тыс. Если откажет, политическая власть не вернётся.",
         "The chosen country gets a cooperation offer. If it accepts: foreign specialists §G+15§! k for us, §G+5§! k for it. If it refuses, political power is not refunded."),
        ("ktits_edu_req_for10", "Иностранных специалистов не меньше §Y10§! (сейчас [?ktits_spec_foreign|0])", "Foreign specialists at least §Y10§! (now [?ktits_spec_foreign|0])"),
        ("ktits_edu_req_refuge", "У соседа идёт война или ступень Казуальности не ниже §Y3§!", "A neighbour is at war or has a Casuality tier of at least §Y3§!"),
        ("ktits_edu_req_totalitarian", "Правитель: тотальный фашизм или тотальный коммунизм", "Ruler: total fascism or total communism"),
        ("ktits_edu_tt_mentor", "На 180 дней иностранные специалисты становятся нашими по §G10 %§! в месяц вместо 5 %.", "For 180 days §G10%§! of foreign specialists a month become own instead of 5%."),
    ]
    for full in (5, 10, 20):
        L.append((f"ktits_edu_req_own{full}", f"Наших специалистов не меньше §Y{full}§! (сейчас [?ktits_spec_own|0])", f"Own specialists at least §Y{full}§! (now [?ktits_spec_own|0])"))
    L += [
        ("ktits_edu_tt_ktits_edu_simp_1", "Наши специалисты: §R-5§! тыс. (§R-3§! после фокуса «Своими силами»). +50 политической власти.", "Own specialists: §R-5§! k (§R-3§! after the focus). +50 political power."),
        ("ktits_edu_tt_ktits_edu_simp_2", "Наши специалисты: §R-10§! тыс. (§R-5§! после фокуса «Своими силами»). Пополнение §G+3 %§! на 180 дней.", "Own specialists: §R-10§! k (§R-5§! after the focus). Replenishment §G+3%§! for 180 days."),
        ("ktits_edu_tt_ktits_edu_simp_3", "Наши специалисты: §R-20§! тыс. (§R-10§! после фокуса «Своими силами»). Иностранные специалисты: §R0§!. Поддержка войны §G+10 %§!, стабильность §R-5 %§!.",
         "Own specialists: §R-20§! k (§R-10§! after the focus). Foreign specialists: §R0§!. War support §G+10%§!, stability §R-5%§!."),
        (SP_WARE[0], "Образование: " + SP_WARE[1], None), (SP_WARE[0] + "_desc", SP_WARE[2], None),
    ]
    L += tt_loc()
    L += [(k, r, None) for k, r in EVENT_LOC]
    return L


def events_text():
    """events of the cooperation treaty: 1 = offer to the target (options accept / refuse), 2 = answer 'accepted' to the sender, 3 = answer 'refused' to the sender"""
    pic = "GFX_report_event_ktits_casuality"
    return f"""# cooperation treaty (docs/global_mechanics/Education.md); generated by tools/make_education.py, do not edit by hand
add_namespace = ktits_edu

# the target of the decision ktits_edu_coop: FROM = the sender
country_event = {{
@tid = ktits_edu.1
@ttitle = ktits_edu.1.t
@tdesc = ktits_edu.1.d
@tpicture = {pic}
@tis_triggered_only = yes

@toption = {{
@t@tname = ktits_edu.1.a
@t@tai_chance = {{
@t@t@tbase = 10
@t@t@tmodifier = {{ factor = 0 has_opinion = {{ target = FROM value < 0 }} }}
@t@t@tmodifier = {{
@t@t@t@tfactor = 0
@t@t@t@tis_in_faction = yes
@t@t@t@tFROM = {{ is_in_faction = yes }}
@t@t@t@tNOT = {{ is_in_faction_with = FROM }}
@t@t@t}}
@t@t}}
{spec(0, 5, "@t@t")}@t@tFROM = {{ country_event = {{ id = ktits_edu.2 }} }}
@t}}
@toption = {{
@t@tname = ktits_edu.1.b
@t@tai_chance = {{ base = 1 }}
@t@tFROM = {{ country_event = {{ id = ktits_edu.3 }} }}
@t}}
}}

# to the sender: accepted
country_event = {{
@tid = ktits_edu.2
@ttitle = ktits_edu.2.t
@tdesc = ktits_edu.2.d
@tpicture = {pic}
@tis_triggered_only = yes

@toption = {{
@t@tname = ktits_edu.2.a
{spec(0, 15, "@t@t")}@t}}
}}

# to the sender: refused (the political power is not refunded)
country_event = {{
@tid = ktits_edu.3
@ttitle = ktits_edu.3.t
@tdesc = ktits_edu.3.d
@tpicture = {pic}
@tis_triggered_only = yes

@toption = {{
@t@tname = ktits_edu.3.a
@t}}
}}
""".replace("@t", chr(9)).replace("@n", chr(10))


EVENT_LOC = [  # key, ru text (INVENTED flavour, docs/lore/Invented-Lore.md)
    ("ktits_edu.1.t", "Предложение о сотрудничестве"),
    ("ktits_edu.1.d", "Министр просвещения страны [From.GetName] прислал проект договора: обмен учёными, открытые лаборатории и общие конференции. Взамен просят только уважения и пару свободных кафедр. Решать нам, и торопиться некуда: учёные народ терпеливый."),
    ("ktits_edu.1.a", "Согласиться"),
    ("ktits_edu.1.b", "Отказать"),
    ("ktits_edu.2.t", "Договор подписан"),
    ("ktits_edu.2.d", "Страна [From.GetName] приняла наше предложение. В лабораториях меняют таблички, в общежитиях ищут свободные койки, а первые иностранные специалисты уже ищут, где здесь можно поесть."),
    ("ktits_edu.2.a", "Добро пожаловать"),
    ("ktits_edu.3.t", "Договор отклонён"),
    ("ktits_edu.3.d", "Страна [From.GetName] вежливо отказалась. Проект договора вернулся с пометкой «рассмотрено», а потраченную политическую власть уже не вернуть. Учёные пожимают плечами и пишут новые черновики."),
    ("ktits_edu.3.a", "Жаль"),
]
