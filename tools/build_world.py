"""Штаты, стратрегионы, страны, здания, снабжение, локализация.

Вход: no_commit/temp/provinces.json, prov.npy, height.npy (их делает tools/build_map.py).
Запуск из корня репозитория: python tools/build_world.py
"""
import json, os, re, shutil
from collections import deque, defaultdict
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = r"D:/SteamLibrary/steamapps/common/Hearts of Iron IV"
TMP = os.path.join(ROOT, "no_commit", "temp")
rng = np.random.default_rng(1936)

D = json.load(open(os.path.join(TMP, "provinces.json")))
W, H = D["W"], D["H"]
P = {int(k): v for k, v in D["prov"].items()}
prov = np.load(os.path.join(TMP, "prov.npy"))
hm = np.load(os.path.join(TMP, "height.npy"))
SX, SY = W / 1600, H / 1040

# --- страны: тег -> (название, прилагательное, цвет, столица (x,y по схеме), имя столицы, штатов, население млн)
C = {
 "CSL": ("Казуалия", "казуальский", (195, 207, 132), (1112, 498), "Ставка Казуала", 5, 30),
 "SVS": ("Советский Союз", "советский", (224, 122, 116), (862, 400), "Ваньград-на-Окре", 40, 120),
 "KZZ": ("Казачья Земля", "казачий", (239, 159, 79), (816, 515), "Станица Дарьевская", 4, 10),
 "BRT": ("Бриттан", "бриттский", (183, 154, 208), (140, 445), "Большой Джон", 6, 70),
 "ICL": ("Айцланд", "айцландский", (205, 184, 224), (50, 290), "Рейкьяборо", 2, 1),
 "IRK": ("Иракиккистан", "иракиккистанский", (155, 127, 196), (930, 742), "Лахарабад", 7, 125),
 "IRR": ("Ирракия", "ирракийский", (198, 163, 224), (1090, 722), "Дехлагарх", 22, 350),
 "MUS": ("Королевство Муси", "мусийский", (120, 199, 160), (1228, 718), "Мандалаят", 13, 70),
 "TRV": ("Травинная Федерация", "травинный", (143, 209, 138), (1130, 990), "Травопорт", 7, 100),
 "TMR": ("Тямовский рейх", "тямовский", (125, 125, 125), (540, 410), "Барбинсберг", 9, 5),
 "SOY": ("Соевая Республика", "соевый", (127, 167, 224), (340, 540), "Поридж-Сити", 8, 5),
 "ZLD": ("Демократический Зеленодольск", "зеленодольский", (95, 192, 200), (330, 352), "Мирный", 2, 5),
 "ADL": ("Айдалия", "айдалийский", (240, 216, 106), (500, 566), "Бернхорн", 2, 5),
 "SVA": ("Северная Ассамблея", "северный", (142, 160, 232), (490, 232), "Ослорвик", 9, 5),
 "FDP": ("Федерация Депутатов", "депутатский", (230, 184, 78), (705, 405), "Депутатск", 5, 5),
 "DMK": ("Дмитровское Княжество", "дмитровский", (217, 138, 163), (850, 730), "Ордабад", 9, 5),
 "CLB": ("Челяба", "челябинский", (169, 184, 201), (975, 412), "Челябинск", 11, 5),
 "MGN": ("Магнолия", "магнольский", (236, 217, 160), (1240, 530), "Улан-Батыр", 17, 5),
 "KTY": ("Кытай", "кытайский", (201, 116, 74), (1490, 380), "Бэйчжао", 28, 5),
 "BLK": ("Чёрная Республика", "чёрный", (85, 90, 110), (1426, 788), "Токомэ", 5, 100),
 "SRK": ("Сарайкумское Ханство", "сарайкумский", (184, 167, 106), (1100, 603), "Кумыс-Орда", 11, 40),
 "Z01": ("Заготовка страны 1", "заготовочный", (201, 201, 232), None, "Столица заготовки 1", 1, 2),
 "Z02": ("Заготовка страны 2", "заготовочный", (183, 211, 232), None, "Столица заготовки 2", 1, 2),
 "Z03": ("Заготовка страны 3", "заготовочный", (232, 201, 216), None, "Столица заготовки 3", 1, 2),
 "Z04": ("Заготовка страны 4", "заготовочный", (214, 232, 201), None, "Столица заготовки 4", 1, 2),
 "Z05": ("Заготовка страны 5", "заготовочный", (217, 201, 232), None, "Столица заготовки 5", 1, 2),
}
PUPPETS = {"BRT": ["ICL", "IRK", "IRR"]}

