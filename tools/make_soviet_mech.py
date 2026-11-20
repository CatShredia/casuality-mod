"""Soviet Union, phase 2 (docs/mechanics/Soviet-Union.md): the monthly mechanic (Paranoia and the four personalities, balance Pimenov - Party, Integrity and its tiers,
collapse with the break-up into K01-K06, K42, the economic zone and the crash spirits of a fast/slow collapse), decisions (Integrity, Paranoia, Balance, Church of the
Ancient Dinosaur, Communism for export) and the spirit of Idel-Kama. Numbers and texts are INVENTED (docs/lore/Invented-Lore.md). Variables are set by make_soviet.py
(ktits_sov_start). NOT done: graphic bars (the value is shown in the first line of the category description), the construction projects and the map,
renaming of the country, aid to the Cossack Land. [uncertain]: set_autonomy autonomy_free, random_list weights, the `every_country` loop in on_monthly.
Writes: common/{ideas,scripted_effects,decisions,decisions/categories,on_actions}/ktits_soviet_mech*, events/ktits_soviet_mech_events.txt, localisation ktits_soviet_mech_l_*.yml.
Usage: python tools/make_soviet_mech.py [--mod PATH]"""
import argparse, re
from pathlib import Path
import lore_data as L
from make_splits import FIXED, SPLITS

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
a = ap.parse_args()
M = Path(a.mod)
SOV = "MAK"
P = "ktits_sov_"
NAMES = SPLITS["MAK"]
TAGS = ["K01", "K02", "K03", "K04", "K05", "K06", "K42"]
STATES = dict(zip(TAGS, FIXED["MAK"]))
def T(s): return re.sub(r"(?m)^( {4})+", lambda m: "\t" * (len(m.group()) // 4), s)
def w(rel, text):
    p = M / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(T(text), encoding="utf-8", newline="\n")
ru, en = [], []
def add(k, r, e=None): ru.append((k, r)); en.append((k, e or L.translit(r)))
def ind(s, n=8): return "".join(" " * n + l + "\n" for l in s.rstrip("\n").split("\n") if l)
KT = "OR = { " + " ".join(f"original_tag = {t}" for t in TAGS) + " }"

# ---------------- spirits ----------------
SPI = {"int_hi": ("Единый Союз", "Республики не спорят, потому что некому: все слушают Ваньград.", {"stability_factor": 0.05, "conscription_factor": 0.01}),
       "int_lo": ("Союз трещит", "По окраинам шепчутся на своих языках, и шёпот слышен в Ваньграде.", {"stability_factor": -0.1, "political_power_gain": -0.2}),
       "pw_auto": ("Генсек-самодержец", "Генсек вспомнил, что цари были не хуже, и подписал указ о собственном царстве.", {"political_power_gain": 0.5, "stability_factor": -0.05}),
       "pw_soft": ("Добрый Генсек", "Генсек стал добрым и мягким. Подчинённые забыли, как выглядит страх.", {"stability_factor": 0.1, "industrial_capacity_factory": -0.05}),
       "pw_hard": ("Железный Генсек", "Генсек стал железным. Скрипят в основном двери.", {"industrial_capacity_factory": 0.1, "stability_factor": -0.1, "conscription_factor": 0.02}),
       "pw_schizo": ("Генсек видит заговоры", "Генсек видит заговор в каждой скрепке. Скрепки, впрочем, тоже что-то замышляют.", {"stability_factor": -0.03, "political_power_gain": 0.1}),
       "pw_balance": ("Генсек в равновесии", "Генсек наконец заснул без охраны и проснулся живым. Удивились оба.", {"stability_factor": 0.05, "political_power_gain": 0.15}),
       "party_dict": ("Партийная диктатура", "На пленуме спорят уже не о политике, а о том, кто будет подписывать повестку. Побеждает тот, кто громче читает вслух.", {"political_power_factor": -0.2, "stability_factor": 0.1}),
       "pcult": ("Культ личности", "Портреты Генсека висят даже в кабинетах, где вешать нечего. Страна улыбается: так велено.", {"political_power_factor": 0.3, "stability_factor": -0.1}),
       "crash": ("Хозяйственный обвал", "Республики разошлись за неделю. Рубль остался в одной, станки в другой, паспорта в третьей. Заводы встали от того, что никто не знал, чья теперь печать.", {"industrial_capacity_factory": -0.15, "stability_factor": -0.1, "production_speed_buildings_factor": -0.15, "consumer_goods_factor": 0.1}),
       "crash_half": ("Хозяйственный обвал (смягчённый)", "Зона держится: печать общая, и обвал бьёт вполсилы. Заводы встали, но ненадолго.", {"industrial_capacity_factory": -0.075, "stability_factor": -0.05, "production_speed_buildings_factor": -0.075, "consumer_goods_factor": 0.05}),
       "crash_soft": ("Распад по плану", "Республики расходились по расписанию, и расписание даже почти соблюдали.", {"industrial_capacity_factory": -0.05, "stability_factor": -0.03, "consumer_goods_factor": 0.03})}
PIC = {"stability_factor": "eng_tackle_capitalism", "political_power_gain": "generic_communism_drift_bonus", "political_power_factor": "generic_communism_drift_bonus",
       "industrial_capacity_factory": "generic_production_bonus", "conscription_factor": "generic_manpower_bonus"}
ideas = "ideas = {\n    country = {\n"
def idea(key, mods):
    pic = next((PIC[k] for k in mods if k in PIC), "generic_communism_drift_bonus")
    return (f"        {key} = {{\n            picture = {pic}\n            allowed = {{ always = no }}\n            allowed_civil_war = {{ always = yes }}\n            removal_cost = -1\n            modifier = {{\n"
            + "".join(f"                {k} = {v}\n" for k, v in mods.items()) + "            }\n        }\n")
for k, (r_, d_, mods) in SPI.items():
    ideas += idea(P + "sp_" + k, mods); add(P + "sp_" + k, r_); add(P + "sp_" + k + "_desc", d_)
# vanilla volunteers (diplomacy action «Отправить добровольцев»): the rule can_send_volunteers + the modifiers of the vanilla ideas (afghanistan.txt:686, australia.txt:1681)
ideas += ("        ktits_sov_sp_volunteers = {\n            picture = generic_volunteer_expedition_bonus\n            allowed = { always = no }\n            removal_cost = -1\n            rule = {\n                can_send_volunteers = yes\n            }\n"
          "            modifier = {\n                send_volunteer_divisions_required = -1\n                send_volunteer_size = 3\n            }\n        }\n")
add("ktits_sov_sp_volunteers", "Союзные добровольцы"); add("ktits_sov_sp_volunteers_desc", "Союз разрешил своим добровольцам ездить на чужие войны. Добровольцы едут охотно: там кормят, а дома ещё надо оформлять отпуск.")
IDEL = ("Союз двух рек", "Две реки сливаются, и никто уже не спорит, какая из них главнее. Татарин и башкир делят один паром и один самовар.", {"stability_factor": 0.05, "production_speed_buildings_factor": 0.1, "consumer_goods_factor": -0.05})
ideas += idea("ktits_idel_two_rivers", IDEL[2]); add("ktits_idel_two_rivers", IDEL[0]); add("ktits_idel_two_rivers_desc", IDEL[1])
w("common/ideas/ktits_soviet_mech_ideas.txt", ideas + "    }\n}\n")

# ---------------- effects ----------------
def tier(var, rules):   # rules: [(condition, idea)]; removes all the tier ideas, then adds the one whose condition holds first
    s = "".join(f"if = {{ limit = {{ has_idea = {P}sp_{i} }} remove_ideas = {P}sp_{i} }}\n" for _, i in rules)
    for n, (cond, i) in enumerate(rules):
        s += ("if" if n == 0 else "else_if") + f" = {{\n    limit = {{ {cond} }}\n    add_ideas = {P}sp_{i}\n}}\n"
    return s
BOP = "ktits_sov_power_balance"
def pb(op, v): return f"power_balance_value = {{ id = {BOP} value {op} {v} }}"
def BV(d): return f"add_power_balance_value = {{ id = {BOP} value = {d} }}\n"
def cv(v, val, cmp): return f"check_variable = {{ var = {P}{v} value = {val} compare = {cmp} }}"
eff = ""
eff += f"ktits_sov_tiers = {{\n" + ind(
    tier("integrity", [(cv("integrity", 70, "greater_than_or_equals"), "int_hi"), (cv("integrity", 40, "less_than") , "int_lo")]), 4) + "}\n\n"
# release of one part (the army/navy/air split of make_splits.py: population before the transfer, ratio ladder ktits_split_share)
for t in TAGS:
    sts = STATES[t]
    calc = ("set_variable = { ktits_sp_rem = 0 }\nset_variable = { ktits_sp_part = 0 }\nevery_owned_state = { OWNER = { add_to_variable = { ktits_sp_rem = PREV.state_population_k } } }\n" +
            "".join(f"if = {{\n    limit = {{ {x} = {{ is_owned_by = ROOT }} }}\n    {x} = {{ OWNER = {{ add_to_variable = {{ ktits_sp_part = PREV.state_population_k }} }} }}\n}}\n" for x in sts) +
            "set_variable = { ktits_sp_ratio = ktits_sp_part }\nif = {\n    limit = { check_variable = { ktits_sp_rem > 0 } }\n    divide_variable = { ktits_sp_ratio = ktits_sp_rem }\n}\n")
    moves = "".join(f"if = {{\n    limit = {{ {x} = {{ is_owned_by = ROOT }} }}\n    {t} = {{ transfer_state = {x} }}\n}}\n" for x in sts)
    units = (f"if = {{\n    limit = {{ country_exists = {t} }}\n    {t} = {{ save_event_target_as = ktits_split_target }}\n    ktits_split_share = yes\n}}\nclear_variable = ktits_sp_rem\nclear_variable = ktits_sp_part\nclear_variable = ktits_sp_ratio\n")
    after = (f"if = {{\n    limit = {{ country_exists = {t} }}\n    {SOV} = {{ puppet = {t} }}\n    {t} = {{\n        add_ideas = ktits_sez_member\n        set_country_flag = ktits_sez_part\n"
             + ("        add_ideas = ktits_idel_two_rivers\n" if t == "K42" else "") +
             f"        if = {{ limit = {{ {SOV} = {{ has_country_flag = {P}fast_fall }} }} add_timed_idea = {{ idea = {P}sp_crash_half days = 730 }} }}\n"
             f"        else = {{ add_timed_idea = {{ idea = {P}sp_crash_soft days = 365 }} }}\n    }}\n}}\n")
    eff += f"# scope = Soviet Union: release of {t} (a puppet of the Union, member of the economic zone)\n{P}release_{t} = {{\n    if = {{\n        limit = {{ NOT = {{ country_exists = {t} }} }}\n" + ind(calc + moves + units + after, 8) + "    }\n}\n\n"
eff += (f"# the collapse: fast (Integrity fell from 40+ to 10 within 180 days, or before 1938) -> the crash for 2 years, otherwise a soft one\n{P}collapse = {{\n    set_country_flag = {P}collapsed\n"
        f"    if = {{\n        limit = {{ OR = {{ has_country_flag = {P}fall_clock date < 1938.1.1 }} }}\n        set_country_flag = {P}fast_fall\n        add_timed_idea = {{ idea = {P}sp_crash days = 730 }}\n    }}\n"
        f"    else = {{ add_timed_idea = {{ idea = {P}sp_crash_soft days = 365 }} }}\n" + "".join(f"    {P}release_{t} = yes\n" for t in TAGS) +
        f"    country_event = {{ id = ktits_soviet.40 }}\n}}\n\n")
eff += (f"# scope = Soviet Union, every month\n{P}monthly = {{\n"
 + ind(
 # integrity: slow drift, monolith floor, fall clock
 f"if = {{ limit = {{ check_variable = {{ var = ktits_casuality value = 50 compare = greater_than }} }} add_to_variable = {{ var = {P}integrity value = -1 }} }}\n"
 f"if = {{ limit = {{ {cv('paranoia', 70, 'greater_than_or_equals')} }} add_to_variable = {{ var = {P}integrity value = -1 }} }}\n"
 f"if = {{ limit = {{ has_country_flag = {P}monolith {cv('integrity', 50, 'less_than')} }} set_variable = {{ var = {P}integrity value = 50 }} }}\n"
 f"clamp_variable = {{ var = {P}integrity min = 0 max = 100 }}\n"
 f"if = {{\n    limit = {{ {cv('integrity', 40, 'less_than')} NOT = {{ has_country_flag = {P}fall_started }} }}\n    set_country_flag = {P}fall_started\n    set_country_flag = {{ flag = {P}fall_clock days = 180 value = 1 }}\n}}\n"
 f"if = {{\n    limit = {{ {cv('integrity', 40, 'greater_than_or_equals')} has_country_flag = {P}fall_started NOT = {{ has_country_flag = {P}collapsed }} }}\n    clr_country_flag = {P}fall_started\n    clr_country_flag = {P}fall_clock\n}}\n"
 f"if = {{\n    limit = {{ {cv('integrity', 10, 'less_than_or_equals')} NOT = {{ has_country_flag = {P}collapsed }} }}\n    {P}collapse = yes\n}}\n"
 f"if = {{\n    limit = {{ {cv('integrity', 0, 'less_than_or_equals')} has_country_flag = {P}collapsed NOT = {{ has_country_flag = {P}free_all }} }}\n    set_country_flag = {P}free_all\n"
 + "".join(f"    if = {{ limit = {{ country_exists = {t} }} set_autonomy = {{ target = {t} autonomy_state = autonomy_free }} }}\n" for t in TAGS) + "}\n"
 # paranoia: +2 base, balance changes the speed
 f"if = {{\n    limit = {{ has_country_flag = {P}para_on NOT = {{ has_country_flag = {P}pers_won }} NOT = {{ has_idea = {P}sp_party_dict }} }}\n    set_variable = {{ var = {P}pg value = 2 }}\n"
 f"    if = {{ limit = {{ {pb('<', -0.5)} }} set_variable = {{ var = {P}pg value = 1 }} }}\n"
 f"    else_if = {{ limit = {{ {pb('<', -0.2)} }} set_variable = {{ var = {P}pg value = 1.5 }} }}\n"
 f"    else_if = {{ limit = {{ {pb('>', 0.5)} }} set_variable = {{ var = {P}pg value = 3 }} }}\n"
 f"    else_if = {{ limit = {{ {pb('>', 0.2)} }} set_variable = {{ var = {P}pg value = 2.5 }} }}\n"
 f"    if = {{ limit = {{ has_idea = {P}sp_pcult }} add_to_variable = {{ var = {P}pg value = 1 }} }}\n"
 f"    add_to_variable = {{ var = {P}paranoia value = {P}pg }}\n    clamp_variable = {{ var = {P}paranoia min = 0 max = 100 }}\n"
 f"    random_list = {{\n        25 = {{ add_to_variable = {{ var = {P}p_auto value = 3 }} }}\n        25 = {{ add_to_variable = {{ var = {P}p_soft value = 3 }} }}\n        25 = {{ add_to_variable = {{ var = {P}p_hard value = 3 }} }}\n        25 = {{ add_to_variable = {{ var = {P}p_schizo value = 3 }} }}\n    }}\n"
 + "".join(f"    clamp_variable = {{ var = {P}p_{k} min = 0 max = 100 }}\n" for k in ("auto", "soft", "hard", "schizo")) +
 f"    if = {{ limit = {{ NOT = {{ has_country_flag = {P}para_clock_set }} }} set_country_flag = {P}para_clock_set set_country_flag = {{ flag = {P}para_clock days = 365 value = 1 }} }}\n}}\n"
 # personality / balance victory (events 30-34)
 f"if = {{\n    limit = {{ has_country_flag = {P}para_on NOT = {{ has_country_flag = {P}pers_won }} }}\n"
 + "".join(f"    {'if' if n == 0 else 'else_if'} = {{ limit = {{ {cv('p_' + k, 100, 'greater_than_or_equals')} }} set_country_flag = {P}pers_won country_event = {{ id = ktits_soviet.{30 + n} }} }}\n" for n, k in enumerate(("auto", "soft", "hard", "schizo"))) +
 f"    else_if = {{\n        limit = {{\n            has_country_flag = {P}para_clock_set NOT = {{ has_country_flag = {P}para_clock }}\n" + "".join(f"            {cv('p_' + k, 70, 'less_than_or_equals')}\n" for k in ("auto", "soft", "hard", "schizo")) +
 f"        }}\n        set_country_flag = {P}pers_won\n        country_event = {{ id = ktits_soviet.34 }}\n    }}\n}}\n"
 f"{P}tiers = yes\n"
 # Church: repentance grows with the countries that incline to theology
 f"if = {{\n    limit = {{ has_idea = {P}sp_church }}\n    every_other_country = {{\n        limit = {{ theology > 0.249 }}\n        ROOT = {{ add_to_variable = {{ var = {P}repent value = 1 }} }}\n    }}\n    clamp_variable = {{ var = {P}repent min = 0 max = 100 }}\n}}\n"
 f"if = {{\n    limit = {{ {cv('repent', 100, 'greater_than_or_equals')} NOT = {{ has_country_flag = {P}repent_done }} }}\n    set_country_flag = {P}repent_done\n    every_other_country = {{ add_popularity = {{ ideology = theology popularity = 0.1 }} }}\n}}\n"
 , 4) + "}\n")
w("common/scripted_effects/ktits_soviet_mech_effects.txt", eff)
w("common/on_actions/ktits_soviet_mech_on_actions.txt", f"on_actions = {{\n    on_monthly = {{\n        effect = {{\n            if = {{\n                limit = {{ ktits_is_soviet = yes }}\n                {P}monthly = yes\n            }}\n        }}\n    }}\n}}\n")

# ---------------- events 30-34 (personality victory), 40 (collapse) ----------------
EV = {30: ("Самодержец проснулся", "pw_auto", "Генсек долго смотрел в зеркало и увидел царя. Зеркало возражало, но его не спрашивали."),
      31: ("Добрый Генсек", "pw_soft", "Генсек вдруг стал добрым и мягким. Подчинённые подозревают подвох и ждут его до сих пор."),
      32: ("Железный Генсек", "pw_hard", "Генсек стал железным. Скрипят в основном двери, и ему это нравится."),
      33: ("Генсек видит заговоры", "pw_schizo", "Генсек увидел заговор в скрепке. Скрепку расстреляли, но заговор, говорят, остался."),
      34: ("Баланс найден", "pw_balance", "Год прошёл, а ни одна из личностей Генсека не взяла верх. Наступило равновесие, и все осторожно перевели дух."),
      40: ("Союз распался", None, "Республики разошлись по домам с печатями под мышкой. В Ваньграде ещё долго горел свет: считали, что осталось и чьё это теперь.")}
evt = "add_namespace = ktits_soviet\n\n"
for eid, (t_, sp, d_) in EV.items():
    add(f"ktits_soviet.{eid}.t", t_); add(f"ktits_soviet.{eid}.d", d_); add(f"ktits_soviet.{eid}.a", "Принять")
    evt += f"country_event = {{\n    id = ktits_soviet.{eid}\n    title = ktits_soviet.{eid}.t\n    desc = ktits_soviet.{eid}.d\n    picture = GFX_report_event_generic_factory\n    is_triggered_only = yes\n    option = {{\n        name = ktits_soviet.{eid}.a\n"
    if sp: evt += f"        add_ideas = {P}sp_{sp}\n"
    evt += "    }\n}\n\n"
w("events/ktits_soviet_mech_events.txt", evt)

# ---------------- decisions ----------------
CATS = {"integrity": ("Целостность Союза", "ktits_is_soviet = yes"), "paranoia": ("Паранойя Пименова", f"ktits_is_soviet = yes\n        has_country_flag = {P}para_on"),
        "balance": ("Баланс Пименов — Партия", "ktits_is_soviet = yes"), "church": ("Церковь Древнего Динозавра", f"ktits_is_soviet = yes\n        has_idea = {P}sp_church"),
        "export": ("Коммунизм на экспорт", f"ktits_is_soviet = yes\n        has_country_flag = {P}export_on")}
CDESC = {"integrity": "Целостность Союза: §Y[?ktits_sov_integrity]§! из 100. Союз держится на съездах, рельсах и печатях. Если печати кончатся, разойдутся и республики.",
         "paranoia": "Паранойя Генсека: §Y[?ktits_sov_paranoia]§!. Личности: Самодержец §Y[?ktits_sov_p_auto]§!, Мягкий §Y[?ktits_sov_p_soft]§!, Жёсткий §Y[?ktits_sov_p_hard]§!, Шиз §Y[?ktits_sov_p_schizo]§!. Чья личность дойдёт до 100, тот и правит.",
         "balance": "Баланс сил Пименов — Партия показан панелью ниже (механика «Баланс сил» игры, как у Италии). Пленум спорит с Генсеком: кто громче, тот и прав.",
         "church": "Покаяние мира: §Y[?ktits_sov_repent]§! из 100. Кости ящеров ждут, когда мир признает вину.",
         "export": "Стран, где коммунизм не ниже 30 %: §Y[?ktits_sov_export]§!. Красная агитация Союза: книги, кино и комиссары с улыбкой. Страны с вечным нейтралитетом не слушают."}
BARS_ = {"integrity": "ktits_sint", "paranoia": "ktits_spar", "church": "ktits_srep"}
cats = ""
for k, (nm, vis) in CATS.items():
    cats += f"{P}{k}_category = {{\n    icon = generic_propaganda\n    picture = GFX_decision_cat_picture_generic_border_conflicts\n" + (f"    scripted_gui = {BARS_[k]}_ui\n" if k in BARS_ else "") + f"    visible = {{\n        {vis}\n    }}\n}}\n\n"
    add(f"{P}{k}_category", nm); add(f"{P}{k}_category_desc", CDESC[k])
w("common/decisions/categories/ktits_soviet_categories.txt", cats)
dec = {k: "" for k in CATS}
def D(cat, key, ru_, desc, cost, cd, body, avail="", target=None, vis=None):
    k = P + key
    s = f"    {k} = {{\n        icon = generic_propaganda\n"
    if vis: s += f"        visible = {{\n            {vis}\n        }}\n"
    if target: s += f"        target_trigger = {{\n            FROM = {{\n                {target}\n            }}\n        }}\n"
    s += f"        available = {{\n            NOT = {{ has_country_flag = {P}cd_{key} }}\n" + (f"            {avail}\n" if avail else "") + "        }\n"
    s += f"        cost = {cost}\n        fire_only_once = no\n        ai_will_do = {{ factor = 1 }}\n        complete_effect = {{\n            if = {{ limit = {{ has_global_flag = ktits_debug }} log = \"KTITS:DEC:[THIS.GetTag]:DONE {k}\" }}\n            set_country_flag = {{ flag = {P}cd_{key} days = {cd} value = 1 }}\n" + ind(body, 12) + "        }\n    }\n\n"
    dec[cat] += s
    add(k, ru_); add(k + "_desc", desc)
def V(var, d, lo=0, hi=100): return f"add_to_variable = {{ var = {P}{var} value = {d} }}\nclamp_variable = {{ var = {P}{var} min = {lo} max = {hi} }}\n"
NP = "ktits_is_soviet = yes"
D("integrity", "dc_congress", "Съезд народов Союза", "В Ваньграде собираются делегаты всех республик. Спорят до хрипоты, но расходятся друзьями.", 75, 90, V("integrity", 8))
D("integrity", "dc_rouble", "Единый рубль", "Деньги республик сводят в одну валюту. Бухгалтеры плачут, экономисты радуются.", 100, 120, V("integrity", 5) + "add_stability = 0.02\n")
D("integrity", "dc_rail", "Железная дорога дружбы", "Рельсы связывают окраины с центром. По ним везут хлеб, газеты и комиссаров.", 120, 120, V("integrity", 6) + "every_owned_state = { limit = { is_core_of = ROOT } add_building_construction = { type = infrastructure level = 1 instant_build = yes } }\n")
D("integrity", "dc_schools", "Национальные школы", "В каждой республике учат на родном языке и на языке Русов.", 50, 90, V("integrity", 5))
D("integrity", "dc_holiday", "Праздник Союза", "Парады, песни и пироги. Всем ясно: вместе веселее.", 40, 90, V("integrity", 4) + "add_stability = 0.03\n")
D("integrity", "dc_purge", "Чистка сепаратистов", "Органы ищут тех, кто мечтает о своей стране. Находят многих, и не всегда тех.", 80, 120, V("integrity", 10) + "add_stability = -0.05\n" + V("paranoia", 5))
TGT = f"{KT}\n                is_subject_of = {SOV}"
D("integrity", "dc_autonomy", "Дать автономию", "Республике разрешили сказать «мы» вместо «они». Она сказала и осталась довольна.", 25, 60, f"FROM = {{ add_stability = 0.03 }}\n" + V("integrity", 3), target=TGT, vis=NP)
D("integrity", "dc_governor", "Прислать наместника", "Наместник приехал с чемоданом и инструкцией. Инструкцию потерял на вокзале, но дело пошло.", 40, 60, "FROM = { add_stability = 0.03 }\n" + V("integrity", 2) + V("paranoia", 2), target=TGT, vis=NP)
D("integrity", "dc_invest", "Вложиться в республику", "Союз построил республике завод, школу и памятник Союзу. Памятник вышел самым удачным.", 100, 90,
  "FROM = { random_owned_controlled_state = { limit = { impassable = no } add_extra_state_shared_building_slots = 1 add_building_construction = { type = industrial_complex level = 1 instant_build = yes } } }\n" + V("integrity", 2), target=TGT, vis=NP)
PA = f"has_country_flag = {P}para_on\n            NOT = {{ has_country_flag = {P}pers_won }}"
for k, nm, d_ in (("auto", "Самодержец", "Генсек примеряет корону перед зеркалом."), ("soft", "Мягкий коммунист", "Генсек гладит по голове подчинённых и просит не бояться."), ("hard", "Жёсткий коммунист", "Генсек стучит кулаком по столу, стол скрипит."), ("schizo", "Шиз", "Генсек считает лампочки и ищет среди них заговорщиков.")):
    D("paranoia", f"dc_p_{k}", f"Усилить личность: {nm}", d_, 50, 30, V("p_" + k, 10) + V("paranoia", 2), PA)
D("paranoia", "dc_calm", "Бессонная ночь без охраны", "Генсек отпускает охрану на одну ночь. Утром охрана аккуратно удивлена.", 60, 90, V("paranoia", -8), PA)
D("balance", "dc_plenum", "Пленум ЦК", "Пленум собрался и единогласно решил, что Партия мудра. Генсек подписал.", 60, 60, BV(-0.15))
D("balance", "dc_order", "Личный приказ Генсека", "Генсек написал приказ собственной рукой. Рука дрожала, приказ нет.", 60, 60, BV(0.15))
D("balance", "dc_politburo", "Обновить Политбюро", "В Политбюро заменили троих. Остальные пересели ближе к выходу.", 80, 90, BV(-0.1) + V("paranoia", 3))
CH = f"has_idea = {P}sp_church"
D("church", "dc_preach", "Проповедь у костей", "Священник читает проповедь над рёбрами ящера. Прихожане стоят молча: так ближе к костям.", 50, 20, "add_popularity = { ideology = theology popularity = 0.07 }\n", vis=CH)
D("church", "dc_dig", "Раскопки для веры", "Землекопы раскапывают всё новые кости. Верующим достаточно одной, но она, как водится, неполная.", 60, 60, V("repent", 2) + "random_owned_controlled_state = { limit = { impassable = no } add_extra_state_shared_building_slots = 1 add_building_construction = { type = industrial_complex level = 1 instant_build = yes } }\n", f"has_completed_focus = {P}ch1", vis=CH)
D("church", "dc_letters", "Письмо в чужие столицы", "Письма с костью в конверте. Адресаты вскрывают, читают и надолго задумываются.", 100, 60, "FROM = { add_popularity = { ideology = theology popularity = 0.05 } }\n" + V("repent", 2),
  f"has_completed_focus = {P}ch6", target=f"exists = yes\n                NOT = {{ original_tag = {SOV} }}\n                NOT = {{ has_idea = ktits_eternal_neutrality }}", vis=CH)
D("church", "dc_confess", "Исповедь Кормчего", "Кормчий кается вслух перед страной, и страна не знает, куда смотреть.", 80, 120, V("repent", 10) + "add_stability = -0.05\n", vis=CH)
EXP = f"has_country_flag = {P}export_on"
XT = f"exists = yes\n                NOT = {{ original_tag = {SOV} }}\n                NOT = {{ has_idea = ktits_eternal_neutrality }}\n                NOT = {{ is_subject_of = {SOV} }}"
D("export", "dc_press", "Красная пресса", "Газеты, книги и кино про светлое будущее. Будущее обещали, сроков не называли.", 50, 60, "FROM = { add_popularity = { ideology = communism popularity = 0.05 } }\n", target=XT, vis=EXP)
D("export", "dc_party", "Поддержать компартию", "Союз присылает местной партии деньги, листовки и инструкторов. Инструкторы сразу идут обедать.", 100, 120, "FROM = { add_popularity = { ideology = communism popularity = 0.1 } add_stability = -0.05 }\n", target=XT, vis=EXP)
D("export", "dc_invite", "Пригласить в Союз", "Союз приглашает: бумаги готовы, ручки лежат, осталось подписать. Отказываться вежливо не принято.", 150, 180,
  f"FROM = {{ set_politics = {{ ruling_party = communism }} }}\n{SOV} = {{ puppet = FROM }}\n", target=XT + "\n                communism > 0.499", vis=EXP)
for k, body in dec.items():
    w(f"common/decisions/ktits_soviet_{k}_decisions.txt", f"{P}{k}_category = {{\n\n{body}}}\n")
# ---------------- extra: Great Socialist Builds (decisions instead of the map), export count, cosmetic names, bars ----------------
def civ_(n): return f"random_owned_controlled_state = {{ limit = {{ impassable = no }} add_extra_state_shared_building_slots = {n} add_building_construction = {{ type = industrial_complex level = {n} instant_build = yes }} }}\n"
def mil_(n): return f"random_owned_controlled_state = {{ limit = {{ impassable = no }} add_extra_state_shared_building_slots = {n} add_building_construction = {{ type = arms_factory level = {n} instant_build = yes }} }}\n"
BUILDS = [("hydro", "Окринская ГЭС", "Плотина на Окре перегородила реку и споры о том, чья она. Свет дали, а споры до сих пор в темноте.", 365, civ_(3) + "add_stability = 0.01\n", ""),
          ("road", "Магистраль до Желтой Реки", "Дорога дотянулась до дальних краёв. По ней уже едут, а где кончается, спорят.", 540, "every_owned_state = { limit = { is_core_of = ROOT } add_building_construction = { type = infrastructure level = 2 instant_build = yes } }\n", ""),
          ("bog", "Осушение Наших Болот", "Болота осушили. Казуалы вышли из камышей и растерянно ищут, где теперь лежать.", 450, f"add_to_variable = {{ var = ktits_casuality value = -10 }}\nclamp_variable = {{ var = ktits_casuality min = 0 max = 100 }}\n" + civ_(2), f"has_country_flag = {P}drain_bog"),
          ("city", "Ваньград-на-Устое: город-завод", "Город построили вокруг завода, а завод вокруг плана. План выполнен, город живёт.", 365, mil_(3), ""),
          ("steel", "Урурский металлургический комбинат", "Комбинат стоит у гор и дымит так, что горы кажутся дымовой трубой.", 400, mil_(2), ""),
          ("sea", "Северный морской путь", "Корабли идут по льду, лёд идёт по кораблям. Порты построены, остальное уточняется.", 400, "random_owned_controlled_state = { limit = { is_coastal = yes } add_building_construction = { type = dockyard level = 1 instant_build = yes } }\n", "")]
ttl_ = {}
bd = f"{P}builds_category = {{\n\n"
bcheck = ""
for k, nm, ds, days, eff_b, avail in BUILDS:
    bd += (f"    {P}b_{k} = {{\n        icon = generic_construction\n        visible = {{\n            has_country_flag = {P}builds_on\n        }}\n        available = {{\n            NOT = {{ has_country_flag = {P}b_{k}_started }}\n"
           + (f"            {avail}\n" if avail else "") +
           f"        }}\n        cost = 150\n        fire_only_once = no\n        ai_will_do = {{ factor = 1 }}\n        complete_effect = {{\n            set_country_flag = {P}b_{k}_started\n            set_country_flag = {{ flag = {P}b_{k}_run days = {days} value = 1 }}\n        }}\n    }}\n\n")
    add(f"{P}b_{k}", nm); add(f"{P}b_{k}_desc", ds)
    bcheck += (f"if = {{\n    limit = {{ has_country_flag = {P}b_{k}_started NOT = {{ has_country_flag = {P}b_{k}_run }} NOT = {{ has_country_flag = {P}b_{k}_done }} }}\n    set_country_flag = {P}b_{k}_done\n"
               f"    add_to_variable = {{ var = {P}builds_done value = 1 }}\n" + ind(eff_b, 4) + "}\n")
w("common/decisions/ktits_soviet_builds_decisions.txt", bd + "}\n")
w("common/decisions/categories/ktits_soviet_builds_category.txt", f"{P}builds_category = {{\n    icon = generic_construction\n    picture = GFX_decision_cat_picture_generic_border_conflicts\n    visible = {{\n        ktits_is_soviet = yes\n        has_country_flag = {P}builds_on\n    }}\n}}\n")
add(f"{P}builds_category", "Великие социалистические стройки"); add(f"{P}builds_category_desc", "Завершено строек: §Y[?ktits_sov_builds_done]§! из 6. Карта строек не нарисована: прогресс показывают решения и их сроки.")
# cosmetic names: the title of the country after the reforms and the Country of Rusy after the collapse (a year later), by the ruling ideology
COS = {"pres": ("Президентский Союз Советских Республик", "Президентского Союза Советских Республик", "президентскосоюзный", (180, 60, 60)),
       "soy": ("Соевый Советский Союз", "Соевого Советского Союза", "соево-советский", (200, 180, 60)),
       "rus_comm": ("Социалистическая Страна Русов", "Социалистической Страны Русов", "русский", (190, 40, 40)), "rus_dem": ("Республика Русов", "Республики Русов", "русский", (60, 110, 190)),
       "rus_fas": ("Держава Русов", "Державы Русов", "русский", (110, 70, 40)), "rus_neu": ("Страна Русов", "Страны Русов", "русский", (140, 140, 140)),
       "rus_cas": ("Сонная Страна Русов", "Сонной Страны Русов", "русский", (60, 180, 75)), "rus_the": ("Святая Русь Русов", "Святой Руси Русов", "русский", (212, 175, 55))}
w("common/countries/cosmetic.txt", "".join(f"ktits_sov_{k} = {{\n    color = rgb {{ {c[0]} {c[1]} {c[2]} }}\n    color_ui = rgb {{ {c[0]} {c[1]} {c[2]} }}\n}}\n\n" for k, (_, _, _, c) in COS.items()))
for k, (n_, d_, a_, _) in COS.items():
    add(f"ktits_sov_{k}", n_); add(f"ktits_sov_{k}_DEF", n_); add(f"ktits_sov_{k}_ADJ", a_)
RUSMAP = [("communism", "comm"), ("democratic", "dem"), ("fascism", "fas"), ("neutrality", "neu"), ("casuality", "cas"), ("theology", "the")]
rus_eff = "".join(f"{'if' if n == 0 else 'else_if'} = {{ limit = {{ has_government = {g} }} set_cosmetic_tag = ktits_sov_rus_{c} }}\n" for n, (g, c) in enumerate(RUSMAP))
extra = (f"# scope = Soviet Union, every month: builds, count of the countries that incline to communism, the Country of Rusy a year after the collapse\n{P}extra_monthly = {{\n" + ind(
    bcheck +
    f"if = {{\n    limit = {{ has_country_flag = {P}export_on }}\n    set_variable = {{ var = {P}export value = 0 }}\n    every_other_country = {{\n        limit = {{ communism > 0.299 }}\n        ROOT = {{ add_to_variable = {{ var = {P}export value = 1 }} }}\n    }}\n}}\n"
    f"if = {{\n    limit = {{ has_country_flag = {P}collapsed NOT = {{ has_country_flag = {P}rus_started }} }}\n    set_country_flag = {P}rus_started\n    set_country_flag = {{ flag = {P}rus_clock days = 365 value = 1 }}\n}}\n"
    f"if = {{\n    limit = {{ has_country_flag = {P}rus_started NOT = {{ has_country_flag = {P}rus_clock }} NOT = {{ has_country_flag = {P}rus_done }} }}\n    set_country_flag = {P}rus_done\n" + ind(rus_eff, 4) + ind("".join(f"every_owned_state = {{ limit = {{ is_core_of = {t_} }} remove_core_of = {t_} }}\n" for t_ in TAGS), 4) + "}\n", 4) + "}\n")
w("common/scripted_effects/ktits_soviet_mech2_effects.txt", extra)
w("common/on_actions/ktits_soviet_mech_on_actions.txt", f"on_actions = {{\n    on_monthly = {{\n        effect = {{\n            if = {{\n                limit = {{ ktits_is_soviet = yes }}\n                {P}monthly = yes\n                {P}extra_monthly = yes\n            }}\n        }}\n    }}\n}}\n")
# graphic bars of the scales (the segments and the frame of make_casuality.py): integrity, paranoia (steps of 5), balance (steps of 10 from -100), repentance
SEG_N, SEG_W, GAP, BAR_X = 20, 22, 1, 14
BARS = {"integrity": ("ktits_sint", "ktits_sov_integrity", 0, 5, "Целостность Союза"), "paranoia": ("ktits_spar", "ktits_sov_paranoia", 0, 5, "Паранойя Пименова"),
        "church": ("ktits_srep", "ktits_sov_repent", 0, 5, "Покаяние мира")}
sg, gg = "", ""
for k, (pre, var, lo, step, lab) in BARS.items():
    trg = "".join(f"            {pre}_seg_{i}_visible = {{\n                check_variable = {{ var = {var} value = {lo + i * step} compare = greater_than_or_equals }}\n            }}\n" for i in range(1, SEG_N + 1))
    sg += f"    {pre}_ui = {{\n        context_type = decision_category\n        window_name = \"{pre}_ui_window\"\n\n        triggers = {{\n{trg}        }}\n    }}\n\n"
    g = f"    containerWindowType = {{\n        name = \"{pre}_ui_window\"\n        position = {{ x = 0 y = 0 }}\n        size = {{ width = 100% height = 50 }}\n        clipping = no\n\n"
    g += f"        instantTextBoxType = {{\n            name = \"{pre}_label\"\n            position = {{ x = {BAR_X} y = 2 }}\n            font = \"hoi_16mbs\"\n            text = \"{pre}_bar_label\"\n            format = left\n            maxHeight = 18\n        }}\n\n"
    g += f"        iconType = {{\n            name = \"{pre}_frame\"\n            spriteType = \"GFX_ktits_cas_bar_frame\"\n            position = {{ x = {BAR_X} y = 22 }}\n            pdx_tooltip = \"{pre}_bar_tt\"\n        }}\n\n"
    for i in range(1, SEG_N + 1):
        g += f"        iconType = {{\n            name = \"{pre}_seg_{i}\"\n            spriteType = \"GFX_ktits_cas_seg_{(i - 1) // 5 + 1}\"\n            position = {{ x = {BAR_X + 3 + (i - 1) * (SEG_W + GAP)} y = 25 }}\n        }}\n"
    gg += g + "    }\n\n"
    add(f"{pre}_bar_label", f"{lab}: [?{var}|0]"); add(f"{pre}_bar_tt", "Каждое деление — " + (f"{step}" ) + " пунктов шкалы.")
w("common/scripted_guis/ktits_soviet.txt", "scripted_gui = {\n\n" + sg + "}\n")
w("interface/ktits_soviet.gui", "guiTypes = {\n\n" + gg + "}\n")


# ---------------- Balance of Power Pimenov - Party (vanilla mechanic of Italy: common/bop/ITA.txt); values -1..1, < 0 towards the Party, > 0 towards Pimenov ----------------
def rng(rid, lo, hi, mods="", act="", deact=""):
    return (f"        range = {{\n            id = {rid}\n            min = {lo}\n            max = {hi}\n            modifier = {{\n{mods}            }}\n            on_activate = {{\n{act}            }}\n            on_deactivate = {{\n{deact}            }}\n        }}\n")
def mods(d): return "".join(f"                {k} = {v}\n" for k, v in d.items())
bop_txt = (f"{BOP} = {{\n    initial_value = 0.25\n    left_side = ktits_sov_party_side\n    right_side = ktits_sov_pimenov_side\n    decision_category = ktits_sov_balance_category\n\n"
           + rng("ktits_sov_balance_range", -0.2, 0.2).replace("        range", "    range") .replace("\n        ", "\n    ") + "\n"
           + "    side = {\n        id = ktits_sov_party_side\n        icon = GFX_bop_ITA_grand_council_side\n\n"
           + rng("ktits_sov_party_low", -0.5, -0.2)
           + rng("ktits_sov_party_high", -0.9, -0.5, mods({"political_power_factor": -0.1, "stability_factor": 0.05}))
           + rng("ktits_sov_party_total", -1, -0.9, "", f"                add_ideas = {P}sp_party_dict\n", f"                remove_ideas = {P}sp_party_dict\n")
           + "    }\n\n    side = {\n        id = ktits_sov_pimenov_side\n        icon = GFX_bop_ITA_mussolini_side\n\n"
           + rng("ktits_sov_pimenov_low", 0.2, 0.5, mods({"political_power_factor": 0.1}))
           + rng("ktits_sov_pimenov_high", 0.5, 0.9, mods({"political_power_factor": 0.2}))
           + rng("ktits_sov_pimenov_total", 0.9, 1, "", f"                add_ideas = {P}sp_pcult\n", f"                remove_ideas = {P}sp_pcult\n")
           + "    }\n}\n")
w("common/bop/ktits_sov.txt", bop_txt)
for k_, r_ in ((BOP, "Баланс Пименов — Партия"), ("ktits_sov_party_side", "Партия"), ("ktits_sov_pimenov_side", "Генсек Пименов"), ("ktits_sov_balance_range", "Равновесие"),
               ("ktits_sov_party_low", "Влияние Партии"), ("ktits_sov_party_high", "Власть Партии"), ("ktits_sov_party_total", "Партийная диктатура"),
               ("ktits_sov_pimenov_low", "Рука Генсека"), ("ktits_sov_pimenov_high", "Личная власть Генсека"), ("ktits_sov_pimenov_total", "Культ личности")):
    add(k_, r_)

L.write_yml(str(M / "localisation/russian/ktits_soviet_mech_l_russian.yml"), "russian", ru)
L.write_yml(str(M / "localisation/english/ktits_soviet_mech_l_english.yml"), "english", en)
print(f"soviet mech: {len(SPI) + 1} spirits, {sum(d.count('complete_effect') for d in dec.values())} decisions in {len(CATS)} categories, {len(EV)} events, release effects for {len(TAGS)} parts")
