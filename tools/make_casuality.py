"""Global mechanic "Казуальность" (docs/lore/Contries-Description.md, docs/global_mechanics/Casuality-Mechanic.md): a 0..100 scale in every country except Казуалия (variable ktits_casuality, starts at 0).

 * 4 tier spirits ktits_cas_1..4 with industry debuffs (laziness); swapped automatically when the scale changes;
 * decisions to fight it (-10, -20) or to support it (+10, +20), each country may use them (Казуалия excluded: its own mechanic, later);
 * at 100 the country "falls into casuality": event, ruling party casuality, the country becomes a puppet of Казуалия;
 * every country gets a casuality-group leader (needed by the game when the ruling party changes).
Values, names and texts are INVENTED (docs/lore/Invented-Lore.md, docs/global_mechanics/Casuality-Mechanic.md). Pictures: no_commit/image.jpg is a placeholder, converted to PNG sprites.
Writes: common/scripted_effects|scripted_triggers|ideas|decisions(+categories), events, localisation ru/en, interface/ktits_casuality.gfx,
gfx/interface/ktits/*.png, common/characters/<TAG>.txt (leader block appended).
Usage: python tools/make_casuality.py [--mod PATH] [--image PATH]
"""
import argparse, re
from pathlib import Path
from PIL import Image
import lore_data as L
from make_splits import SPLITS  # parents of releasable countries K01-K35 = "big" countries (docs/countries/Splits.md)

CAS_TT = set()  # scale deltas used in decisions/events -> tooltip loc keys ktits_cas_tt_p10 / ktits_cas_tt_m5
def tt_key(d):
    return "ktits_cas_tt_" + ("p%d" % d if d > 0 else "m%d" % -d)
def cas_tt(d, tabs="\t\t\t"):
    CAS_TT.add(d)
    return tabs + "custom_effect_tooltip = " + tt_key(d) + "\n"

TIERS = [  # (key, ru name, ru desc, lower bound, industrial_capacity_factory, production_speed_buildings_factor, research_speed_factor, stability_factor) docs/global_mechanics/Casuality-Mechanic.md (numbers by the author); texts of 4, 5 INVENTED
    (1, "Ленца", "Граждане начинают опаздывать, недоделывать работу.", 1, -0.03, -0.05, 0.0, 0.0),
    (2, "Расслабон", "Люди расслаблены, некоторые этим пользуются.", 25, -0.06, -0.10, 0.0, 0.0),
    (3, "Болотная лень", "Переходный период: заводы встали, люди ничего не делают. Страна встала.", 50, -0.95, -0.95, -0.95, -0.50),
    (4, "Дурманище", "Болотный дурман окутал страну: у станков почти никого, а те, кто есть, ждут, пока всё случится само. Заводы дымят вхолостую, наука дремлет, но государство каким-то чудом держится.", 75, -0.65, -0.65, -0.65, -0.65),
    (5, "Казуальная идилия", "Общество достигло просветлённого безделья: заводы едва шевелятся, науке не до открытий, зато люди спокойны, довольны и ни о чём не тревожатся. Ещё шаг - и страна уйдёт в Казуальность.", 95, -0.10, -0.15, -0.50, 0.80),
]
# decisions: key, ru name, ru desc, delta, cost PP, cooldown days, side, min scale value (0 = none), extra effect lines  (docs/global_mechanics/Casuality-Mechanic.md table by the author; the new ones INVENTED)
# key, ru name, ru desc, delta, cost PP, cooldown days, side, min scale value (0 = none), extra effect token (EXTRA)  docs/global_mechanics/Casuality-Mechanic.md: the six first rows are the author's table, the rest INVENTED
EXTRA = {
    'campaign': ['set_country_flag = { flag = ktits_cas_campaign days = 180 value = 1 }', 'set_variable = { var = ktits_cas_tick value = 0 }'],
    'st5': ['add_stability = -0.05'],
    'st10': ['add_stability = -0.10'],
    'last': ['add_war_support = -0.10', 'add_stability = -0.10'],
    'pp': ['add_political_power = 25'],
    'siesta': ['add_stability = 0.03'],
    'pop': ['add_popularity = { ideology = casuality popularity = 0.05 }'],
    'pop2': ['add_popularity = { ideology = casuality popularity = 0.02 }'],
    'pop3': ['add_popularity = { ideology = casuality popularity = 0.03 }'],
    'pop10': ['add_popularity = { ideology = casuality popularity = 0.10 }'],
}
DECISIONS = [
    ('ktits_cas_fight_1', 'Кампания «Подъём на труд!»', 'Агитация за труд и дисциплину: плакаты, собрания, ударные бригады. Казуальность в стране падает на 10.', -10, 50, 30, 'fight', 0, ''),
    ('ktits_cas_fight_2', 'Провести переговоры с профсоюзами', 'Договориться с профсоюзами о нормах выработки и графиках. Казуальность в стране падает на 20.', -20, 100, 90, 'fight', 0, ''),
    ('ktits_cas_fight_0', 'Противодействие, труд и власть!', 'Государство берёт Казуальность под постоянный надзор: следующие полгода каждые 15 дней шкала падает на 10.', 0, 150, 180, 'fight', 0, 'campaign'),
    ('ktits_cas_fight_3', 'Чрезвычайный трудовой режим', 'Заводы переходят на казарменный график, прогульщиков наказывают. Казуальность падает на 30, но стабильность падает. Доступно, когда шкала не ниже 50.', -30, 200, 120, 'fight', 50, 'st5'),
    ('ktits_cas_fight_4', 'Осушение болот', 'Масштабная программа осушения: вода уходит, а вместе с ней и дурман. Казуальность падает на 40, стабильность страдает от переселений. Доступно, когда шкала не ниже 75.', -40, 300, 180, 'fight', 75, 'st10'),
    ('ktits_cas_fight_5', 'Последний рывок', 'Отчаянная мобилизация всех сил накануне падения. Казуальность падает на 50, но армия и народ изматываются. Доступно, когда шкала не ниже 95.', -50, 400, 365, 'fight', 95, 'last'),
    ('ktits_cas_support_1', 'Праздник безделья', 'Всенародный выходной: Казуальность растёт на 10, власти достаётся немного политического веса.', 10, 0, 30, 'support', 0, 'pp+pop2'),
    ('ktits_cas_support_2', 'Культ болота', 'Официально поощрять болотный образ жизни: ритуальные посиделки у воды. Казуальность растёт на 10, партия Казуальности набирает популярность.', 10, 0, 90, 'support', 0, 'pop3'),
    ('ktits_cas_support_3', 'Культ Священного-Архо-Казуала', 'Культ создателя Казуальности даёт людям смысл ничего не делать. Казуальность растёт на 20. Доступно, когда шкала выше 25.', 20, 0, 90, 'support', 26, 'pop'),
    ('ktits_cas_support_4', 'Всеобщая сиеста', 'Дневной сон по распоряжению властей: работа встаёт, люди довольны. Казуальность растёт на 15, стабильность немного растёт. Доступно, когда шкала не ниже 50.', 15, 0, 60, 'support', 50, 'siesta+pop2'),
    ('ktits_cas_support_5', 'Присяга Ставке Казуала', 'Страна присягает Ставке Казуала. Казуальность растёт на 20, партия Казуальности набирает популярность. Доступно, когда шкала не ниже 75.', 20, 0, 120, 'support', 75, 'pop'),
    ('ktits_cas_support_6', 'Дома Безделья', 'По стране открываются клубы, где можно легально ничего не делать: бесплатный чай, мягкие кресла и лекции о Священном-Архо-Казуале. Партия Казуальности вербует посетителей прямо у входа. Казуальность растёт на 5, популярность партии растёт на 10 %.', 5, 50, 120, 'support', 0, 'pop10'),
]
BIG = sorted(SPLITS)  # tags of big countries
# AI weights: fight decisions prefer the stronger effect at a high scale, support decisions follow docs/global_mechanics/Casuality-Mechanic.md priority
AI_W = {'ktits_cas_fight_5': 60, 'ktits_cas_fight_4': 50, 'ktits_cas_fight_3': 40, 'ktits_cas_fight_0': 30, 'ktits_cas_fight_2': 20, 'ktits_cas_fight_1': 10,
        'ktits_cas_support_5': 60, 'ktits_cas_support_6': 50, 'ktits_cas_support_3': 40, 'ktits_cas_support_4': 30, 'ktits_cas_support_2': 20, 'ktits_cas_support_1': 10}