def w(path, text, bom=False, crlf=False):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8-sig" if bom else "utf-8", newline="\r\n" if crlf else "\n") as f:
        f.write(text)

# --- представительная точка провинции (пиксель ближе всего к центроиду)
flat = prov.ravel()
order = np.argsort(flat, kind="stable")
bounds = np.searchsorted(flat[order], np.arange(1, len(P) + 2))
REP = {}
for i in P:
    idx = order[bounds[i - 1]:bounds[i]]
    ys, xs = idx // W, idx % W
    k = np.argmin((xs - P[i]["x"]) ** 2 + (ys - P[i]["y"]) ** 2)
    REP[i] = (int(xs[k]), int(ys[k]))
def xyz(i, dx=0, dy=0):
    x, y = REP[i]; x += dx; y += dy
    x = min(max(x, 0), W - 1); y = min(max(y, 0), H - 1)
    return f"{x:.2f};{hm[y, x] / 10:.2f};{H - y:.2f}"

land = {t: [i for i, v in P.items() if v["tag"] == t] for t in C}
ADJ = {i: set(v["adj"]) for i, v in P.items()}

# --- штаты: k-means по центрам + связность
def kmeans(ids, k):
    pts = np.array([[P[i]["x"], P[i]["y"]] for i in ids])
    k = min(k, len(ids))
    cen = pts[rng.choice(len(ids), k, replace=False)]
    for _ in range(25):
        lab = ((pts[:, None] - cen[None]) ** 2).sum(-1).argmin(1)
        for j in range(k):
            if (lab == j).any(): cen[j] = pts[lab == j].mean(0)
    return {i: int(l) for i, l in zip(ids, lab)}
def fix_conn(ids, lab):
    """Каждый кластер связный: лишние компоненты отдать соседнему кластеру."""
    s = set(ids)
    for _ in range(20):
        moved = False
        groups = defaultdict(list)
        for i in ids: groups[lab[i]].append(i)
        for g, mem in groups.items():
            ms = set(mem); seen = set(); comps = []
            for st in mem:
                if st in seen: continue
                q = deque([st]); seen.add(st); cc = [st]
                while q:
                    u = q.popleft()
                    for v in ADJ[u]:
                        if v in ms and v not in seen: seen.add(v); q.append(v); cc.append(v)
                comps.append(cc)
            comps.sort(key=len, reverse=True)
            for cc in comps[1:]:
                nb = [lab[v] for u in cc for v in ADJ[u] if v in s and lab[v] != g]
                if nb:
                    ng = max(set(nb), key=nb.count)
                    for u in cc: lab[u] = ng
                    moved = True
        if not moved: break
    return lab

states = []          # dict(tag, provs)
for t, ids in land.items():
    k = C[t][5]
    lab = fix_conn(ids, kmeans(ids, k)) if k > 1 else {i: 0 for i in ids}
    g = defaultdict(list)
    for i in ids: g[lab[i]].append(i)
    for mem in g.values(): states.append({"tag": t, "provs": sorted(mem)})
states.sort(key=lambda s: (list(C).index(s["tag"]), min(s["provs"])))
SOF = {}
for sid, s in enumerate(states, 1):
    s["id"] = sid
    for i in s["provs"]: SOF[i] = sid

def nearest_prov(t, pt):
    x, y = pt[0] * SX, pt[1] * SY
    return min(land[t], key=lambda i: (P[i]["x"] - x) ** 2 + (P[i]["y"] - y) ** 2)
