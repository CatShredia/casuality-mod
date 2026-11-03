"""Сборка растров карты из docs/03-Map-Sketch.svg.

Выход: map/*.bmp, map/definition.csv, map/continent.txt, no_commit/temp/provinces.json.
Запуск из корня репозитория: python tools/build_map.py
"""
import json, re, random, os
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAN = r"D:/SteamLibrary/steamapps/common/Hearts of Iron IV/map"
W, H = 4352, 2816
SX, SY = W / 1600, H / 1040
SEED = 1936
rng = np.random.default_rng(SEED)
random.seed(SEED)
OUT = os.path.join(ROOT, "map")
TMP = os.path.join(ROOT, "no_commit", "temp")
os.makedirs(OUT, exist_ok=True); os.makedirs(TMP, exist_ok=True)

svg = open(os.path.join(ROOT, "docs", "03-Map-Sketch.svg"), encoding="utf-8").read()

def pts(s):
    return [(float(a) * SX, float(b) * SY) for a, b in re.findall(r"(-?[\d.]+),(-?[\d.]+)", s)]

# --- страны: (подстрока комментария или fill) -> тег; порядок отрисовки как в SVG
COUNTRY_BY_COMMENT = [
    ("Чёрная Республика", "BLK"), ("заготовка страны 1", "Z01"), ("заготовка страны 3", "Z03"),
    ("заготовка страны 2", "Z02"), ("заготовка страны 4", "Z04"), ("заготовка страны 5", "Z05"),
    ("Соевая Республика", "SOY"), ("Зеленодольск: Мирный", "ZLD"), ("Зеленодольск: Центр", "ZLD"),
    ("Тямовский рейх", "TMR"), ("Айдалия", "ADL"), ("Северная Ассамблея", "SVA"),
    ("Федерация Депутатов", "FDP"), ("Советский Союз", "SVS"), ("Дмитровское Княжество", "DMK"),
    ("Казачья Земля", "KZZ"), ("Казуалия", "CSL"), ("Челяба", "CLB"), ("Иракиккистан", "IRK"),
    ("Ирракия", "IRR"), ("Муси", "MUS"), ("Магнолия", "MGN"), ("Сарайкумское Ханство", "SRK"),
    ("Кытай", "KTY"),
]
TAGS = ["BRT", "ICL", "TRV"] + sorted({t for _, t in COUNTRY_BY_COMMENT})
TAGS = list(dict.fromkeys(TAGS))
TID = {t: i + 1 for i, t in enumerate(TAGS)}          # 1..N
UNASSIGNED, WATER, LAKE = 250, 0, 251

def poly_of(comment):
    m = re.search(r'<polygon[^>]*points="([^"]+)"[^>]*/>\s*<!--\s*' + re.escape(comment), svg)
    assert m, comment
    return pts(m.group(1))

country = Image.new("L", (W, H), WATER)
dc = ImageDraw.Draw(country)
base = re.search(r'<polygon fill="#dedacb"[^>]*points="([^"]+)"', svg).group(1)
dc.polygon(pts(base), fill=UNASSIGNED)
dc.polygon(pts("70,340 170,330 200,400 170,480 100,470 60,410"), fill=TID["BRT"])
dc.polygon(pts("20,270 70,260 80,310 30,320"), fill=TID["ICL"])
for c, t in COUNTRY_BY_COMMENT:
    dc.polygon(poly_of(c), fill=TID[t])
for p in re.search(r'Травинная Федерация -->(.*?)</g>', svg, re.S).group(1).split("<polygon")[1:]:
    dc.polygon(pts(re.search(r'points="([^"]+)"', p).group(1)), fill=TID["TRV"])
seas = re.findall(r'<polygon class="sea" points="([^"]+)"', svg)
for i, s in enumerate(seas):
    dc.polygon(pts(s), fill=LAKE if i == 2 else WATER)      # 3-й полигон - Каспийская Дырка (озеро)
cx, cy = 1000 * SX, 450 * SY
dc.ellipse([cx - 26 * SX, cy - 16 * SY, cx + 26 * SX, cy + 16 * SY], fill=LAKE)  # озеро Челяба

# --- рельеф (в координатах схемы)
PLAINS, FOREST, HILLS, MOUNT, DESERT, MARSH, URBAN, JUNGLE = range(8)
terr = Image.new("L", (W, H), PLAINS)
dt = ImageDraw.Draw(terr)
for s in re.findall(r'<polygon fill="url\(#forest\)" points="([^"]+)"', svg):
    dt.polygon(pts(s), fill=FOREST)
