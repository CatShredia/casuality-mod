"""Global mechanic "Казуальность" (docs/01, docs/14): a 0..100 scale in every country except Казуалия (variable ktits_casuality, starts at 0).

 * 4 tier spirits ktits_cas_1..4 with industry debuffs (laziness); swapped automatically when the scale changes;
 * decisions to fight it (-10, -20) or to support it (+10, +20), each country may use them (Казуалия excluded: its own mechanic, later);
 * at 100 the country "falls into casuality": event, ruling party casuality, the country becomes a puppet of Казуалия;
 * every country gets a casuality-group leader (needed by the game when the ruling party changes).
Values, names and texts are INVENTED (docs/12, docs/14). Pictures: no_commit/image.jpg is a placeholder, converted to PNG sprites.
Writes: common/scripted_effects|scripted_triggers|ideas|decisions(+categories), events, localisation ru/en, interface/ktits_casuality.gfx,
gfx/interface/ktits/*.png, common/characters/<TAG>.txt (leader block appended).
Usage: python tools/make_casuality.py [--mod PATH] [--image PATH]
"""
import argparse, re
from pathlib import Path
from PIL import Image
import lore_data as L

TIERS = [  # (key, ru name, ru desc, lower bound, industrial_capacity_factory, production_speed_buildings_factor, research_speed_factor, stability_factor) docs/14 (numbers by the author); texts of 4, 5 INVENTED
    (1, "Ленца", "Граждане начинают опаздывать, недоделывать работу.", 1, -0.03, -0.05, 0.0, 0.0),
    (2, "Расслабон", "Люди расслаблены, некоторые этим пользуются.", 25, -0.06, -0.10, 0.0, 0.0),
    (3, "Болотная лень", "Переходный период: заводы встали, люди ничего не делают. Страна встала.", 50, -0.95, -0.95, -0.95, -0.50),
    (4, "Дурманище", "Болотный дурман окутал страну: у станков почти никого, а те, кто есть, ждут, пока всё случится само. Заводы дымят вхолостую, наука дремлет, но государство каким-то чудом держится.", 75, -0.65, -0.65, -0.65, -0.65),
    (5, "Казуальная идилия", "Общество достигло просветлённого безделья: заводы едва шевелятся, науке не до открытий, зато люди спокойны, довольны и ни о чём не тревожатся. Ещё шаг - и страна уйдёт в Казуальность.", 95, -0.10, -0.15, -0.50, 0.80),
]
# decisions: key, ru name, ru desc, delta, cost PP, cooldown days, side, min scale value (0 = none), extra effect lines  (docs/14 table by the author; the new ones INVENTED)
# key, ru name, ru desc, delta, cost PP, cooldown days, side, min scale value (0 = none), extra effect token (EXTRA)  docs/14: the six first rows are the author's table, the rest INVENTED
EXTRA = {
    'campaign': ['set_country_flag = { flag = ktits_cas_campaign days = 180 value = 1 }', 'set_variable = { var = ktits_cas_tick value = 0 }'],
    'st5': ['add_stability = -0.05'],
    'st10': ['add_stability = -0.10'],
    'last': ['add_war_support = -0.10', 'add_stability = -0.10'],
    'pp': ['add_political_power = 25'],
    'siesta': ['add_stability = 0.03'],
    'pop': ['add_popularity = { ideology = casuality popularity = 0.05 }'],
}
DECISIONS = [
    ('ktits_cas_fight_1', 'Кампания «Подъём на труд!»', 'Агитация за труд и дисциплину: плакаты, собрания, ударные бригады. Казуальность в стране падает на 10.', -10, 50, 30, 'fight', 0, ''),
    ('ktits_cas_fight_2', 'Провести переговоры с профсоюзами', 'Договориться с профсоюзами о нормах выработки и графиках. Казуальность в стране падает на 20.', -20, 100, 90, 'fight', 0, ''),
    ('ktits_cas_fight_0', 'Противодействие, труд и власть!', 'Государство берёт Казуальность под постоянный надзор: следующие полгода каждые 15 дней шкала падает на 10.', 0, 150, 180, 'fight', 0, 'campaign'),
    ('ktits_cas_fight_3', 'Чрезвычайный трудовой режим', 'Заводы переходят на казарменный график, прогульщиков наказывают. Казуальность падает на 30, но стабильность падает. Доступно, когда шкала не ниже 50.', -30, 200, 120, 'fight', 50, 'st5'),
    ('ktits_cas_fight_4', 'Осушение болот', 'Масштабная программа осушения: вода уходит, а вместе с ней и дурман. Казуальность падает на 40, стабильность страдает от переселений. Доступно, когда шкала не ниже 75.', -40, 300, 180, 'fight', 75, 'st10'),
    ('ktits_cas_fight_5', 'Последний рывок', 'Отчаянная мобилизация всех сил накануне падения. Казуальность падает на 50, но армия и народ изматываются. Доступно, когда шкала не ниже 95.', -50, 400, 365, 'fight', 95, 'last'),
    ('ktits_cas_support_1', 'Праздник безделья', 'Всенародный выходной: Казуальность растёт на 10, власти достаётся немного политического веса.', 10, 0, 30, 'support', 0, 'pp'),
    ('ktits_cas_support_2', 'Культ болота', 'Официально поощрять болотный образ жизни: ритуальные посиделки у воды. Казуальность растёт на 10.', 10, 0, 90, 'support', 0, ''),
    ('ktits_cas_support_3', 'Культ Священного-Архо-Казуала', 'Культ создателя Казуальности даёт людям смысл ничего не делать. Казуальность растёт на 20. Доступно, когда шкала выше 25.', 20, 0, 90, 'support', 26, ''),
    ('ktits_cas_support_4', 'Всеобщая сиеста', 'Дневной сон по распоряжению властей: работа встаёт, люди довольны. Казуальность растёт на 15, стабильность немного растёт. Доступно, когда шкала не ниже 50.', 15, 0, 60, 'support', 50, 'siesta'),
    ('ktits_cas_support_5', 'Присяга Ставке Казуала', 'Страна присягает Ставке Казуала. Казуальность растёт на 20, партия Казуальности набирает популярность. Доступно, когда шкала не ниже 75.', 20, 0, 120, 'support', 75, 'pop'),
]

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