CAPP = {}
for t, c in C.items():
    if c[3]: CAPP[t] = nearest_prov(t, c[3])
    else:
        mx = np.mean([P[i]["x"] for i in land[t]]); my = np.mean([P[i]["y"] for i in land[t]])
        CAPP[t] = min(land[t], key=lambda i: (P[i]["x"] - mx) ** 2 + (P[i]["y"] - my) ** 2)
CAPS = {t: SOF[p] for t, p in CAPP.items()}

def center_prov(s):
    mx = np.mean([P[i]["x"] for i in s["provs"]]); my = np.mean([P[i]["y"] for i in s["provs"]])
    return min(s["provs"], key=lambda i: (P[i]["x"] - mx) ** 2 + (P[i]["y"] - my) ** 2)
for s in states:
    s["main"] = CAPP[s["tag"]] if CAPS[s["tag"]] == s["id"] else center_prov(s)

# --- history/states + локализация штатов
loc_states = []
for f in os.listdir(os.path.join(ROOT, "history", "states")) if os.path.isdir(os.path.join(ROOT, "history", "states")) else []:
    os.remove(os.path.join(ROOT, "history", "states", f))
nst = defaultdict(int)
for t in C: nst[t] = sum(1 for s in states if s["tag"] == t)
cnt = defaultdict(int)
for s in states:
    t = s["tag"]; cnt[t] += 1
    cap = CAPS[t] == s["id"]
    man = int(C[t][6] * 1_000_000 / nst[t])
    cat = "city" if cap else ("rural" if not t.startswith("Z") else "town")
    vp = f"\t\tvictory_points = {{ {s['main']} {15 if cap else 1} }}\n"
    txt = (f"state = {{\n\tid = {s['id']}\n\tname = \"STATE_{s['id']}\"\n\tmanpower = {man}\n"
           f"\tstate_category = {cat}\n\tprovinces = {{ {' '.join(map(str, s['provs']))} }}\n"
           f"\thistory = {{\n\t\towner = {t}\n\t\tadd_core_of = {t}\n{vp}"
           f"\t\tbuildings = {{\n\t\t\tinfrastructure = 2\n" + ("\t\t\tindustrial_complex = 2\n\t\t\tarms_factory = 1\n" if cap else "") +
           "\t\t}\n\t}\n}\n")
    w(f"history/states/{s['id']}-{t}.txt", txt)
    nm = C[t][4] if cap else f"{C[t][0]}, область {cnt[t]}"
    loc_states.append(f' STATE_{s["id"]}:0 "{nm}"')
    loc_states.append(f' VICTORY_POINTS_{s["main"]}:0 "{C[t][4] if cap else nm}"')

# --- стратегические регионы
def vblock(name):
    src = open(os.path.join(GAME, "map", "strategicregions", name), encoding="utf-8-sig").read()
    i = src.index("weather")
    j = src.index("{", i); d = 0
    for k in range(j, len(src)):
        d += src[k] == "{"; d -= src[k] == "}"
        if d == 0: return src[i:k + 1]
    raise ValueError(name)
WEATHER = {"cold": vblock("10-Southern Sweden.txt"), "temp": vblock("1-Southern England.txt"),
           "desert": vblock("127-Saharadesert.txt"), "trop": vblock("153-Northern India.txt"),
           "sea": vblock("16-North Sea.txt")}
def climate(t, y):
    if t in ("MGN", "SRK"): return "desert"
    if t in ("IRR", "IRK", "MUS", "TRV", "BLK"): return "trop"
    return "cold" if y < 300 * SY else "temp"
regions = []
for t in C:
    sts = [s for s in states if s["tag"] == t]
    k = max(1, round(len(sts) / 5))
    if k == 1: groups = [sts]
    else:
        ids = [s["id"] for s in sts]
        cen = {s["id"]: P[s["main"]] for s in sts}
        pts = np.array([[cen[i]["x"], cen[i]["y"]] for i in ids])
        c0 = pts[rng.choice(len(ids), k, replace=False)]
        for _ in range(20):
            lab = ((pts[:, None] - c0[None]) ** 2).sum(-1).argmin(1)
            for j in range(k):
                if (lab == j).any(): c0[j] = pts[lab == j].mean(0)
        groups = [[s for s, l in zip(sts, lab) if l == j] for j in range(k)]
        groups = [g for g in groups if g]
    for g in groups:
        pv = [i for s in g for i in s["provs"]]
        regions.append({"provs": pv, "clim": climate(t, np.mean([P[i]["y"] for i in pv])), "naval": None})