RAPP = "ktits_cas_ai_rapprochement"   # country flag: AI course "Сближение" (no flag = course "Борьба")
# Game rule "Глобальная Казуальность" (custom game rules screen, group AI behavior): (option, ru name, en name, start chance % of the course "Сближение", multiplier of the 180-day chance)
# Only without the historical AI focus. Default = author's 5 % rule; the other options and numbers are INVENTED (docs/lore/Invented-Lore.md, docs/global_mechanics/Casuality-Mechanic.md)
CAS_RULE = "ktits_global_casuality"
CAS_RULE_OPTS = [("DEFAULT", "Крайне низкая", "Extremely low", 5, 1), ("RAISED", "Повышенная", "Raised", 15, 2),
                 ("HIGH", "Высокая", "High", 35, 4), ("EXTREME", "Всемирное болото", "World swamp", 70, 8)]
EDU_MULT = [1.5, 1.25, 1.0, 0.85, 0.7, 0.5]  # growth multiplier by ktits_edu_0..5 (docs/global_mechanics/Casuality-Mechanic.md)
FIGHT_KEYS = [d[0] for d in DECISIONS if d[6] == 'fight']

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
ap.add_argument("--image", default=str(L.REPO / "no_commit/image.jpg"))
a = ap.parse_args()
M = Path(a.mod)
info = L.load_mod(M)
lore2tag = {lt: t for t, lt in info["tag2lore"].items()}
KAZ = lore2tag["CSL"]
def w(rel, text, enc="utf-8"):
    p = M / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding=enc, newline="\n")

def rule_opt_effects(tabs, fmt):
    """one `if = { limit = { has_game_rule ... } <effect> }` per rule option; fmt takes (start %, multiplier)"""
    return "\n".join(f"{tabs}if = {{ limit = {{ has_game_rule = {{ rule = {CAS_RULE} option = {o} }} }} {fmt(s, m)} }}" for o, _r, _e, s, m in CAS_RULE_OPTS if fmt(s, m))
RULE_START = rule_opt_effects("\t\t", lambda s, m: f"set_variable = {{ var = ktits_cas_ai_chance value = {s} }}")
RULE_MULT = rule_opt_effects("\t\t", lambda s, m: f"multiply_variable = {{ var = ktits_cas_ai_chance value = {m} }}" if m != 1 else "")

# ---- triggers / effects ----
w("common/scripted_triggers/ktits_casuality_triggers.txt", f"""ktits_is_kazualia = {{
	original_tag = {KAZ}
}}

# big country = has releasable countries K01-K35 (docs/countries/Splits.md)
ktits_is_big_country = {{
	OR = {{
""" + "".join(f"		original_tag = {b}"+chr(10) for b in BIG) + """	}
}
""")
upd = "".join(f"""	if = {{
		limit = {{ has_idea = ktits_cas_{k} }}
		remove_ideas = ktits_cas_{k}
	}}
""" for k, *_ in TIERS)
for k, _, _, lo, *_ in TIERS:
    hi = next((t[3] for t in TIERS if t[0] == k + 1), 100)
    upd += f"""	if = {{
		limit = {{
			check_variable = {{ var = ktits_casuality value = {lo} compare = greater_than_or_equals }}
			check_variable = {{ var = ktits_casuality value = {hi} compare = less_than }}
		}}
		add_ideas = ktits_cas_{k}
	}}
"""
# notifications 30 (scale >= 50) and 31 (scale >= 95): once per state; the flag is dropped when the scale leaves the state
def notif(eid, lo):
    ge = f"check_variable = {{ var = ktits_casuality value = {lo} compare = greater_than_or_equals }}"
    return f"""	if = {{
		limit = {{
			{ge}
			check_variable = {{ var = ktits_casuality value = 100 compare = less_than }}
			NOT = {{ has_country_flag = ktits_cas_n{eid} }}
		}}
		set_country_flag = ktits_cas_n{eid}
		country_event = {{ id = ktits_casuality.{eid} }}
	}}
	if = {{
		limit = {{
			check_variable = {{ var = ktits_casuality value = {lo} compare = less_than }}
			has_country_flag = ktits_cas_n{eid}
		}}
		clear_country_flag = ktits_cas_n{eid}
	}}
"""
w("common/scripted_effects/ktits_casuality_effects.txt", f"""ktits_casuality_update = {{
{upd}{notif(30, 50)}{notif(31, 95)}	if = {{
		limit = {{
			check_variable = {{ var = ktits_casuality value = 100 compare = greater_than_or_equals }}
			NOT = {{ has_country_flag = ktits_casuality_fallen }}
			has_capitulated = no
		}}
		set_country_flag = ktits_casuality_fallen
		country_event = {{ id = ktits_casuality.1 }}
	}}
}}

# author's rule: puppets of Kazualia have education level 0; the level is NOT restored after the country stops being a puppet (invented)
ktits_kaz_puppet_education = {{
	if = {{
		limit = {{
			is_puppet_of = {KAZ}
			NOT = {{ has_idea = ktits_edu_0 }}
		}}
{"".join(f"{chr(9)}{chr(9)}remove_ideas = ktits_edu_{i}{chr(10)}" for i in range(1, 6))}		add_ideas = ktits_edu_0
	}}
}}

ktits_casuality_change = {{
	add_to_variable = {{ var = ktits_casuality value = $VALUE$ }}
	clamp_variable = {{ var = ktits_casuality min = 0 max = 100 }}
	ktits_casuality_update = yes
	ktits_casuality_call = yes
}}
""")

# campaign "Противодействие, труд и власть!": while the flag lives (180 days) the scale falls by 10 every 15 days (on_daily of the country)
w("common/scripted_effects/ktits_casuality_daily_effects.txt", """ktits_casuality_daily = {
	if = {
		limit = { has_country_flag = ktits_cas_campaign }
		add_to_variable = { var = ktits_cas_tick value = 1 }
		if = {
			limit = { check_variable = { var = ktits_cas_tick value = 15 compare = greater_than_or_equals } }
			set_variable = { var = ktits_cas_tick value = 0 }
			add_to_variable = { var = ktits_casuality value = -10 }
			clamp_variable = { var = ktits_casuality min = 0 max = 100 }
			ktits_casuality_update = yes
		}
	}
}
""")

