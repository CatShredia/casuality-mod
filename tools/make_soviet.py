"""Soviet Union (tag MAK) in the game: start (laws, variables, event), focus tree (docs/focuses/Soviet-Union-Focus-Tree.md), national spirits, opinion modifiers,
the game rule ktits_mak_paths and the economic-zone focus trees of the breakaway countries K01-K06, K42 (docs/mechanics/Soviet-Union.md, sections 8, 13, 14).
Names, days and lore descriptions of the focuses are read from the focus-tree document (tables), so the texts live in one place. Numbers are INVENTED
(docs/lore/Invented-Lore.md). NOT done yet (next phase): the scales as decisions with a bar (integrity, paranoia, balance, repentance), construction projects,
export of communism, the monthly collapse check and the zone/crash spirits on a break-up. Several keys are [uncertain] (marked below): take_claimed_state wargoal,
release_puppet, create_faction.
Writes: common/{national_focus,ideas,scripted_triggers,scripted_effects,on_actions,opinion_modifiers,game_rules}/ktits_soviet*, events/ktits_soviet_events.txt,
localisation ru/en ktits_soviet_l_*.yml. Usage: python tools/make_soviet.py [--mod PATH]"""
import argparse, math, re
from pathlib import Path
import lore_data as L

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
a = ap.parse_args()
M = Path(a.mod)
info = L.load_mod(M)
lore2tag = {lt: t for t, lt in info["tag2lore"].items()}
SOV, KAZ, ASM, KYT, DMK, CSK, BRT, REI, SOYA = "MAK", lore2tag["CSL"], lore2tag["SVA"], lore2tag["KTY"], lore2tag["DMK"], lore2tag["KZZ"], lore2tag["BRT"], lore2tag["TMR"], lore2tag["SOY"]
PARTS = ["K01", "K02", "K03", "K04", "K05", "K06", "K42"]
P = "ktits_sov_"