ROF = {}
for rid, r in enumerate(regions, 1):
    for i in r["provs"]: ROF[i] = rid
# озёра -> регион соседней суши
lakes = [i for i, v in P.items() if v["type"] == "lake"]
pending = lakes[:]
for _ in range(50):
    nxt = []
    for i in pending:
        nb = [ROF[j] for j in ADJ[i] if j in ROF]
        if nb: ROF[i] = max(set(nb), key=nb.count); regions[ROF[i] - 1]["provs"].append(i)
        else: nxt.append(i)
    pending = nxt
    if not pending: break
# моря: кластеры ~18 провинций
seas = [i for i, v in P.items() if v["type"] == "sea"]
k = max(1, len(seas) // 18)
lab = fix_conn(seas, kmeans(seas, k))
g = defaultdict(list)
for i in seas: g[lab[i]].append(i)
for mem in g.values():
    regions.append({"provs": mem, "clim": "sea", "naval": "water_shallow_sea"})
    for i in mem: ROF[i] = len(regions)
sr_dir = os.path.join(ROOT, "map", "strategicregions")
shutil.rmtree(sr_dir, ignore_errors=True)
loc_sr = []
for rid, r in enumerate(regions, 1):
    nav = f"\tnaval_terrain={r['naval']}\n" if r["naval"] else ""
    w(f"map/strategicregions/{rid}-region.txt",
      f"strategic_region={{\n\tid={rid}\n\tname=\"STRATEGICREGION_{rid}\"\n\tprovinces={{\n\t\t{' '.join(map(str, sorted(r['provs'])))}\n\t}}\n{nav}\t{WEATHER[r['clim']]}\n}}\n")
    loc_sr.append(f' STRATEGICREGION_{rid}:0 "Регион {rid}"')
assert len(ROF) == len(P), (len(ROF), len(P))

# --- страны
tags_txt = "".join(f'{t}\t= "countries/{t}.txt"\n' for t in C)
w("common/country_tags/00_countries.txt", tags_txt)
shutil.copy(os.path.join(GAME, "common", "country_tags", "zz_dynamic_countries.txt"),
            os.path.join(ROOT, "common", "country_tags", "zz_dynamic_countries.txt"))
hc = os.path.join(ROOT, "history", "countries"); shutil.rmtree(hc, ignore_errors=True)
for t, c in C.items():
    w(f"common/countries/{t}.txt", f"graphical_culture = western_european_gfx\ngraphical_culture_2d = western_european_2d\n\ncolor = {{ {c[2][0]} {c[2][1]} {c[2][2]} }}\n")
    extra = ""
    for p in PUPPETS.get(t, []):
        extra += f"set_autonomy = {{\n\ttarget = {p}\n\tautonomous_state = autonomy_puppet\n}}\n"
    w(f"history/countries/{t} - {t}.txt",
      f"capital = {CAPS[t]}\noob = \"{t}_1936\"\n"
      "set_politics = {\n\truling_party = neutrality\n\tlast_election = \"1932.1.1\"\n\telection_frequency = 48\n\telections_allowed = no\n}\n"
      "set_popularities = {\n\tdemocratic = 0\n\tfascism = 0\n\tcommunism = 0\n\tneutrality = 100\n}\n"
      "set_stability = 0.5\nset_war_support = 0.2\n" + extra)
    w(f"history/units/{t}_1936.txt", "division_template = {\n\tname = \"Пехотная дивизия\"\n\tregiments = {\n\t\tinfantry = { x = 0 y = 0 }\n\t\tinfantry = { x = 0 y = 1 }\n\t}\n}\nunits = {\n\tdivision = {\n\t\tlocation = %d\n\t\tdivision_template = \"Пехотная дивизия\"\n\t\tstart_experience_factor = 0.1\n\t}\n}\n" % CAPP[t])

# --- закладка
majors = ["SVS", "BRT", "TMR", "SOY", "KTY", "CSL"]
w("common/bookmarks/kazual_1936.txt",
  "bookmarks = {\n\tbookmark = {\n\t\tname = \"KAZUAL_BOOKMARK_NAME\"\n\t\tdesc = \"KAZUAL_BOOKMARK_DESC\"\n\t\tdate = 1936.1.1.12\n"
  "\t\tpicture = \"GFX_select_date_1936\"\n\t\tdefault_country = \"CSL\"\n\t\tdefault = yes\n"
  + "".join(f"\t\t\"{t}\" = {{\n\t\t\thistory = \"KAZUAL_{t}_DESC\"\n\t\t\tideology = neutrality\n\t\t\tideas = {{ }}\n\t\t\tfocuses = {{ }}\n\t\t}}\n" for t in majors)
  + "\t\t\"---\" = {\n\t\t\thistory = \"OTHER_GATHERING_STORM_DESC\"\n\t\t}\n\t\teffect = {\n\t\t\trandomize_weather = 22345\n\t\t}\n\t}\n}\n")

# --- локализация (UTF-8 с BOM)
loc = ["l_russian:"]
for t, c in C.items():
    loc += [f' {t}:0 "{c[0]}"', f' {t}_DEF:0 "{c[0]}"', f' {t}_ADJ:0 "{c[1]}"']
    for ide in ("neutrality", "democratic", "fascism", "communism"):
        loc += [f' {t}_{ide}:0 "{c[0]}"', f' {t}_{ide}_DEF:0 "{c[0]}"', f' {t}_{ide}_ADJ:0 "{c[1]}"']
    loc.append(f' KAZUAL_{t}_DESC:0 "{c[0]}. Описание - TODO."')
loc += [' KAZUAL_BOOKMARK_NAME:0 "Казуальность"', ' KAZUAL_BOOKMARK_DESC:0 "Мир Казуальности, 1936 год."',
        ' kazual_mainland:0 "Материк"', ' kazual_islands:0 "Острова"']
w("localisation/russian/kazual_countries_l_russian.yml", "\n".join(loc) + "\n", bom=True)
w("localisation/russian/kazual_states_l_russian.yml", "\n".join(["l_russian:"] + loc_states + loc_sr) + "\n", bom=True)
# английская копия, чтобы не было сырых ключей при английском языке игры
for name in ("kazual_countries", "kazual_states"):
    src = open(os.path.join(ROOT, "localisation", "russian", f"{name}_l_russian.yml"), encoding="utf-8-sig").read()
    w(f"localisation/english/{name}_l_english.yml", src.replace("l_russian:", "l_english:", 1), bom=True)

# --- снабжение, ж/д, здания, погода, стеки
w("map/supply_nodes.txt", "".join(f"1 {s['main']}\n" for s in states))
rail = set()
for t in C:
    root = CAPP[t]; mine = set(land[t])
    par = {root: None}; q = deque([root])
    while q:
        u = q.popleft()
        for v in ADJ[u]:
            if v in mine and v not in par: par[v] = u; q.append(v)
    for s in states:
        if s["tag"] != t: continue
        u = s["main"]
        while u in par and par[u] is not None:
            rail.add((min(u, par[u]), max(u, par[u]))); u = par[u]
w("map/railways.txt", "".join(f"1 2 {a} {b}\n" for a, b in sorted(rail)))

bl = []
STATE_B = ["industrial_complex"] * 6 + ["arms_factory"] * 6 + ["anti_air_building"] * 3 + [
    "synthetic_refinery", "stronghold_network", "rocket_site_spawn", "radar_station",
    "nuclear_reactor_spawn", "fuel_silo", "air_base"]
COAST_B = ["naval_supply_hub", "naval_headquarters", "naval_base_spawn", "coastal_bunker", "floating_harbor"]
for s in states:
    sea_adj = {i: [j for j in ADJ[i] if P[j]["type"] == "sea"] for i in s["provs"]}
    for n, b in enumerate(STATE_B):
        bl.append(f"{s['id']};{b};{xyz(s['main'], (n % 5) * 2 - 4, (n // 5) * 2 - 4)};0.00;0")
    coast = [i for i in s["provs"] if sea_adj[i]]
    if coast: bl.append(f"{s['id']};dockyard;{xyz(coast[0], 2, 2)};0.00;0")
    for i in s["provs"]:
        bl.append(f"{s['id']};supply_node;{xyz(i, 1, 0)};0.00;0")
        bl.append(f"{s['id']};special_project_facility_spawn;{xyz(i, -1, 0)};0.00;0")
        bl.append(f"{s['id']};bunker;{xyz(i)};0.00;0")
        for n, b in enumerate(COAST_B if sea_adj[i] else []):
            bl.append(f"{s['id']};{b};{xyz(i, n - 2, 1)};0.00;{sea_adj[i][0] if b in ('naval_base_spawn', 'floating_harbor') else 0}")
w("map/buildings.txt", "\n".join(bl) + "\n")
wp = []
for rid, r in enumerate(regions, 1):
    i = r["provs"][len(r["provs"]) // 2]
    wp.append(f"{rid};{xyz(i)};small"); wp.append(f"{rid};{xyz(i, 3, 3)};large")
w("map/weatherpositions.txt", "\n".join(wp) + "\n")
us = []
for i in sorted(P):
    LAND_T = [0, 1, 2, 3, 4, 5, 6, 9, 10, 21, 22, 23, 24, 25, 26, 27, 38]
    SEA_T = sorted(LAND_T + [11, 12, 13, 14, 15, 16, 30, 31, 32, 33, 34, 35])
    if P[i]["type"] == "lake": continue
    for ty in (SEA_T if P[i]["type"] == "sea" else LAND_T):
        us.append(f"{i};{ty};{xyz(i, (ty % 5) - 2, (ty // 5) % 5 - 2)};0.00;0.00")
w("map/unitstacks.txt", "\n".join(us) + "\n")

# --- проливы (adjacencies) и прочие файлы карты
def coast_of(t, nearpt):
    x, y = nearpt[0] * SX, nearpt[1] * SY
    c = [i for i in land[t] if any(P[j]["type"] == "sea" for j in ADJ[i])]
    return min(c, key=lambda i: (P[i]["x"] - x) ** 2 + (P[i]["y"] - y) ** 2)
def sea_near(pt):
    x, y = pt[0] * SX, pt[1] * SY
    return min(seas, key=lambda i: (P[i]["x"] - x) ** 2 + (P[i]["y"] - y) ** 2)
adjl = ["From;To;Type;Through;start_x;start_y;stop_x;stop_y;adjacency_rule_name;Comment"]
for a, b, thr, name in [(("BRT", (200, 420)), ("SOY", (252, 430)), (226, 425), "Technical strait"),
                        (("DMK", (752, 640)), ("Z04", (712, 640)), (733, 640), "Kryakht-Middle strait")]:
    pa, pb = coast_of(*a), coast_of(*b)
    adjl.append(f"{pa};{pb};sea;{sea_near(thr)};-1;-1;-1;-1;;{name}")
adjl.append("-1;-1;-1;-1;-1;-1;-1;-1;-1")
w("map/adjacencies.csv", "\n".join(adjl) + "\n", crlf=True)
w("map/adjacency_rules.txt", "# Правил пока нет (Казуальность)\n")
w("map/positions.txt", "")
shutil.copy(os.path.join(GAME, "map", "default.map"), os.path.join(ROOT, "map", "default.map"))
os.makedirs(os.path.join(ROOT, "map", "supplyareas"), exist_ok=True)

# --- портреты (по континентам) и имена (по тегам)
NL = chr(10)
def cont_block(path, cname):
    src = open(path, encoding="utf-8-sig").read()
    i = src.index(f"name = {cname}")
    j = src.rindex("continent", 0, i); d = 0
    for k in range(src.index("{", j), len(src)):
        d += src[k] == "{"; d -= src[k] == "}"
        if d == 0: return src[j:k + 1]
_sp = open(os.path.join(GAME, "portraits", "998_scientist_portraits.txt"), encoding="utf-8-sig").read()
_g = re.findall(r'"(GFX_[^"]+)"', _sp)
_fem = sorted({g for g in _g if "female" in g.lower()}); _mal = sorted({g for g in _g if "female" not in g.lower()})
_q = lambda L: NL.join(f'			"{g}"' for g in L)
w("portraits/kazual_998_scientist_portraits.txt", NL.join(
    f"continent = {{{NL}	name = {c}{NL}	scientist = {{{NL}		female = {{{NL}{_q(_fem)}{NL}		}}{NL}		male = {{{NL}{_q(_mal)}{NL}		}}{NL}	}}{NL}}}"
    for c in ("kazual_mainland", "kazual_islands")) + NL)
for fname in ("00_portraits.txt",):
    blk = cont_block(os.path.join(GAME, "portraits", fname), "europe")
    out = NL.join(blk.replace("name = europe", f"name = {c}") for c in ("kazual_mainland", "kazual_islands"))
    w(f"portraits/kazual_{fname}", out + NL)
MALE = "Иван Пётр Алексей Сергей Николай Дмитрий Андрей Михаил Константин Булат Саид Рустам Тимур Олег Виктор Павел Григорий Фёдор Артём Ильдар"
FEMALE = "Анна Мария Дарья Ольга Елена Альфия Наталья Ирина Светлана Татьяна Екатерина Вера Лиля Зарина Юлия"
SURN = "Иванов Петров Сидоров Кузнецов Смирнов Попов Соколов Лебедев Козлов Новиков Морозов Волков Арифуллин Багаутдинов Юзеев Пименов Сабиров Алексеев Орлов Зайцев"
nm = ""
for t in C:
    nm += (f"{t} = {{" + NL + f"	male = {{ names = {{ {MALE} }} }}" + NL + f"	female = {{ names = {{ {FEMALE} }} }}" + NL
           + f"	surnames = {{ {SURN} }}" + NL + "	callsigns = { \"Казуал\" \"Болотник\" }" + NL + "}" + NL)
w("common/names/kazual_names.txt", nm)

# --- ИИ: ванильные зоны/театры/стратегии ссылаются на чужие регионы и теги
_aa = open(os.path.join(GAME, "common", "ai_areas", "default.txt"), encoding="utf-8-sig").read()
_names, _d = [], 0
for tok in re.finditer(r"([A-Za-z_]+)\s*=\s*\{|\{|\}", _aa):
    if tok.group(0) == "}": _d -= 1; continue
    if _d == 1 and tok.group(1): _names.append(tok.group(1))
    _d += 1
w("common/ai_areas/default.txt", "areas = {" + NL + "".join(
    f"	{n} = {{ continents = {{ kazual_mainland kazual_islands }} }}{NL}" for n in dict.fromkeys(_names)) + "}" + NL)
w("common/ai_faction_theaters/kazual_theaters.txt", "# театры ИИ пока не заданы" + NL)
w("common/ai_strategy/kazual_default.txt", "# стратегии ИИ пока не заданы" + NL)
w("common/ai_strategy_plans/kazual_plans.txt", "# планы ИИ пока не заданы" + NL)

# --- флаги-заглушки: цвет страны, полоса светлее (TGA 32 бит, как в ванили)
from PIL import Image
for t, c in C.items():
    for sub, (fw, fh) in (("", (82, 52)), ("medium/", (41, 26)), ("small/", (10, 7))):
        im = Image.new("RGBA", (fw, fh), c[2] + (255,))
        light = tuple(min(255, v + 60) for v in c[2]) + (255,)
        for y in range(fh // 3, 2 * fh // 3):
            for x in range(fw): im.putpixel((x, y), light)
        d = os.path.join(ROOT, "gfx", "flags", sub); os.makedirs(d, exist_ok=True)
        im.save(os.path.join(d, f"{t}.tga"))

print("штатов:", len(states), "регионов:", len(regions), "ж/д:", len(rail), "зданий:", len(bl))