# ---- monthly scale change, costs, war with Kazualia, AI course (docs/global_mechanics/Casuality-Mechanic.md) ----
def edu_chain(body_fn):
    """one 'if' per education level ktits_edu_0..5"""
    return "".join(f"\tif = {{\n\t\tlimit = {{ has_idea = ktits_edu_{i} }}\n{body_fn(i)}\t}}\n" for i in range(6))
COSTS = "".join(
    f"\tset_variable = {{ var = ktits_cas_cost_{k.rsplit('_', 1)[1]} value = {next(d[4] for d in DECISIONS if d[0] == k)} }}\n" for k in FIGHT_KEYS) + \
    "\tif = {\n\t\tlimit = { OR = { has_idea = ktits_edu_4 has_idea = ktits_edu_5 } }\n" + "".join(
    f"\t\tmultiply_variable = {{ var = ktits_cas_cost_{k.rsplit('_', 1)[1]} value = 0.75 }}\n\t\tround_variable = ktits_cas_cost_{k.rsplit('_', 1)[1]}\n" for k in FIGHT_KEYS) + "\t}\n" + \
    "\tif = {\n\t\tlimit = { OR = { has_idea = ktits_edu_0 has_idea = ktits_edu_1 } }\n" + "".join(
    f"\t\tmultiply_variable = {{ var = ktits_cas_cost_{k.rsplit('_', 1)[1]} value = 1.25 }}\n\t\tround_variable = ktits_cas_cost_{k.rsplit('_', 1)[1]}\n" for k in FIGHT_KEYS) + "\t}\n"
POP_STEPS = "".join(
    f"\tif = {{\n\t\tlimit = {{ casuality > {i / 10 - 0.001:.3f} }}\n\t\tadd_to_variable = {{ var = ktits_cas_g value = 1 }}\n\t}}\n" for i in range(1, 11))
w("common/scripted_effects/ktits_casuality_monthly_effects.txt", f"""# edu cost of the fight decisions: -25 % PP at education 4-5, +25 % at 0-1 (the decisions read the variables ktits_cas_cost_N)
ktits_casuality_costs = {{
{COSTS}}}

# growth of the scale = (neighbour Kazualia +2, neighbours-puppets of Kazualia +1 each (max 3), +1 per full 10 % of the casuality party) x education multiplier, rounded down
ktits_casuality_growth = {{
	set_variable = {{ var = ktits_cas_g value = 0 }}
	set_variable = {{ var = ktits_cas_n value = 0 }}
	if = {{
		limit = {{ any_neighbor_country = {{ ktits_is_kazualia = yes }} }}
		add_to_variable = {{ var = ktits_cas_g value = 2 }}
	}}
	every_neighbor_country = {{
		limit = {{ is_puppet_of = {KAZ} }}
		PREV = {{ add_to_variable = {{ var = ktits_cas_n value = 1 }} }}
	}}
	clamp_variable = {{ var = ktits_cas_n min = 0 max = 3 }}
	add_to_variable = {{ var = ktits_cas_g value = ktits_cas_n }}
{POP_STEPS}{edu_chain(lambda i: f"		multiply_variable = {{ var = ktits_cas_g value = {EDU_MULT[i]} }}" + chr(10))}	# floor: -0.49 then round to the nearest integer (fractions here are at most .95)
	add_to_variable = {{ var = ktits_cas_g value = -0.49 }}
	round_variable = ktits_cas_g
	clamp_variable = {{ var = ktits_cas_g min = 0 max = 100 }}
	if = {{
		limit = {{ check_variable = {{ var = ktits_cas_g value = 1 compare = greater_than_or_equals }} }}
		add_to_variable = {{ var = ktits_casuality value = ktits_cas_g }}
		clamp_variable = {{ var = ktits_casuality min = 0 max = 100 }}
		ktits_casuality_update = yes
	}}
}}

# national spirit "Зов болот": war with Kazualia and scale > 80
ktits_casuality_call = {{
	if = {{
		limit = {{
			country_exists = {KAZ}
			has_war_with = {KAZ}
			check_variable = {{ var = ktits_casuality value = 80 compare = greater_than }}
		}}
		if = {{
			limit = {{ NOT = {{ has_idea = ktits_cas_call_1 }} }}
			add_ideas = ktits_cas_call_1
			if = {{
				limit = {{ NOT = {{ has_country_flag = ktits_cas_n34 }} }}
				set_country_flag = ktits_cas_n34
				country_event = {{ id = ktits_casuality.34 }}
			}}
		}}
	}}
	if = {{
		limit = {{
			has_idea = ktits_cas_call_1
			OR = {{
				NOT = {{ country_exists = {KAZ} }}
				NOT = {{ has_war_with = {KAZ} }}
				check_variable = {{ var = ktits_casuality value = 80 compare = less_than_or_equals }}
			}}
		}}
		remove_ideas = ktits_cas_call_1
		clear_country_flag = ktits_cas_n34
	}}
}}

# AI course (docs/global_mechanics/Casuality-Mechanic.md): flag {RAPP} = "Сближение", no flag = "Борьба"
ktits_casuality_ai_start = {{
	if = {{
		limit = {{
			is_ai = yes
			NOT = {{ ktits_is_kazualia = yes }}
			is_historical_focus_on = no
			NOT = {{ ktits_is_big_country = yes }}
		}}
{RULE_START}
		random = {{
			chance = ktits_cas_ai_chance
			set_country_flag = {RAPP}
		}}
	}}
}}

ktits_casuality_ai_monthly = {{
	if = {{
		limit = {{
			is_ai = yes
			has_country_flag = {RAPP}
			OR = {{
				is_historical_focus_on = yes
				ktits_is_big_country = yes
				has_war_with = {KAZ}
				AND = {{
					casuality < 0.1
					check_variable = {{ var = ktits_casuality value = 25 compare = less_than }}
				}}
			}}
		}}
		clear_country_flag = {RAPP}
	}}
	if = {{
		limit = {{
			is_ai = yes
			is_historical_focus_on = no
			NOT = {{ ktits_is_big_country = yes }}
			NOT = {{ has_country_flag = {RAPP} }}
			NOT = {{ has_country_flag = ktits_cas_ai_cd }}
		}}
		set_country_flag = {{ flag = ktits_cas_ai_cd days = 180 value = 1 }}
		set_variable = {{ var = ktits_cas_ai_chance value = 2 }}
		if = {{
			limit = {{
				OR = {{
					any_neighbor_country = {{ ktits_is_kazualia = yes }}
					any_neighbor_country = {{ is_puppet_of = {KAZ} }}
				}}
			}}
			add_to_variable = {{ var = ktits_cas_ai_chance value = 3 }}
		}}
		if = {{
			limit = {{ check_variable = {{ var = ktits_casuality value = 50 compare = greater_than_or_equals }} }}
			add_to_variable = {{ var = ktits_cas_ai_chance value = 5 }}
		}}
		if = {{
			limit = {{ casuality > 0.299 }}
			add_to_variable = {{ var = ktits_cas_ai_chance value = 5 }}
		}}
		if = {{
			limit = {{ OR = {{ has_idea = ktits_edu_0 has_idea = ktits_edu_1 }} }}
			add_to_variable = {{ var = ktits_cas_ai_chance value = 2 }}
		}}
		if = {{
			limit = {{ OR = {{ has_idea = ktits_edu_4 has_idea = ktits_edu_5 }} }}
			add_to_variable = {{ var = ktits_cas_ai_chance value = -2 }}
		}}
{RULE_MULT}
		clamp_variable = {{ var = ktits_cas_ai_chance min = 0 max = 100 }}
		random = {{
			chance = ktits_cas_ai_chance
			set_country_flag = {RAPP}
		}}
	}}
}}

# scale "Партия бездельников" (event 35): casuality popularity >= 30 %, once per state
ktits_casuality_party_notify = {{
	if = {{
		limit = {{
			casuality > 0.299
			NOT = {{ has_country_flag = ktits_cas_n35 }}
		}}
		set_country_flag = ktits_cas_n35
		country_event = {{ id = ktits_casuality.35 }}
	}}
	if = {{
		limit = {{
			casuality < 0.25
			has_country_flag = ktits_cas_n35
		}}
		clear_country_flag = ktits_cas_n35
	}}
}}

ktits_casuality_monthly = {{
	ktits_casuality_costs = yes
	if = {{
		limit = {{ check_variable = {{ var = ktits_casuality value = 100 compare = greater_than_or_equals }} }}
		ktits_casuality_update = yes
	}}
	ktits_casuality_growth = yes
	ktits_casuality_call = yes
	ktits_casuality_party_notify = yes
	ktits_casuality_ai_monthly = yes
}}
""")
w("common/on_actions/ktits_casuality_on_actions.txt", """on_actions = {
	on_startup = {
		effect = {
			if = {
				limit = { NOT = { ktits_is_kazualia = yes } }
				ktits_casuality_costs = yes
				ktits_casuality_ai_start = yes
			}
		}
	}
	on_monthly = {
		effect = {
		# safety net for every country, fallen ones included (author's rule: puppets of Kazualia have education 0)
		ktits_kaz_puppet_education = yes
			if = {
				limit = {
					NOT = { ktits_is_kazualia = yes }
					NOT = { has_country_flag = ktits_casuality_fallen }
				}
				ktits_casuality_monthly = yes
			}
		}
	}
	on_weekly = {
		effect = {
			if = {
				limit = {
					NOT = { ktits_is_kazualia = yes }
					NOT = { has_country_flag = ktits_casuality_fallen }
				}
				ktits_casuality_call = yes
			}
		}
	}
	# release through the occupied territories menu is forbidden while the releasing country's scale > 50 (docs/global_mechanics/Casuality-Mechanic.md): the release is undone
	# ROOT = released country, FROM = overlord (vanilla 12_wuw_on_actions.txt)
	on_release_as_puppet = {
		effect = {
			if = {
				limit = {
					FROM = {
						NOT = { ktits_is_kazualia = yes }
						check_variable = { var = ktits_casuality value = 50 compare = greater_than }
					}
				}
				FROM = {
					annex_country = { target = ROOT transfer_troops = yes }
					country_event = { id = ktits_casuality.36 }
				}
			}
		}
	}
	on_war_relation_added = {
		effect = {
			if = {
				limit = { NOT = { ktits_is_kazualia = yes } }
				ktits_casuality_call = yes
			}
			FROM = {
				if = {
					limit = { NOT = { ktits_is_kazualia = yes } }
					ktits_casuality_call = yes
				}
			}
		}
	}
	on_daily = {
		effect = {
			if = {
				limit = { has_country_flag = ktits_cas_campaign }
				ktits_casuality_daily = yes
			}
		}
	}
}
""")