for s in re.findall(r'<polygon fill="url\(#swamp\)"[^>]*points="([^"]+)"', svg):
    dt.polygon(pts(s), fill=MARSH)
dt.polygon(pts(re.search(r'<polygon fill="url\(#desert\)" points="([^"]+)"', svg).group(1)), fill=DESERT)
for tag in ("MUS",):
    dt.polygon(poly_of("Муси"), fill=JUNGLE)
dt.polygon(pts("1010,780 1175,780 1105,880 1045,925 1010,860"), fill=JUNGLE)   # юг Ирракии
for p in re.search(r'Травинная Федерация -->(.*?)</g>', svg, re.S).group(1).split("<polygon")[1:]:
    dt.polygon(pts(re.search(r'points="([^"]+)"', p).group(1)), fill=JUNGLE)
dt.polygon(pts("300,340 445,340 445,362 300,362"), fill=URBAN)                  # Мирный
dt.polygon(poly_of("Айдалия"), fill=MOUNT)
dt.polygon(pts("330,70 372,70 372,300 330,300"), fill=MOUNT)                    # горы на западе СевАссамблеи
dt.polygon(pts(re.search(r'<polygon fill="url\(#mount\)"[^>]*points="([^"]+)"', svg).group(1)), fill=MOUNT)
ridges = [pts(d.replace("M", "").replace("L", " ")) for d in re.findall(r'<path class="mtn" d="([^"]+)"', svg)]
for r in ridges:
    dt.line(r, fill=HILLS, width=int(26 * SX), joint="curve")
for r in ridges:
    dt.line(r, fill=MOUNT, width=int(11 * SX), joint="curve")
for x, y in [(1112, 452), (1084, 482), (1140, 482)]:                           # 3 горы у Ставки Казуала
    dt.ellipse([x * SX - 14, y * SY - 14, x * SX + 14, y * SY + 14], fill=MOUNT)

# --- деформация границ (берега и рубежи не по линейке)
def field(lo, amp):
    g = rng.standard_normal((lo[1], lo[0])).astype(np.float32)
    im = Image.fromarray(g).resize((W, H), Image.BICUBIC)
    a = np.asarray(im, dtype=np.float32)
    return a / (np.abs(a).max() + 1e-6) * amp
DX = field((60, 40), 22) + field((240, 160), 6)
DY = field((60, 40), 22) + field((240, 160), 6)
yy, xx = np.mgrid[0:H, 0:W]
SXI = np.clip((xx + DX).round().astype(np.int32), 0, W - 1)
SYI = np.clip((yy + DY).round().astype(np.int32), 0, H - 1)
def warp(a):
    return a[SYI, SXI]

C = warp(np.asarray(country))
DX2 = DX * 2 + field((90, 60), 30); DY2 = DY * 2 + field((90, 60), 30)
T = np.asarray(terr)[np.clip((yy + DY2).round().astype(np.int32), 0, H - 1), np.clip((xx + DX2).round().astype(np.int32), 0, W - 1)].copy()
_n = field((200, 130), 1.0) + field((60, 40), 0.6)
T[((T == FOREST) | (T == JUNGLE) | (T == DESERT) | (T == MARSH)) & (_n < -0.25)] = PLAINS

# ничейная суша -> ближайшая страна
def shifts(a, fill):
    out = []
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        b = np.full_like(a, fill)
        ys = slice(max(dy, 0), H + min(dy, 0)); yd = slice(max(-dy, 0), H + min(-dy, 0))
        xs = slice(max(dx, 0), W + min(dx, 0)); xd = slice(max(-dx, 0), W + min(-dx, 0))
        b[ys, xs] = a[yd, xd]
        out.append(b)
    return out
left = int((C == UNASSIGNED).sum())
while (C == UNASSIGNED).any():
    for b in shifts(C, WATER):
        m = (C == UNASSIGNED) & (b >= 1) & (b < UNASSIGNED)
        C[m] = b[m]
print("ничейной суши присоединено, px:", left)

land = (C >= 1) & (C < UNASSIGNED)
lake = C == LAKE
sea = C == WATER
# убрать одиночные пиксели суши/воды
for _ in range(2):
    n = sum((b >= 1) & (b < UNASSIGNED) for b in shifts(C, WATER))
    C[land & (n <= 1)] = WATER
    land = (C >= 1) & (C < UNASSIGNED); sea = C == WATER