# ---- triggers / effects ----
w("common/scripted_triggers/ktits_casuality_triggers.txt", f"""ktits_is_kazualia = {{
	original_tag = {KAZ}
}}
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
w("common/scripted_effects/ktits_casuality_effects.txt", f"""ktits_casuality_update = {{
{upd}	if = {{
		limit = {{
			check_variable = {{ var = ktits_casuality value = 100 compare = greater_than_or_equals }}
			NOT = {{ has_country_flag = ktits_casuality_fallen }}
		}}
		set_country_flag = ktits_casuality_fallen
		country_event = {{ id = ktits_casuality.1 }}
	}}
}}

ktits_casuality_change = {{
	add_to_variable = {{ var = ktits_casuality value = $VALUE$ }}
	clamp_variable = {{ var = ktits_casuality min = 0 max = 100 }}
	ktits_casuality_update = yes
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
w("common/on_actions/ktits_casuality_on_actions.txt", """on_actions = {
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
    extra = "".join("\t\t\t" + e + "\n" for e in EXTRA.get(ex, []))
    avail = ("check_variable = { var = ktits_casuality value = %d compare = greater_than_or_equals }" % max(lo, 1) if side == "fight"
             else "check_variable = { var = ktits_casuality value = 100 compare = less_than }")
    if side != "fight" and lo:
        avail += "\n\t\t\tcheck_variable = { var = ktits_casuality value = %d compare = greater_than_or_equals }" % lo
    delta_eff = "" if delta == 0 else ("\t\t\tadd_to_variable = { var = ktits_casuality value = %d }\n\t\t\tclamp_variable = { var = ktits_casuality min = 0 max = 100 }\n\t\t\tktits_casuality_update = yes\n" % delta)
    dec += f"""
	{key} = {{
		icon = ktits_casuality
		visible = {{ NOT = {{ ktits_is_kazualia = yes }} }}
		available = {{
			{avail}
			NOT = {{ has_country_flag = ktits_casuality_fallen }}
		}}
		cost = {cost}
		days_re_enable = {cd}
		fire_only_once = no
		complete_effect = {{
{extra}{delta_eff}		}}
		ai_will_do = {{ factor = {5 if side == "fight" and lo == 0 else 0} }}
	}}
"""
w("common/decisions/ktits_casuality.txt", dec + "}\n")

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
			if = {{
				limit = {{ is_subject = yes }}
				overlord = {{ end_puppet = PREV }}
			}}
			set_politics = {{ ruling_party = casuality }}
			add_popularity = {{ ideology = casuality popularity = 0.5 }}
			ktits_split_on_fall = yes
			if = {{
				limit = {{ country_exists = {KAZ} }}
				{KAZ} = {{ puppet = ROOT }}
			}}
		}}
	}}

	option = {{
		name = ktits_casuality.1.a
		custom_effect_tooltip = ktits_casuality_fall_tt
	}}
}}
""")

# ---- random events (docs/14, "Случайные события"; all INVENTED) ----
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
]
stab_ideas = sorted({o[3] for e in RAND_EVENTS for o in e[6] if o[3]})
sidea = {v: f"ktits_cas_ev_stab_{i}" for i, v in enumerate(stab_ideas)}
w("common/ideas/ktits_casuality_event_ideas.txt", "ideas = {\n\tcountry = {\n" + "".join(
    "\t\t" + sidea[v] + " = {\n\t\t\tpicture = ktits_casuality\n\t\t\tallowed = { always = no }\n\t\t\tallowed_civil_war = { always = yes }\n\t\t\tremoval_cost = -1\n"
    "\t\t\tmodifier = {\n\t\t\t\tstability_factor = " + str(v[0]) + "\n\t\t\t}\n\t\t}\n" for v in stab_ideas) + "\t}\n}\n")
rev = ""
for eid, kind, lo, needs_kaz, _t, _d, opts in RAND_EVENTS:
    # frequency: "up" events more often at a high scale, "down" events more often at a low scale
    mods = ("\t\t\tmodifier = { factor = 0.6 check_variable = { var = ktits_casuality value = 50 compare = greater_than_or_equals } }\n"
            "\t\t\tmodifier = { factor = 0.6 check_variable = { var = ktits_casuality value = 75 compare = greater_than_or_equals } }\n") if kind == "up" else \
           ("\t\t\tmodifier = { factor = 0.6 check_variable = { var = ktits_casuality value = 25 compare = less_than } }\n"
            "\t\t\tmodifier = { factor = 0.6 check_variable = { var = ktits_casuality value = 10 compare = less_than } }\n")
    kaz = ("\t\tcountry_exists = " + KAZ + "\n") if needs_kaz else ""
    flag = "ktits_cas_ev_" + str(eid)
    rev += ("\ncountry_event = {\n\tid = ktits_casuality." + str(eid) + "\n\ttitle = ktits_casuality." + str(eid) + ".t\n\tdesc = ktits_casuality." + str(eid) + ".d\n"
            "\tpicture = GFX_report_event_ktits_casuality\n\tfire_only_once = no\n\n\ttrigger = {\n\t\tNOT = { ktits_is_kazualia = yes }\n"
            "\t\tNOT = { has_country_flag = ktits_casuality_fallen }\n\t\tNOT = { has_country_flag = " + flag + " }\n"
            "\t\tcheck_variable = { var = ktits_casuality value = " + str(lo) + " compare = greater_than_or_equals }\n" + kaz + "\t}\n\n"
            "\tmean_time_to_happen = {\n\t\tdays = 120\n" + mods + "\t}\n")
    for i, (_n, delta, pp, stab, pop) in enumerate(opts):
        eff = "\t\t\tset_country_flag = { flag = " + flag + " days = 180 value = 1 }\n"
        eff += "\t\t\tadd_to_variable = { var = ktits_casuality value = " + str(delta) + " }\n\t\t\tclamp_variable = { var = ktits_casuality min = 0 max = 100 }\n\t\t\tktits_casuality_update = yes\n"
        if pp: eff += "\t\t\tadd_political_power = " + str(pp) + "\n"
        if stab: eff += "\t\t\tadd_timed_idea = { idea = " + sidea[stab] + " days = " + str(stab[1]) + " }\n"
        if pop: eff += "\t\t\tadd_popularity = { ideology = casuality popularity = " + str(pop) + " }\n"
        rev += ("\n\toption = {\n\t\tname = ktits_casuality." + str(eid) + "." + "ab"[i] + "\n\t\tai_chance = { base = " + str(2 - i) + " }\n" + eff + "\t}\n")
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
add("ktits_casuality.1.t", "Страна погрузилась в Казуальность")
add("ktits_casuality.1.d", "Никто уже не помнит, когда в последний раз кто-то спешил. [Root.GetName] окончательно приняла Казуальность: дела решаются сами собой, власть перешла к тем, кто умеет ничего не делать, а Ставка Казуала принимает присягу. Единое государство развалилось: каждая область выбрала собственное болото.")
add("ktits_casuality.1.a", "Всё само получится...")
add("ktits_casuality_fall_tt", "Правящая партия станет Казуальностью, страна станет марионеткой Казуалии, а все части, которые можно освободить, станут отдельными марионетками Казуалии.")
for eid, _k, _lo, _nk, t_, d_, opts in RAND_EVENTS:
    add(f"ktits_casuality.{eid}.t", t_); add(f"ktits_casuality.{eid}.d", d_)
    for i, o in enumerate(opts):
        add(f"ktits_casuality.{eid}.{'ab'[i]}", o[0])
for (v, days), key in sidea.items():
    add(key, "Казуальность: последствия события"); add(key + "_desc", "Временное изменение стабильности после случайного события Казуальности.")
L.write_yml(str(M / "localisation/russian/ktits_casuality_l_russian.yml"), "russian", ru)
L.write_yml(str(M / "localisation/english/ktits_casuality_l_english.yml"), "english", en)

# ---- pictures (placeholder: one image for everything) ----
src = Image.open(a.image).convert("RGB")
def crop(sz):
    tw, th = sz; r = max(tw / src.width, th / src.height)
    im = src.resize((round(src.width * r), round(src.height * r)))
    x, y = (im.width - tw) // 2, (im.height - th) // 2
    return im.crop((x, y, x + tw, y + th))
art = M / "gfx/interface/ktits"; art.mkdir(parents=True, exist_ok=True)
SPR = [("GFX_idea_ktits_casuality", "idea_casuality.png", (65, 67)), ("GFX_decision_ktits_casuality", "decision_casuality.png", (65, 67)),
       ("GFX_decision_cat_picture_ktits_casuality", "decision_cat_casuality.png", (420, 120)), ("GFX_report_event_ktits_casuality", "event_casuality.png", (210, 120))]
for _, fn, sz in SPR: crop(sz).save(art / fn)
w("interface/ktits_casuality.gfx", "spriteTypes = {\n" + "".join(
    f'\tspriteType = {{\n\t\tname = "{n}"\n\t\ttexturefile = "gfx/interface/ktits/{fn}"\n\t}}\n' for n, fn, _ in SPR) + "}\n", "utf-8")

# ---- scale bar in the decision category (scripted GUI: 20 segments of 5 %, shown by variable thresholds; no progressbar exists for decision GUIs) ----
from PIL import ImageDraw
SEG_N, SEG_W, SEG_H, GAP, BAR_X = 20, 22, 14, 1, 14
bar_w = SEG_N * (SEG_W + GAP) + 6
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