# ---- ideas ----
w("common/ideas/ktits_casuality.txt", "ideas = {\n\tcountry = {\n" + "".join(f"""		ktits_cas_{k} = {{
			picture = ktits_casuality
			allowed = {{ always = no }}
			allowed_civil_war = {{ always = yes }}
			removal_cost = -1
			modifier = {{
				industrial_capacity_factory = {ic}
				production_speed_buildings_factor = {pb}
				research_speed_factor = {rs}
				stability_factor = {st}
			}}
		}}
""" for k, _, _, _, ic, pb, rs, st in TIERS) + "\t}\n}\n")

# "Зов болот" (docs/global_mechanics/Casuality-Mechanic.md): stage 1 given by the monthly check, stage 2 = an extra timed spirit from the Kazualia decision (stacks to -45 % attack / -30 % defence)
w("common/ideas/ktits_casuality_call.txt", """ideas = {
	country = {
		ktits_cas_call_1 = {
			picture = ktits_casuality
			allowed = { always = no }
			allowed_civil_war = { always = yes }
			removal_cost = -1
			modifier = {
				army_attack_factor = -0.30
				army_defence_factor = -0.20
				war_support_factor = -0.25
				surrender_limit = -0.20
			}
		}
		ktits_cas_call_2 = {
			picture = ktits_casuality
			allowed = { always = no }
			allowed_civil_war = { always = yes }
			removal_cost = -1
			modifier = {
				army_attack_factor = -0.15
				army_defence_factor = -0.10
			}
		}
	}
}
""")

# ---- decisions ----
w("common/decisions/categories/ktits_casuality_categories.txt", """ktits_casuality_category = {
	icon = generic_propaganda
	picture = GFX_decision_cat_picture_ktits_casuality
	scripted_gui = ktits_casuality_ui
	visible = {
		NOT = { ktits_is_kazualia = yes }
	}
}
""")
dec = "ktits_casuality_category = {\n"
for key, _, _, delta, cost, cd, side, lo, ex in DECISIONS:
    extra = "".join("\t\t\t" + e + "\n" for k_ in ex.split("+") for e in EXTRA.get(k_, []))
    avail = ("check_variable = { var = ktits_casuality value = %d compare = greater_than_or_equals }" % max(lo, 1) if side == "fight"
             else "check_variable = { var = ktits_casuality value = 100 compare = less_than }")
    if side != "fight" and lo:
        avail += "\n\t\t\tcheck_variable = { var = ktits_casuality value = %d compare = greater_than_or_equals }" % lo
    cost_var = "ktits_cas_cost_" + key.rsplit("_", 1)[1]
    if side == "fight":   # the cost depends on education (+-25 %): variable cost set by ktits_casuality_costs
        avail += "\n\t\t\tcheck_variable = { var = %s value = 1 compare = greater_than_or_equals }" % cost_var
    # tooltip "Казуальность: +N" (variable changes are not shown in tooltips by the game)
    # AI: course "Борьба" takes fight decisions, "Сближение" takes support decisions (weights AI_W, docs/global_mechanics/Casuality-Mechanic.md)
    if side == "fight":
        ai = f"base = {AI_W[key]}\n\t\t\tmodifier = {{ factor = 0 has_country_flag = {RAPP} }}"
    else:
        ai = f"base = {AI_W[key]}\n\t\t\tmodifier = {{ factor = 0 NOT = {{ has_country_flag = {RAPP} }} }}"
    delta_eff = "" if delta == 0 else (cas_tt(delta) + "\t\t\tadd_to_variable = { var = ktits_casuality value = %d }\n\t\t\tclamp_variable = { var = ktits_casuality min = 0 max = 100 }\n\t\t\tktits_casuality_update = yes\n" % delta)
    dec += f"""
	{key} = {{
		icon = ktits_casuality
		visible = {{ NOT = {{ ktits_is_kazualia = yes }} }}
		available = {{
			{avail}
			NOT = {{ has_country_flag = ktits_casuality_fallen }}
		}}
		cost = {cost_var if side == "fight" else cost}
		days_re_enable = {cd}
		fire_only_once = no
		complete_effect = {{
{extra}{delta_eff}		}}
		ai_will_do = {{
			{ai}
		}}
	}}
"""
w("common/decisions/ktits_casuality.txt", dec + "}\n")