# --- провинции: рост от семян внутри зон (страна / море / озеро)
AVG = {"SVS": 2600, "MGN": 4200, "KTY": 2600, "SRK": 3400, "CLB": 2600, "IRR": 1700, "MUS": 2200,
       "TRV": 1600, "KZZ": 1300, "DMK": 1800, "BRT": 1200, "ICL": 1200, "CSL": 1100, "IRK": 1700}
DEFAULT_AVG, SEA_AVG, LAKE_AVG = 1400, 14000, 9000
zone = C.astype(np.int32).copy()            # зона роста: id страны, 0 море, 251 озеро
prov = np.zeros((H, W), np.int32)
next_id = 1
def seed_zone(mask, avg):
    global next_id
    ys, xs = np.nonzero(mask)
    if len(ys) == 0: return
    k = max(1, int(round(len(ys) / avg)))
    idx = rng.choice(len(ys), size=k, replace=False)
    for i in idx:
        prov[ys[i], xs[i]] = next_id; next_id += 1
for t, i in TID.items():
    seed_zone(C == i, AVG.get(t, DEFAULT_AVG))
seed_zone(sea, SEA_AVG)
seed_zone(lake, LAKE_AVG)

ZS = shifts(zone, -1)
def shift1(a, k, fill):
    dy, dx = ((1, 0), (-1, 0), (0, 1), (0, -1))[k]
    b = np.full_like(a, fill)
    ys = slice(max(dy, 0), H + min(dy, 0)); yd = slice(max(-dy, 0), H + min(-dy, 0))
    xs = slice(max(dx, 0), W + min(dx, 0)); xd = slice(max(-dx, 0), W + min(-dx, 0))
    b[ys, xs] = a[yd, xd]
    return b
def grow():
    order = [0, 1, 2, 3]
    while True:
        changed = 0
        random.shuffle(order)
        for k in order:
            b = shift1(prov, k, 0); z = ZS[k]
            m = (prov == 0) & (b > 0) & (z == zone)
            changed += int(m.sum()); prov[m] = b[m]
        if not changed: break
for _ in range(100):
    grow()
    rest = prov == 0
    if not rest.any(): break
    ys, xs = np.nonzero(rest)              # несвязанные куски без семян
    for j in range(0, len(ys), 400):
        if prov[ys[j], xs[j]] == 0:
            prov[ys[j], xs[j]] = next_id; next_id += 1

# слить мелкие провинции (<150 px) с соседом той же зоны
cnt = np.bincount(prov.ravel(), minlength=next_id)
small = set(np.nonzero((cnt > 0) & (cnt < 150))[0].tolist())
for _ in range(3):
    if not small: break
    for b, z in zip(shifts(prov, 0), shifts(zone, -1)):
        m = np.isin(prov, list(small)) & (b > 0) & (z == zone) & ~np.isin(b, list(small))
        prov[m] = b[m]
    cnt = np.bincount(prov.ravel(), minlength=next_id)
    small = set(np.nonzero((cnt > 0) & (cnt < 150))[0].tolist())

# X-пересечения 2x2 (шахматка и 4 разных цвета) -> правка пикселя
for _ in range(6):
    a, b, c, d = prov[:-1, :-1], prov[:-1, 1:], prov[1:, :-1], prov[1:, 1:]
    bad = ((a == d) & (b == c) & (a != b)) | ((a != b) & (a != c) & (a != d) & (b != c) & (b != d) & (c != d))
    ys, xs = np.nonzero(bad)
    if len(ys) == 0: break
    prov[ys, xs + 1] = prov[ys, xs]; zone[ys, xs + 1] = zone[ys, xs]
    print("x-crossing правок:", len(ys))

# повторное слияние мелочи после правок (до 120 px), при необходимости через границу зон
for anyzone in (False, False, True, True):
    cnt = np.bincount(prov.ravel(), minlength=prov.max() + 1)
    small = np.nonzero((cnt > 0) & (cnt < 120))[0]
    if len(small) == 0: break
    sm = np.isin(prov, small)
    for k in range(4):
        b = shift1(prov, k, 0); z = shift1(zone, k, -1)
        m = sm & (b > 0) & ~np.isin(b, small) & ((z == zone) | anyzone)
        prov[m] = b[m]; zone[m] = z[m]
        sm = np.isin(prov, small)
print("мелких провинций осталось:", int(len(np.nonzero((np.bincount(prov.ravel()) > 0) & (np.bincount(prov.ravel()) < 120))[0])))
assert (prov > 0).all(), int((prov == 0).sum())
# перенумерация подряд
ids = np.unique(prov)
ids = ids[ids > 0]
remap = np.zeros(next_id, np.int32); remap[ids] = np.arange(1, len(ids) + 1)
prov = remap[prov]
N = len(ids)
print("провинций:", N)

