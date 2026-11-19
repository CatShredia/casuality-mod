"""Mechanics and focus tree of Kazualia (docs/mechanics/Kazualia.md, docs/focuses/Kazualia-Focus-Tree.md).

Everything here is generated from the data tables below (numbers, names and texts come from the two documents; items the documents do not fix are marked INVENTED).
Implemented (see docs/mechanics/Kazualia.md, section "Реализация"):
  * start event "Утро в Ставке" (only Kazualia), start values, division templates, cores of Kazualia on the swamp states of the Soviet Union (Наши Болота);
  * Internal Casuality: variable ktits_kaz_inner (start 50) -> dynamic modifier ktits_kaz_inner_dm (table of section 2), Reform path flag strengthens the debuffs;
    lateness (section 2.1) through hidden delayed events;
  * the national spirit "Дурманище" for countries with the casuality ideology (+ stages removed by focuses with swap_ideas);
  * Economic Casuality: "Казуальная Вера" and the decisions "Дары болот"; category with the numbers;
  * the focus tree ktits_kazualia_focus (all branches of the document) with national spirits;
  * Reforms (5.1): category and 4 decisions, events "Болотный мятеж" and "Индустриальное общество";
  * British influence (5.2): spirit with 3 levels + "Корона и болото", decision "Выгнать клерков";
  * decision "Принять в Ставку", spirit "Отрезвление" (defined, not wired: Casual rebellions are not implemented).
Casual rebellions, "Наши Болота" (K35), the civil war, the categories with scale bars: tools/make_kazualia_outer.py.
NOT implemented: terrain-specific bonuses (no country modifier for terrain in the game docs), state-scope bonuses (resistance, capital defence), civil war (6).
Writes: common/{national_focus,ideas,dynamic_modifiers,scripted_effects,scripted_triggers,scripted_localisation,decisions,decisions/categories,on_actions,opinion_modifiers}/ktits_kazualia*.txt,
events/ktits_kazualia_events.txt, localisation ru/en ktits_kazualia_l_*.yml. Run after set_terrain.py (the swamp states are read from map/definition.csv).
Usage: python tools/make_kazualia.py [--mod PATH]
"""
import argparse, re
from pathlib import Path
import lore_data as L
import invented_lore as INV

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
a = ap.parse_args()
M = Path(a.mod)
info = L.load_mod(M)
lore2tag = {lt: t for t, lt in info["tag2lore"].items()}
KAZ, SOV, BRT = lore2tag["CSL"], lore2tag["SVS"], lore2tag["BRT"]
PIC = "GFX_report_event_ktits_casuality"
IDEA_PIC = "ktits_casuality"