# Kazualia: targeted decision "Позвать с болот" (docs/global_mechanics/Casuality-Mechanic.md, war with Kazualia)
w("common/decisions/categories/ktits_casuality_kaz_categories.txt", """ktits_casuality_kaz_category = {
	icon = generic_propaganda
	picture = GFX_decision_cat_picture_ktits_casuality
	visible = {
		ktits_is_kazualia = yes
	}
}
""")
w("common/decisions/ktits_casuality_kaz.txt", """ktits_casuality_kaz_category = {

	ktits_cas_call_swamp = {
		icon = ktits_casuality
		visible = { ktits_is_kazualia = yes }
		available = { ktits_is_kazualia = yes }
		target_trigger = {
			FROM = {
				has_war_with = ROOT
				NOT = { has_country_flag = ktits_casuality_fallen }
				NOT = { has_idea = ktits_cas_call_2 }
				check_variable = { var = ktits_casuality value = 80 compare = greater_than }
			}
		}
		cost = 75
		days_re_enable = 90
		fire_only_once = no
		complete_effect = {
			FROM = {
				custom_effect_tooltip = ktits_cas_tt_p10
				add_to_variable = { var = ktits_casuality value = 10 }
				clamp_variable = { var = ktits_casuality min = 0 max = 100 }
				ktits_casuality_update = yes
				add_timed_idea = { idea = ktits_cas_call_2 days = 60 }
			}
		}
		ai_will_do = { base = 10 }
	}
}
""")

# ---- return of conquered lands on the fall (author's rule, docs/global_mechanics/Casuality-Mechanic.md) ----
# tags checked in order: a state that is a core of several countries goes to the first one (deterministic, INVENTED choice).
# Kazualia and the parts K01-K35 are skipped (the parts are handled by ktits_split_on_fall).
RET_TAGS = [t for t in sorted(info["tags"]) if t != KAZ and not re.fullmatch(r"K\d\d", t)]
ret = ("# called in the immediate block of ktits_casuality.1 (scope = the falling country): every owned state that is not a core of it\n"
       "# but is a core of another country goes to that country; a non-existing country is released first (release = TAG as in vanilla common/decisions/YUG.txt)\n"
       "ktits_return_lands = {\n")
for t in RET_TAGS:
    ret += ("\tif = {\n\t\tlimit = {\n\t\t\tNOT = { original_tag = %s }\n\t\t\tany_owned_state = {\n\t\t\t\tis_core_of = %s\n\t\t\t\tNOT = { is_core_of = ROOT }\n\t\t\t}\n\t\t}\n"
            "\t\tif = {\n\t\t\tlimit = { %s = { exists = no } }\n\t\t\trelease = %s\n\t\t\tend_puppet = %s\n\t\t}\n"
            "\t\tevery_owned_state = {\n\t\t\tlimit = {\n\t\t\t\tis_core_of = %s\n\t\t\t\tNOT = { is_core_of = ROOT }\n\t\t\t}\n\t\t\ttransfer_state_to = %s\n\t\t}\n\t}\n") % ((t,) * 7)
ret += "}\n"
w("common/scripted_effects/ktits_casuality_return_effects.txt", ret)

# ---- event: a country falls into casuality ----
w("events/ktits_casuality_events.txt", f"""add_namespace = ktits_casuality

country_event = {{
	id = ktits_casuality.1
	title = ktits_casuality.1.t
	desc = ktits_casuality.1.d
	picture = GFX_report_event_ktits_casuality
	is_triggered_only = yes
	fire_only_once = no

	immediate = {{
		hidden_effect = {{
			# subjects: scale > 80 -> puppet of Kazualia, others -> fully independent (then event 33)
			every_subject_country = {{
				if = {{
					limit = {{
						check_variable = {{ var = ktits_casuality value = 80 compare = greater_than }}
						country_exists = {KAZ}
					}}
					ROOT = {{ end_puppet = PREV }}
					{KAZ} = {{ puppet = PREV }}
				}}
				if = {{
					limit = {{
						OR = {{
							check_variable = {{ var = ktits_casuality value = 80 compare = less_than_or_equals }}
							NOT = {{ country_exists = {KAZ} }}
						}}
					}}
					ROOT = {{ end_puppet = PREV }}
					country_event = {{ id = ktits_casuality.33 }}
				}}
			}}
			if = {{
				limit = {{ is_subject = yes }}
				overlord = {{ end_puppet = PREV }}
			}}
			# conquered lands go back to their original countries (docs/global_mechanics/Casuality-Mechanic.md); must run before the split of big countries
			ktits_return_lands = yes
			set_politics = {{ ruling_party = casuality }}
			add_popularity = {{ ideology = casuality popularity = 0.5 }}
			ktits_split_on_fall = yes
			if = {{
				limit = {{ country_exists = {KAZ} }}
				{KAZ} = {{ puppet = ROOT }}
			}}
			# author's rule: puppets of Kazualia (ROOT, its former subjects, released Kxx parts) get education level 0
			if = {{
				limit = {{ country_exists = {KAZ} }}
				{KAZ} = {{
					every_subject_country = {{ ktits_kaz_puppet_education = yes }}
				}}
			}}
			# neighbours get the notification "Сосед пал"
			every_neighbor_country = {{
				limit = {{
					NOT = {{ ktits_is_kazualia = yes }}
					NOT = {{ has_country_flag = ktits_casuality_fallen }}
				}}
				country_event = {{ id = ktits_casuality.32 }}
			}}
		}}
	}}

	option = {{
		name = ktits_casuality.1.a
		custom_effect_tooltip = ktits_casuality_fall_tt
	}}
}}
""")