# --- атрибуты провинций
flat = prov.ravel()
cntp = np.bincount(flat, minlength=N + 1)
sx_ = np.bincount(flat, weights=np.tile(np.arange(W), H), minlength=N + 1)
sy_ = np.bincount(flat, weights=np.repeat(np.arange(H), W), minlength=N + 1)
zone_of = np.zeros(N + 1, np.int32); zone_of[flat] = zone.ravel()
terr_count = np.zeros((N + 1, 8), np.int64)
for k in range(8):
    terr_count[:, k] = np.bincount(flat[(T.ravel() == k)], minlength=N + 1)
TERR_NAME = ["plains", "forest", "hills", "mountain", "desert", "marsh", "urban", "jungle"]

pairs = set()
for a, b in ((prov[:, :-1], prov[:, 1:]), (prov[:-1, :], prov[1:, :])):
    m = a != b
    pp = np.stack([np.minimum(a[m], b[m]), np.maximum(a[m], b[m])], 1)
    pairs |= set(map(tuple, np.unique(pp, axis=0).tolist()))
adj = {i: set() for i in range(1, N + 1)}
for a, b in pairs:
    adj[a].add(b); adj[b].add(a)

# континенты: 1 - материк (крупнейший массив суши), 2 - острова
from collections import deque
land_ids = [i for i in range(1, N + 1) if 1 <= zone_of[i] < UNASSIGNED]
comp = {}
for s in land_ids:
    if s in comp: continue
    q = deque([s]); comp[s] = s; members = [s]
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v not in comp and 1 <= zone_of[v] < UNASSIGNED:
                comp[v] = s; q.append(v); members.append(v)
sizes = {}
for i, r in comp.items(): sizes[r] = sizes.get(r, 0) + cntp[i]
mainland = max(sizes, key=sizes.get)

colors = set([(0, 0, 0)])
rows, info = ["0;0;0;0;land;false;unknown;0"], {}
INV = {v: k for k, v in TID.items()}
for i in range(1, N + 1):
    while True:
        col = tuple(int(v) for v in rng.integers(1, 255, 3))
        if col not in colors: colors.add(col); break
    z = zone_of[i]
    if z == WATER: typ, ter, cont = "sea", "ocean", 0
    elif z == LAKE: typ, ter, cont = "lake", "lakes", 0
    else:
        typ = "land"; ter = TERR_NAME[int(terr_count[i].argmax())]
        cont = 8 if comp[i] == mainland else 9
    coastal = typ == "land" and any(zone_of[j] == WATER for j in adj[i])
    rows.append(f"{i};{col[0]};{col[1]};{col[2]};{typ};{str(coastal).lower()};{ter};{cont}")
    info[i] = dict(color=col, type=typ, terrain=ter, coastal=coastal, cont=cont,
                   tag=INV.get(int(z)) if typ == "land" else None, px=int(cntp[i]),
                   x=float(sx_[i] / cntp[i]), y=float(sy_[i] / cntp[i]), adj=sorted(adj[i]))
open(os.path.join(OUT, "definition.csv"), "w", newline="\r\n").write("\n".join(rows) + "\n")
open(os.path.join(OUT, "continent.txt"), "w").write("continents = {\n\teurope\n\tnorth_america\n\tsouth_america\n\taustralia\n\tafrica\n\tasia\n\tmiddle_east\n\tkazual_mainland\n\tkazual_islands\n}\n")

lut = np.zeros((N + 1, 3), np.uint8)
for i, d in info.items(): lut[i] = d["color"]
Image.fromarray(lut[prov], "RGB").save(os.path.join(OUT, "provinces.bmp"))