def T(s): return re.sub(r"(?m)^( {4})+", lambda m: "\t" * (len(m.group()) // 4), s)
def w(rel, text):
    p = M / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(T(text), encoding="utf-8", newline="\n")
ru, en = [], []
def add(k, r, e=None):
    ru.append((k, r)); en.append((k, e or L.translit(r)))
def q(s): return s.replace("`", "").replace('"', "'")

# ---------------- map: states for claims and wargoals ----------------
pc, _ = L.province_centroids(M)
st = info["states"]
def cen(sid):
    ps = st[sid]["provs"]; return (sum(pc[p][0] for p in ps) / len(ps), sum(pc[p][1] for p in ps) / len(ps))
def owned(tag): return [s for s, v in st.items() if v["owner"] == tag and v["provs"]]
def nearest(tag, ref, k):
    refc = [cen(s) for s in owned(ref)]
    return sorted(sorted(owned(tag), key=lambda s: min(math.dist(cen(s), r) for r in refc))[:k])
ASM_ST = nearest(ASM, SOV, 5)
DMK_ST = nearest(DMK, CSK, 5)
KYT_ST = sorted(sorted(owned(KYT), key=lambda s: cen(s)[1])[:6])
NEW_T = [("fdp", "FDP", "Федерации Депутатов", 5, "f"), ("ara", "Z06", "Арагонии", 5, "g"), ("mgn", "MGN", "Магнолии", 5, "m"), ("clb", "CLB", "Челябе", 4, "h"), ("srk", "SRK", "Сарайкумскому Ханству", 5, "s")]   # (key, lore tag, dative, states, focus letter)
NT = {k: (lore2tag[lt], nearest(lore2tag[lt], SOV, n), dat, ch) for k, lt, dat, n, ch in NEW_T}
_hc = next((M / "history/countries").glob(f"{CSK} - *.txt"))
_capst = int(re.search(r"capital\s*=\s*(\d+)", _hc.read_text(encoding="utf-8", errors="ignore")).group(1))
_vp = re.findall(r"victory_points\s*=\s*\{\s*(\d+)\s+(\d+)", (M / "history/states" / f"{_capst}.txt").read_text(encoding="utf-8", errors="ignore"))
CSK_PROV = int(max(_vp, key=lambda v: int(v[1]))[0]) if _vp else st[_capst]["provs"][0]
VOL_UNIT = f'create_unit = {{ division = "name = \\"Добровольцы Союза\\" division_template = \\"Добровольцы Союза\\" start_experience_factor = 0.3 start_equipment_factor = 1" owner = PREV prioritize_location = {CSK_PROV} }}'
VOL_TPL = 'division_template = { name = "Добровольцы Союза" regiments = { infantry = { x = 0 y = 0 } infantry = { x = 0 y = 1 } infantry = { x = 1 y = 0 } infantry = { x = 1 y = 1 } } }'
print("soviet: claims", {k: v[1] for k, v in NT.items()})
print(f"soviet: claims Assembly {ASM_ST}, Dmitrov strip {DMK_ST}, northern Kytai {KYT_ST}")

# ---------------- doc tables: name -> (days, description) ----------------
doc = (L.REPO / "docs/focuses/Soviet-Union-Focus-Tree.md").read_text(encoding="utf-8").replace("\r\n", "\n")
DOC = {}
for l in doc.split("\n"):
    if l.startswith("|") and not l.startswith("|---"):
        c = [x.strip() for x in l.strip().strip("|").split("|")]
        if len(c) >= 4 and re.match(r"\d+$", c[1]): DOC[c[0]] = (int(c[1]), c[2])
def dd(key):
    m = [k for k in DOC if k.startswith(key)]
    assert len(m) == 1, (key, m)
    return m[0], DOC[m[0]]

# ---------------- effect helpers ----------------
TT = {}
def ttl(key, r, e=None): TT[key] = (r, e or L.translit(r))
def pp(v): return f"add_political_power = {v}\n"
def stab(pct): return f"add_stability = {pct / 100:g}\n"
def pop(ideo, pct): return f"add_popularity = {{ ideology = {ideo} popularity = {pct / 100:g} }}\n"
def flag(f): return f"set_country_flag = {f}\n"
def var(name, v, ru_, lo=0, hi=100):
    k = f"{P}tt_{name}_{'p' if v > 0 else 'm'}{abs(v):g}".replace(".", "_")
    ttl(k, f"{ru_}: §{'G' if v > 0 else 'R'}{v:+g}§!", f"{L.translit(ru_)}: §{'G' if v > 0 else 'R'}{v:+g}§!")
    return f"custom_effect_tooltip = {k}\nadd_to_variable = {{ var = {P}{name} value = {v} }}\nclamp_variable = {{ var = {P}{name} min = {lo} max = {hi} }}\n"
def INT(v): return var("integrity", v, "Целостность Союза")
def PAR(v): return var("paranoia", v, "Паранойя Пименова")
def BAL(v):
    k = f"{P}tt_balance_{'p' if v > 0 else 'm'}{abs(v)}"
    ttl(k, f"Баланс сил: §Y{v:+g} %§! ({'к Пименову' if v > 0 else 'к Партии'})")
    return f"custom_effect_tooltip = {k}\nadd_power_balance_value = {{ id = ktits_sov_power_balance value = {v / 100:g} }}\n"
def PERS(k, v): return var("p_" + k, v, {"auto": "Личность «Самодержец»", "soft": "Личность «Мягкий коммунист»", "hard": "Личность «Жёсткий коммунист»", "schizo": "Личность «Шиз»"}[k])
def REP(v): return var("repent", v, "Покаяние мира")
def CAS(v):
    k = f"{P}tt_cas_{'p' if v > 0 else 'm'}{abs(v)}"
    ttl(k, f"Шкала Казуальности Союза: §{'R' if v > 0 else 'G'}{v:+g}§!")
    return f"custom_effect_tooltip = {k}\nadd_to_variable = {{ var = ktits_casuality value = {v} }}\nclamp_variable = {{ var = ktits_casuality min = 0 max = 100 }}\nhidden_effect = {{ ktits_casuality_update = yes }}\n"
def tip(key, r):
    ttl(key, r); return f"custom_effect_tooltip = {key}\n"
SP = {}
PIC = {"stability_factor": "eng_tackle_capitalism", "political_power_gain": "generic_communism_drift_bonus", "industrial_capacity_factory": "generic_production_bonus",
       "production_speed_buildings_factor": "generic_production_bonus", "army_attack_factor": "generic_war_preparation", "army_org_factor": "generic_war_preparation",
       "conscription_factor": "generic_manpower_bonus", "consumer_goods_factor": "generic_production_bonus", "research_speed_factor": "generic_research_bonus"}
def spirit(key, ru_, desc, mods):
    SP[P + "sp_" + key] = (ru_, desc, mods); return f"add_ideas = {P}sp_{key}\n"
def civ(n):
    k = f"{P}tt_civ{n}"; ttl(k, f"Гражданских фабрик: §G+{n}§! (в случайном штате)")
    return f"custom_effect_tooltip = {k}\nhidden_effect = {{\n    random_owned_controlled_state = {{ limit = {{ impassable = no }} add_extra_state_shared_building_slots = {n} add_building_construction = {{ type = industrial_complex level = {n} instant_build = yes }} }}\n}}\n"
def mil(n):
    k = f"{P}tt_mil{n}"; ttl(k, f"Военных фабрик: §G+{n}§! (в случайном штате)")
    return f"custom_effect_tooltip = {k}\nhidden_effect = {{\n    random_owned_controlled_state = {{ limit = {{ impassable = no }} add_extra_state_shared_building_slots = {n} add_building_construction = {{ type = arms_factory level = {n} instant_build = yes }} }}\n}}\n"
def OP(tag, v):
    m = f"{P}op_{'p' if v > 0 else 'm'}{abs(v)}"
    return f"add_opinion_modifier = {{ target = {tag} modifier = {m} }}\n{tag} = {{ add_opinion_modifier = {{ target = ROOT modifier = {m} }} }}\n"
OPS = sorted({10, 20, 25, 30, 40, 50})
def claims(ids, key, r, cf=()):
    ttl(key, r)
    return f"custom_effect_tooltip = {key}\nhidden_effect = {{\n" + "".join(f"    {s} = {{ add_claim_by = ROOT }}\n" for s in ids) + "}\n" + "".join(flag(P + "cl_" + c) for c in cf)
def wargoal(tag, ids, key, r):   # [uncertain: take_claimed_state with generator]
    ttl(key, r)
    return f"custom_effect_tooltip = {key}\nhidden_effect = {{\n    create_wargoal = {{ type = take_claimed_state target = {tag} generator = {{ {' '.join(map(str, ids))} }} }}\n}}\n"
def annex_wg(tag, key, r):
    ttl(key, r)
    return f"custom_effect_tooltip = {key}\nhidden_effect = {{ create_wargoal = {{ type = annex_everything target = {tag} }} }}\n"
def ev(tag, eid, key, r):
    ttl(key, r)
    return f"custom_effect_tooltip = {key}\nhidden_effect = {{ {tag} = {{ country_event = {{ id = ktits_soviet.{eid} }} }} }}\n"
def needs(ideo, pct, key):
    ttl(key, f"Популярность идеологии не ниже §Y{pct} %§!")
    return f"custom_trigger_tooltip = {{\n    tooltip = {key}\n    {ideo} > {pct / 100 - 0.001:.3f}\n}}"
def exists(tag): return f"country_exists = {tag}"
def infra(n):
    k = f"{P}tt_infra{n}"; ttl(k, f"Инфраструктура: §G+{n}§! в каждом штате")
    return f"custom_effect_tooltip = {k}\nhidden_effect = {{ every_owned_state = {{ add_building_construction = {{ type = infrastructure level = {n} instant_build = yes }} }} }}\n"

# ---------------- focus data ----------------
POL, IND, ARM = "FOCUS_FILTER_POLITICAL", "FOCUS_FILTER_INDUSTRY", "FOCUS_FILTER_ARMY_XP"
F = []   # (id, doc key, branch, prerequisites [OR groups], exclusive ids, available, reward, filter, icon, ai factor)
def fc(i, key, br, pre, excl, avail, rew, flt=POL, icon="GFX_goal_generic_political_pressure", ai=60): F.append((i, key, br, pre, excl, avail, rew, flt, icon, ai))
CASUAL = f"NOT = {{ has_country_flag = {P}casual_path }}"
# --- Паранойя
fc("p0", "Бессонные ночи", "para", [], [], "has_government = communism", flag(P + "para_on") + tip(P + "tt_para_on", "Запускает механику Паранойи: шкала, личности и решения категории «Паранойя Пименова»"), ai=5000)
for k, nm in (("pa", "Самодержец"), ("ps", "Мягкий коммунист"), ("ph", "Жёсткий коммунист"), ("pz", "Шиз")):
    key = {"pa": "auto", "ps": "soft", "ph": "hard", "pz": "schizo"}[k]
    fc(k, nm, "para", [["p0"]], [x for x in ("pa", "ps", "ph", "pz", "pb") if x != k], None, PERS(key, 20) + flag(P + "pf_" + key), ai=40)
fc("pb", "Баланс", "para", [["p0"]], ["pa", "ps", "ph", "pz"], None, "".join(PERS(k, -10) for k in ("auto", "soft", "hard", "schizo")) + PAR(-10) + flag(P + "pf_balance"), ai=5)
# --- корень и пути
ttl(P + "tt_pers_won", "Одна из личностей Генсека победила (шкала «Паранойя Пименова»)")
PERS_OK = f"custom_trigger_tooltip = {{\n    tooltip = {P}tt_pers_won\n    has_country_flag = {P}pers_won\n}}"
fc("cong", "Съезд после войны", "root", [], [], None, pp(50) + flag(P + "congress"), ai=1000, icon="GFX_goal_generic_dangerous_deal")
ROOTS = ["u1", "r1", "m1", "t1", "k1", "f1"]
def root(i, key, pre, rew, ai, avail=None): fc(i, key, "p_" + i, [["cong"]], [x for x in ROOTS if x != i], avail or PERS_OK, rew, ai=ai)
root("u1", "Немыслимый вариант", 0, pop("theology", 5) + pop("democratic", 5) + INT(-5), 40)
fc("u2", "Оружие для недовольных", "p_u1", [["u1"]], [], None, pop("theology", 15), ai=120)
fc("u3", "Вторая гражданская", "p_u1", [["u2"]], [], needs("theology", 30, P + "tt_need_th30"),
   tip(P + "tt_civil", "Гражданская война: Союз против теократов") + "start_civil_war = { ideology = theology size = 0.4 }\n", ai=120)
fc("g1", "Гласность", "p_u1", [["u1"]], ["u2"], None, pop("democratic", 15) + stab(-5), ai=120)
fc("g2", "Свободные выборы", "p_u1", [["g1"]], [], None, pop("democratic", 20), ai=120)
fc("g3", "Соевый Советский Союз", "p_u1", [["g2"]], [], needs("democratic", 50, P + "tt_need_dem"),
   "set_politics = { ruling_party = democratic elections_allowed = yes }\nset_cosmetic_tag = ktits_sov_soy\n" + OP(SOYA, 50), ai=120)
root("r1", "Политические реформы", 0, INT(5) + stab(-3), 120)
fc("r2", "Федеративный договор", "p_r1", [["r1"]], [], None, INT(5) + flag(P + "fed_treaty"), ai=120)
fc("r3", "Договоры с республиками", "p_r1", [["r2"]], [], None, INT(5) + tip(P + "tt_repub_ev", "События республик (`K01`–`K06`): поддержать федерацию или нет"), ai=120)
fc("r4", "Президентский Союз", "p_r1", [["r3"]], [], None, INT(5) + flag(P + "president") + stab(3) + "set_cosmetic_tag = ktits_sov_pres\n", ai=120)
fc("r5", "Ослабление цензуры", "p_r1", [["r1"]], [], None, pop("democratic", 10), ai=120)
fc("r6", "Многопартийность", "p_r1", [["r5"]], [], None, pop("democratic", 15) + BAL(-10), ai=120)
fc("r7", "Демократический Союз", "p_r1", [["r6"]], [], needs("democratic", 50, P + "tt_need_dem"), "set_politics = { ruling_party = democratic elections_allowed = yes }\n", ai=120)
root("m1", "Мягкий коммунизм", 0, stab(5) + BAL(-10), 300)
fc("m2", "Амнистия", "p_m1", [["m1"]], [], None, stab(5) + PAR(-10) + spirit("amnesty", "Амнистия", "Двери тюрем открыли, и выяснилось, что внутри сидели в основном соседи.", {"conscription_factor": 0.01}), ai=200)
fc("m3", "Открытые съезды", "p_m1", [["m1"]], [], None, INT(5) + spirit("open_congress", "Открытые съезды", "Съезды теперь открыты для всех. Желающих выступать мало, желающих слушать ещё меньше.", {"political_power_gain": 0.1}), ai=200)
fc("m4", "Советы трудовых коллективов", "p_m1", [["m2"]], [], None, spirit("councils", "Советы трудовых коллективов", "Коллективы сами решают, как им работать. Обычно решают отдохнуть и обсудить.", {"industrial_capacity_factory": 0.1}), ai=200)
fc("m5", "Власть коллектива", "p_m1", [["m4", "m3"]], [], None, BAL(-15) + spirit("collective", "Коллективное руководство", "Решения принимает коллектив, а ответственность несёт стол, за которым спорили.", {"stability_factor": 0.1}), ai=200)
root("t1", "Тоталитарный коммунизм", 0, pop("communism", 10) + BAL(10), 100)
fc("t2", "Органы не дремлют", "p_t1", [["t1"]], [], None, INT(10) + stab(-5) + PAR(5), ai=100)
fc("t3", "Трудовые армии", "p_t1", [["t1"]], [], None, civ(3) + stab(-5), ai=100)
fc("t4", "Культ Генсека", "p_t1", [["t2"]], [], None, spirit("cult", "Культ Генсека", "Портреты Генсека висят везде, даже там, где вешать нечего. Генсек смотрит с них строго и устало.", {"political_power_gain": 0.3, "war_support_factor": 0.1}), ai=100)
fc("t5", "Государство-монолит", "p_t1", [["t4", "t3"]], [], None, flag(P + "monolith") + spirit("monolith", "Монолит", "Государство стоит как плита: давит и не шевелится. Окраины подпирают её, чтобы не упала.", {"stability_factor": 0.05}) + tip(P + "tt_mono", "Целостность не падает ниже 50"), ai=100)
root("k1", "Казуальный путь", 0, CAS(15) + flag(P + "casual_path"), 30)
fc("k2", "Право на сиесту", "p_k1", [["k1"]], [], None, CAS(15) + stab(5), ai=100)
fc("k3", "Посольство в Ставку", "p_k1", [["k2"]], [], None, OP(KAZ, 50), ai=100)
fc("k4", "Под рукой Ставки", "p_k1", [["k3"]], [], f"{exists(KAZ)}\n{KAZ} = {{ is_subject = no }}",
   f"{KAZ} = {{ puppet = {{ target = {SOV} end_wars = no }} }}\n", ai=100)
fc("k5", "Покорность", "p_k1", [["k4"]], ["k7"], None, flag(P + "obey") + tip(P + "tt_obey", "Открывает «Раздел ради покоя»"), ai=100)
fc("k6", "Раздел ради покоя", "p_k1", [["k5"]], [], None,
   flag("ktits_casuality_fallen") + tip(P + "tt_split", "`K01`–`K06` и Идель-Кама выделяются марионетками Казуалии") + "hidden_effect = {\n" + "".join(f"    ktits_release_{t} = yes\n" for t in PARTS) + "}\n", ai=100)
fc("k7", "Перехват титула", "p_k1", [["k4"]], ["k5"], None, f"{KAZ} = {{ add_to_variable = {{ var = ktits_kaz_inner value = -10 }} }}\n" + tip(P + "tt_title", "Внутренняя Казуальность Казуалии: §G−10§!") + OP(KAZ, -50), ai=100)
fc("k8", "Борьба за титул", "p_k1", [["k7"]], [], None, tip(P + "tt_indep", "Война за независимость от Казуалии [uncertain: освобождение марионетки]") + f"{KAZ} = {{ end_puppet = {SOV} }}\n" + spirit("arkho_claim", "Претензия на титул", "Союз потребовал титул Священного-Архо-Казуала и получил в ответ длинный зевок.", {"war_support_factor": 0.1}), ai=100)
# --- Церковь Древнего Динозавра
fc("ch1", "Кости под Ваньградом", "church", [["u3"]], [], None, pop("theology", 5) + tip(P + "tt_dig", "Открывает решение «Раскопки для веры» [следующая фаза]"), ai=150)
fc("ch2", "Вина Иоанна", "church", [["ch1"]], [], None, pop("theology", 10) + stab(-5), ai=150)
fc("ch3", "Церковь Древнего Динозавра", "church", [["ch2"]], [], None, pop("theology", 10) + spirit("church", "Церковь Древнего Динозавра", "Первая служба прошла над костями. Прихожане молчали, потому что ящеры тоже не говорили.", {"stability_factor": 0.1, "political_power_gain": -0.1}), ai=150)
fc("ch4", "Храмы-скелеты", "church", [["ch3"]], [], None, civ(3) + pop("theology", 10), ai=150)
fc("ch5", "Великий Кормчий", "church", [["ch4"]], [], needs("theology", 50, P + "tt_need_th50"), "set_politics = { ruling_party = theology elections_allowed = no }\n", ai=150)
fc("ch6", "Проповедь покаяния", "church", [["ch3"]], ["ch8"], None, REP(10) + tip(P + "tt_letters", "Решение «Письмо в чужие столицы» [следующая фаза]"), ai=150)
fc("ch7", "Всемирное покаяние", "church", [["ch6"]], [], None, REP(10) + tip(P + "tt_repent", "Шкала Покаяния: при 100 события целей [следующая фаза]"), ai=150)
fc("ch8", "Огонь и кость", "church", [["ch3"]], ["ch6"], None, spirit("bone_fire", "Огонь и кость", "Полковые священники идут с армией. У каждого солдата по кости на счастье и по молитве на всякий случай.", {"army_org_factor": 0.05, "war_support_factor": 0.1}), ai=150)
fc("ch9", "Поход покаяния", "church", [["ch8"]], [], None, tip(P + "tt_crusade", "Цели войны против стран с популярностью теологии ниже 10 % [следующая фаза]") + flag(P + "crusade"), ai=150)
# --- Фашистский путь
root("f1", "Самодержавный курс", 0, pop("fascism", 10) + BAL(20), 40)
fc("f2", "Встанька", "p_f1", [["f1"]], [], None, pop("fascism", 15), ai=120)
fc("f3", "Вертикаль власти", "p_f1", [["f2"]], [], None, stab(5) + spirit("vertical", "Вертикаль власти", "Все приказы идут сверху вниз. Снизу идут только отчёты.", {"political_power_gain": 0.3}), ai=120)
fc("f4", "Чистка Партии", "p_f1", [["f3"]], ["f6"], None, BAL(30) + pop("fascism", 10), ai=120)
fc("f5", "Империя Русов", "p_f1", [["f4"]], [], needs("fascism", 50, P + "tt_need_fas"), "set_politics = { ruling_party = fascism elections_allowed = no }\n" + INT(10), ai=120)
fc("f6", "Приказ о единстве", "p_f1", [["f3"]], ["f4"], None, INT(15) + spirit("unity", "Приказ о единстве", "Республикам приказано любить друг друга. Любовь проверяют на местах.", {"conscription_factor": 0.02}), ai=120)
fc("f7", "Великий поход", "p_f1", [["f6"]], [], needs("fascism", 50, P + "tt_need_fas"), spirit("great_march", "Великий поход", "Единство, которое не пускают наружу, застаивается. Колонны выступили.", {"army_attack_factor": 0.1}) + flag(P + "great_march"), ai=120)
# --- Борьба с Казуальностью
fc("a1", "Комиссия по бодрости", "anti", [], [], CASUAL, CAS(-10), ai=40)
fc("a2", "Буфер на болотах", "anti", [["a1"]], [], CASUAL, tip(P + "tt_buffer", "Решение «Буфер на болотах» бесплатно [uncertain: связь с решением Казуалии]") + flag(P + "buffer_free"), ai=40)
fc("a3", "Агентурная сеть против Казуальности", "anti", [["a1"]], [], CASUAL, flag(P + "agents") + tip(P + "tt_agents", "Агентство: +1 оперативник [uncertain: ключ]"), ai=40)
fc("a4", "Глаза в тумане", "anti", [["a3"]], [], CASUAL, f"{KAZ} = {{ add_to_variable = {{ var = ktits_kaz_inner value = -5 }} }}\n" + tip(P + "tt_eyes", "Внутренняя Казуальность Казуалии: §G−5§!"), ai=40)
fc("a5", "Ударники против лени", "anti", [["a1"]], [], CASUAL, CAS(-10) + spirit("udarniki", "Ударники против лени", "Ударники выходят на смену раньше гудка. Остальные просыпаются от их песен.", {"industrial_capacity_factory": 0.05}), ai=40)
fc("a6", "Осушение Наших Болот", "anti", [["a5"]], [], CASUAL, flag(P + "drain_bog") + tip(P + "tt_drain", "Открывает стройку «Осушение Наших Болот» [следующая фаза]"), ai=40)
# --- Внешняя политика
fc("x0", "Мир за окном", "ext", [["g3", "r4", "r7", "m5", "t5", "f5", "ch5"]], [], CASUAL, flag(P + "world_open"), ai=40, icon="GFX_goal_generic_improve_relations")
fc("x1", "Коммунизм на экспорт", "ext", [["x0"]], ["x2", "x3", "x4"], "has_government = communism", flag(P + "export_on") + tip(P + "tt_export", "Включает механику «Коммунизм на экспорт» [следующая фаза]"), ai=30)
fc("x2", "Коммунизм в отдельной стране", "ext", [["x0"]], ["x1", "x3", "x4"], "has_government = communism", "add_war_support = 0.1\n", ai=30)
fc("x3", "Великая Континентальная империя", "ext", [["x0"]], ["x1", "x2", "x4"], "has_government = fascism", flag(P + "continental"), ai=30)
fc("x4", "Демократический щит", "ext", [["x0"]], ["x1", "x2", "x3"], "has_government = democratic", OP(BRT, 50) + OP(SOYA, 50), ai=30)
fc("x5", "Договор с Тямовским рейхом", "ext", [["x2"]], [], exists(REI), ev(REI, 20, P + "tt_reich_ev", "Событие рейха: договор (технологии и торговля) или отказ") + OP(REI, 10), ai=30)
fc("x6", "Временный союз с рейхом", "ext", [["x3"]], [], exists(REI), ev(REI, 21, P + "tt_reich_ally", "Событие рейха: союз на 2 года"), ai=30)
fc("x7", "Континент под Союзом", "ext", [["x6"]], [], None, claims(ASM_ST + DMK_ST, P + "tt_cont_claims", "Претензии на соседние штаты Ассамблеи и Княжества", ("asm", "dmk")), ai=30)
fc("x8", "Союз с Бриттаном и Соевой Республикой", "ext", [["x4"]], [], None, OP(BRT, 40) + OP(SOYA, 40), ai=30)
fc("x9", "Уничтожение угроз", "ext", [["x8"]], [], None, annex_wg(KAZ, P + "tt_threat_wg", "Цель войны против Казуалии [uncertain: полный список фашистских и казуальных соседей]"), ai=30)
# --- Рубежи Союза
RX = [["x2"]]
fc("ra1", "Претензии на Северную Ассамблею", "rub_a", RX, [], exists(ASM), claims(ASM_ST, P + "tt_asm_claims", "Претензии на 5 ближайших штатов Северной Ассамблеи; открывает решение-ультиматум", ("asm",)) + OP(ASM, -30), ai=30)
fc("ra2", "Отторжение окраин", "rub_a", [["ra1"]], [], None, wargoal(ASM, ASM_ST, P + "tt_asm_wg", "Цель войны на претензионные штаты Ассамблеи (без аннексии)"), ai=30)
fc("ra3", "Освоение окраин", "rub_a", [["ra2"]], [], None, civ(1) + infra(1), ai=30)
fc("rd1", "Взгляд за хребет", "rub_d", RX, [], exists(DMK), OP(DMK, -20) + "add_war_support = 0.03\n" + claims(DMK_ST, P + "tt_dmk_claims", "Претензии на 5 прикуштунских штатов Княжества; открывает решение-ультиматум", ("dmk",)), ai=30)
fc("rd2", "Урок Княжеству", "rub_d", [["rd1"], ["rc2"], ["rc4"]], [], None, wargoal(DMK, DMK_ST, P + "tt_dmk_wg", "Цель войны на прикуштунскую полосу Княжества"), ai=30)
fc("rc0", "Казачий вопрос", "rub_c", RX, [], exists(CSK), OP(CSK, 10), ai=30)
fc("rc1", "Помощь без обязательств", "rub_c", [["rc0"]], ["rc3"], None, OP(CSK, 40) + tip(P + "tt_help", "Казачья Земля получает 2000 единиц пехотного снаряжения от Союза, без альянса и гарантий 2 добровольческие дивизии в её столице; Союз получает ванильное действие «Отправить добровольцев»") + f"hidden_effect = {{ {CSK} = {{ add_equipment_to_stockpile = {{ type = infantry_equipment amount = 2000 producer = {SOV} }}\n {VOL_TPL}\n capital_scope = {{ {VOL_UNIT} {VOL_UNIT} }} }} }}\nadd_ideas = {P}sp_volunteers\n", ai=30)
fc("rc2", "Станичные поставки", "rub_c", [["rc1"]], [], None, tip(P + "tt_supply", "Торговый договор: снабжение Казачьей Земли +15 % [следующая фаза]") + flag(P + "cossack_supply"), ai=30)
fc("rc3", "Давление на Казачью Землю", "rub_c", [["rc0"]], ["rc1"], None, OP(CSK, -40), ai=30)
fc("rc4", "Ультиматум присоединения", "rub_c", [["rc3"]], [], None, ev(CSK, 10, P + "tt_ultimatum", "Событие Казачьей Земли: стать марионеткой Союза или получить войну"), ai=30)
fc("rk1", "Карантин на юге", "rub_k", RX, [], CASUAL, CAS(-1) + tip(P + "tt_quarantine", "Укрепления на границе с Казуалией +1 [uncertain: массовая стройка укреплений]"), ai=30)
fc("rk2", "Конец Ставки", "rub_k", [["rk1"]], [], exists(KAZ), annex_wg(KAZ, P + "tt_kaz_wg", "Цель войны (аннексия) против Казуалии"), ai=30)
fc("ry1", "Претензии на север Кытая", "rub_y", RX, [], exists(KYT), claims(KYT_ST, P + "tt_kyt_claims", "Претензии на 6 самых северных штатов Кытая; открывает решение-ультиматум", ("kyt",)) + OP(KYT, -30), ai=30)
fc("ry2", "Северные провинции", "rub_y", [["ry1"]], [], None, wargoal(KYT, KYT_ST, P + "tt_kyt_wg", "Цель войны на северные штаты Кытая"), ai=30)
for _k, (_tg, _ids, _dat, _ch) in NT.items():
    fc("r" + _ch + "1", "Претензии на " + _dat, "rub_" + _ch, RX, [], exists(_tg), claims(_ids, P + f"tt_{_k}_claims", f"Претензии на {len(_ids)} ближайших штатов; открывает решение-ультиматум", (_k,)) + OP(_tg, -20), ai=30)
fc("ry3", "Северные заставы", "rub_y", [["ry2"]], [], None, spirit("north_posts", "Северные заставы", "Новые границы, новые заставы. Заставы пока пустые, но флаг уже есть.", {"supply_consumption_factor": -0.1}), ai=30)
# --- Экономика
IC = "GFX_goal_generic_construct_civ_factory"
fc("e1", "Восстановление после войны", "eco", [], [], None, civ(2), IND, IC, 20)
fc("e2", "Первая пятилетка", "eco", [["e1"]], [], None, spirit("five_year", "Первая пятилетка", "План выполнили на бумаге. Бумагу пустили на растопку, чтобы заводам было тепло.", {"production_speed_buildings_factor": 0.1}), IND, IC, 20)
fc("e3", "Великие социалистические стройки", "eco", [["e2"]], [], None, flag(P + "builds_on") + tip(P + "tt_builds", "Включает стройки и интерактивную карту [следующая фаза]"), IND, IC, 20)
fc("e4", "Электрификация", "eco", [["e1"]], [], None, spirit("electric", "Электрификация", "Лампочки Ильича горят над каждой избой. Избы удивлены.", {"industrial_capacity_factory": 0.05}), IND, IC, 20)
fc("e5", "Урурская индустрия", "eco", [["e4"]], [], None, mil(2), IND, IC, 20)
fc("e6", "Колхозы Росской Равнины", "eco", [["e2"]], [], None, spirit("kolkhoz", "Колхозы Росской Равнины", "Поля общие, урожай общий, споры о том, чей он, тоже общие.", {"consumer_goods_factor": -0.05, "conscription_factor": 0.01}), IND, IC, 20)
fc("e7", "Сибирские недра", "eco", [["e5"]], [], None, tip(P + "tt_res", "Нефть, хром и вольфрам +4 каждого [uncertain: ключ ресурсов]"), IND, IC, 20)
# --- Армия
AI_ = "GFX_goal_generic_army_tanks"
fc("ar1", "Красная армия после войны", "army", [], [], None, "army_experience = 25\n", ARM, AI_, 3)
fc("ar2", "Массовая армия", "army", [["ar1"]], [], None, spirit("mass_army", "Массовая армия", "Призвали всех, у кого есть сапоги. У кого нет, призовут весной.", {"conscription_factor": 0.02}), ARM, AI_, 3)
fc("ar3", "Кадровая армия", "army", [["ar1"]], [], None, "army_experience = 25\n" + spirit("cadre", "Кадровая армия", "Служат те, кто умеет. Остальные учатся у тех, кто умеет.", {"army_org_factor": 0.05}), ARM, AI_, 3)
fc("ar4", "Глубокая операция", "army", [["ar2", "ar3"]], [], None, "add_doctrine_cost_reduction = { name = ktits_sov_doc cost_reduction = 0.5 uses = 1 category = land_doctrine }\n", ARM, AI_, 3)
fc("ar5", "Танковые корпуса", "army", [["ar4"]], [], None, "add_tech_bonus = { name = ktits_sov_tank bonus = 0.5 uses = 2 category = armor }\n", ARM, AI_, 3)
fc("ar6", "Воздушный флот Союза", "army", [["ar1"]], [], None, "air_experience = 25\n" + mil(1), ARM, AI_, 3)
fc("ar7", "Штурмовики", "army", [["ar6"]], [], None, "add_tech_bonus = { name = ktits_sov_cas bonus = 0.5 uses = 1 category = cas_bomber }\n", ARM, AI_, 3)
fc("ar8", "Дальние бомбардировщики", "army", [["ar7"]], [], None, "add_tech_bonus = { name = ktits_sov_bomb bonus = 0.5 uses = 1 category = cat_strategic_bomber }\n", ARM, AI_, 3)
fc("ar9", "Флот двух морей", "army", [["ar1"]], [], None, "random_owned_controlled_state = { limit = { is_coastal = yes } add_building_construction = { type = dockyard level = 1 instant_build = yes } }\n", ARM, AI_, 3)
fc("ar10", "Синее и Кряхтское море", "army", [["ar9"]], [], None, "add_tech_bonus = { name = ktits_sov_dd bonus = 0.5 uses = 1 category = dd_tech }\n", ARM, AI_, 3)
fc("ar11", "Северный флот", "army", [["ar10"]], [], None, "random_owned_controlled_state = { limit = { is_coastal = yes } }\n", ARM, AI_, 3)
# --- Спасение экономики (Экономический блок)
KTAGS = "OR = { " + " ".join(f"original_tag = {t}" for t in PARTS) + " }"
def OPK(v, key, r):
    m = f"{P}op_{'p' if v > 0 else 'm'}{abs(v)}"
    ttl(key, r)
    return f"custom_effect_tooltip = {key}\nhidden_effect = {{\n    every_country = {{\n        limit = {{ {KTAGS} }}\n        add_opinion_modifier = {{ target = {SOV} modifier = {m} }}\n        {SOV} = {{ add_opinion_modifier = {{ target = PREV modifier = {m} }} }}\n    }}\n}}\n"
ttl(P + "tt_int50", "Целостность Союза ниже §Y50§!")
INT50 = f"custom_trigger_tooltip = {{\n    tooltip = {P}tt_int50\n    check_variable = {{ var = {P}integrity value = 50 compare = less_than }}\n}}"
fc("eb0", "Экстренный съезд хозяйственников", "rescue", [], [], INT50, pp(40), ai=80)
fc("eb1", "Создать Экономический Блок", "rescue", [["eb0"]], [], None, flag(P + "econ_bloc") + spirit("econ_bloc", "Экономический блок", "Политика врозь, рубль и рельсы вместе. Республики подписали и теперь гадают, что именно.", {"industrial_capacity_factory": 0.05, "consumer_goods_factor": -0.03})
   + tip(P + "tt_bloc_members", "Все существующие республики получают дух «Союзная хозяйственная зона»") + f"hidden_effect = {{ every_country = {{ limit = {{ {KTAGS} }} add_ideas = ktits_sez_member }} }}\n", ai=80)
fc("eb2", "Единый расчётный рубль", "rescue", [["eb1"]], [], None, stab(3) + spirit("bloc_rouble", "Единый расчётный рубль", "Республики расплачиваются одним рублём и ворчат на одном языке.", {"consumer_goods_factor": -0.03}), ai=80)
fc("eb3", "Общие железнодорожные тарифы", "rescue", [["eb1"]], [], None, spirit("bloc_tariff", "Общие железнодорожные тарифы", "Тариф на перегон один, и никто не просит скидку за национальность.", {"production_speed_buildings_factor": 0.1}), ai=80)
fc("eb4", "Спасательный фонд", "rescue", [["eb2"]], [], None, pp(50) + civ(3), ai=80)
fc("eb5", "Выкуп долгов республик", "rescue", [["eb3"]], [], None, OPK(25, P + "tt_debts", "Отношения со всеми республиками: §G+25§!"), ai=80)
fc("eb6", "Хозяйственная дипломатия", "rescue", [["eb4"], ["eb5"]], [], None, OPK(40, P + "tt_econ_dip", "Отношения со всеми республиками: §G+40§!"), ai=80)
F = [f for f in F if f]
# author's rule 2026-11-20: the focus "Бессонные ночи" (p0) is the first and obligatory: every focus without prerequisites needs it
F = [f if f[0] == "p0" or f[3] else (f[0], f[1], f[2], [["p0"]], f[4], f[5], f[6], f[7], f[8], f[9]) for f in F]
# mutual exclusivity must be written on both focuses (the game logs an error otherwise)
_ex = {f[0]: set(f[4]) for f in F}
for _f in F:
    for _e in _f[4]: _ex[_e].add(_f[0])
F = [(f[0], f[1], f[2], f[3], sorted(_ex[f[0]]), f[5], f[6], f[7], f[8], f[9]) for f in F]
FIDS = {f[0] for f in F}
assert len(FIDS) == len(F)

# ---------------- layout ----------------
BASE = {"para": 0, "root": 40, "p_u1": 10, "church": 20, "p_r1": 30, "p_m1": 50, "p_t1": 60, "p_k1": 70, "p_f1": 80, "anti": 90,
        "ext": 100, "rescue": 152, "rub_a": 110, "rub_d": 115, "rub_c": 120, "rub_k": 126, "rub_y": 130, "rub_f": 160, "rub_g": 164, "rub_m": 168, "rub_h": 172, "rub_s": 176, "eco": 136, "army": 144}
byid = {f[0]: f for f in F}
depth = {}
def dep(i):
    if i in depth: return depth[i]
    ps = [p for g in byid[i][3] for p in g]
    depth[i] = 0 if not ps else 1 + max(dep(p) for p in ps)
    return depth[i]
for i in byid: dep(i)
cursor = {}
POS = {}
for f in F:   # F order is stable: siblings at one depth go left to right
    i, br = f[0], f[2]
    k = (br, depth[i]); n = cursor.get(k, 0); cursor[k] = n + 1
    POS[i] = (BASE[br] + n, depth[i])
# the root of the paths sits above the six path roots; the paths hang off one row (depth 1 = y 1)
ROOT_X = POS["cong"][0]

def fid(i): return P + i
out = (f"focus_tree = {{\n    id = {P}focus\n    country = {{\n        factor = 0\n        modifier = {{\n            add = 100\n            original_tag = {SOV}\n        }}\n    }}\n"
       f"    default = no\n    reset_on_civilwar = no\n    continuous_focus_position = {{ x = 40 y = 1250 }}\n    initial_show_position = {{\n        focus = {P}cong\n    }}\n\n")
AIPF = {"ps": ("DEFAULT", "HISTORICAL", "REFORMS"), "ph": ("HARD_COMM",), "pa": ("FASCISM",), "pz": ("UNTHINKABLE", "CASUAL")}   # the AI takes only the personality focus of its path
RULE = {"m1": "HISTORICAL", "r1": "REFORMS", "t1": "HARD_COMM", "u1": "UNTHINKABLE", "f1": "FASCISM", "k1": "CASUAL"}
for (i, key, br, pre, excl, avail, rew, flt, icon, aiw) in F:
    nm, (days, desc) = dd(key)
    s = f"    focus = {{\n        id = {fid(i)}\n        icon = {icon}\n"
    for grp in pre: s += "        prerequisite = { " + " ".join(f"focus = {fid(g)}" for g in grp) + " }\n"
    if excl: s += "        mutually_exclusive = { " + " ".join(f"focus = {fid(g)}" for g in excl) + " }\n"
    x, y = POS[i]
    s += f"        x = {x}\n        y = {y}\n        cost = {max(1, days // 7)}\n        search_filters = {{ {flt} }}\n"
    if avail: s += f"        available = {{\n            {avail}\n        }}\n"
    s += "        cancel_if_invalid = no\n        continue_if_invalid = yes\n"
    s += f"        ai_will_do = {{\n            factor = {aiw}\n"
    if i in AIPF:
        ok = " ".join(f"has_game_rule = {{ rule = ktits_mak_paths option = {o} }}" for o in AIPF[i])
        s += f"            modifier = {{\n                factor = 0\n                NOT = {{ OR = {{ {ok} }} }}\n            }}\n"
    if i in RULE:
        ok = " ".join(f"has_game_rule = {{ rule = ktits_mak_paths option = {o} }}" for o in ("DEFAULT", RULE[i]))
        s += f"            modifier = {{\n                factor = 0\n                NOT = {{ OR = {{ {ok} }} }}\n            }}\n"
    s += "        }\n"
    s += f"        completion_reward = {{\n            if = {{ limit = {{ has_global_flag = ktits_debug }} log = \"KTITS:FOC:[THIS.GetTag]:DONE {fid(i)} integrity=[?{P}integrity]\" }}\n"
    s += "".join("            " + l + "\n" for l in rew.rstrip("\n").split("\n") if l) + "        }\n    }\n\n"
    out += s
    add(fid(i), nm); add(fid(i) + "_desc", q(desc))
w("common/national_focus/ktits_soviet.txt", out + "}\n")

# ---------------- zone branch of the breakaway countries (docs section 14): a branch of the STANDARD focus tree (generic.txt), so the republics keep the standard focuses ----------------
ZONE_DESC = {"K01": "Старые города помнят, чей хлеб кормил Ваньград. Теперь спрашивают цену.",
             "K02": "У холодных долин Ладожь с видом на мёрзлую даль: сюда проще привезти шёлк из-за моря, чем масло из Ваньграда.",
             "K03": "Татары и сибиряки привыкли считать вместе: ярмарка в Радогощи не знает границ, пока не придёт таможня.",
             "K04": "Железо и лес идут на юг по Устою. Если закрыть реку, замёрзнут и те, и другие.",
             "K05": "Раздолье не любит печатей: что выращено, то и продаётся, куда повезут.",
             "K06": "Заводы здесь стоят на болоте и на привычке; без общих поставок они встанут первыми.",
             "K42": "Две реки сходятся в один торговый путь; чужим таможням на нём нечего делать."}
Z = {"stay": ("Остаться в зоне", "Рубль общий, рельсы общие, обиды тоже общие. Зато хлеб привозят вовремя."),
     "market": ("Общий рынок", "Купцы возят товар через границы без печатей. Печати отдыхают."),
     "rails": ("Единые рельсы", "Поезда идут из конца в конец, и никто не спрашивает, чей это перегон."),
     "exit": ("Выйти из зоны", "Страна решила жить на свои. Бывшие соседи обиделись, зато сами себе хозяева."),
     "rouble": ("Свой рубль", "Новая валюта пахнет типографской краской и надеждой. Курс определяют на глаз."),
     "wall": ("Таможенный барьер", "На границе встали будки с шлагбаумами. Будочники важнее генералов.")}
ttl("ktits_sez_need_stay", f"Страна — марионетка Союза или Союз завершил фокус «Создать Экономический Блок»")
STAY_OK = f"custom_trigger_tooltip = {{\n    tooltip = ktits_sez_need_stay\n    OR = {{\n        is_puppet_of = {SOV}\n        {SOV} = {{ has_country_flag = {P}econ_bloc }}\n    }}\n}}"
GBEGIN, GEND = "# KTITS_ZONE_BRANCH_BEGIN (tools/make_soviet.py, do not edit by hand)", "# KTITS_ZONE_BRANCH_END"
zt = GBEGIN + "\n"
nzone = 0
zf = [("0", 95, 0, [], [], None, pp(30)),
      ("stay", 93, 1, ["0"], ["exit"], STAY_OK, "add_ideas = ktits_sez_member\nremove_ideas = ktits_sez_exit\n" + OP(SOV, 25)),
      ("market", 93, 2, ["stay"], [], None, pp(40) + spirit("zone_market", "Общий рынок", "Торговля идёт без печатей, и купцы не успевают удивляться.", {"consumer_goods_factor": -0.05})),
      ("rails", 93, 3, ["market"], [], None, infra(1) + "add_ideas = ktits_sez_rails\n"),
      ("exit", 97, 1, ["0"], ["stay"], None, "remove_ideas = ktits_sez_member\nadd_ideas = ktits_sez_exit\n" + OP(SOV, -50) + flag("ktits_sez_free")),
      ("rouble", 97, 2, ["exit"], [], None, stab(5) + "add_ideas = ktits_sez_rouble\n"),
      ("wall", 97, 3, ["rouble"], [], None, "add_ideas = ktits_sez_wall\n")]
GATE = "        allow_branch = {\n            OR = {\n" + "".join(f"                original_tag = {t}\n" for t in PARTS) + "            }\n        }\n"
for k, x, y, pre, excl, avail, rew in zf:
    nzone += 1
    z = "ktits_zone_"
    zt += f"    focus = {{\n        id = {z}{k}\n        icon = GFX_goal_generic_positive_trade_relations\n"
    if pre: zt += "        prerequisite = { " + " ".join(f"focus = {z}{p}" for p in pre) + " }\n"
    if excl: zt += "        mutually_exclusive = { " + " ".join(f"focus = {z}{p}" for p in excl) + " }\n"
    if k == "0": zt += GATE
    zt += f"        x = {x}\n        y = {y}\n        cost = {5 if k == '0' else 10}\n        search_filters = {{ {POL} }}\n"
    if avail: zt += f"        available = {{\n            {avail}\n        }}\n"
    zt += "        cancel_if_invalid = no\n        continue_if_invalid = yes\n        ai_will_do = { factor = 20 }\n"
    zt += "        completion_reward = {\n" + "".join("            " + l + "\n" for l in rew.rstrip("\n").split("\n") if l) + "        }\n    }\n\n"
    if k == "0":
        add(z + k, "Судьба зоны"); add(z + k + "_desc", "Страна получила печать, а вместе с ней вопрос: торговать с бывшими своими или считать их соседями. [GetKtitsZoneDesc]")
    else:
        add(z + k, Z[k][0]); add(z + k + "_desc", q(Z[k][1]))
zt += GEND + "\n"
g = M / "common/national_focus/generic.txt"
txt = g.read_text(encoding="utf-8", newline=""); nl = "\r\n" if "\r\n" in txt else "\n"
txt = re.sub(r"\r?\n?" + re.escape(GBEGIN) + r".*?" + re.escape(GEND) + r"\r?\n?", "", txt, flags=re.S)
kk = txt.rindex("}")
txt = txt[:kk].rstrip() + nl + nl + T(zt).replace("\n", nl) + nl + txt[kk:]
g.write_text(txt, encoding="utf-8", newline="")
old = M / "common/national_focus/ktits_soviet_zone.txt"
if old.exists(): old.unlink()
sl = "# the lore text of the first zone focus depends on the country that looks at it\ndefined_text = {\n    name = GetKtitsZoneDesc\n"
for t_ in PARTS:
    sl += f"    text = {{\n        trigger = {{ original_tag = {t_} }}\n        localization_key = ktits_zone_desc_{t_}\n    }}\n"
    add(f"ktits_zone_desc_{t_}", ZONE_DESC[t_])
sl += f"    text = {{\n        localization_key = ktits_zone_desc_{PARTS[0]}\n    }}\n}}\n"
w("common/scripted_localisation/ktits_soviet_loc.txt", sl)
ZS = {"ktits_sez_member": ("Союзная хозяйственная зона", "Рубль общий, рельсы общие, обиды тоже общие. Зато хлеб привозят вовремя.", {"production_speed_buildings_factor": 0.1, "consumer_goods_factor": -0.05}),
      "ktits_sez_exit": ("Хозяйственный разрыв", "Страна вышла из зоны, и теперь каждый ящик гвоздей пересчитывают на границе. Гвозди недовольны.", {"industrial_capacity_factory": -0.1, "stability_factor": -0.05}),
      "ktits_sez_rails": ("Единые рельсы зоны", "Поезда идут из конца в конец, и никто не спрашивает, чей это перегон.", {"production_speed_buildings_factor": 0.1}),
      "ktits_sez_rouble": ("Свой рубль страны", "Новая валюта пахнет типографской краской и надеждой. Курс определяют на глаз.", {"consumer_goods_factor": 0.05}),
      "ktits_sez_wall": ("Таможенный барьер страны", "На границе встали будки с шлагбаумами. Будочники важнее генералов.", {"industrial_capacity_factory": 0.1})}

# ---------------- spirits ----------------
ideas = "ideas = {\n    country = {\n"
def idea_block(key, mods):
    pic = next((PIC[k] for k in mods if k in PIC), "generic_communism_drift_bonus")
    return (f"        {key} = {{\n            picture = {pic}\n            allowed = {{ always = no }}\n            allowed_civil_war = {{ always = yes }}\n            removal_cost = -1\n            modifier = {{\n"
            + "".join(f"                {k} = {v}\n" for k, v in mods.items()) + "            }\n        }\n")
for key, (r_, d_, mods) in SP.items():
    ideas += idea_block(key, mods); add(key, r_); add(key + "_desc", d_)
for key, (r_, d_, mods) in ZS.items():
    ideas += idea_block(key, mods); add(key, r_); add(key + "_desc", d_)
w("common/ideas/ktits_soviet_ideas.txt", ideas + "    }\n}\n")

# ---------------- opinion modifiers, triggers, start, on_actions ----------------
w("common/opinion_modifiers/ktits_soviet_opinion.txt", "opinion_modifiers = {\n" + "".join(f"    {P}op_{s_}{v} = {{ value = {'' if s_ == 'p' else '-'}{v} months = 36 }}\n" for v in OPS for s_ in "pm") + "}\n")
for v in OPS:
    add(f"{P}op_p{v}", "Дружеский жест Союза"); add(f"{P}op_m{v}", "Давление Союза")
w("common/scripted_triggers/ktits_soviet_triggers.txt", f"ktits_is_soviet = {{\n    original_tag = {SOV}\n}}\n")
w("common/scripted_effects/ktits_soviet_effects.txt",
  "# scope = Soviet Union at the start of the game: laws (partial mobilisation = partial_economic_mobilisation [INVENTED: the closest law], limited conscription), variables of the scales\n"
  f"ktits_sov_start = {{\n    add_ideas = partial_economic_mobilisation\n    add_ideas = limited_conscription\n"
  f"    set_variable = {{ var = {P}integrity value = 70 }}\n    set_variable = {{ var = {P}paranoia value = 20 }}\n    set_power_balance = {{ id = ktits_sov_power_balance left_side = ktits_sov_party_side right_side = ktits_sov_pimenov_side set_value = 0.2 }}\n"
  f"    set_variable = {{ var = {P}p_auto value = 20 }}\n    set_variable = {{ var = {P}p_soft value = 20 }}\n    set_variable = {{ var = {P}p_hard value = 20 }}\n    set_variable = {{ var = {P}p_schizo value = 20 }}\n"
  f"    set_variable = {{ var = {P}repent value = 0 }}\n}}\n")
w("common/on_actions/ktits_soviet_on_actions.txt",
  "on_actions = {\n    on_startup = {\n        effect = {\n            every_country = {\n                limit = { ktits_is_soviet = yes }\n                ktits_sov_start = yes\n                country_event = { id = ktits_soviet.1 }\n            }\n        }\n    }\n}\n")

# ---------------- events ----------------
ENV = {1: ("Десять лет после победы", "Гражданская война закончилась десять лет назад: царисты сдались не врагам, а усталости, и Ваньград давно перестал украшать площади флагами победы. Но Генсек Ваня Пименов так и не поверил в мир. Он до сих пор видит врагов и соперников в каждом коридоре, проверяет подписи под указами и не спит по ночам: за дверью шепчутся, а в протоколах всё сходится слишком гладко. Республики говорят на своих языках, Партия считает потери, а Казуалия на юге зевает так, что слышно на границе. Пока Генсек не успокоится, ни один курс выбрать невозможно.", "Созвать съезд"),
       10: ("Ультиматум из Ваньграда", "Атаману принесли бумагу из Ваньграда. Там вежливо сказано: либо Казачья Земля становится частью Союза, либо остаётся сама по себе, но уже без Союза рядом.", "Принять"),
       20: ("Договор с Ваньградом", "Ваньград предлагает обмен: технологии за сырьё и раздел общей границы. Рейх долго считает, кто выигрывает больше, и выходит, что оба.", "Подписать"),
       21: ("Временный союз", "Ваньград предлагает союз на два года. В рейхе говорят: два года — это немного. В Ваньграде кивают и пишут «до особого распоряжения».", "Согласиться")}
ACC = {1: "add_political_power = 20\n",
       10: f"{SOV} = {{ puppet = {{ target = ROOT end_wars = no }} }}\n",
       20: f"{SOV} = {{ add_political_power = 50 }}\nadd_opinion_modifier = {{ target = {SOV} modifier = {P}op_p25 }}\n",
       21: f"add_opinion_modifier = {{ target = {SOV} modifier = {P}op_p50 }}\ngive_guarantee = {SOV}\n{SOV} = {{ give_guarantee = ROOT }}\n"}
REJ = {10: f"{SOV} = {{ create_wargoal = {{ type = annex_everything target = ROOT }} }}\n", 20: "add_stability = 0.01\n", 21: "add_stability = 0.01\n"}
evt = ""
for eid, (t_, d_, a_) in ENV.items():
    add(f"ktits_soviet.{eid}.t", t_); add(f"ktits_soviet.{eid}.d", d_); add(f"ktits_soviet.{eid}.a", a_)
    evt += f"country_event = {{\n    id = ktits_soviet.{eid}\n    title = ktits_soviet.{eid}.t\n    desc = ktits_soviet.{eid}.d\n    picture = GFX_report_event_generic_factory\n    is_triggered_only = yes\n    fire_only_once = {'yes' if eid == 1 else 'no'}\n"
    evt += f"    option = {{\n        name = ktits_soviet.{eid}.a\n        ai_chance = {{ factor = {30 if eid == 10 else 50} }}\n" + "".join("        " + l + "\n" for l in ACC[eid].rstrip("\n").split("\n")) + "    }\n"
    if eid != 1:
        add(f"ktits_soviet.{eid}.b", "Отказаться")
        evt += f"    option = {{\n        name = ktits_soviet.{eid}.b\n        ai_chance = {{ factor = {70 if eid == 10 else 50} }}\n" + "".join("        " + l + "\n" for l in REJ[eid].rstrip("\n").split("\n")) + "    }\n"
    evt += "}\n\n"
w("events/ktits_soviet_events.txt", "add_namespace = ktits_soviet\n\n" + evt)

# ---------------- game rule ktits_mak_paths ----------------
OPTS = [("HISTORICAL", "Исторический путь", "Мягкий коммунизм."), ("REFORMS", "Политические реформы", "Путь мягких реформ."), ("HARD_COMM", "Тоталитарный коммунизм", "Путь жёсткого коммунизма."),
        ("UNTHINKABLE", "Немыслимый вариант", "Курс на смену идеологии: теология или гласность."), ("FASCISM", "Фашистский путь", "Империя Русов."), ("CASUAL", "Казуальный путь", "Союз идёт к Казуальности.")]
rule = 'ktits_mak_paths = {\n    name = "KTITS_RULE_MAK_PATHS"\n    group = "RULE_GROUP_AI_BEHAVIOR"\n    default = {\n        name = DEFAULT\n        text = "KTITS_RULE_OPT_MAK_PATHS_DEFAULT"\n        desc = "KTITS_RULE_OPT_MAK_PATHS_DEFAULT_DESC"\n    }\n'
for n_, r_, d_ in OPTS:
    rule += f'    option = {{\n        name = {n_}\n        text = "KTITS_RULE_OPT_MAK_PATHS_{n_}"\n        desc = "KTITS_RULE_OPT_MAK_PATHS_{n_}_DESC"\n        allow_achievements = no\n    }}\n'
    add(f"KTITS_RULE_OPT_MAK_PATHS_{n_}", r_); add(f"KTITS_RULE_OPT_MAK_PATHS_{n_}_DESC", d_)
w("common/game_rules/ktits_mak_paths_rules.txt", rule + "}\n")
add("KTITS_RULE_MAK_PATHS", "Путь Советского Союза"); add("KTITS_RULE_MAK_PATHS_DESC", "Какой путь выбирает Советский Союз под управлением ИИ.")
add("KTITS_RULE_OPT_MAK_PATHS_DEFAULT", "По весам ИИ"); add("KTITS_RULE_OPT_MAK_PATHS_DEFAULT_DESC", "ИИ выбирает путь по весам (чаще всего мягкий коммунизм).")
for k, (r_, e_) in TT.items(): add(k, r_, e_)
L.write_yml(str(M / "localisation/russian/ktits_soviet_l_russian.yml"), "russian", ru)
L.write_yml(str(M / "localisation/english/ktits_soviet_l_english.yml"), "english", en)
print(f"soviet: {len(F)} focuses + {nzone} zone focuses, {len(SP) + len(ZS)} spirits, {len(ENV)} events, rule ktits_mak_paths; x {min(p[0] for p in POS.values())}..{max(p[0] for p in POS.values())}, y max {max(p[1] for p in POS.values())}")

# the casuality ruler of the Union (author's decision 2026-11-20): "Болотный Иоанн"; recruited at the start so that the portrait and the name are used when the Union turns casual
_cf = M / "common/characters/MAK.txt"; _ct = _cf.read_text(encoding="utf-8")
_m = re.search(r'(\tMAK_casuality_leader\s*=\s*\{\s*name\s*=\s*)"[^"]*"', _ct)
if _m: _cf.write_text(_ct[:_m.start()] + _m.group(1) + '"Болотный Иоанн"' + _ct[_m.end():], encoding="utf-8", newline="")
_hf = next((M / "history/countries").glob("MAK - *.txt")); _ht = _hf.read_text(encoding="utf-8", errors="ignore")
if not re.search(r"^\s*recruit_character\s*=\s*MAK_casuality_leader\s*$", _ht, re.M):
    _ht = re.sub(r"^(recruit_character[^\n]*)$", lambda m_: m_.group(1) + "\nrecruit_character = MAK_casuality_leader", _ht, count=1, flags=re.M) if re.search(r"^recruit_character", _ht, re.M) else _ht.rstrip() + "\n\nrecruit_character = MAK_casuality_leader\n"
    _hf.write_text(_ht, encoding="utf-8", newline="")