# ---- random events (docs/global_mechanics/Casuality-Mechanic.md, "Случайные события"; all INVENTED) ----
# (id, kind, min scale, needs Kazualia, ru title, ru text, [(option ru, delta, pp, (stab_value, days) or None, popularity or 0)])
RAND_EVENTS = [
    (10, "up", 1, False, "Туман с болот", "Утром над городами лёг тёплый туман с запахом тины. Рабочие стоят у проходных и не решаются войти: «Чего спешить, всё равно ничего не видно».",
     [("Переждём", 5, 0, None, 0), ("Объявить рабочий день", 2, -10, None, 0)]),
    (11, "up", 10, False, "Бродячий проповедник", "По сёлам ходит человек в болотных сапогах и рассказывает, что Священный-Архо-Казуал не работал ни дня и ни в чём не знал нужды. Слушают его всё охотнее.",
     [("Пусть говорит", 8, 0, None, 0), ("Арестовать", 3, 0, (-0.02, 30), 0)]),
    (12, "up", 25, False, "Урожай сам собой", "Поля, которые никто не засевал, дали урожай. Агрономы разводят руками. Крестьяне делают вывод: трудиться было необязательно.",
     [("Чудо!", 10, 0, (0.03, 60), 0), ("Засекретить", 4, -25, None, 0)]),
    (13, "up", 50, False, "Опустевший цех", "Вечерняя смена целого завода разошлась по домам ещё до гудка. План при этом выполнен - никто не может понять как.",
     [("Не трогать то, что работает", 12, 0, None, 0), ("Расследование", 5, -50, None, 0)]),
    (14, "up", 75, True, "Письмо из Казуалии", "В почтовых ящиках по всей стране появились открытки с видами болот и подписью «Приезжайте. Здесь не надо стараться».",
     [("Пусть читают", 15, 0, None, 0.03), ("Изъять почту", 6, -75, None, 0)]),
    (20, "down", 1, False, "Стахановец", "Простой токарь за смену перевыполнил норму в десять раз. Газеты печатают его портрет, а в цехах спорят, правда ли так можно.",
     [("Наградить орденом", -5, -10, None, 0), ("Скромно отметить", -2, 0, None, 0)]),
    (21, "down", 10, False, "Засуха на болотах", "Жаркое лето высушило топи. Без привычной сырости и дурмана люди будто проснулись и с удивлением смотрят на брошенные дела.",
     [("Воспользоваться моментом", -8, -25, None, 0), ("Само пройдёт", -3, 0, None, 0)]),
    (22, "down", 25, False, "Обрушение моста", "Мост, который годами «чинился сам», рухнул вместе с поездом. Страна в трауре, но многие впервые задумались, к чему ведёт безделье.",
     [("Показательный суд", -10, 0, (-0.03, 60), 0), ("Тихо отстроить", -5, -50, None, 0)]),
    (23, "down", 50, False, "Голодная зима", "Склады пусты: урожай, «который соберётся сам», так и сгнил в полях. Люди берутся за лопаты, чтобы выжить.",
     [("Трудовые отряды", -15, 0, (-0.05, 90), 0), ("Просить помощи", -8, -100, None, 0)]),
    (24, "down", 75, False, "Пробуждение", "Учитель из глухой деревни поднял учеников, затем село, затем округ. Движение «Проснись!» расходится по стране быстрее любой агитации.",
     [("Поддержать движение", -20, -75, None, 0), ("Опасно, распустить", -5, 0, (0.02, 60), 0)]),
    # notification events (docs/global_mechanics/Casuality-Mechanic.md): fired by effects, once per state; kind "note", the condition column is unused
    (30, "note", 0, False, "Страна встала", "Утром не открылся ни один завод. Министры собираются на совещание, но половина не пришла. Советники объясняют: это ещё не конец, но дальше так жить нельзя.",
     [("Бороться!", -5, -25, None, 0), ("Будь что будет", 5, 0, None, 0)]),
    (31, "note", 0, False, "Последний рубеж", "Газеты печатают одно слово: «Почти». На улицах тихо и спокойно, и именно это пугает остатки правительства.",
     [("Последний рывок готов", 0, 0, None, 0), ("Пусть будет", 2, 0, None, 0)]),
    (32, "note", 0, False, "Сосед пал", "Граница с соседом больше не охраняется: пограничники ушли рыбачить. С той стороны доносятся песни и запах костров.",
     [("Укрепить границу", -5, -50, None, 0), ("Ничего не делать", 5, 0, None, 0)]),
    (33, "note", 0, False, "Мы свободны!", "Бывший сюзерен растворился в болоте, и столица вдруг стала столицей настоящего государства. Никто не знает, что делать с этой свободой.",
     [("Строить своё", -10, -25, None, 0), ("Праздновать", 5, 0, (0.05, 60), 0)]),
    (34, "note", 0, False, "Зов болот", "Комиссары докладывают о пустых окопах. В дневниках дезертиров одно и то же: «Там тепло и не стреляют».",
     [("Расстрелы", -5, 0, (-0.05, 60), 0), ("Понять и простить", 5, 0, None, 0)]),
    (35, "note", 0, False, "Партия бездельников", "На митинге партии Казуальности никто не выступает: все лежат на траве. Митинг признан самым массовым за год.",
     [("Запретить митинги", 0, 0, (-0.03, 60), -0.05), ("Пусть лежат", 3, 0, None, 0)]),
    (36, "note", 0, False, "Некому управлять", "Мы попытались передать оккупированные земли новому правительству, но чиновники так и не пришли на церемонию. Пока Казуальность в стране выше 50, выделять государства некому: земли остаются за нами.",
     [("Ну и ладно", 0, 0, None, 0)]),
]
stab_ideas = sorted({o[3] for e in RAND_EVENTS for o in e[6] if o[3]})
sidea = {v: f"ktits_cas_ev_stab_{i}" for i, v in enumerate(stab_ideas)}
w("common/ideas/ktits_casuality_event_ideas.txt", "ideas = {\n\tcountry = {\n" + "".join(
    "\t\t" + sidea[v] + " = {\n\t\t\tpicture = ktits_casuality\n\t\t\tallowed = { always = no }\n\t\t\tallowed_civil_war = { always = yes }\n\t\t\tremoval_cost = -1\n"
    "\t\t\tmodifier = {\n\t\t\t\tstability_factor = " + str(v[0]) + "\n\t\t\t}\n\t\t}\n" for v in stab_ideas) + "\t}\n}\n")
rev = ""
for eid, kind, lo, needs_kaz, _t, _d, opts in RAND_EVENTS:
    note = kind == "note"
    # frequency: "up" events more often at a high scale, "down" events more often at a low scale
    mods = ("\t\t\tmodifier = { factor = 0.6 check_variable = { var = ktits_casuality value = 50 compare = greater_than_or_equals } }\n"
            "\t\t\tmodifier = { factor = 0.6 check_variable = { var = ktits_casuality value = 75 compare = greater_than_or_equals } }\n") if kind == "up" else \
           ("\t\t\tmodifier = { factor = 0.6 check_variable = { var = ktits_casuality value = 25 compare = less_than } }\n"
            "\t\t\tmodifier = { factor = 0.6 check_variable = { var = ktits_casuality value = 10 compare = less_than } }\n")
    kaz = ("\t\tcountry_exists = " + KAZ + "\n") if needs_kaz else ""
    flag = "ktits_cas_ev_" + str(eid)
    head = ("\ncountry_event = {\n\tid = ktits_casuality." + str(eid) + "\n\ttitle = ktits_casuality." + str(eid) + ".t\n\tdesc = ktits_casuality." + str(eid) + ".d\n"
            "\tpicture = GFX_report_event_ktits_casuality\n")
    if note:
        rev += head + "\tis_triggered_only = yes\n\tfire_only_once = no\n"
    else:
        rev += (head + "\tfire_only_once = no\n\n\ttrigger = {\n\t\tNOT = { ktits_is_kazualia = yes }\n"
            "\t\tNOT = { has_country_flag = ktits_casuality_fallen }\n\t\tNOT = { has_country_flag = " + flag + " }\n"
            "\t\tcheck_variable = { var = ktits_casuality value = " + str(lo) + " compare = greater_than_or_equals }\n" + kaz + "\t}\n\n"
            "\tmean_time_to_happen = {\n\t\tdays = 120\n" + mods + "\t}\n")
    # AI: course "Борьба" prefers the option with the lowest scale delta, "Сближение" the highest; an option the country cannot pay is never chosen
    best_f = min(range(len(opts)), key=lambda k: opts[k][1]); best_r = max(range(len(opts)), key=lambda k: opts[k][1])
    for i, (_n, delta, pp, stab, pop) in enumerate(opts):
        eff = "" if note else "\t\t\tset_country_flag = { flag = " + flag + " days = 180 value = 1 }\n"
        if delta: eff += cas_tt(delta) + "\t\t\tadd_to_variable = { var = ktits_casuality value = " + str(delta) + " }\n\t\t\tclamp_variable = { var = ktits_casuality min = 0 max = 100 }\n\t\t\tktits_casuality_update = yes\n"
        if pp: eff += "\t\t\tadd_political_power = " + str(pp) + "\n"
        if stab: eff += "\t\t\tadd_timed_idea = { idea = " + sidea[stab] + " days = " + str(stab[1]) + " }\n"
        if pop: eff += "\t\t\tadd_popularity = { ideology = casuality popularity = " + str(pop) + " }\n"
        if not eff and eid == 31: eff = "\t\t\tcustom_effect_tooltip = ktits_casuality_31_tt\n"
        ai = "\t\tai_chance = {\n\t\t\tbase = 1\n"
        if i == best_f: ai += "\t\t\tmodifier = { factor = 10 NOT = { has_country_flag = " + RAPP + " } }\n"
        if i == best_r: ai += "\t\t\tmodifier = { factor = 10 has_country_flag = " + RAPP + " }\n"
        if pp < 0: ai += "\t\t\tmodifier = { factor = 0 NOT = { has_political_power > " + str(-pp - 1) + " } }\n"
        ai += "\t\t}\n"
        rev += ("\n\toption = {\n\t\tname = ktits_casuality." + str(eid) + "." + "ab"[i] + "\n" + ai + eff + "\t}\n")
    rev += "}\n"