# --- карта высот
isw = (zone == WATER); isl = (zone == LAKE)
hgt = np.full((H, W), 102.0, np.float32)
hgt += field((120, 80), 6) + field((480, 320), 3)
hgt[T == HILLS] += 25
hgt[T == MOUNT] += 70
hgt[T == MOUNT] += np.clip(field((300, 200), 40), 0, None)[T == MOUNT]
h_img = Image.fromarray(np.clip(hgt, 0, 255).astype(np.uint8)).resize((W // 8, H // 8), Image.BILINEAR).resize((W, H), Image.BICUBIC)
hgt = np.asarray(h_img, np.float32)
hgt = np.maximum(hgt, 97)
hgt[isw] = 86; hgt[isl] = 90
heightmap = np.clip(hgt, 0, 255).astype(np.uint8)
Image.fromarray(heightmap, "L").save(os.path.join(OUT, "heightmap.bmp"))

# нормали (половинный размер)
hs = np.asarray(Image.fromarray(heightmap).resize((W // 2, H // 2), Image.BILINEAR), np.float32)
gx = np.gradient(hs, axis=1); gy = np.gradient(hs, axis=0)
nz = np.ones_like(hs) * 6.0
nn = np.sqrt(gx ** 2 + gy ** 2 + nz ** 2)
nrm = np.stack([(-gx / nn + 1) * 127.5, (gy / nn + 1) * 127.5, (nz / nn + 1) * 127.5], -1)
Image.fromarray(nrm.clip(0, 255).astype(np.uint8), "RGB").save(os.path.join(OUT, "world_normal.bmp"))

# --- terrain.bmp (индексы палитры из common/terrain/00_terrain.txt)
IDX = {PLAINS: 0, FOREST: 1, HILLS: 17, MOUNT: 6, DESERT: 3, MARSH: 9, URBAN: 13, JUNGLE: 21}
tb = np.zeros((H, W), np.uint8)
for k, v in IDX.items(): tb[T == k] = v
tb[isw] = 15; tb[isl] = 14
def save_p(arr, name, size=None):
    van = Image.open(os.path.join(VAN, name))
    im = Image.fromarray(arr, "P"); im.putpalette(van.getpalette())
    im.save(os.path.join(OUT, name))
save_p(tb, "terrain.bmp")

cb = np.zeros((H, W), np.uint8); cb[isw | isl] = 15
save_p(cb, "cities.bmp")

# trees.bmp: пропорционально ванильному соотношению 5632/1650
TW, TH = round(W * 1650 / 5632), round(H * 600 / 2048)
tr = np.zeros((TH, TW), np.uint8)
ts = np.asarray(Image.fromarray(T).resize((TW, TH), Image.NEAREST))
tr[ts == FOREST] = 6; tr[ts == JUNGLE] = 28
save_p(tr, "trees.bmp")

# --- реки
rv = np.full((H, W), 255, np.uint8); rv[isw | isl] = 254
def to_out(p):
    x, y = int(round(p[0])), int(round(p[1]))
    x = min(max(x, 0), W - 1); y = min(max(y, 0), H - 1)
    return int(round(x - DX[y, x])), int(round(y - DY[y, x]))
def line4(a, b):
    (x0, y0), (x1, y1) = a, b
    out = [(x0, y0)]
    while (x0, y0) != (x1, y1):
        if abs(x1 - x0) * 1.0 >= abs(y1 - y0): x0 += 1 if x1 > x0 else -1
        else: y0 += 1 if y1 > y0 else -1
        out.append((x0, y0))
    return out
water = isw | isl
nriv = 0
for d in re.findall(r'<path class="river" d="([^"]+)"', svg):
    P = [to_out(p) for p in pts(d.replace("M", "").replace("L", " "))]
    if len(P) < 2: continue
    def nearw(p): return water[max(p[1] - 6, 0):p[1] + 7, max(p[0] - 6, 0):p[0] + 7].any()
    if nearw(P[0]) and not nearw(P[-1]): P = P[::-1]
    path = []
    for a, b in zip(P, P[1:]): path += line4(a, b)[(1 if path else 0):]
    # продлить до воды по последнему направлению
    if not water[path[-1][1], path[-1][0]]:
        dx_, dy_ = P[-1][0] - P[-2][0], P[-1][1] - P[-2][1]
        n_ = max(abs(dx_), abs(dy_), 1)
        tgt = (path[-1][0] + round(dx_ / n_ * 40), path[-1][1] + round(dy_ / n_ * 40))
        ext = line4(path[-1], (min(max(tgt[0], 0), W - 1), min(max(tgt[1], 0), H - 1)))[1:]
        for p in ext:
            path.append(p)
            if water[p[1], p[0]]: break
    cut = []
    for p in path:
        if water[p[1], p[0]]: break
        cut.append(p)
    if len(cut) < 8: continue
    L = len(cut)
    for j, (x, y) in enumerate(cut):
        rv[y, x] = 0 if j == 0 else 3 + min(3, int(4 * j / L))
    nriv += 1
save_p(rv, "rivers.bmp")
print("рек:", nriv)

json.dump({"N": N, "W": W, "H": H, "tags": TID, "prov": info}, open(os.path.join(TMP, "provinces.json"), "w"))
np.save(os.path.join(TMP, "prov.npy"), prov)
np.save(os.path.join(TMP, "height.npy"), heightmap)
print("готово")