def T(s):   # 4 spaces -> tab (house style)
    return re.sub(r"(?m)^( {4})+", lambda m: "\t" * (len(m.group()) // 4), s)

def w(rel, text):
    p = M / rel; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(T(text), encoding="utf-8", newline="\n")

ru, en = [], []
def add(k, r, e=None):
    ru.append((k, r)); en.append((k, e or L.translit(r)))

# ---------------- map data: swamp states of Наши Болота, swamp states of Kazualia, capital province ----------------
cent, idxmap = L.province_centroids(M)
terr = {}
for l in open(M / "map/definition.csv", encoding="latin1"):
    p = l.strip().split(";")
    if len(p) > 6 and p[0].isdigit():
        terr[int(p[0])] = p[6]
nb = INV.NASHI_BOLOTA
swamp_sov = {}
kaz_state_terr = {}
for sid, s in info["states"].items():
    lt = info["tag2lore"].get(s["owner"])
    if lt == nb["country"]:
        n = [p for p in s["provs"] if nb["x"][0] <= cent[p][0] <= nb["x"][1] and nb["y"][0] <= cent[p][1] <= nb["y"][1] and terr.get(p) == "marsh"]
        if n:
            swamp_sov[sid] = len(n)
    if lt == "CSL":
        ms = sum(1 for p in s["provs"] if terr.get(p) == "marsh")
        kaz_state_terr[sid] = (ms, len(s["provs"]))
swamp_ids = sorted(swamp_sov)
kaz_swamp = sorted(sid for sid, (m_, n_) in kaz_state_terr.items() if m_ * 2 > n_) or sorted(kaz_state_terr)
KAZ_CAP_STATE = info["capital_state"].get("CSL") or info["capital_state"].get(KAZ)
if not KAZ_CAP_STATE:   # not in the lore table: the capital written in history/countries
    _hc = next((M / "history/countries").glob(f"{KAZ} - *.txt"))
    KAZ_CAP_STATE = int(re.search(r"capital\s*=\s*(\d+)", _hc.read_text(encoding="utf-8", errors="ignore")).group(1))
# capital province = the province with the most victory points in the capital state (the old pixel lookup gave a province of another country: create_unit -- invalid scope state)
_vp = re.findall(r"victory_points\s*=\s*\{\s*(\d+)\s+(\d+)", (M / "history/states" / f"{KAZ_CAP_STATE}.txt").read_text(encoding="utf-8", errors="ignore"))
CAP_PROV = int(max(_vp, key=lambda v: int(v[1]))[0]) if _vp else info["states"][KAZ_CAP_STATE]["provs"][0]
print(f"kazualia: swamp states of Наши Болота = {swamp_ids}; swamp states of Kazualia = {kaz_swamp}; capital province {CAP_PROV}, capital state {KAZ_CAP_STATE}")

# ---------------- no railways in Kazualia (author): cut out of map/railways.txt, supply nodes removed from map/supply_nodes.txt ----------------
# The files are written by the RandomParadox export. Row: "level count province..." (railways), "level province" (supply nodes). A copy of the export is kept in
# no_commit/temp/backup_railways/; if the mod file still has Kazualia rails (fresh export) the copy is refreshed, otherwise the step starts from the copy (idempotent).
KAZ_PROVS = {p_ for sid in kaz_state_terr for p_ in info["states"][sid]["provs"]}
RWBK = L.REPO / "no_commit/temp/backup_railways"; RWBK.mkdir(parents=True, exist_ok=True)
def _rw_has_kaz(txt):
    return any(set(map(int, l.split()[2:])) & KAZ_PROVS for l in txt.splitlines() if len(l.split()) > 2)
def _sn_has_kaz(txt):
    return any(len(l.split()) == 2 and int(l.split()[1]) in KAZ_PROVS and int(l.split()[1]) != CAP_PROV for l in txt.splitlines())
_rwp, _snp = M / "map/railways.txt", M / "map/supply_nodes.txt"
for _p in (_rwp, _snp):
    _b = RWBK / _p.name; _cur = _p.read_text(encoding="utf-8")
    if not _b.exists() or (_rw_has_kaz(_cur) if _p is _rwp else _sn_has_kaz(_cur)):
        _b.write_text(_cur, encoding="utf-8", newline="")
_rw_src = (RWBK / "railways.txt").read_text(encoding="utf-8")
_out, RW_DROP, RW_CUT, RW_KEEP = [], 0, 0, 0
for _l in _rw_src.splitlines():
    _t = _l.split()
    if len(_t) < 3 or not (set(map(int, _t[2:])) & KAZ_PROVS):
        _out.append(_l); RW_KEEP += 1; continue
    _runs, _run = [], []
    for _pv in _t[2:]:
        if int(_pv) in KAZ_PROVS:
            if _run: _runs.append(_run)
            _run = []
        else:
            _run.append(_pv)
    if _run: _runs.append(_run)
    _runs = [r_ for r_ in _runs if len(r_) >= 2]
    for r_ in _runs:
        _out.append(f"{_t[0]} {len(r_)} " + " ".join(r_) + " ")
    if _runs: RW_CUT += 1
    else: RW_DROP += 1
_rwp.write_text("\n".join(_out) + "\n", encoding="utf-8", newline="")
_sn_out, SN_DROP, SN_CAP = [], 0, False
for _l in (RWBK / "supply_nodes.txt").read_text(encoding="utf-8").splitlines():
    _t = _l.split()
    if len(_t) == 2 and int(_t[1]) in KAZ_PROVS and int(_t[1]) != CAP_PROV:
        SN_DROP += 1; continue
    if len(_t) == 2 and int(_t[1]) == CAP_PROV: SN_CAP = True
    _sn_out.append(_l)
_snp.write_text("\n".join(_sn_out) + "\n", encoding="utf-8", newline="")
print(f"kazualia: railways: rows kept {RW_KEEP}, cut (outer parts kept) {RW_CUT}, dropped entirely {RW_DROP}; supply nodes removed {SN_DROP}, capital node kept: {SN_CAP}")

# ---------------- rail targets for the Reform focuses: nearest land provinces outside Kazualia, by different owners ----------------
_land = set()
for _l in open(M / "map/definition.csv", encoding="latin1"):
    _q = _l.strip().split(";")
    if len(_q) > 6 and _q[0].isdigit() and _q[4] == "land": _land.add(int(_q[0]))
_prov_owner = {p_: s_["owner"] for s_ in info["states"].values() for p_ in s_["provs"]}
def _d(p_):
    return (cent[p_][0] - cent[CAP_PROV][0]) ** 2 + (cent[p_][1] - cent[CAP_PROV][1]) ** 2
RAIL_T = []
for p_ in sorted((x_ for x_ in _land if x_ in _prov_owner and x_ not in KAZ_PROVS and x_ in cent), key=_d):
    if _prov_owner[p_] not in {o_ for _, o_ in RAIL_T}:
        RAIL_T.append((p_, _prov_owner[p_]))
    if len(RAIL_T) == 2: break
print(f"kazualia: rail targets (province, owner) {RAIL_T}")

# ---------------- constants (documents) ----------------
DURM_CORE_ATK = 0.40                      # docs/mechanics/Kazualia.md section 1 (the author corrected it to +0.40)
DURM = [("ktits_durmanische", -0.20, -0.10), ("ktits_durmanische_1", -0.13, -0.07), ("ktits_durmanische_2", -0.06, -0.04), ("ktits_durmanische_3", 0.0, 0.0)]
# supply buffs of the Durmanische (INVENTED numbers, docs/lore/Invented-Lore.md): compensation for the absence of railways in Kazualia
DURM_SUP = {"supply_consumption_factor": -0.15, "attrition": -0.10}   # keys: modifiers_documentation.md (army / country)
DURM_TXT = ("Над болотами стоит сладкий туман. Солдаты, вошедшие в него, сначала замедляют шаг, потом садятся «на минутку», а потом забывают, зачем пришли. "
            "Офицеры кричат, но и их голоса вязнут в тумане. Казуалам он не мешает: для них это просто воздух родины.")

# Gifts of the swamp (section 4): key, name, lore text, effect text, faith price, cooldown days
GIFTS = [
    ("militia", "Болотное ополчение", "Из тумана выходят люди с вилами и сетями: никто их не звал, они пришли сами.", "2 дивизии ополчения в столице", 150, 90),
    ("guard", "Казуальная гвардия", "Лучшие из ленивых: те, кто ленится даже отступать.", "1 пехотная дивизия (шаблон «Казуальная гвардия»)", 250, 120),
    ("guns", "Ружья из тины", "Склады наполняются оружием, которого никто не заказывал.", "+2000 пехотного снаряжения", 100, 60),
    ("cannons", "Пушки сами приплыли", "По реке Казуахии приплыла баржа с артиллерией. Хозяина не нашли.", "+200 артиллерии", 150, 90),
    ("vision", "Откровение Архо-Казуала", "Правитель засыпает и во сне видит чертёж. Утром чертёж лежит на столе.", "скидка 100 % на одну исследуемую технологию", 300, 180),
    ("built", "Само построилось", "Утром на пустыре стоит завод. Строителей никто не видел.", "+1 гражданская фабрика в случайном штате", 200, 120),
    ("grace", "Благодать Ставки", "Священный-Архо-Казуал благословляет народ, и всем становится хорошо.", "+100 ПВ, стабильность +5 % на 180 дней", 120, 90),
    ("trucks", "Грузовики из топи", "Из трясины с чавканьем выезжают грузовики. Они стоят в колонне и ждут, когда кто-нибудь догадается сесть за руль.", "+300 грузовиков (motorized_equipment_1)", 120, 75),
    ("support", "Походные кухни и палатки", "Над болотом поднимается дымок: кто-то уже варит кашу. Походные кухни пришли раньше, чем армия проголодалась.", "+300 вспомогательной техники (support_equipment_1)", 100, 60),
    ("atpvo", "Трофейные стволы", "В камышах находят орудия, которые никто не заказывал и никто не терял. Для верности к ним прилагаются и зенитки: небо тоже иногда нужно проспать спокойно.", "+150 ПТ-орудий и +150 ПВО (anti_tank_equipment_1, anti_air_equipment_1)", 150, 90),
    ("peat", "Болотный газ и руда", "Торф горит, болотный газ шипит, а в тине находят ржавые жилы. Откуда они — спрашивать некогда: пока тепло.", "+15 000 топлива; +10 стали в случайном штате на 365 дней", 130, 120),
    ("mission", "Миссионеры лени", "Проповедники Казуальности уходят в соседние страны.", "шкала Казуальности в выбранной соседней стране +10", 100, 60),
]
# decision groups (colour = icon + colour code of the name): group -> (colour code, ru, en, decision icon)
GRP = {"army": ("§R", "Армия", "Army", "generic_military"), "equip": ("§Y", "Снаряжение", "Equipment", "generic_army_support"),
       "econ": ("§G", "Экономика", "Economy", "generic_construction"), "sci": ("§B", "Наука", "Science", "generic_research"),
       "pol": ("§O", "Политика", "Politics", "generic_political_address")}   # §O (orange) exists in vanilla loc; §P and §M do not
GIFT_GRP = {"militia": "army", "guard": "army", "guns": "equip", "cannons": "equip", "trucks": "equip", "support": "equip", "atpvo": "equip",
            "vision": "sci", "built": "econ", "peat": "econ", "grace": "pol", "mission": "pol"}
GIFT_ICON = {"trucks": "generic_trucks"}
GIFT_DISC = {"guns": 0.25, "cannons": 0.25}   # focus "Болотные склады" (-25 %)

# Reforms (section 5.1): key, name, lore text, progress, inner, PP (INVENTED inside the range 50-75), stability(-5 % for "work day")
REFORMS = [
    ("drain", "Осушение болот", "Землемеры с лопатами идут в трясину. Многие возвращаются, некоторые — даже с картой.", 15, -5, 50, "прогресс +15, Внутр. Казуальность −5 %, +1 слот строительства в 2 болотных штатах"),
    ("workday", "Рабочий день", "Указ: работать с утра до вечера. Половина страны впервые узнала, что такое утро.", 20, -10, 75, "прогресс +20, Внутр. Казуальность −10 %, стабильность −5 % на 90 дней"),
    ("schools", "Школы вместо Ставок", "Священные палаты отдают под классы. Учитель приходит раньше учеников — это уже прогресс.", 15, -5, 60, "прогресс +15, специалисты +5 тыс."),
    ("horn", "Фабричный гудок", "Над болотом впервые гудит завод. Казуалы приходят посмотреть и почему-то остаются.", 20, -5, 75, "прогресс +20, +1 гражданская фабрика"),
]

# ---------------- effect helpers (strings of script, indent with 4 spaces) ----------------
TT = {}   # tooltip loc: key -> (ru, en)
def ttl(key, r, e=None):
    TT[key] = (r, e or L.translit(r))
def sgn(v):
    return ("+%g" % v) if v > 0 else ("%g" % v)
def inner(d):
    k = "ktits_kaz_tt_in_" + ("p%g" % d if d > 0 else "m%g" % -d)
    ttl(k, f"Внутренняя Казуальность: §{'G' if d < 0 else 'Y'}{sgn(d)} %§!", f"Internal Casuality: §{'G' if d < 0 else 'Y'}{sgn(d)}%§!")
    return f"custom_effect_tooltip = {k}\nadd_to_variable = {{ var = ktits_kaz_inner value = {d} }}\nhidden_effect = {{ ktits_kaz_inner_update = yes }}\n"
def reform(d):
    k = "ktits_kaz_tt_rf_p%g" % d
    ttl(k, f"Прогресс реформ: §G+{d}§!", f"Reform progress: §G+{d}§!")
    return (f"custom_effect_tooltip = {k}\nadd_to_variable = {{ var = ktits_kaz_reform value = {d} }}\n"
            "clamp_variable = { var = ktits_kaz_reform min = 0 max = 100 }\n")
def faith(d):
    k = "ktits_kaz_tt_fa_p%g" % d
    ttl(k, f"Казуальная Вера: §G+{d}§!", f"Casual Faith: §G+{d}§!")
    return f"custom_effect_tooltip = {k}\nadd_to_variable = {{ var = ktits_kaz_faith value = {d} }}\n"
def hid(tip, body):
    return f"custom_effect_tooltip = {tip}\nhidden_effect = {{\n" + "".join(f"    {l}\n" for l in body) + "}\n"
def pp(v): return f"add_political_power = {v}\n"
def stab(v): return f"add_stability = {v}\n"
def pop(ideo, v): return f"add_popularity = {{ ideology = {ideo} popularity = {v} }}\n"
def flag(f_, tip=None, tip_ru=None):
    s = f"set_country_flag = {f_}\n"
    if tip:
        ttl(tip, tip_ru)
        s += f"custom_effect_tooltip = {tip}\n"
    return s
def civ(n):
    ttl(f"ktits_kaz_tt_civ{n}", f"Гражданских фабрик: §G+{n}§! (в случайном штате)", f"Civilian factories: §G+{n}§! (in a random state)")
    return hid(f"ktits_kaz_tt_civ{n}", [f"random_owned_controlled_state = {{ limit = {{ impassable = no }} add_extra_state_shared_building_slots = {n} add_building_construction = {{ type = industrial_complex level = {n} instant_build = yes }} }}"])
def mil(n):
    ttl(f"ktits_kaz_tt_mil{n}", f"Военных фабрик: §G+{n}§! (в случайном штате)", f"Military factories: §G+{n}§! (in a random state)")
    return hid(f"ktits_kaz_tt_mil{n}", [f"random_owned_controlled_state = {{ limit = {{ impassable = no }} add_extra_state_shared_building_slots = {n} add_building_construction = {{ type = arms_factory level = {n} instant_build = yes }} }}"])
def swamp_slots(n, st):
    ttl(f"ktits_kaz_tt_sw{n}_{st}", f"Слотов строительства: §G+{n}§! в каждом из {st} болотных штатов", f"Building slots: §G+{n}§! in each of {st} swamp states")
    lim = " ".join(f"state = {s}" for s in kaz_swamp)
    return hid(f"ktits_kaz_tt_sw{n}_{st}", [f"random_owned_state = {{ limit = {{ OR = {{ {lim} }} }} add_extra_state_shared_building_slots = {n} }}"] * st)
def divs(template, n):
    ttl(f"ktits_kaz_tt_div_{template}{n}", f"Дивизий ({'ополчения' if template == 'militia' else 'гвардии'}): §G+{n}§! в столице", f"Divisions: §G+{n}§! in the capital")
    one = (f'create_unit = {{ division = "name = \\"Казуальная дивизия\\" division_template = \\"{"Болотное ополчение" if template == "militia" else "Казуальная гвардия"}\\" start_experience_factor = 0.1 start_equipment_factor = 0.7" '
           f"owner = ROOT prioritize_location = {CAP_PROV} }}")
    return hid(f"ktits_kaz_tt_div_{template}{n}", [one] * n)
def scale_nb(d):
    ttl(f"ktits_kaz_tt_nb{d}", f"Шкала Казуальности всех соседей: §Y+{d}§!", f"Casuality scale of all neighbours: §Y+{d}§!")
    return hid(f"ktits_kaz_tt_nb{d}", [f"every_neighbor_country = {{ limit = {{ NOT = {{ has_country_flag = ktits_casuality_fallen }} NOT = {{ ktits_is_kazualia = yes }} }} add_to_variable = {{ var = ktits_casuality value = {d} }} clamp_variable = {{ var = ktits_casuality min = 0 max = 100 }} ktits_casuality_update = yes }}"])
def src_tt(key, r):
    ttl(key, r); return f"custom_effect_tooltip = {key}\n"

def wargoals_tt():
    ttl("ktits_kaz_tt_wargoal", "Цели войны (аннексия) против слабых соседей (слабее Казуалии по армии) со шкалой Казуальности ≥ 50", "War goals (annexation) against weaker neighbours with the Casuality scale of 50 or more")
    return ("custom_effect_tooltip = ktits_kaz_tt_wargoal\nhidden_effect = {\n    every_neighbor_country = {\n        limit = { NOT = { ktits_is_kazualia = yes } is_subject = no check_variable = { var = ktits_casuality value = 50 compare = greater_than_or_equals } strength_ratio = { tag = ROOT ratio < 1 } }\n"
            "        ROOT = { create_wargoal = { type = annex_everything target = PREV } }\n    }\n}\n")

# ================= focus tree =================
# (id, ru name, days, desc, x, y, prerequisites (list of OR-groups), mutually exclusive, available, reward, delay?, icon)
POL, IND, RES, ARM = "FOCUS_FILTER_POLITICAL", "FOCUS_FILTER_INDUSTRY", "FOCUS_FILTER_RESEARCH", "FOCUS_FILTER_ARMY_XP"
I_POL, I_CIV, I_MIL, I_INF = "GFX_goal_generic_political_pressure", "GFX_goal_generic_construct_civ_factory", "GFX_goal_generic_construct_mil_factory", "GFX_goal_generic_construct_infrastructure"
I_ARM, I_ALL, I_IMP, I_DEAL, I_SCI, I_FORT, I_PROD, I_TRADE = ("GFX_goal_generic_army_tanks", "GFX_goal_generic_alliance", "GFX_goal_generic_improve_relations", "GFX_goal_generic_dangerous_deal",
                                                         "GFX_goal_generic_scientific_exchange", "GFX_goal_generic_fortify_city", "GFX_goal_generic_production2", "GFX_goal_generic_positive_trade_relations")
NOREFORM = "NOT = { has_country_flag = ktits_kaz_industrial }"
F = []
def fc(i, name, days, desc, x, y, pre, excl, avail, rew, late=True, icon=I_POL, flt=POL):
    F.append((i, name, days, desc, x, y, pre, excl, avail, rew, late, icon, flt))
P = "ktits_kaz_"
# --- Пути развития
fc("wake", "Пробуждение Ставки", 35, "Священный-Архо-Казуал открыл один глаз. Придворные в панике: такого не было сто лет. Придётся что-то решать.", 30, 0, [], [], None, pp(50) + "custom_effect_tooltip = ktits_kaz_tt_choose\n", False)
fc("sleep", "Вечный сон", 70, "Ставка постановила: просыпаться было ошибкой. Казуалия остаётся собой и несёт покой всему материку.", 12, 1, [["wake"]], ["hum", "red"], None,
   inner(10) + "set_country_flag = ktits_kaz_casual\n" + src_tt("ktits_kaz_tt_great", "Открывает Казуальный путь: после «Власти Священной Ставки» выбор между Нейтралитетом и Великой Казуалией"), False)
fc("hum", "Заводской гудок", 70, "Молодые казуалы увидели за горами заводской дым и захотели такого же.", 30, 1, [["wake"]], ["sleep", "red"], None,
   "set_politics = { ruling_party = democratic elections_allowed = yes }\nadd_ideas = civilian_economy\nadd_ideas = volunteer_only\nset_country_flag = ktits_kaz_reformist\nhidden_effect = { ktits_kaz_inner_update = yes }\n" + src_tt("ktits_kaz_tt_reformist", "Правительство — демократия; открывает Реформистский путь и Реформы; дебаффы Внутренней Казуальности усиливаются и задевают армию"), False)
fc("red", "Красное болото", 70, "Агитаторы объяснили казуалам, что лень — пережиток эксплуатации. Казуалы задумались. Надолго.", 48, 1, [["wake"]], ["sleep", "hum"], None,
   "set_politics = { ruling_party = communism elections_allowed = yes }\nadd_ideas = civilian_economy\nadd_ideas = volunteer_only\nset_country_flag = ktits_kaz_comm\n" + src_tt("ktits_kaz_tt_comm", "Правительство — коммунизм; открывает Коммунистический путь"), False)
# --- Велико-Казуальный
G = lambda s: [[P + s]]
fc("g_power", "Власть Священной Ставки", 70, "Все решения теперь принимаются во сне правителя. Сны толкуют жрецы, жрецов назначает Ставка.", 12, 2, [["sleep"]], [], None, stab(0.10) + inner(5))
fc("g_preach", "Проповедь лени", 70, "Казуальные проповедники уходят за границу с котомками и хорошим настроением.", 8, 3, [["g_power"]], [], None,
   "set_variable = { var = ktits_kaz_c_mission value = 50 }\n" + src_tt("ktits_kaz_tt_preach", "Решение «Миссионеры лени» дешевле на 50 % Веры"))
fc("g_border", "Болото не знает границ", 70, "Туман ползёт через границу, и пограничники засыпают на постах.", 16, 3, [["g_power"]], [], None,
   inner(5) + faith(150) + "add_ideas = ktits_kaz_sp_fog\n" + "set_country_flag = ktits_kaz_f_outer\n" + src_tt("ktits_kaz_tt_outer", "Открывает категорию «Внешняя Казуальность»: Казуальное восстание, «Ничего не делать и ждать», снабжение повстанцев"))
fc("g_mission", "Миссии в каждый город", 105, "В каждом городе материка есть хотя бы один казуал, который никуда не спешит.", 8, 4, [["g_preach"]], [], None, scale_nb(10))
fc("g_fog", "Зов из тумана", 105, "Восстание — это просто очень много людей, которые разом перестали работать.", 16, 4, [["g_border"]], [], None,
   faith(100) + "set_country_flag = ktits_kaz_f_rebel_plus\n" + src_tt("ktits_kaz_tt_fog", "Казуальные восстания на 1 дивизию сильнее"))
fc("g_all", "Казуальность на весь материк", 140, "Ставка объявляет цель: весь материк должен отдохнуть. Это не война — это забота.", 12, 5, [["g_mission"], ["g_fog"]], [], None,
   "set_country_flag = ktits_kaz_f_wargoal\nadd_ideas = ktits_kaz_sp_march\n" + wargoals_tt())
fc("g_accept", "Принять всех в Ставку", 70, "Новые болота — новые лентяи. Места в тумане хватит всем.", 12, 6, [["g_all"]], [], None,
   pp(50) + "set_country_flag = ktits_kaz_f_accept_cheap\n" + src_tt("ktits_kaz_tt_accept", "Решение «Принять в Ставку» без перезарядки и дешевле на 50 ПВ"))
fc("g_quiet", "Тихая власть", 70, "Приказы больше не пишут: их шепчут в тумане, и они почему-то исполняются. Канцелярия отдыхает, а власть работает.", 13, 7, [["g_border"]], [], None,
   inner(5) + "add_ideas = ktits_kaz_sp_pp1\n" +src_tt("ktits_kaz_tt_pp1", "Прирост политической власти +20 %"))
fc("g_echo", "Эхо в камышах", 70, "Шёпот из тумана доходит до самой дальней деревни. Деревня зевает и соглашается.", 13, 8, [["g_quiet"]], [], None,
   "add_ideas = ktits_kaz_sp_pp2\n" +src_tt("ktits_kaz_tt_pp2", "Прирост политической власти ещё +30 %"))
# --- Нейтралитет / Великая Казуалия: после «Власти Священной Ставки» ровно одна из двух веток (взаимоисключающие)
fc("g_root", "Курс на материк", 70, "Ставка решила: болото слишком хорошо, чтобы держать его при себе. Пусть весь материк узнает, как это — ничего не делать.", 14, 3, [["g_power"]], ["n_root"], None,
   pp(50) + "set_country_flag = ktits_kaz_great\n" + src_tt("ktits_kaz_tt_great2", "Великая Казуалия: ветка экспансии (Внешняя Казуальность, восстания, цели войны, присоединение); закрывает «Нейтралитет»"))
fc("n_root", "Курс на покой", 70, "Ставка решила: болото — для казуалов. Соседи пусть живут как хотят, лишь бы не будили.", 2, 3, [["g_power"]], ["g_root"], None,
   inner(10) + stab(0.05) + "add_ideas = ktits_eternal_neutrality\n" + "set_country_flag = ktits_kaz_neutral\n" + src_tt("ktits_kaz_tt_neutral", "Нейтралитет: ветка внутреннего развития (Внутренняя Казуальность, Вера, оборона, стабильность); закрывает «Великую Казуалию»; дух «Вечный нейтралитет»: нельзя основать альянс и вступить в альянс"))
fc("n_siesta", "Священная сиеста", 70, "Сиеста объявлена государственным делом. Опоздавшим на сон выдают справку, что они не опоздали.", 0, 4, [["n_root"]], [], None,
   inner(10) + "add_ideas = ktits_kaz_sp_siesta\n")
fc("n_temple", "Храм безделья", 70, "Построили храм, куда никто не заходит. Паломники лежат у входа и считают это службой.", 4, 4, [["n_root"]], [], None,
   faith(300) + "add_to_variable = { var = ktits_kaz_faith_mult value = 0.10 }\n" + src_tt("ktits_kaz_tt_mult3", "Прирост Веры +10 %"), icon=I_TRADE, flt=IND)
fc("n_watch", "Сторожа сна", 70, "Вдоль границы выставлены посты. Их задача простая: стоять и никого не пускать будить.", 0, 5, [["n_siesta"]], [], None,
   divs("militia", 2) + "add_ideas = ktits_kaz_sp_watch\n", icon=I_ARM, flt=ARM)
fc("n_calm", "Тихие границы", 70, "На границе тишина. Контрабандисты тоже спят, а пограничники делают вид, что это порядок.", 4, 5, [["n_temple"]], [], None,
   "add_ideas = ktits_kaz_sp_calm\n")
fc("n_peace", "Мир на болотах", 105, "Все соседи заключили с Казуалией пакт о ненападении. Казуалия его не читала, но подписала.", 2, 6, [["n_watch"], ["n_calm"]], [], None,
   pp(100) + inner(10))
fc("n_golden", "Золотая лень", 140, "Казуалия достигла того, к чему стремилась веками: ничего не происходит, и это прекрасно.", 2, 7, [["n_peace"]], [], None,
   inner(15) + stab(0.10) + faith(200))
fc("g_end", "Единое болото", 105, "Над материком стелется туман. Границы остались на картах, но никто не помнит, зачем они нужны.", 10, 8, [["g_accept"]], [], None,
   pp(100) + inner(10) + faith(200))
# --- Дурманище
fc("d_swamp", "Болото с собой", 70, "Солдаты набирают во фляги болотную воду. На чужой земле глоток — и снова как дома.", 2, 2, [["sleep"]], [], None,
   "swap_ideas = { remove_idea = ktits_durmanische add_idea = ktits_durmanische_1 }\n" + src_tt("ktits_kaz_tt_d1", "Штраф Дурманища на чужой земле ослаблен на треть"), False)
fc("d_fog", "Туман над чужбиной", 70, "Туман идёт впереди армии. Чужие поля становятся вязкими, а казуалы — спокойными.", 2, 3, [["d_swamp"]], [], None,
   "swap_ideas = { remove_idea = ktits_durmanische_1 add_idea = ktits_durmanische_2 }\n" + src_tt("ktits_kaz_tt_d2", "Штраф Дурманища на чужой земле ослаблен ещё на треть"), False)
fc("d_home", "Везде как дома", 105, "Казуал засыпает на чужой земле так же крепко, как в своих камышах. Значит, это уже его земля.", 2, 4, [["d_fog"]], [], None,
   "swap_ideas = { remove_idea = ktits_durmanische_2 add_idea = ktits_durmanische_3 }\n" + src_tt("ktits_kaz_tt_d3", "Штраф Дурманища на чужой земле снят"), False)
# --- Реформистский
fc("r_council", "Совет общин", 70, "Впервые в истории казуалы выбирают власть сами. Явка — 12 %: остальные проспали.", 30, 2, [["hum"]], [], None, pop("democratic", 0.15) + reform(5))
fc("r_decree", "Указ о рабочем дне", 70, "Работать с утра до вечера. Половина страны впервые узнала, что такое утро.", 26, 3, [["r_council"]], [], None, reform(10) + inner(-10) + stab(-0.05))
fc("r_drain", "Осушение болот", 105, "Землемеры с лопатами уходят в трясину. Многие возвращаются, некоторые — даже с картой.", 34, 3, [["r_council"]], [], None, reform(10) + swamp_slots(1, 3), icon=I_INF, flt=IND)
fc("r_crush", "Подавить болотных реакционеров", 70, "Старые казуалы ушли в камыши с плакатами «Верните покой!». Их надо вернуть — или победить.", 26, 4, [["r_decree"]], [], None,
   "set_country_flag = ktits_kaz_f_riot_half\n" + src_tt("ktits_kaz_tt_riot_half", "Риск «Болотного мятежа» −50 %") + divs("militia", 2), icon=I_ARM, flt=ARM)
fc("r_plants", "Первые заводы", 105, "Над болотом впервые гудит завод. Казуалы приходят посмотреть и почему-то остаются.", 34, 4, [["r_drain"]], [], None, civ(2) + reform(10), icon=I_CIV, flt=IND)
def rail(level, targets):
    ttl(f"ktits_kaz_tt_rail{level}_{len(targets)}", f"Железная дорога уровня {level} от столицы к границе: §G{len(targets)}§! ветк.", f"Railway of level {level} from the capital to the border: §G{len(targets)}§! line(s)")
    return hid(f"ktits_kaz_tt_rail{level}_{len(targets)}", [f"build_railway = {{ level = {level} start_province = {CAP_PROV} target_province = {t_} }}" for t_ in targets])
_RT = [t_ for t_, _o in RAIL_T]
assert len(_RT) == 2, RAIL_T
fc("r_rail1", "Первая узкоколейка", 70, "Землемеры нашли, где у страны выход: рельсы протянули до ближайшей границы. Поезд ходит раз в неделю, но уже ходит — и не опаздывает, потому что расписания нет.", 18, 3, [["r_council"]], [], None,
   rail(1, _RT[:1]), icon=I_INF, flt=IND)
fc("r_rail2", "Рельсы к соседям", 70, "Вторая ветка ушла к другому соседу. Казуалы смотрели, как её кладут, и предложили класть лёжа — получилось медленнее, зато основательно.", 18, 4, [["r_rail1"]], [], None,
   rail(1, _RT[1:]), icon=I_INF, flt=IND)
fc("r_rail3", "Железная дорога в тумане", 105, "Узкоколейку расширили до настоящей дороги. Туман по-прежнему стелется над шпалами, но составы научились ходить и в нём.", 18, 5, [["r_rail2"]], [], None,
   rail(2, _RT), icon=I_INF, flt=IND)
fc("r_comm", "Демократическая община", 70, "Казуалия больше не Ставка, а община свободных граждан. Священный-Архо-Казуал ушёл на покой — ему не привыкать.", 30, 5, [["r_crush"], ["r_plants"]], [], None,
   "set_politics = { ruling_party = democratic elections_allowed = yes }\n" + pop("democratic", 0.6) + inner(-10))
fc("r_ind", "Индустриальное общество", 140, "Гудок больше никого не удивляет. Туман рассеялся, страна проснулась.", 30, 6, [["r_comm"]], [], "check_variable = { var = ktits_kaz_reform value = 80 compare = greater_than_or_equals }",
   "country_event = { id = ktits_kazualia.4 }\n", False)
# --- Коммунистический
fc("c_sov", "Болотные Советы", 70, "В каждой деревне — совет. Заседания идут лёжа, но решения принимаются.", 48, 2, [["red"]], [], None, pop("communism", 0.15) + inner(-5))
fc("c_help", "Помощь братских стран", 70, "Коммунистические страны шлют инструкторов, станки и брошюры. Брошюры казуалы читают охотнее всего.", 44, 3, [["c_sov"]], [], None,
   "set_variable = { var = ktits_kaz_cn value = 0 }\nhidden_effect = {\n    every_other_country = { limit = { has_government = communism } ROOT = { add_to_variable = { var = ktits_kaz_cn value = 1 } } add_opinion_modifier = { target = ROOT modifier = ktits_kaz_comm_help } ROOT = { add_opinion_modifier = { target = PREV modifier = ktits_kaz_comm_help } } }\n"
   "    clamp_variable = { var = ktits_kaz_cn min = 0 max = 3 }\n"
   + "".join(f"    if = {{ limit = {{ check_variable = {{ var = ktits_kaz_cn value = {i} compare = greater_than_or_equals }} }} random_owned_controlled_state = {{ limit = {{ impassable = no }} add_extra_state_shared_building_slots = 1 add_building_construction = {{ type = industrial_complex level = 1 instant_build = yes }} }} }}\n" for i in (1, 2, 3))
   + "}\n" + src_tt("ktits_kaz_tt_help", "+1 гражданская фабрика за каждую коммунистическую страну (до 3); отношения с ними +25"), icon=I_IMP)
fc("c_plan", "Пятилетка в три года", 105, "План простой: за три года построить всё, чего не строили триста.", 52, 3, [["c_sov"]], [], None, civ(3) + inner(-10) + stab(-0.10), icon=I_CIV, flt=IND)
fc("c_guard", "Красная гвардия болот", 70, "Вчерашние лентяи получают винтовки и красные повязки. Ленятся теперь организованно.", 44, 4, [["c_help"]], [], None,
   divs("militia", 3) + "set_country_flag = ktits_kaz_f_civwar_half\n" + src_tt("ktits_kaz_tt_civwar_half", "Риск гражданской войны −50 % (гражданская война не реализована)"), icon=I_ARM, flt=ARM)
fc("c_coll", "Коллективизация трясин", 105, "Болота объявлены общими. Никто не понял, что изменилось, но работать стали больше.", 52, 4, [["c_plan"]], [], None, mil(2) + inner(-10), icon=I_MIL, flt=IND)
fc("c_rep", "Народная Республика Казуалия", 70, "Над Ставкой — красное знамя. Ставка переименована в Дом Советов, но все по привычке зовут её Ставкой.", 48, 5, [["c_guard"], ["c_coll"]], [], None,
   "set_politics = { ruling_party = communism elections_allowed = yes }\n" + pop("communism", 0.7) + src_tt("ktits_kaz_tt_comm_all", "Может вступить в коммунистический альянс"))
# --- Образование
SP = "ktits_kaz_edu_open"
def spec(n):
    ttl(f"ktits_kaz_tt_sp{n}", f"Специалисты: §G+{n}§! тыс. (ограничение «всегда 0» снято)", f"Specialists: §G+{n}§! k (the 'always 0' rule is lifted)")
    return f"set_country_flag = {SP}\ncustom_effect_tooltip = ktits_kaz_tt_sp{n}\nhidden_effect = {{ add_to_variable = {{ var = ktits_spec_own value = {n} }} ktits_education_update = yes }}\n"
fc("s_school", "Школы вместо Ставок", 70, "Священные палаты отдают под классы. Учитель приходит раньше учеников — это уже прогресс.", 62, 2, [["hum", "red"]], [], None, spec(5), icon=I_SCI, flt=RES)
fc("s_lit", "Грамота для всех", 105, "Казуалы учатся читать. Первая прочитанная книга у всех одна — «Как перестать откладывать».", 62, 3, [["s_school"]], [], None, spec(10) + inner(-5), icon=I_SCI, flt=RES)
fc("s_univ", "Болотный университет", 105, "Первый университет посреди болот. Лекции начинаются в полдень: компромисс с традицией.", 62, 4, [["s_lit"]], [], None,
   spec(15) + "add_ideas = ktits_kaz_sp_univ\n", icon=I_SCI, flt=RES)
# --- Резервация
SUB = "is_subject = yes"
COUP = ("overlord = {\n    end_puppet = ROOT\n    ROOT = { declare_war_on = { target = PREV type = annex_everything } add_timed_idea = { idea = ktits_kaz_coup_t days = 180 } }\n"
        "    if = { limit = { check_variable = { var = ktits_casuality value = 75 compare = greater_than_or_equals } } every_owned_state = { add_claim_by = ROOT } }\n}\n")
fc("z_new", "Новая Ставка", 35, "Чужие флаги над старой Ставкой. Казуалам выделили болото и велели вести себя тихо.", 76, 0, [], [], SUB,
   "set_country_flag = ktits_kaz_f_reserve\n" + pp(50) + "add_timed_idea = { idea = ktits_kaz_quiet_t days = 180 }\n" + src_tt("ktits_kaz_tt_capital", "+50 ПВ, дух «Тихая жизнь» на 180 дней (стабильность +10 %); открывает выбор подпути (перенос столицы в 5 провинций не реализован)"), False)
fc("z_obey", "Покорность", 70, "Будем служить. Будем полезны. А когда-нибудь хозяин сдержит слово.", 72, 1, [["z_new"]], ["z_riot"], None,
   "overlord = { add_opinion_modifier = { target = ROOT modifier = ktits_kaz_obey } }\n" + stab(0.05) + pp(25) + src_tt("ktits_kaz_tt_obey", "Отношения сюзерена +50; +25 ПВ; стабильность +5 % (ускорения автономии в игре нет)"), False)
fc("z_serve", "Верная служба", 105, "Казуальные полки воюют за хозяина. Не быстро, но стоят насмерть.", 72, 2, [["z_obey"]], [], None,
   "add_autonomy_ratio = { value = 0.20 localization = ktits_kaz_tt_serve }\n" + "overlord = { add_ideas = ktits_kaz_sp_levy }\n" + src_tt("ktits_kaz_tt_serve2", "Сюзерен получает дух «Казуальные полки» (защита армии +5 %, призыв +2 %); автономия +20 %"))
fc("z_indep", "Обещанная независимость", 70, "Хозяин держит слово — или Казуалия напоминает ему об этом очень вежливо.", 72, 3, [["z_serve"]], [], None,
   "set_country_flag = ktits_kaz_f_indep\n" + "overlord = { country_event = { id = ktits_kazualia.5 } }\n" + src_tt("ktits_kaz_tt_indep", "Сюзерену приходит событие: дать независимость или отказать (отказ: отношения −100, Внутренняя Казуальность +20 %)"))
fc("z_riot", "Казуальное восстание", 70, "Хозяин думает, что казуалы спят. Хозяин ошибается.", 80, 1, [["z_new"]], ["z_obey"], None,
   inner(10) + "overlord = { if = { limit = { NOT = { has_country_flag = ktits_casuality_fallen } } add_to_variable = { var = ktits_casuality value = 10 } clamp_variable = { var = ktits_casuality min = 0 max = 100 } ktits_casuality_update = yes } }\n" + src_tt("ktits_kaz_tt_riot_o", "Шкала Казуальности сюзерена +10"), False)
fc("z_reeds", "Камыши и винтовки", 105, "По ночам в камышах раздают оружие, которое хозяин сам сюда привёз.", 80, 2, [["z_riot"]], [], None,
   "add_equipment_to_stockpile = { type = infantry_equipment_1 amount = 3000 }\n" + src_tt("ktits_kaz_tt_reeds", "+3000 пехотного снаряжения (в запасе); партизаны в штатах сюзерена не реализованы"))
fc("z_fog", "Туман над столицей хозяина", 105, "Чиновники сюзерена всё чаще смотрят в окно вместо отчёта.", 80, 3, [["z_reeds"]], [], None,
   "overlord = { if = { limit = { NOT = { has_country_flag = ktits_casuality_fallen } } add_to_variable = { var = ktits_casuality value = 20 } clamp_variable = { var = ktits_casuality min = 0 max = 100 } ktits_casuality_update = yes add_stability = -0.10 } }\n" + src_tt("ktits_kaz_tt_zfog", "Шкала Казуальности сюзерена +20; стабильность сюзерена −10 %"))
fc("z_coup", "Казуальный переворот", 70, "Вооружённое восстание: казуалы выходят из тумана, и власть хозяина рушится.", 80, 4, [["z_fog"]], [], None,
   "set_country_flag = ktits_kaz_f_coup\n" + COUP + src_tt("ktits_kaz_tt_coup", "Казуалия перестаёт быть марионеткой и объявляет сюзерену войну; при шкале Казуальности сюзерена ≥ 75 получает претензии на все его штаты; +20 % к поддержке войны на 180 дней"))
# --- Экономика
fc("e_faith", "Вера в само собой", 70, "Казуалы не работают, но у них всё есть. Никто не знает откуда, и никто не спрашивает.", 92, 0, [], [], NOREFORM,
   faith(200) + "add_to_variable = { var = ktits_kaz_faith_mult value = 0.10 }\n" + src_tt("ktits_kaz_tt_mult1", "Прирост Веры +10 %"), False, icon=I_TRADE, flt=IND)
fc("e_stock", "Болотные склады", 70, "В тине находят ящики с припасами. Кто их туда положил — тайна.", 88, 1, [["e_faith"]], [], None,
   "multiply_variable = { var = ktits_kaz_c_guns value = 0.75 }\nmultiply_variable = { var = ktits_kaz_c_cannons value = 0.75 }\n" + src_tt("ktits_kaz_tt_stock", "Решения «Ружья из тины» и «Пушки сами приплыли» дешевле на 25 %"), icon=I_TRADE, flt=IND)
fc("e_prophets", "Пророки урожая", 70, "Пророки говорят, что урожай будет. Урожай слушается.", 96, 1, [["e_faith"]], [], None,
   "add_to_variable = { var = ktits_kaz_faith_mult value = 0.15 }\n" + src_tt("ktits_kaz_tt_mult2", "Прирост Веры +15 %") + stab(0.05), icon=I_TRADE, flt=IND)
fc("e_miracle", "Чудеса по расписанию", 105, "Чудеса случаются так часто, что к ним привыкли.", 92, 2, [["e_stock"], ["e_prophets"]], [], None,
   faith(300) + "set_country_flag = ktits_kaz_cd_fast\n" + src_tt("ktits_kaz_tt_fast", "Перезарядка всех «Даров болот» −25 %"), icon=I_TRADE, flt=IND)
# --- Бриттанское влияние
BR_ND = "NOT = { has_completed_focus = ktits_kaz_red }"
def lvl(n):
    names = {1: "ktits_kaz_britt_influence", 2: "ktits_kaz_britt_2", 3: "ktits_kaz_britt_3"}
    rm = "".join(f"    if = {{ limit = {{ has_idea = {v} }} remove_ideas = {v} }}\n" for k, v in names.items() if k != n)
    return f"hidden_effect = {{\n{rm}    if = {{ limit = {{ NOT = {{ has_idea = {names[n]} }} }} add_ideas = {names[n]} }}\n}}\n"
fc("b_friends", "Бриттанские друзья", 35, "На пристани Казуахии встречают первый бриттанский пароход. Казуалы машут, бритты записывают.", 106, 0, [], [], BR_ND,
   lvl(1) + src_tt("ktits_kaz_tt_b1", "Дух «Бриттанское влияние»: уровень 1 (Бриттанские советники)") + f"{BRT} = {{ add_opinion_modifier = {{ target = ROOT modifier = ktits_kaz_britt_friend }} }}\n", icon=I_IMP)
fc("b_advisers", "Советники с острова", 70, "В каждом министерстве теперь сидит бритт. Он пьёт чай и молча смотрит, как работает министр. Министр работает.", 106, 1, [["b_friends"]], [], None,
   lvl(2) + src_tt("ktits_kaz_tt_b2", "Дух «Бриттанское влияние»: уровень 2 (Бриттанские займы)"), icon=I_IMP)
fc("b_loans", "Займы под болота", 70, "Бриттанский фунт пришёл на болота. Строятся дороги, гудят машины, и все вдруг стали должны.", 106, 2, [["b_advisers"]], [], None,
   civ(2) + src_tt("ktits_kaz_tt_b2b", "Дух остаётся на уровне 2"), icon=I_CIV, flt=IND)
fc("b_protect", "Бриттанский протекторат", 105, "Флаг Ставки по-прежнему над дворцом. Просто рядом теперь висит ещё один — побольше.", 106, 3, [["b_loans"]], [], None,
   lvl(3) + src_tt("ktits_kaz_tt_b3", "Дух «Бриттанское влияние»: уровень 3 (Бриттанский протекторат)"), icon=I_IMP)
BX = ["b_crown", "b_sea", "b_free"]
fc("b_crown", "Под крылом короны", 70, "Священный-Архо-Казуал преклоняет колено перед бриттанским наместником. Зато теперь можно больше ни о чём не думать — за казуалов думает корона.", 102, 4, [["b_protect"]], ["b_sea", "b_free"], "has_country_flag = ktits_kaz_reformist",
   "hidden_effect = {\n    if = { limit = { has_idea = ktits_kaz_britt_3 } swap_ideas = { remove_idea = ktits_kaz_britt_3 add_idea = ktits_kaz_crown } }\n}\n"
   + f"{BRT} = {{ puppet = ROOT }}\n" + src_tt("ktits_kaz_tt_crown", "Казуалия — марионетка Бриттана; дух «Корона и болото»"), icon=I_DEAL)
fc("b_sea", "Морской союз", 70, "Не слуги, а союзники. Бриттанский флот и казуальное болото: никто не пройдёт ни по морю, ни по суше.", 106, 4, [["b_protect"]], ["b_crown", "b_free"], f"NOT = {{ has_government = casuality }}\n            is_subject = no\n            country_exists = {BRT}\n            {BRT} = {{ NOT = {{ ktits_ally_barred = yes }} }}",
   "hidden_effect = {\n    " + BRT + " = {\n        if = { limit = { is_in_faction = no } create_faction_from_template = ktits_alliance_template add_to_faction = ROOT }\n"
   "        else_if = { limit = { is_faction_leader = yes } add_to_faction = ROOT }\n"
   "        else = { every_allied_country = { limit = { is_faction_leader = yes } add_to_faction = ROOT } }\n    }\n}\n"
   + src_tt("ktits_kaz_tt_sea", "Только при правлении не-Казуальности: вступает в альянс Бриттана (если его нет, Бриттан создаёт альянс и принимает Казуалию)"), icon=I_ALL)
fc("b_free", "Дружба без обязательств", 70, "Чай вместе пьём, а дом у каждого свой. Бриттам вежливо указали на дверь, оставив её приоткрытой.", 110, 4, [["b_protect"]], ["b_crown", "b_sea"], None,
   lvl(2) + src_tt("ktits_kaz_tt_free", "Дух остаётся на уровне 2, ограничения уровня 3 сняты"), icon=I_IMP)
# --- Армия
fc("a_militia", "Болотное ополчение", 70, "Каждый казуал умеет держать вилы и лежать в засаде. Второе — особенно.", 124, 0, [], [], None, divs("militia", 2) + "add_ideas = ktits_kaz_sp_army1\n", icon=I_ARM, flt=ARM)
fc("a_paths", "Тропы в трясине", 70, "Казуалы знают каждую кочку. Чужаки — ни одной.", 120, 1, [["a_militia"]], [], None,
   "add_ideas = ktits_kaz_sp_paths\n" + src_tt("ktits_kaz_tt_a2", "Скорость армии +10 %, атака +5 % (модификатора местности для страны в игре нет, поэтому бонус общий)"), icon=I_ARM, flt=ARM)
fc("a_posts", "Горные заставы Ставки", 70, "Горы стерегут столицу с трёх сторон. Теперь в горах ещё и сторожа.", 128, 1, [["a_militia"]], [], None,
   "add_ideas = ktits_kaz_sp_posts\n" + src_tt("ktits_kaz_tt_a3", "Защита армии +5 %, макс. окапывание +10 % (модификатора местности нет, бонус общий); +2 форта в штате столицы")
   + f"hidden_effect = {{ capital_scope = {{ add_building_construction = {{ type = bunker level = 2 province = {CAP_PROV} instant_build = yes }} }} }}\n", icon=I_FORT, flt=ARM)
fc("a_reeds", "Засады в камышах", 105, "Враг идёт по болоту и вдруг понимает, что болото на него смотрит.", 120, 2, [["a_paths"]], [], None, "add_ideas = ktits_kaz_sp_army2\n" + src_tt("ktits_kaz_tt_a4", "Скорость окапывания +20 %; организация +5 %"), icon=I_ARM, flt=ARM)
fc("a_hold", "Неприступная Ставка", 105, "Южный проход к Ставке перекрыт. Остальные три закрыли горы.", 128, 2, [["a_posts"]], [], None,
   "add_ideas = ktits_kaz_sp_hold\n" + src_tt("ktits_kaz_tt_a5", "Защита армии +5 %, организация +5 %; ещё +2 форта в штате столицы")
   + f"hidden_effect = {{ capital_scope = {{ add_building_construction = {{ type = bunker level = 2 province = {CAP_PROV} instant_build = yes }} }} }}\n", icon=I_FORT, flt=ARM)
fc("a_slow", "Армия, которая не спешит", 105, "Казуальная армия не наступает быстро. Зато и не отступает никогда.", 124, 3, [["a_reeds", "a_hold"]], [], None, "add_ideas = ktits_kaz_sp_army3\n", icon=I_ARM, flt=ARM)
# prerequisites for a_slow are AND: both branches
for n, f_ in enumerate(F):
    if f_[0] == "a_slow": F[n] = f_[:6] + ([["a_reeds"], ["a_hold"]],) + f_[7:]
    if f_[0] == "g_all": pass
# compact layout (x grid: neighbours at distance 2, branches separated by one empty slot); overrides the x, y given above
LAYOUT = {
    "wake": (20, 0), "sleep": (6, 1), "hum": (22, 1), "red": (34, 1),
    "g_power": (6, 2), "n_root": (2, 3), "g_root": (10, 3),
    "n_siesta": (0, 4), "n_temple": (4, 4), "n_watch": (0, 5), "n_calm": (4, 5), "n_peace": (2, 6), "n_golden": (2, 7),
    "g_preach": (8, 4), "g_border": (12, 4), "g_mission": (8, 5), "g_fog": (12, 5), "g_all": (10, 6), "g_accept": (10, 7), "g_end": (10, 8),
    "d_swamp": (15, 4), "d_fog": (15, 5), "d_home": (15, 6),
    "r_council": (22, 2), "r_decree": (20, 3), "r_drain": (24, 3), "r_crush": (20, 4), "r_plants": (24, 4), "r_rail1": (18, 3), "r_rail2": (18, 4), "r_rail3": (18, 5), "r_comm": (22, 5), "r_ind": (22, 6),
    "s_school": (28, 2), "s_lit": (28, 3), "s_univ": (28, 4),
    "c_sov": (34, 2), "c_help": (32, 3), "c_plan": (36, 3), "c_guard": (32, 4), "c_coll": (36, 4), "c_rep": (34, 5),
    "g_quiet": (14, 7), "g_echo": (14, 8), "e_faith": (42, 1), "e_stock": (40, 2), "e_prophets": (44, 2), "e_miracle": (42, 3),
    "b_friends": (50, 1), "b_advisers": (50, 2), "b_loans": (50, 3), "b_protect": (50, 4), "b_crown": (48, 5), "b_sea": (50, 5), "b_free": (52, 5),
    "a_militia": (58, 1), "a_paths": (56, 2), "a_posts": (60, 2), "a_reeds": (56, 3), "a_hold": (60, 3), "a_slow": (58, 4),
    "z_new": (66, 1), "z_obey": (64, 2), "z_riot": (68, 2), "z_serve": (64, 3), "z_reeds": (68, 3), "z_indep": (64, 4), "z_fog": (68, 4), "z_coup": (68, 5),
}
assert set(LAYOUT) == {f_[0] for f_ in F}, set(LAYOUT) ^ {f_[0] for f_ in F}
assert len(set(LAYOUT.values())) == len(LAYOUT)
# AI: the political branches first (path choice and path branches very high), then the economy / education / British influence, the army last
AIW = {"wake": 1000, "sleep": 300, "hum": 120, "red": 60, "g_root": 150, "n_root": 100, "z_obey": 150, "z_riot": 80}
def ai_weight(i):
    if i in AIW: return AIW[i]
    k = i.split("_")[0]
    return {"g": 100, "n": 100, "r": 100, "c": 100, "z": 100, "d": 40, "s": 30, "e": 20, "b": 15, "a": 3}[k]
SUBREQ = ("z_riot", "z_reeds", "z_fog", "z_serve", "z_indep", "z_coup")
for n, f_ in enumerate(F):
    f_ = F[n] = f_[:4] + LAYOUT[f_[0]] + f_[6:]
    if f_[0] in SUBREQ and f_[8] is None: F[n] = f_[:8] + (SUB,) + f_[9:]
FOC = {f_[0]: f_ for f_ in F}
assert len({f_[0] for f_ in F}) == len(F)
GATE = {"hum": "reform", "red": "comm"}
# availability of the 4 path roots
ROOT_AVAIL = {
    "r_council": "has_country_flag = ktits_kaz_reformist", "r_decree": "has_country_flag = ktits_kaz_reformist",
}
FOC_TXT = ""
LATE_IDS = []
for (i, name, days, desc, x, y, pre, excl, avail, rew, late, icon, flt) in F:
    fid = P + i
    s = f"    focus = {{\n        id = {fid}\n        icon = {icon}\n"
    for grp in pre:
        s += "        prerequisite = { " + " ".join(f"focus = {P + g}" for g in grp) + " }\n"
    if excl:
        s += "        mutually_exclusive = { " + " ".join(f"focus = {P + g}" for g in excl) + " }\n"
    s += f"        x = {x}\n        y = {y}\n        cost = {days // 7}\n        search_filters = {{ {flt} }}\n"
    if i.startswith('b_'):   # the British branch closes after the decision 'Выгнать клерков' (flag ktits_kaz_expelled)
        avail = (avail + chr(10) + '            ' if avail else '') + 'NOT = { has_country_flag = ktits_kaz_expelled }'
        s += "        allow_branch = {\n            NOT = { has_country_flag = ktits_kaz_expelled }\n        }\n"
    if avail:
        s += f"        available = {{\n            {avail}\n        }}\n"
    s += "        cancel_if_invalid = no\n        continue_if_invalid = yes\n"
    s += f"        ai_will_do = {{\n            factor = {ai_weight(i)}\n        }}\n"
    if late:
        LATE_IDS.append(i)
        s += (f"        completion_reward = {{\n            if = {{\n                limit = {{ check_variable = {{ var = ktits_kaz_inner value = 80 compare = greater_than }} }}\n"
              f"                random_list = {{\n                    50 = {{ ktits_kaz_rw_{i} = yes }}\n"
              f"                    50 = {{\n                        custom_effect_tooltip = ktits_kaz_late_tt\n                        hidden_effect = {{ country_event = {{ id = ktits_kazualia.{100 + len(LATE_IDS)} days = 7 random_days = 23 }} }}\n                    }}\n"
              f"                }}\n            }}\n            else = {{ ktits_kaz_rw_{i} = yes }}\n        }}\n")
    else:
        s += "        completion_reward = {\n" + "".join("            " + l + "\n" for l in rew.splitlines()) + "        }\n"
    s += "    }\n"
    FOC_TXT += "\n" + s
    add(fid, name); add(fid + "_desc", desc)
# Path choice focuses are not late; the second condition of the tree: wake has no prerequisite and the paths follow
tree = ("focus_tree = {\n    id = ktits_kazualia_focus\n    country = {\n        factor = 0\n        modifier = {\n            add = 100\n            original_tag = " + KAZ + "\n        }\n    }\n"
        "    default = no\n    reset_on_civilwar = no\n    continuous_focus_position = { x = 50 y = 1250 }\n    initial_show_position = {\n        focus = ktits_kaz_wake\n    }\n" + FOC_TXT + "}\n")
w("common/national_focus/ktits_kazualia.txt", "﻿" + tree)
# reward bodies of delayed focuses
rw_txt = "# generated by tools/make_kazualia.py: the rewards of focuses/decisions that can be delayed (docs/mechanics/Kazualia.md, section 2.1)\n"
for (i, name, days, desc, x, y, pre, excl, avail, rew, late, icon, flt) in F:
    if late:
        rw_txt += f"ktits_kaz_rw_{i} = {{\n" + "".join("    " + l + "\n" for l in rew.splitlines()) + "}\n\n"

# ================= spirits =================
def idea(name, mods, pic=IDEA_PIC):
    body = "".join(f"            {k} = {v:g}\n" for k, v in mods.items())
    return f"        {name} = {{\n            picture = {pic}\n            allowed = {{ always = no }}\n            allowed_civil_war = {{ always = yes }}\n            removal_cost = -1\n            modifier = {{\n{body}            }}\n        }}\n"
ideas = ""
for n, ca, cd in DURM:
    mods = {"army_core_attack_factor": DURM_CORE_ATK}
    mods.update(DURM_SUP)          # supply compensation (no railways in Kazualia)
    if ca: mods["army_non_core_attack_factor"] = ca
    if cd: mods["army_non_core_defence_factor"] = cd
    ideas += idea(n, mods)
STAGE_RU = ["", " (ослаблено на треть)", " (ослаблено на две трети)", " (остался только бафф)"]
STAGE_TXT = ["", " Первый глоток болотной воды уже делает чужую землю чуть роднее.", " Туман идёт впереди армии, и чужие поля почти не мешают.", " Теперь казуал спит на чужой земле как дома, и туман ему не помеха."]
for n, (nm, _a, _d) in zip(range(4), DURM):
    add(nm, "Дурманище" + STAGE_RU[n]); add(nm + "_desc", DURM_TXT + STAGE_TXT[n])
ideas += idea("ktits_kaz_britt_influence", {"research_speed_factor": 0.05})
ideas += idea("ktits_kaz_britt_2", {"production_speed_buildings_factor": 0.10, "industrial_capacity_factory": 0.05})
ideas += idea("ktits_kaz_britt_3", {"production_speed_buildings_factor": 0.15, "industrial_capacity_factory": 0.10, "navy_capital_ship_attack_factor": 0.10, "navy_screen_attack_factor": 0.10})
ideas += idea("ktits_kaz_crown", {"production_speed_buildings_factor": 0.225, "industrial_capacity_factory": 0.15, "navy_capital_ship_attack_factor": 0.15, "navy_screen_attack_factor": 0.15, "research_speed_factor": 0.075})
ideas += idea("ktits_kaz_sobering", {"stability_factor": 0.05})
ideas += idea("ktits_kaz_grace_t", {"stability_factor": 0.05})
ideas += idea("ktits_kaz_resist_t", {"stability_factor": -0.03})
ideas += idea("ktits_kaz_resist5_t", {"stability_factor": -0.05})
ideas += idea("ktits_kaz_sp_univ", {"research_speed_factor": 0.05})
ideas += idea("ktits_kaz_sp_army1", {"conscription_factor": 0.01})
ideas += idea("ktits_kaz_sp_army2", {"dig_in_speed_factor": 0.2, "army_org_factor": 0.05})
ideas += idea("ktits_kaz_sp_army3", {"army_org_regain": 0.10, "supply_consumption_factor": -0.10})
NEWSP = [
    ("ktits_kaz_sp_siesta", "Священная сиеста", {"stability_factor": 0.05, "political_power_gain": 0.10}, "Сиеста объявлена государственным делом. Опоздавшим на сон выдают справку, что они не опоздали."),
    ("ktits_kaz_sp_watch", "Сторожа сна", {"army_defence_factor": 0.10, "max_dig_in_factor": 0.10}, "Вдоль границы выставлены посты. Их задача простая: стоять и никого не пускать будить."),
    ("ktits_kaz_sp_calm", "Тихие границы", {"stability_factor": 0.05, "consumer_goods_factor": -0.05}, "На границе тишина. Контрабандисты тоже спят, а пограничники делают вид, что это порядок. Меньше ввозят, меньше и хотят."),
    ("ktits_kaz_sp_fog", "Туман на границе", {"war_support_factor": 0.10, "army_speed_factor": 0.05}, "Туман ползёт через границу, и по нему казуалы ходят как по собственной кухне."),
    ("ktits_kaz_sp_pp1", "Тихая власть", {"political_power_gain": 0.20}, "Приказы больше не пишут: их шепчут в тумане, и они почему-то исполняются."),
    ("ktits_kaz_sp_pp2", "Эхо в камышах", {"political_power_gain": 0.30}, "Шёпот из тумана доходит до самой дальней деревни. Деревня зевает и соглашается."),
    ("ktits_kaz_sp_march", "Поход ленивых", {"war_support_factor": 0.10, "conscription_factor": 0.02}, "Ставка объявила: весь материк должен отдохнуть. Армия идёт на это отдыхать неторопливо, зато с песней."),
    ("ktits_kaz_sp_paths", "Тропы в трясине", {"army_speed_factor": 0.10, "army_attack_factor": 0.05}, "Казуалы знают каждую кочку. Чужаки — ни одной."),
    ("ktits_kaz_sp_posts", "Горные заставы Ставки", {"army_defence_factor": 0.05, "max_dig_in_factor": 0.10}, "Горы стерегут столицу с трёх сторон. Теперь в горах ещё и сторожа."),
    ("ktits_kaz_sp_hold", "Неприступная Ставка", {"army_defence_factor": 0.05, "army_org_factor": 0.05}, "Южный проход к Ставке перекрыт. Остальные три закрыли горы."),
    ("ktits_kaz_sp_levy", "Казуальные полки", {"army_defence_factor": 0.05, "conscription_factor": 0.02}, "Казуальные полки воюют за хозяина. Не быстро, но стоят насмерть."),
    ("ktits_kaz_quiet_t", "Тихая жизнь", {"stability_factor": 0.10}, "Чужие флаги над старой Ставкой, зато никто больше не требует вставать рано."),
    ("ktits_kaz_coup_t", "Туман выходит из камышей", {"war_support_factor": 0.20}, "Казуалы вышли из тумана с оружием, которое хозяин сам сюда привёз. Впервые за век они спешат."),
]
for n_, ru_, md_, ds_ in NEWSP:
    ideas += idea(n_, md_); add(n_, ru_); add(n_ + "_desc", ds_)
w("common/ideas/ktits_kazualia_ideas.txt", "ideas = {\n    country = {\n" + ideas + "    }\n}\n")
# economy law "Казуальное общество" (docs/mechanics/Kazualia.md 2.0): 100 % of the factories go to consumer goods.
# Key consumer_goods_expected_value is what the vanilla economy laws use (common/ideas/_economic.txt); the value 1.0 (all civilian factories) is invented [uncertain: clamping in game]
LAW = "ktits_eco_casual_society"
w("common/ideas/ktits_kaz_laws.txt", f"""ideas = {{
    economy = {{
        law = yes
        use_list_view = yes

        {LAW} = {{
            picture = {IDEA_PIC}
            allowed = {{ always = no }}
            allowed_civil_war = {{ always = yes }}
            removal_cost = -1
            cancel_if_invalid = no
            modifier = {{
                consumer_goods_expected_value = 1.0
            }}
        }}
    }}
}}
""")
add(LAW, "Казуальное общество")
add(LAW + "_desc", "Всё, что производится, сразу потребляется. Заводы делают гамаки, подушки и чай; на пушки не остаётся ни станка, ни желания.")
ttl("ktits_casual_law_lock_tt", "Действует закон «Казуальное общество»: сменить экономический закон можно только фокусом «Заводской гудок» или «Красное болото»", "The law 'Casual Society' is in force: it can only be replaced by the focus 'Factory Whistle' or 'Red Swamp'")
# the vanilla economy laws (a copy in the mod folder) are locked while the casual law stands: insert the check into every law of the economy block
def _lock_vanilla_economy():
    p_ = M / "common/ideas/_economic.txt"
    if not p_.exists(): return
    t_ = p_.read_text(encoding="utf-8")
    if "ktits_casual_law_lock_tt" in t_: return
    i0 = t_.index("\n\teconomy = {"); i1 = t_.index("\n\ttrade_laws = {")
    blk = t_[i0:i1]
    chk = "custom_trigger_tooltip = { tooltip = ktits_casual_law_lock_tt NOT = { has_idea = " + LAW + " } }"
    parts = re.split(r"(?m)^(\t\t\w+ = \{\n)", blk)
    out = parts[0]
    for j in range(1, len(parts), 2):
        head, body = parts[j], parts[j + 1]
        if re.search(r"(?m)^\t\t\tavailable = \{[ \t]*\n", body):
            body = re.sub(r"(?m)^(\t\t\tavailable = \{[ \t]*\n)", lambda m: m.group(1) + "\t\t\t\t" + chk + "\n", body, count=1)
        else:
            body = "\t\t\tavailable = {\n\t\t\t\t" + chk + "\n\t\t\t}\n" + body
        out += head + body
    p_.write_text(t_[:i0] + out + t_[i1:], encoding="utf-8", newline="")
_lock_vanilla_economy()
add("ktits_kaz_britt_influence", "Бриттанское влияние: Бриттанские советники"); add("ktits_kaz_britt_influence_desc", "Вежливые люди с острова учат казуалов считать и писать отчёты. Отчёты получаются короткими, но бриттам этого хватает.")
add("ktits_kaz_britt_2", "Бриттанское влияние: Бриттанские займы"); add("ktits_kaz_britt_2_desc", "Бриттанские банки дают деньги под залог болот. Болота никому не нужны, поэтому и деньги дают охотно. Пока.")
add("ktits_kaz_britt_3", "Бриттанское влияние: Бриттанский протекторат"); add("ktits_kaz_britt_3_desc", "Ставка подписывает бумаги, которые ей приносят из посольства. Читать их не обязательно: бритты всё уже прочитали за неё.")
add("ktits_kaz_crown", "Корона и болото"); add("ktits_kaz_crown_desc", "Казуалия — жемчужина бриттанской короны. Немного мутная, зато своя.")
add("ktits_kaz_sobering", "Отрезвление"); add("ktits_kaz_sobering_desc", "Восстание подавлено, туман рассеялся. Люди протирают глаза и с удивлением смотрят на заросшие поля и брошенные станки. Ещё долго никто не захочет даже слышать о том, чтобы прилечь «на минутку».")
add("ktits_kaz_grace_t", "Благодать Ставки"); add("ktits_kaz_grace_t_desc", "Священный-Архо-Казуал благословляет народ, и всем становится хорошо.")
add("ktits_kaz_resist_t", "Народ сопротивляется"); add("ktits_kaz_resist_t_desc", "Реформы раздражают: люди ворчат, прячутся в камышах и делают вид, что указа не было.")
add("ktits_kaz_resist5_t", "Народ сопротивляется: рабочий день"); add("ktits_kaz_resist5_t_desc", "Половина страны впервые встала до обеда и теперь не в духе.")
add("ktits_kaz_sp_univ", "Болотный университет"); add("ktits_kaz_sp_univ_desc", "Первый университет посреди болот. Лекции начинаются в полдень: компромисс с традицией.")
add("ktits_kaz_sp_army1", "Болотное ополчение"); add("ktits_kaz_sp_army1_desc", "Каждый казуал умеет держать вилы и лежать в засаде. Второе — особенно.")
add("ktits_kaz_sp_army2", "Засады в камышах"); add("ktits_kaz_sp_army2_desc", "Враг идёт по болоту и вдруг понимает, что болото на него смотрит.")
add("ktits_kaz_sp_army3", "Армия, которая не спешит"); add("ktits_kaz_sp_army3_desc", "Казуальная армия не наступает быстро. Зато и не отступает никогда.")

# ================= dynamic modifier (Internal Casuality, section 2) =================
# value coefficients per 1 % of the scale: (modifier, normal, on the Reform path); N/5 % -> 0.002, N/4 % -> 0.0025, N/10 % -> 0.001, N/2 % -> 0.005, N/20 % -> 0.0005
DM = [
    ("army_attack_factor", 0.002, 0.001), ("army_defence_factor", 0.002, 0.001),                    # +N/5 %; Reform: -N/10 % taken from the buff
    ("industrial_capacity_factory", -0.0025, -0.005), ("production_speed_buildings_factor", -0.0025, -0.005),
    ("army_org_regain", 0.002, 0.002), ("supply_consumption_factor", -0.002, -0.002), ("dig_in_speed_factor", 0.005, 0.005),
    ("conscription_factor", 0.001, 0.001), ("army_speed_factor", -0.001, -0.001),
    ("research_speed_factor", -0.006, -0.003), ("stability_factor", 0.0, -0.001), ("consumer_goods_factor", 0.0, 0.0005),
    ("production_factory_efficiency_gain_factor", -0.001, -0.002), ("army_org_factor", 0.0, -0.001),
]
dm = "# generated by tools/make_kazualia.py: docs/mechanics/Kazualia.md section 2; values come from the variables of ktits_kaz_inner_update\nktits_kaz_inner_dm = {\n    icon = GFX_idea_ktits_casuality\n"
for k, _n, _r in DM:
    dm += f"    {k} = ktits_kz_{k}\n"
dm += "}\n"
w("common/dynamic_modifiers/ktits_kazualia_dynamic_modifiers.txt", dm)
add("ktits_kaz_inner_dm", "Внутренняя Казуальность")
add("ktits_kaz_inner_dm_desc", "Казуал не ленится — он ждёт. Ждёт урожая, приказа, конца света. Пока он ждёт, ружьё у него всегда под рукой, а болото за спиной знает каждую его тропу. Шкала: [?ktits_kaz_inner|0] %.")

# ================= scripted effects / triggers =================
upd = "# scope = Kazualia: the scale -> variables of the dynamic modifier (Reform path = country flag ktits_kaz_reformist)\nktits_kaz_inner_update = {\n    clamp_variable = { var = ktits_kaz_inner min = 0 max = 100 }\n"
for k, nrm, rf in DM:
    v = f"ktits_kz_{k}"
    upd += f"    set_variable = {{ var = {v} value = ktits_kaz_inner }}\n"
    if nrm == rf:
        upd += f"    multiply_variable = {{ var = {v} value = {nrm} }}\n"
    else:
        upd += (f"    if = {{\n        limit = {{ has_country_flag = ktits_kaz_reformist }}\n        multiply_variable = {{ var = {v} value = {rf} }}\n    }}\n"
                f"    else = {{\n        multiply_variable = {{ var = {v} value = {nrm} }}\n    }}\n")
upd += "    if = {\n        limit = { NOT = { has_dynamic_modifier = { modifier = ktits_kaz_inner_dm } } NOT = { has_country_flag = ktits_kaz_industrial } }\n        add_dynamic_modifier = { modifier = ktits_kaz_inner_dm }\n    }\n    force_update_dynamic_modifier = yes\n}\n"
# the capital state province / cost variables
start = f"""# scope = Kazualia, once at the start of the game
ktits_kaz_start = {{
    set_variable = {{ var = ktits_kaz_inner value = 50 }}
    set_variable = {{ var = ktits_kaz_faith value = 100 }}
    set_variable = {{ var = ktits_kaz_faith_mult value = 1 }}
    set_variable = {{ var = ktits_kaz_faith_gain value = 0 }}
    set_variable = {{ var = ktits_kaz_pop_k value = 0 }}
    set_variable = {{ var = ktits_kaz_reform value = 0 }}
    set_variable = {{ var = ktits_kaz_cn value = 0 }}
"""
for key, nm, _d, _e, price, cd in GIFTS:
    start += f"    set_variable = {{ var = ktits_kaz_c_{key} value = {price} }}\n"
start += """    ktits_kaz_templates = yes
    add_ideas = ktits_durmanische
    add_ideas = ktits_kaz_britt_influence
    add_ideas = ktits_eco_casual_society
    add_ideas = disarmed_nation
    ktits_kaz_inner_update = yes
"""
for sid in swamp_ids:
    start += f"    {sid} = {{ add_core_of = PREV }}\n"
start += "}\n\n"
start += """ktits_kaz_templates = {
    division_template = {
        name = "Болотное ополчение"
        regiments = {
            infantry = { x = 0 y = 0 }
            infantry = { x = 0 y = 1 }
            infantry = { x = 1 y = 0 }
            infantry = { x = 1 y = 1 }
        }
    }
    division_template = {
        name = "Казуальная гвардия"
        regiments = {
            infantry = { x = 0 y = 0 }
            infantry = { x = 0 y = 1 }
            infantry = { x = 0 y = 2 }
            infantry = { x = 1 y = 0 }
            infantry = { x = 1 y = 1 }
            infantry = { x = 1 y = 2 }
        }
    }
}

# scope = any country: the spirit "Дурманище" for countries ruled by the casuality ideology (docs/mechanics/Kazualia.md, section 1)
ktits_durm_check = {
    if = {
        limit = {
            has_government = casuality
            NOT = { has_idea = ktits_durmanische }
            NOT = { has_idea = ktits_durmanische_1 }
            NOT = { has_idea = ktits_durmanische_2 }
            NOT = { has_idea = ktits_durmanische_3 }
        }
        add_ideas = ktits_durmanische
    }
    if = {
        limit = { NOT = { has_government = casuality } }
""" + "".join(f"        if = {{ limit = {{ has_idea = {n} }} remove_ideas = {n} }}\n" for n, _a, _d in DURM) + """    }
}

# scope = Kazualia: monthly Faith gain = population of own core states (thousands) / 1000 x (0.5 + scale / 100) x multiplier; also called at the start so the gain is shown at once
ktits_kaz_faith_calc = {
    set_variable = { var = ktits_kaz_pop_k value = 0 }
    every_owned_state = {
        limit = { is_core_of = PREV }
        OWNER = { add_to_variable = { var = ktits_kaz_pop_k value = PREV.state_population_k } }
    }
    set_variable = { var = ktits_kaz_faith_gain value = ktits_kaz_pop_k }
    divide_variable = { var = ktits_kaz_faith_gain value = 1000 }
    set_temp_variable = { kz_m = ktits_kaz_inner }
    divide_temp_variable = { kz_m = 100 }
    add_to_temp_variable = { kz_m = 0.5 }
    multiply_variable = { var = ktits_kaz_faith_gain value = kz_m }
    multiply_variable = { var = ktits_kaz_faith_gain value = ktits_kaz_faith_mult }
    round_variable = ktits_kaz_faith_gain
}

# scope = Kazualia, every month: Casual Faith, reform decay, the news of puppets, the riot, the end of the reforms
ktits_kaz_monthly = {
    # Faith: 1 per 1 million of the population of own core states x (0.5 + scale / 100) x multiplier
    if = {
        limit = { NOT = { has_country_flag = ktits_kaz_industrial } }
        ktits_kaz_faith_calc = yes
        add_to_variable = { var = ktits_kaz_faith value = ktits_kaz_faith_gain }
        clamp_variable = { var = ktits_kaz_faith min = 0 max = 1000 }
    }
    # reform progress falls by 1 a month while the scale is >= 75 %
    if = {
        limit = {
            has_country_flag = ktits_kaz_reformist
            check_variable = { var = ktits_kaz_inner value = 75 compare = greater_than_or_equals }
            check_variable = { var = ktits_kaz_reform value = 0 compare = greater_than }
        }
        add_to_variable = { var = ktits_kaz_reform value = -1 }
    }
    # puppets that appeared: 365 days of waiting before "Принять в Ставку" (flag set when the monthly check sees the puppet first)
    every_subject_country = {
        limit = { NOT = { has_country_flag = ktits_kaz_accept_seen } }
        set_country_flag = ktits_kaz_accept_seen
        set_country_flag = { flag = ktits_kaz_accept_wait days = 365 value = 1 }
    }
    # "Болотный мятеж": reform progress 30..70, chance grows with the scale (INVENTED: 5 / 10 / 20 % a month), halved by the focus
    if = {
        limit = {
            has_country_flag = ktits_kaz_reformist
            NOT = { has_country_flag = ktits_kaz_industrial }
            NOT = { has_country_flag = ktits_kaz_riot_cd }
            check_variable = { var = ktits_kaz_reform value = 30 compare = greater_than_or_equals }
            check_variable = { var = ktits_kaz_reform value = 70 compare = less_than_or_equals }
        }
        if = {
            limit = { check_variable = { var = ktits_kaz_inner value = 75 compare = greater_than_or_equals } }
            ktits_kaz_riot_roll_hi = yes
        }
        else_if = {
            limit = { check_variable = { var = ktits_kaz_inner value = 50 compare = greater_than_or_equals } }
            ktits_kaz_riot_roll_mid = yes
        }
        else = { ktits_kaz_riot_roll_lo = yes }
    }
    if = {
        limit = {
            has_country_flag = ktits_kaz_reformist
            NOT = { has_country_flag = ktits_kaz_industrial }
            check_variable = { var = ktits_kaz_reform value = 100 compare = greater_than_or_equals }
        }
        country_event = { id = ktits_kazualia.4 }
    }
    ktits_kaz_inner_update = yes
}

ktits_kaz_riot_roll_hi = {
    if = { limit = { has_country_flag = ktits_kaz_f_riot_half } random_list = { 10 = { ktits_kaz_riot_fire = yes } 90 = { } } }
    else = { random_list = { 20 = { ktits_kaz_riot_fire = yes } 80 = { } } }
}
ktits_kaz_riot_roll_mid = {
    if = { limit = { has_country_flag = ktits_kaz_f_riot_half } random_list = { 5 = { ktits_kaz_riot_fire = yes } 95 = { } } }
    else = { random_list = { 10 = { ktits_kaz_riot_fire = yes } 90 = { } } }
}
ktits_kaz_riot_roll_lo = {
    if = { limit = { has_country_flag = ktits_kaz_f_riot_half } random_list = { 3 = { ktits_kaz_riot_fire = yes } 97 = { } } }
    else = { random_list = { 5 = { ktits_kaz_riot_fire = yes } 95 = { } } }
}
ktits_kaz_riot_fire = {
    set_country_flag = { flag = ktits_kaz_riot_cd days = 180 value = 1 }
    country_event = { id = ktits_kazualia.3 }
}

# scope = Kazualia: after a Faith purchase the cooldown flag (the flag name is passed by the decision itself)
"""
w("common/scripted_effects/ktits_kazualia_effects.txt", upd + "\n" + start + "\n" + rw_txt)
w("common/scripted_triggers/ktits_kazualia_triggers.txt", f"""# docs/mechanics/Kazualia.md. Generated by tools/make_kazualia.py
# Kazualia is a country of the "Казуальная Вера" economy (before the event "Индустриальное общество")
ktits_kaz_faith_economy = {{
    ktits_is_kazualia = yes
    NOT = {{ has_country_flag = ktits_kaz_industrial }}
}}
""")

# ================= decisions =================
dec = ""
cat = ("ktits_kaz_faith_category = {\n    icon = generic_propaganda\n    picture = GFX_decision_cat_picture_ktits_casuality\n    visible = {\n        ktits_kaz_faith_economy = yes\n    }\n}\n\n"
       "ktits_kaz_reform_category = {\n    icon = generic_propaganda\n    picture = GFX_decision_cat_picture_ktits_casuality\n    visible = {\n        ktits_is_kazualia = yes\n        has_country_flag = ktits_kaz_reformist\n    }\n}\n\n"
       "ktits_kaz_britt_category = {\n    icon = generic_propaganda\n    picture = GFX_decision_cat_picture_ktits_casuality\n    visible = {\n        ktits_is_kazualia = yes\n        OR = {\n            has_idea = ktits_kaz_britt_influence\n            has_idea = ktits_kaz_britt_2\n            has_idea = ktits_kaz_britt_3\n            has_idea = ktits_kaz_crown\n        }\n    }\n}\n\n"
       "ktits_kaz_accept_category = {\n    icon = generic_propaganda\n    picture = GFX_decision_cat_picture_ktits_casuality\n    visible = {\n        ktits_is_kazualia = yes\n        any_subject_country = { always = yes }\n    }\n}\n")
w("common/decisions/categories/ktits_kazualia_categories.txt", cat)
add("ktits_kaz_faith_category", "Экономическая Казуальность")
add("ktits_kaz_faith_category_desc", "§YКАЗУАЛЬНАЯ ВЕРА: [?ktits_kaz_faith|0]§! из 1000 (+[?ktits_kaz_faith_gain|0] в месяц)\\n§HЦвет решения — группа: §RАрмия§! §YСнаряжение§! §GЭкономика§! §BНаука§! §OПолитика§!§!\\nКазуалы не работают, но у них всё есть. Никто не знает, откуда. Казуалы и не спрашивают. Вера в то, что всё случится само: чем больше казуалов верят, тем чаще оно действительно случается. Внутренняя Казуальность: [?ktits_kaz_inner|0] %. [GetKtitsKazLate]")
add("ktits_kaz_reform_category", "Реформы")
add("ktits_kaz_reform_category_desc", "Переделать казуала в рабочего — всё равно что осушить болото чайной ложкой. Но ложки уже розданы. Прогресс реформ: [?ktits_kaz_reform|0] из 100. Сколько страны уже вытащено из трясины. Отпустишь — и она медленно сползёт обратно.")
add("ktits_kaz_britt_category", "Бриттанское влияние")
add("ktits_kaz_britt_category_desc", "Бриттанские клерки в котелках давно ходят по коридорам Ставки. Они ничего не требуют — только советуют. Советы почему-то всегда выполняются.")
add("ktits_kaz_accept_category", "Принять в Ставку")
add("ktits_kaz_accept_category_desc", "Ещё одна страна легла в болото и не захотела вставать. Ставка раскрывает объятия: места в тумане хватит всем.")
w("common/scripted_localisation/ktits_kazualia_loc.txt", "defined_text = {\n    name = GetKtitsKazLate\n    text = {\n        trigger = { check_variable = { var = ktits_kaz_inner value = 80 compare = greater_than } }\n        localization_key = ktits_kaz_late_hint_on\n    }\n    text = {\n        localization_key = ktits_kaz_late_hint_off\n    }\n}\n")
add("ktits_kaz_late_hint_on", "Опоздания: риск 50 %, 7–30 дней.")
add("ktits_kaz_late_hint_off", "")
ttl("ktits_kaz_late_tt", "Опаздывает: с шансом 50 % награда придёт через 7–30 дней", "Late: with a 50% chance the reward arrives in 7-30 days")
dec_n = [0]
def ev_late(kind_id):
    LATE_IDS.append(kind_id)
    return 100 + len(LATE_IDS)
def late_body(rw_key, rewards_inline):
    # decisions: delayed reward (same pattern as focuses)
    n = ev_late(rw_key)
    return (f"        if = {{\n            limit = {{ check_variable = {{ var = ktits_kaz_inner value = 80 compare = greater_than }} }}\n            random_list = {{\n"
            f"                50 = {{ ktits_kaz_rw_{rw_key} = yes }}\n"
            f"                50 = {{\n                    custom_effect_tooltip = ktits_kaz_late_tt\n                    hidden_effect = {{ country_event = {{ id = ktits_kazualia.{n} days = 7 random_days = 23 }} }}\n                }}\n"
            f"            }}\n        }}\n        else = {{ ktits_kaz_rw_{rw_key} = yes }}\n")
GIFT_RW = {
    "militia": divs("militia", 2), "guard": divs("guard", 1),
    "guns": "add_equipment_to_stockpile = { type = infantry_equipment_1 amount = 2000 }\n", "cannons": "add_equipment_to_stockpile = { type = artillery_equipment_1 amount = 200 }\n",
    "vision": "add_tech_bonus = { name = ktits_kaz_vision bonus = 1.0 uses = 1 category = infantry_weapons category = artillery category = support_tech }\n",   # [uncertain] categories of the tech bonus
    "trucks": "add_equipment_to_stockpile = { type = motorized_equipment_1 amount = 300 }\n",
    "support": "add_equipment_to_stockpile = { type = support_equipment_1 amount = 300 }\n",
    "atpvo": "add_equipment_to_stockpile = { type = anti_tank_equipment_1 amount = 150 }\nadd_equipment_to_stockpile = { type = anti_air_equipment_1 amount = 150 }\n",
    "peat": "add_fuel = 15000\nrandom_owned_controlled_state = { limit = { impassable = no } add_resource = { type = steel amount = 10 days = 365 } }\n",
    "built": civ(1), "grace": pp(100) + "add_timed_idea = { idea = ktits_kaz_grace_t days = 180 }\n", "mission": "",
}
rw2 = ""
GIFT_EV = []; GIFT_EV_BASE = 500      # a news event per decision "Дары болот": ktits_kazualia.501 ...
# what exactly was received (shown in the event; docs/mechanics/Kazualia.md section 4)
GIFT_GOT = {
    "militia": "В столице: 2 дивизии «Болотное ополчение».", "guard": "В столице: 1 дивизия «Казуальная гвардия».",
    "guns": "На складе: +2000 пехотного снаряжения.", "cannons": "На складе: +200 артиллерии.",
    "vision": "Скидка 100 % на одну исследуемую технологию.", "built": "+1 гражданская фабрика в одном из штатов.",
    "grace": "+100 политической власти; стабильность +5 % на 180 дней.", "trucks": "На складе: +300 грузовиков.",
    "support": "На складе: +300 единиц вспомогательной техники.", "atpvo": "На складе: +150 ПТ-орудий и +150 зенитных орудий.",
    "peat": "+15 000 топлива; +10 стали в одном из штатов на 365 дней.",
}
decision_loc = []
dec = "ktits_kaz_faith_category = {\n\n"
for key, nm, lore, eff, price, cd in GIFTS:
    did = f"ktits_kaz_gift_{key}"
    cdf = f"ktits_kaz_cd_{key}"
    gc, gru, gen, gicon = GRP[GIFT_GRP[key]]
    add(did, f"{gc}{gru}:§! {nm}", f"{gc}{gen}:§! {L.translit(nm)}"); add(did + "_desc", f"{lore} ({eff}; цена — Казуальная Вера: {price}, перезарядка {cd} дн.)")
    add(f"ktits_kaz_need_{key}", f"Казуальной Веры достаточно: нужно §Y[?ktits_kaz_c_{key}|0]§!, есть [?ktits_kaz_faith|0]", f"Enough Casual Faith: §Y[?ktits_kaz_c_{key}|0]§! needed, [?ktits_kaz_faith|0] available")
    fast = round(cd * 0.75)
    cost_pay = f"        subtract_from_variable = {{ var = ktits_kaz_faith value = ktits_kaz_c_{key} }}\n"
    cooldown = (f"        if = {{\n            limit = {{ has_country_flag = ktits_kaz_cd_fast }}\n            set_country_flag = {{ flag = {cdf} days = {fast} value = 1 }}\n        }}\n"
                f"        else = {{\n            set_country_flag = {{ flag = {cdf} days = {cd} value = 1 }}\n        }}\n")
    if key == "mission":
        continue                       # the decision itself (category Внешняя Казуальность) is written by make_kazualia_outer.py
    GIFT_EV.append(key)
    rw2 += f"ktits_kaz_rw_{key} = {{\n" + "".join("    " + l + "\n" for l in GIFT_RW[key].splitlines()) + f"    country_event = {{ id = ktits_kazualia.{GIFT_EV_BASE + len(GIFT_EV)} }}\n" + "}\n\n"
    dec += T(f"""    {did} = {{
        icon = {GIFT_ICON.get(key, gicon)}
        visible = {{
            ktits_kaz_faith_economy = yes
        }}
        available = {{
            NOT = {{ has_country_flag = {cdf} }}
            custom_trigger_tooltip = {{
                tooltip = ktits_kaz_need_{key}
                check_variable = {{ var = ktits_kaz_faith value = ktits_kaz_c_{key} compare = greater_than_or_equals }}
            }}
        }}
        fire_only_once = no
        complete_effect = {{
{cost_pay}{cooldown}{late_body(key, None)}        }}
        ai_will_do = {{ base = 1 }}
    }}

""")
dec += "}\n\n"
# reforms
dec += "ktits_kaz_reform_category = {\n\n"
for key, nm, lore, pr, din, ppc, eff in REFORMS:
    did = f"ktits_kaz_ref_{key}"
    add(did, nm); add(did + "_desc", f"{lore} ({eff}; {ppc} ПВ, стабильность −3 % на 90 дней)")
    extra = ""
    if key == "drain": extra = swamp_slots(1, 2)
    if key == "workday": extra = "add_timed_idea = { idea = ktits_kaz_resist5_t days = 90 }\n"
    if key == "schools": extra = spec(5)
    if key == "horn": extra = civ(1)
    body = reform(pr) + inner(din) + f"add_political_power = -{ppc}\n" + "add_timed_idea = { idea = ktits_kaz_resist_t days = 90 }\n" + extra
    dec += T(f"""    {did} = {{
        icon = generic_propaganda
        visible = {{
            has_country_flag = ktits_kaz_reformist
            NOT = {{ has_country_flag = ktits_kaz_industrial }}
        }}
        available = {{
            NOT = {{ has_country_flag = ktits_kaz_rcd_{key} }}
        }}
        cost = {ppc}
        fire_only_once = no
        complete_effect = {{
            set_country_flag = {{ flag = ktits_kaz_rcd_{key} days = 90 value = 1 }}
{"".join("            " + l + chr(10) for l in (body.replace(f"add_political_power = -{ppc}" + chr(10), "")).splitlines())}        }}
        ai_will_do = {{ base = 2 }}
    }}

""")
dec += "}\n\n"
# British influence: expel the clerks; accept into Stavka
dec += "ktits_kaz_britt_category = {\n\n"
add("ktits_kaz_expel", "Выгнать клерков")
add("ktits_kaz_expel_desc", "Котелки летят в болото, клерки бегут к пароходу. Ставка снова принадлежит казуалам — и долги, кажется, тоже.")
dec += T(f"""    ktits_kaz_expel = {{
        icon = generic_propaganda
        visible = {{
            ktits_is_kazualia = yes
            NOT = {{ has_idea = ktits_kaz_crown }}
        }}
        available = {{
            is_subject = no
        }}
        cost = 0
        fire_only_once = yes
        complete_effect = {{
            set_country_flag = ktits_kaz_expelled
            if = {{ limit = {{ has_idea = ktits_kaz_britt_influence }} remove_ideas = ktits_kaz_britt_influence }}
            if = {{ limit = {{ has_idea = ktits_kaz_britt_2 }} remove_ideas = ktits_kaz_britt_2 }}
            if = {{ limit = {{ has_idea = ktits_kaz_britt_3 }} remove_ideas = ktits_kaz_britt_3 }}
            {BRT} = {{ add_opinion_modifier = {{ target = ROOT modifier = ktits_kaz_britt_expel }} }}
            ROOT = {{ add_opinion_modifier = {{ target = {BRT} modifier = ktits_kaz_britt_expel }} }}
        }}
        # AI on the Great Casuality path: expels the clerks when the British influence stops paying off
        # (after 'Курс на материк', or spirit level 2+ and a war with an ally of Britain)
        ai_will_do = {{
            base = 0
            modifier = {{ add = 100 has_completed_focus = ktits_kaz_g_root }}
            modifier = {{
                add = 100
                has_completed_focus = ktits_kaz_g_power
                OR = {{ has_idea = ktits_kaz_britt_2 has_idea = ktits_kaz_britt_3 }}
                {BRT} = {{ any_allied_country = {{ has_war_with = ROOT }} }}
            }}
        }}
    }}
}}

ktits_kaz_accept_category = {{

    ktits_kaz_accept = {{
        icon = generic_propaganda
        visible = {{
            ktits_is_kazualia = yes
        }}
        target_root_trigger = {{
            ktits_is_kazualia = yes
        }}
        target_trigger = {{
            FROM = {{
                is_subject_of = ROOT
                NOT = {{ has_country_flag = ktits_kaz_accept_wait }}
            }}
        }}
        available = {{
            check_variable = {{ var = ktits_kaz_inner value = 50 compare = greater_than_or_equals }}
            FROM = {{
                NOT = {{ has_war_with = ROOT }}
                custom_trigger_tooltip = {{
                    tooltip = ktits_kaz_tt_accept_alone
                    NOT = {{ any_country = {{ has_war_with = PREV is_subject_of = ROOT }} }}
                }}
            }}
        }}
        cost = 100
        fire_only_once = no
        complete_effect = {{
            if = {{ limit = {{ has_country_flag = ktits_kaz_f_accept_cheap }} add_political_power = 50 }}
            FROM = {{ every_owned_state = {{ add_core_of = {KAZ} }} }}
            annex_country = {{ target = FROM transfer_troops = yes }}
            add_to_variable = {{ var = ktits_kaz_inner value = 5 }}
            ktits_kaz_inner_update = yes
        }}
        ai_will_do = {{
            base = 0
            modifier = {{ add = 5 has_country_flag = ktits_kaz_great }}
        }}
    }}
}}
""")
add("ktits_kaz_accept", "Принять в Ставку")
add("ktits_kaz_accept_desc", "Ещё одна страна легла в болото и не захотела вставать. Ставка раскрывает объятия: места в тумане хватит всем. (100 ПВ; марионетка не воюет отдельно, прошло 365 дней; Внутренняя Казуальность не ниже 50 %, после присоединения +5 %; земли марионетки становятся ядром Казуалии)")
add("ktits_kaz_tt_accept_alone", "Марионетка не воюет отдельно от Казуалии")
w("common/decisions/ktits_kazualia_decisions.txt", dec)
w("common/scripted_effects/ktits_kazualia_gift_effects.txt", "# generated by tools/make_kazualia.py: rewards of the decisions Дары болот (delayed through hidden events when the scale is above 80 %)\n" + rw2)

# ================= events =================
ev = "add_namespace = ktits_kazualia\n\n"
ev += T(f"""# the start event of Kazualia (docs/mechanics/Kazualia.md, section 7)
country_event = {{
    id = ktits_kazualia.1
    title = ktits_kazualia.1.t
    desc = ktits_kazualia.1.d
    picture = {PIC}
    is_triggered_only = yes
    fire_only_once = yes

    option = {{
        name = ktits_kazualia.1.a
    }}
}}

# news: a delayed reward has arrived
country_event = {{
    id = ktits_kazualia.2
    title = ktits_kazualia.2.t
    desc = ktits_kazualia.2.d
    picture = {PIC}
    is_triggered_only = yes
    fire_only_once = no

    option = {{
        name = ktits_kazualia.2.a
    }}
}}

# "Болотный мятеж" (effect INVENTED: stability -5 % for 90 days; the civil war of section 6 is not implemented)
country_event = {{
    id = ktits_kazualia.3
    title = ktits_kazualia.3.t
    desc = ktits_kazualia.3.d
    picture = {PIC}
    is_triggered_only = yes
    fire_only_once = no

    option = {{
        name = ktits_kazualia.3.a
        add_timed_idea = {{ idea = ktits_kaz_resist5_t days = 90 }}
    }}
}}

# "Индустриальное общество": the end of the swamp economy (section 5.1)
country_event = {{
    id = ktits_kazualia.4
    title = ktits_kazualia.4.t
    desc = ktits_kazualia.4.d
    picture = {PIC}
    is_triggered_only = yes
    fire_only_once = yes

    option = {{
        name = ktits_kazualia.4.a
        set_country_flag = ktits_kaz_industrial
        set_variable = {{ var = ktits_kaz_inner value = 0 }}
        set_variable = {{ var = ktits_kaz_faith value = 0 }}
        set_variable = {{ var = ktits_kaz_faith_gain value = 0 }}
        if = {{ limit = {{ has_dynamic_modifier = {{ modifier = ktits_kaz_inner_dm }} }} remove_dynamic_modifier = {{ modifier = ktits_kaz_inner_dm }} }}
""" + "".join(f"        if = {{ limit = {{ has_idea = {n} }} remove_ideas = {n} }}\n" for n, _a, _d in DURM) + """        set_variable = { var = ktits_casuality value = 25 }
        # from now on the scale of the other countries works for Kazualia too (ktits_is_kazualia is false after the flag ktits_kaz_industrial)
        ktits_casuality_costs = yes
        ktits_casuality_ai_start = yes
        ktits_casuality_update = yes
    }
}

""")
add("ktits_kazualia.1.t", "Утро в Ставке")
add("ktits_kazualia.1.d", "Над болотами встаёт солнце, но в Ставке Казуала никто не спешит просыпаться. Тридцать миллионов казуалов живут среди трясин и туманов, не зная ни заводов, ни школ, — и не чувствуют в этом нужды: всё, что нужно, рано или поздно появляется само. Священный-Архо-Казуал дремлет на троне, горы стерегут столицу с трёх сторон, а бриттанские клерки в котелках уже ждут в приёмной. Соседи боятся болотного дурмана и тянущейся из-за границы лени. Куда пойдёт Казуалия — дальше в туман, к заводскому гудку или под чужие знамёна, — решит тот, кто первым проснётся.")
add("ktits_kazualia.1.a", "Ещё пять минут…")
add("ktits_kazualia.2.t", "Наконец-то!")
add("ktits_kazualia.2.d", "Запыхавшийся гонец стоит в дверях Ставки. Он даже не извиняется: в Казуалии все опаздывают, и он уверен, что пришёл вовремя.")
add("ktits_kazualia.2.a", "Дошёл — и ладно")
add("ktits_kazualia.3.t", "Болотный мятеж")
add("ktits_kazualia.3.d", "Старые казуалы вышли из камышей с плакатами «Верните покой!». Их много, они злы и, что хуже всего, впервые за век торопятся.")
add("ktits_kazualia.3.a", "Только бы не проснулись совсем")
add("ktits_kazualia.4.t", "Индустриальное общество")
add("ktits_kazualia.4.d", "Гудок над болотом больше никого не удивляет. Туман рассеялся, казуалы ходят на смену, а о Священном-Архо-Казуале вспоминают только в анекдотах. Страна проснулась.")
add("ktits_kazualia.4.a", "Страна проснулась")
# hidden delayed events, one per delayed focus / decision
ev += T("""# the overlord of Kazualia (focus «Обещанная независимость»): give independence or refuse; ROOT = the overlord, FROM = Kazualia
country_event = {
    id = ktits_kazualia.5
    title = ktits_kazualia.5.t
    desc = ktits_kazualia.5.d
    picture = """ + PIC + """
    is_triggered_only = yes
    fire_only_once = no

    option = {
        name = ktits_kazualia.5.a
        ai_chance = { base = 30 }
        end_puppet = FROM
    }
    option = {
        name = ktits_kazualia.5.b
        ai_chance = { base = 70 }
        FROM = {
            add_opinion_modifier = { target = ROOT modifier = ktits_kaz_refused }
            add_to_variable = { var = ktits_kaz_inner value = 20 }
            ktits_kaz_inner_update = yes
        }
    }
}

""")
add("ktits_kazualia.5.t", "Казуальная просьба")
add("ktits_kazualia.5.d", "Казуальный посол пришёл не вовремя, зато с ворохом бумаг. В бумагах сказано, что хозяин когда-то обещал независимость. Посол вежливо напоминает и устраивается на ковре подождать ответа. Он никуда не торопится.")
add("ktits_kazualia.5.a", "Обещание есть обещание")
add("ktits_kazualia.5.b", "Передайте послу, что мы подумаем (лет сто)")
for n, rk in enumerate(LATE_IDS, 1):
    ev += T(f"""country_event = {{
    id = ktits_kazualia.{100 + n}
    hidden = yes
    is_triggered_only = yes
    fire_only_once = no

    immediate = {{
        ktits_kaz_rw_{rk} = yes
        country_event = {{ id = ktits_kazualia.2 }}
    }}
}}

""")
for n, gk in enumerate(GIFT_EV, 1):
    gnm, glore = next((g[1], g[2]) for g in GIFTS if g[0] == gk)
    eid = GIFT_EV_BASE + n
    ev += T(f"""# news: the gift "{gnm}" has arrived
country_event = {{
    id = ktits_kazualia.{eid}
    title = ktits_kazualia.{eid}.t
    desc = ktits_kazualia.{eid}.d
    picture = {PIC}
    is_triggered_only = yes
    fire_only_once = no

    option = {{
        name = ktits_kazualia.{eid}.a
    }}
}}

""")
    add(f"ktits_kazualia.{eid}.t", gnm)
    add(f"ktits_kazualia.{eid}.d", f"{glore}\\n\\n§YПолучено:§! {GIFT_GOT[gk]}", f"{L.translit(glore)}\\n\\n§YReceived:§! {L.translit(GIFT_GOT[gk])}")
    add(f"ktits_kazualia.{eid}.a", "Само пришло", "It came by itself")
w("events/ktits_kazualia_events.txt", "﻿" + ev)

# ================= on_actions, opinion modifiers =================
w("common/on_actions/ktits_kazualia_on_actions.txt", """on_actions = {
    on_startup = {
        effect = {
            every_country = {
                limit = { ktits_is_kazualia = yes }
                ktits_kaz_start = yes
                country_event = { id = ktits_kazualia.1 }
            }
        }
    }
    on_monthly = {
        effect = {
            ktits_durm_check = yes
            if = {
                limit = { ktits_is_kazualia = yes }
                ktits_kaz_monthly = yes
            }
        }
    }
}
""")
w("common/opinion_modifiers/ktits_kazualia_opinion.txt", """opinion_modifiers = {
    ktits_kaz_britt_friend = { value = 25 months = 24 }
    ktits_kaz_britt_expel = { value = -50 months = 60 }
    ktits_kaz_comm_help = { value = 25 months = 24 }
    ktits_kaz_obey = { value = 50 months = 60 }
    ktits_kaz_refused = { value = -100 months = 60 }
}
""")
for k_, r_ in [("ktits_kaz_britt_friend", "Бриттанские друзья"), ("ktits_kaz_britt_expel", "Клерков выгнали"), ("ktits_kaz_comm_help", "Помощь братских стран"), ("ktits_kaz_obey", "Верная покорность")]:
    add(k_, r_)
for k_, v_ in [("ktits_kaz_tt_choose", ("Открывает выбор пути: Вечный сон (Казуальный путь: Нейтралитет или Великая Казуалия), Заводской гудок (Реформистский) или Красное болото (Коммунистический)", None)), ("ktits_kaz_tt_serve", ("Верная служба", None))]:
    ttl(k_, v_[0])
for k_, (r_, e_) in TT.items():
    ru.append((k_, r_)); en.append((k_, e_))
L.write_yml(str(M / "localisation/russian/ktits_kazualia_l_russian.yml"), "russian", ru)
L.write_yml(str(M / "localisation/english/ktits_kazualia_l_english.yml"), "english", en)
print(f"kazualia: {len(F)} focuses, {len(LATE_IDS)} delayed rewards, {len(ru)} loc keys; cores on {len(swamp_ids)} states of Наши Болота")