ev_path = M / "events/ktits_casuality_events.txt"
ev_path.write_text(ev_path.read_text(encoding="utf-8").rstrip() + "\n" + rev, encoding="utf-8", newline="\n")

# ---- localisation ----
ru, en = [], []
def add(k, ru_t, en_t=None):
    ru.append((k, ru_t)); en.append((k, en_t or L.translit(ru_t)))
add("ktits_casuality_category", "Казуальность")
add("ktits_casuality_category_desc", "Шкала Казуальности: [?ktits_casuality|0] из 100. Лень снижает промышленность; на отметке 100 страна переходит в Казуальность и становится марионеткой Казуалии.")
for k, n, d, *_ in TIERS:
    add(f"ktits_cas_{k}", f"Казуальность: {n}"); add(f"ktits_cas_{k}_desc", d)
for key, n, d, *_ in DECISIONS:
    add(key, n); add(f"{key}_desc", d)
add("ktits_cas_call_1", "Зов болот")
add("ktits_cas_call_1_desc", "Солдаты слышат, что за линией фронта не нужно ни стрелять, ни копать окопы. Целые роты уходят в болота «на минутку» и не возвращаются.")
add("ktits_cas_call_2", "Зов болот: второй голос")
add("ktits_cas_call_2_desc", "Ставка Казуала через громкоговорители над линией фронта приглашает солдат «отдохнуть». Зов болот становится сильнее.")
add("ktits_casuality_kaz_category", "Зов болот")
add("ktits_casuality_kaz_category_desc", "Казуалия может звать на болота солдат стран, которые с ней воюют и уже глубоко увязли в Казуальности (шкала выше 80).")
add("ktits_cas_call_swamp", "Позвать с болот")
add("ktits_cas_call_swamp_desc", "Ставка Казуала через громкоговорители над линией фронта приглашает солдат противника «отдохнуть». Шкала Казуальности цели растёт на 10, а «Зов болот» усиливается на 60 дней.")
add("ktits_casuality.1.t", "Страна погрузилась в Казуальность")
add("ktits_casuality.1.d", "Никто уже не помнит, когда в последний раз кто-то спешил. [Root.GetName] окончательно приняла Казуальность: дела решаются сами собой, власть перешла к тем, кто умеет ничего не делать, а Ставка Казуала принимает присягу. Единое государство развалилось: каждая область выбрала собственное болото.")
add("ktits_casuality.1.a", "Всё само получится...")
for d in sorted(CAS_TT | {10}):
    add(tt_key(d), ("Казуальность: §R+%d§!" % d) if d > 0 else ("Казуальность: §G%d§!" % d), ("Casuality: §R+%d§!" % d) if d > 0 else ("Casuality: §G%d§!" % d))
add("ktits_casuality_31_tt", "Решение «Последний рывок» доступно (шкала не ниже 95).")
add("ktits_casuality_fall_tt", "Правящая партия станет Казуальностью, захваченные земли вернутся прежним владельцам, страна станет марионеткой Казуалии, а все части, которые можно освободить, станут отдельными марионетками Казуалии.")
for eid, _k, _lo, _nk, t_, d_, opts in RAND_EVENTS:
    add(f"ktits_casuality.{eid}.t", t_); add(f"ktits_casuality.{eid}.d", d_)
    for i, o in enumerate(opts):
        add(f"ktits_casuality.{eid}.{'ab'[i]}", o[0])
for (v, days), key in sidea.items():
    add(key, "Казуальность: последствия события"); add(key + "_desc", "Временное изменение стабильности после случайного события Казуальности.")
L.write_yml(str(M / "localisation/russian/ktits_casuality_l_russian.yml"), "russian", ru)
L.write_yml(str(M / "localisation/english/ktits_casuality_l_english.yml"), "english", en)

# ---- game rule "Глобальная Казуальность" (custom game rules screen) ----
RK = CAS_RULE.upper()
_opts = ""
for o, _r, _e, s, m in CAS_RULE_OPTS:
    _opts += ("\tdefault = {\n" if o == "DEFAULT" else "\toption = {\n") + f'\t\tname = {o}\n\t\ttext = "KTITS_RULE_OPT_{o}"\n\t\tdesc = "KTITS_RULE_OPT_{o}_DESC"\n' + ("\t\tallow_achievements = no\n" if o != "DEFAULT" else "") + "\t}\n"
w("common/game_rules/ktits_casuality_rules.txt", f'{CAS_RULE} = {{\n\tname = "{RK}"\n\tdesc = "{RK}_DESC"\n\tgroup = "RULE_GROUP_AI_BEHAVIOR"\n{_opts}}}\n')
_r_ru = [(RK, "Глобальная Казуальность"), (RK + "_DESC", "Как часто ИИ-страны выбирают курс «Сближение» с Казуальностью. Работает только при неисторическом фокусе ИИ (при историческом все воюют, как раньше). Крупные страны (с выделяемыми государствами) всегда на курсе «Борьба».")]
_r_en = [(RK, "Global Casuality"), (RK + "_DESC", "How often AI countries choose the course of rapprochement with Casuality. Works only with non-historical AI focus (with historical focus everyone fights as before). Big countries (with releasable states) always fight it.")]
for o, nru, nen, s, m in CAS_RULE_OPTS:
    _r_ru += [(f"KTITS_RULE_OPT_{o}", nru), (f"KTITS_RULE_OPT_{o}_DESC", f"Шанс курса «Сближение» у малой страны ИИ при старте: {s} %. Динамический шанс, раз в 180 дней, умножается на {m}.")]
    _r_en += [(f"KTITS_RULE_OPT_{o}", nen), (f"KTITS_RULE_OPT_{o}_DESC", f"Start chance of the AI course \"rapprochement\" for a small country: {s}%. The dynamic chance, rolled every 180 days, is multiplied by {m}.")]
L.write_yml(str(M / "localisation/russian/ktits_game_rules_l_russian.yml"), "russian", _r_ru)
L.write_yml(str(M / "localisation/english/ktits_game_rules_l_english.yml"), "english", _r_en)

# ---- pictures (placeholder: one image for everything) ----
src = Image.open(a.image).convert("RGB") if Path(a.image).exists() else None
if src is None:
    print(f"WARNING: picture {a.image} not found, keeping existing sprites")
def crop(sz):
    tw, th = sz; r = max(tw / src.width, th / src.height)
    im = src.resize((round(src.width * r), round(src.height * r)))
    x, y = (im.width - tw) // 2, (im.height - th) // 2
    return im.crop((x, y, x + tw, y + th))
art = M / "gfx/interface/ktits"; art.mkdir(parents=True, exist_ok=True)
SPR = [("GFX_idea_ktits_casuality", "idea_casuality.png", (65, 67)), ("GFX_decision_ktits_casuality", "decision_casuality.png", (65, 67)),
       ("GFX_decision_cat_picture_ktits_casuality", "decision_cat_casuality.png", (420, 120)), ("GFX_report_event_ktits_casuality", "event_casuality.png", (210, 120))]
for _, fn, sz in SPR:
    if src is not None: crop(sz).save(art / fn)
w("interface/ktits_casuality.gfx", "spriteTypes = {\n" + "".join(
    f'\tspriteType = {{\n\t\tname = "{n}"\n\t\ttexturefile = "gfx/interface/ktits/{fn}"\n\t}}\n' for n, fn, _ in SPR) + "}\n", "utf-8")

# ---- scale bar in the decision category (scripted GUI: 20 segments of 5 %, shown by variable thresholds; no progressbar exists for decision GUIs) ----
from PIL import ImageDraw
SEG_N, SEG_W, SEG_H, GAP, BAR_X = 20, 22, 14, 1, 14
bar_w = SEG_N * (SEG_W + GAP) + 6
if src is not None:
    fr = crop((bar_w, SEG_H + 8)).point(lambda v: int(v * 0.35))
    d = ImageDraw.Draw(fr); d.rectangle([0, 0, fr.width - 1, fr.height - 1], outline=(200, 190, 150))
    fr.save(art / "bar_frame.png")
SEG_COL = [(60, 180, 75), (170, 190, 50), (230, 150, 40), (200, 50, 40)]       # quarters: green, yellow, orange, red
for i, col in enumerate(SEG_COL, 1):
    im = Image.new("RGB", (SEG_W, SEG_H), col); ImageDraw.Draw(im).rectangle([0, 0, SEG_W - 1, SEG_H - 1], outline=tuple(int(c * 0.6) for c in col)); im.save(art / f"bar_seg_{i}.png")
w("interface/ktits_casuality.gfx", (M / "interface/ktits_casuality.gfx").read_text(encoding="utf-8").rstrip()[:-1] + "".join(
    f'\tspriteType = {{\n\t\tname = "{n}"\n\t\ttexturefile = "gfx/interface/ktits/{fn}"\n\t}}\n' for n, fn in
    [("GFX_ktits_cas_bar_frame", "bar_frame.png")] + [(f"GFX_ktits_cas_seg_{i}", f"bar_seg_{i}.png") for i in range(1, 5)]) + "}\n", "utf-8")
w("common/scripted_guis/ktits_casuality.txt", "scripted_gui = {\n\n\tktits_casuality_ui = {\n\t\tcontext_type = decision_category\n\t\twindow_name = \"ktits_casuality_ui_window\"\n\n\t\ttriggers = {\n" + "".join(
    f"\t\t\tktits_cas_seg_{i}_visible = {{\n\t\t\t\tcheck_variable = {{ var = ktits_casuality value = {i * 5} compare = greater_than_or_equals }}\n\t\t\t}}\n" for i in range(1, SEG_N + 1)) + "\t\t}\n\t}\n}\n")
gui = "guiTypes = {\n\n\tcontainerWindowType = {\n\t\tname = \"ktits_casuality_ui_window\"\n\t\tposition = { x = 0 y = 0 }\n\t\tsize = { width = 100% height = 50 }\n\t\tclipping = no\n\n"
gui += f"\t\tinstantTextBoxType = {{\n\t\t\tname = \"ktits_cas_label\"\n\t\t\tposition = {{ x = {BAR_X} y = 2 }}\n\t\t\tfont = \"hoi_16mbs\"\n\t\t\ttext = \"ktits_casuality_bar_label\"\n\t\t\tformat = left\n\t\t\tmaxHeight = 18\n\t\t\tmaxwidth = 470\n\t\t}}\n\n"
gui += f"\t\ticonType = {{\n\t\t\tname = \"ktits_cas_frame\"\n\t\t\tspriteType = \"GFX_ktits_cas_bar_frame\"\n\t\t\tposition = {{ x = {BAR_X} y = 22 }}\n\t\t\tpdx_tooltip = \"ktits_casuality_bar_tt\"\n\t\t}}\n\n"
for i in range(1, SEG_N + 1):
    gui += f"\t\ticonType = {{\n\t\t\tname = \"ktits_cas_seg_{i}\"\n\t\t\tspriteType = \"GFX_ktits_cas_seg_{(i - 1) // 5 + 1}\"\n\t\t\tposition = {{ x = {BAR_X + 3 + (i - 1) * (SEG_W + GAP)} y = 25 }}\n\t\t}}\n"
w("interface/ktits_casuality.gui", gui + "\t}\n}\n", "utf-8")
L.write_yml(str(M / "localisation/russian/ktits_casuality_bar_l_russian.yml"), "russian", [("ktits_casuality_bar_label", "Шкала Казуальности: [?ktits_casuality|0] / 100"), ("ktits_casuality_bar_tt", "Каждое деление - 5 пунктов Казуальности. На отметке 100 страна переходит в Казуальность и становится марионеткой Казуалии.")])
L.write_yml(str(M / "localisation/english/ktits_casuality_bar_l_english.yml"), "english", [("ktits_casuality_bar_label", "Casuality scale: [?ktits_casuality|0] / 100"), ("ktits_casuality_bar_tt", "Each segment is 5 points of Casuality. At 100 the country falls into Casuality and becomes a puppet of Kazualia.")])

# ---- a casuality-group leader for every country (the game needs one when the ruling party changes) ----
added = 0
for tag in sorted(info["tags"]):
    cf = M / "common/characters" / f"{tag}.txt"
    if not cf.exists(): continue
    ct = cf.read_text(encoding="utf-8", errors="ignore")
    if "casuality_ideology" in ct: continue
    blk = f'\t{tag}_casuality_leader={{\n\t\tname="Казуал-Предводитель"\n\n\t\tcountry_leader={{\n\t\t\tideology=casuality_ideology\n\t\t\ttraits = {{ }}\n\t\t\texpire="1965.1.1.1"\n\t\t\tid=-1\n\t\t}}\n\n\t}}\n'
    k = ct.rindex("}")
    cf.write_text(ct[:k] + blk + ct[k:], encoding="utf-8", newline=""); added += 1
print(f"casuality mechanic written; Kazualia tag {KAZ}; leaders added {added}; sprites {len(SPR)} (image {a.image})")
