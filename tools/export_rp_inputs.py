"""Картинки для загрузки в RandomParadox (Ktits-Mod 0.1.0), по этапам.

Запуск из корня репозитория: python tools/export_rp_inputs.py [этап]
Выход: no_commit/temp/rp_input/stage_NN/*.png (4352x2816, RGB).
Источник: docs/03-Map-Sketch.svg плюс правки из docs/08-map-fix.md (описаны в разделе EXTRA ниже).
Масштаб: 1 единица SVG ~ 9,85 км, 1 единица^2 ~ 97 км^2, 1 единица SVG = 2,72 px.
"""
import os, re, sys
from collections import deque
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "no_commit", "temp", "rp_input")
W, H = 4608, 2816                                   # холст с полем океана вокруг суши
LAND_K = 0.76                                        # суша занимает 76 % прежнего масштаба
SX, SY = 4352 / 1600 * LAND_K, 2816 / 1040 * LAND_K
OX, OY = (W - 1600 * SX) / 2, (H - 1040 * SY) / 2
KM2_PER_U2 = 97.0
rng = np.random.default_rng(1936)
svg = open(os.path.join(ROOT, "docs", "03-Map-Sketch.svg"), encoding="utf-8").read()


def parse(s):
    return [(float(a), float(b)) for a, b in re.findall(r"(-?[\d.]+),(-?[\d.]+)", s)]


def px(poly):
    return [(x * SX + OX, y * SY + OY) for x, y in poly]


def area(poly):
    return abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                   for i in range(len(poly)))) / 2


def centroid(poly):
    return (sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly))


def fit(poly, target_km2):
    """Масштабирует многоугольник (единицы SVG) вокруг центра до нужной площади, км^2."""
    k = (target_km2 / KM2_PER_U2 / area(poly)) ** 0.5
    cx, cy = centroid(poly)
    return [(cx + (x - cx) * k, cy + (y - cy) * k) for x, y in poly]


def field(lo, amp):
    g = rng.standard_normal((lo[1], lo[0])).astype(np.float32)
    a = np.asarray(Image.fromarray(g).resize((W, H), Image.BICUBIC), dtype=np.float32)
    return a / (np.abs(a).max() + 1e-6) * amp


def mask(draw_fn):
    im = Image.new("L", (W, H), 0)
    draw_fn(ImageDraw.Draw(im))
    return im


# --- схема (docs/03-Map-Sketch.svg)
land_polys = []
for m in re.finditer(r"<polygon([^>]*)points=\"([^\"]+)\"([^>]*)/>", svg):
    attrs = m.group(1) + m.group(3)
    if 'class="sea"' in attrs or "url(#" in attrs or 'class="men"' in attrs:
        continue
    if 'class="c' in attrs or 'fill="#dedacb"' in attrs or 'stroke-dasharray="6 3"' in attrs:
        land_polys.append(parse(m.group(2)))
for g in re.findall(r"<g class=\"c inf\"[^>]*>(.*?)</g>", svg, re.S):          # острова Травинной Федерации
    for k, s in enumerate(re.findall(r"points=\"([^\"]+)\"", g)):
        dx = (0, 20, 45)[k] if k < 3 else 45
        land_polys.append([(x + dx, y + 30) for x, y in parse(s)])      # острова южнее и с большими промежутками
seas = [parse(s) for s in re.findall(r'<polygon class="sea" points="([^"]+)"', svg)]
ell = re.search(r'<ellipse class="sea" cx="([\d.]+)" cy="([\d.]+)" rx="([\d.]+)" ry="([\d.]+)"', svg)
mount_polys = [parse(re.search(r'<polygon fill="url\(#mount\)"[^>]*points="([^"]+)"', svg).group(1))]
ridges = [parse(d.replace("M", "").replace("L", " ")) for d in re.findall(r'<path class="mtn" d="([^"]+)"', svg)]
ridges = [r for r in ridges if not (1340 < centroid(r)[0] < 1500 and 740 < centroid(r)[1] < 880)]   # хребет острова Чёрной Республики задаётся отдельно (japan_axis)
aid = parse(re.search(r'points="([^"]+)"[^>]*/>\s*<!--\s*Айдалия', svg).group(1))
chelyaba = parse(re.search(r'points="([^"]+)"[^>]*/>\s*<!--\s*Челяба', svg).group(1))
japan0 = parse(re.search(r'points="([^"]+)"[^>]*/>\s*<!--\s*Чёрная Республика', svg).group(1))
britain = parse("70,340 170,330 200,400 170,480 100,470 60,410")

land_polys = [q for q in land_polys if q != japan0]
rivers = [parse(d.replace("M", "").replace("L", " ")) for d in re.findall(r'<path class="river" d="([^"]+)"', svg)]
JUNGARIK = parse("575,985 590,940 565,900 585,860 570,825 590,790 585,772")          # река Джунгарик: из джунглей на юге к Срединному морю
rivers.append(JUNGARIK)
# перешеек между СССР и Тямовским рейхом вдвое-втрое шире: Синее море короче с востока, Кряхтское короче с севера
seas[0] = parse("290,255 470,262 560,272 600,270 600,342 560,342 460,335 290,340")
seas[1] = parse("700,495 735,490 775,495 780,500 755,535 715,530 700,500")                          # исходный остров заменяется на JAPAN ниже

# --- EXTRA: правки из docs/08-map-fix.md (в схему SVG и в лор пока не внесены), единицы SVG
JAPAN = fit(japan0, 378_000 * 0.86)                                                     # площадь как у Японии
CEYLON = fit(parse("1040,950 1066,944 1078,970 1062,994 1038,986 1030,966"), 65_600 * 1.2)
LEDYSHKA = fit(parse("30,30 100,12 175,32 200,95 165,150 95,168 38,130"), 2_166_000 * 1.2)   # как Гренландия
LEDYSHKA = [(centroid(LEDYSHKA)[0] + (x - centroid(LEDYSHKA)[0]) / 1.6, centroid(LEDYSHKA)[1] + (y - centroid(LEDYSHKA)[1]) * 1.6) for x, y in LEDYSHKA]  # вытянута с севера на юг, площадь та же
SPAIN = fit(parse("330,628 420,618 438,652 412,698 366,716 336,692 320,656"), 506_000)
SPAIN_BRIDGE = parse("335,600 420,600 420,640 335,640")                          # шов с Соевой Республикой
SOUTH = parse("20,790 130,768 270,782 420,770 560,785 625,800 645,860 630,950 575,1005 440,1030 "
              "280,1030 130,1015 40,960 10,880")                                 # ~1/2 Африки южнее Среднего моря
def tsouth(pts):
    """Вытягивает Фигарию с севера на юг (площадь та же): якорь - северный берег y=775, ось x=345."""
    return [(345 + (x - 345) * 0.66, 775 + (y - 775) * 1.5) for x, y in pts]


SOUTH = tsouth(SOUTH)
KAMCHATKA = parse("1440,140 1500,125 1555,160 1585,240 1590,300 1560,312 1535,255 1500,205 1445,215")
SSSR_CAPES = [parse("860,78 905,50 960,30 1005,48 985,82 930,95"),               # полуострова на севере СССР
              parse("1180,78 1230,45 1300,30 1350,52 1320,85 1250,95")]
DM_WIDER = parse("735,800 700,855 760,895 850,885 905,845 880,770 840,830 780,840")   # Дмитровское Княжество шире
EXTRA_LAND = [JAPAN, CEYLON, LEDYSHKA, SPAIN, SPAIN_BRIDGE, SOUTH, KAMCHATKA, DM_WIDER] + SSSR_CAPES

GULF_NORTH = parse("668,55 738,55 745,120 732,192 706,218 684,192 664,120")      # залив между Сев. Ассамблеей и СССР (перешеек южнее)
SSSR_BAYS = [parse("780,68 830,66 862,92 845,126 805,116"), parse("1040,68 1100,66 1126,100 1090,136 1050,112")]
KYTAI_GULF = parse("1522,316 1440,334 1392,362 1402,396 1452,406 1522,386")      # большой залив на севере Кытая
WIDE_STRAIT = parse("698,515 785,515 790,560 782,680 772,800 705,800 702,740 704,650 706,570")
EXTRA_WATER = [GULF_NORTH, KYTAI_GULF, WIDE_STRAIT] + SSSR_BAYS

SIBERIA_RIDGES = [parse("1200,260 1230,200 1280,170 1330,120"), parse("1260,285 1320,240 1390,232 1440,185"),
                  parse("1170,120 1210,160 1232,205"), parse("1340,280 1390,215 1425,150")]
SIBERIA_PLATEAU = parse("1180,100 1440,100 1440,205 1380,245 1262,272 1190,232")
BRITAIN_RIDGE = parse("70,352 110,342 150,350 188,368")
KAZUAL_HILLS = [(1112, 452), (1084, 482), (1140, 482)]                           # 3 казуальные горы - теперь холмы
FIG_RIDGE = parse("60,890 180,868 300,884 430,864 560,880 640,892")                 # хребет на юге Фигарии
FIG_JUNGLE = parse("40,905 640,908 600,1000 440,1030 280,1030 130,1015 40,960")     # джунгли южнее хребта (этап 2)
FIG_HILLS = parse("12,800 150,790 175,900 170,1000 40,965 10,880")                  # холмы на западе Фигарии
FIG_RIDGE, FIG_JUNGLE, FIG_HILLS, JUNGARIK = (tsouth(q) for q in (FIG_RIDGE, FIG_JUNGLE, FIG_HILLS, JUNGARIK))
rivers[-1] = JUNGARIK
AID_RIDGES = [parse("444,572 478,548 516,532"), parse("450,546 486,560 516,576"), parse("470,522 478,560 468,580")]


def japan_axis():
    best = max(((a, b) for a in JAPAN for b in JAPAN), key=lambda ab: (ab[0][0] - ab[1][0]) ** 2 + (ab[0][1] - ab[1][1]) ** 2)
    (x1, y1), (x2, y2) = best
    return [(x1 + (x2 - x1) * 0.12, y1 + (y2 - y1) * 0.12), (x1 + (x2 - x1) * 0.88, y1 + (y2 - y1) * 0.88)]


def fjords():
    """Фьорды у западного и северного берега Северной Ассамблеи (как Норвегия): узкие каналы от берега внутрь с ответвлениями."""
    out = []
    r = np.random.default_rng(7)
    for y in np.arange(88, 292, 14):                                             # запад, x ~ 330
        x, yy = 300.0, float(y)
        path = [(x, yy)]
        for _ in range(r.integers(3, 6)):
            x += r.uniform(10, 18); yy += r.uniform(-7, 7)
            path.append((x, yy))
        out.append(path)
        if r.random() < 0.5:                                                     # ответвление
            bx, by = path[2]
            out.append([(bx, by), (bx + r.uniform(8, 16), by + r.choice([-1, 1]) * r.uniform(8, 16))])
    for x in np.arange(350, 690, 17):                                            # север, y ~ 70
        yy, xx = 52.0, float(x)
        path = [(xx, yy)]
        for _ in range(r.integers(2, 5)):
            yy += r.uniform(9, 15); xx += r.uniform(-6, 6)
            path.append((xx, yy))
        out.append(path)
    return out


FJORDS = fjords()


def draw_land(d):
    for p in land_polys + EXTRA_LAND:
        d.polygon(px(p), fill=255)
    d.line(px(japan_axis()), fill=255, width=int(46 * SX), joint="curve")      # равнины Чёрной Республики: остров шире
    for p in seas:
        d.polygon(px(p), fill=0)
    for p in EXTRA_WATER:
        d.polygon(px(p), fill=0)


def draw_lakes(d):
    d.polygon(px(seas[2]), fill=255)                                            # Каспийская Дырка
    cx, cy, rx, ry = (float(v) for v in ell.groups())
    d.ellipse([(cx - rx) * SX + OX, (cy - ry) * SY + OY, (cx + rx) * SX + OX, (cy + ry) * SY + OY], fill=255)


def line_mask(lines, width_units):
    def f(d):
        for r in lines:
            d.line(px(r), fill=255, width=int(width_units * SX), joint="curve")
    return f


def draw_fjords(d):
    for path in FJORDS:
        d.line(px(path), fill=255, width=int(7 * SX), joint="curve")


def draw_core(d):
    for p in mount_polys:
        d.polygon(px(p), fill=255)
    d.polygon(px(parse("330,70 372,70 372,300 330,300")), fill=255)             # горы на западе Северной Ассамблеи


def draw_peaks(d):
    for p in mount_polys:
        c = np.mean(px(p), axis=0)
        d.polygon([((x - c[0]) * 0.55 + c[0], (y - c[1]) * 0.55 + c[1]) for x, y in px(p)], fill=255)


def draw_steep(d):
    for p in mount_polys:
        c = np.mean(px(p), axis=0)
        d.polygon([((x - c[0]) * 0.25 + c[0], (y - c[1]) * 0.25 + c[1]) for x, y in px(p)], fill=255)


def draw_kazual_hills(d):
    for x, y in KAZUAL_HILLS:
        r = 26 * SX
        d.ellipse([x * SX + OX - r, y * SY + OY - r, x * SX + OX + r, y * SY + OY + r], fill=255)


def poly_mask(polys):
    def f(d):
        for p in polys:
            d.polygon(px(p), fill=255)
    return f


# --- естественные берега
DX = field((22, 14), 70) + field((70, 46), 30) + field((240, 160), 8)
DY = field((22, 14), 70) + field((70, 46), 30) + field((240, 160), 8)
yy_, xx_ = np.mgrid[0:H, 0:W]
SXI = np.clip((xx_ + DX).round().astype(np.int32), 0, W - 1)
SYI = np.clip((yy_ + DY).round().astype(np.int32), 0, H - 1)


def erode(m, r):
    """Эрозия булевой маски на r пикселей (на 1/4 разрешения, быстро)."""
    k = max(1, r // 4)
    small = Image.fromarray(m.astype(np.uint8) * 255).resize((W // 4, H // 4), Image.NEAREST)
    small = small.filter(ImageFilter.MinFilter(2 * k + 1))
    return np.asarray(small.resize((W, H), Image.NEAREST)) > 127


def warp(im):
    return np.asarray(im)[SYI, SXI] > 127


def stage1():
    lake = warp(mask(draw_lakes))
    land = warp(mask(draw_land)) | lake            # озёра на этапе берега считаем сушей: иначе вокруг них кайма «океана»
    land_orig = land.copy()
    smooth = np.asarray(Image.fromarray(land.astype(np.uint8) * 255).filter(ImageFilter.GaussianBlur(38)), dtype=np.float32) / 255.0
    noise = (field((12, 8), 1.0) * 1.2 + field((30, 20), 1.0) * 1.0 + field((70, 46), 1.0) * 0.9
             + field((160, 105), 1.0) * 0.6 + field((340, 220), 1.0) * 0.35)
    core = erode(land, 17)                                                       # суша не исчезает целиком
    band = 4.0 * smooth * (1.0 - smooth)                                         # шум действует только у берега
    land = (smooth + 2.4 * band * noise > 0.5) | core

    def inner_seas(d):                                                           # внутренние моря и проливы
        for i, q in enumerate(seas):
            if i != 2:
                d.polygon(px(q), fill=255)
        for q in (WIDE_STRAIT, GULF_NORTH):
            d.polygon(px(q), fill=255)
    water_core = erode(warp(mask(inner_seas)), 15)
    gap_core = erode(~land_orig, 37)                                             # проливы между сушами не зарастают
    land &= ~(water_core | gap_core)
    land |= lake
    # мелкие «озерца» воды среди суши заливаем сушей
    sm = np.asarray(Image.fromarray((~land).astype(np.uint8) * 255).resize((W // 8, H // 8), Image.BILINEAR)) > 127
    hh, ww = sm.shape
    seen = np.zeros_like(sm, bool)
    for y0 in range(hh):
        for x0 in range(ww):
            if sm[y0, x0] and not seen[y0, x0]:
                q = deque([(y0, x0)]); seen[y0, x0] = True; cells = []
                while q:
                    cy, cx = q.popleft(); cells.append((cy, cx))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < hh and 0 <= nx < ww and sm[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True; q.append((ny, nx))
                if len(cells) < 150:
                    for cy, cx in cells:
                        land[cy * 8:cy * 8 + 8, cx * 8:cx * 8 + 8] = True
    land |= erode(warp(mask(poly_mask([JAPAN, CEYLON, LEDYSHKA, SPAIN]))), 8)          # острова из docs/08 не исчезают при размытии
    land &= ~lake
    land &= ~warp(mask(draw_fjords))                                             # фьорды вырезаем после сглаживания

    # --- рельеф
    RL = ridges + SIBERIA_RIDGES + [BRITAIN_RIDGE, FIG_RIDGE]
    valley = warp(mask(line_mask(rivers, 6))) & land
    cliffs = warp(mask(lambda d: [d.line(px(q), fill=255, width=int(14 * SX), joint="curve") for q in FJORDS])) & land
    low = warp(mask(line_mask(RL, 70))) & land
    low |= warp(mask(line_mask([japan_axis()], 12))) & land                   # у Чёрной Республики полосы уже: остаются равнины
    low |= warp(mask(poly_mask([aid]))) & land
    hills = warp(mask(line_mask(RL, 44))) & land
    hills |= warp(mask(line_mask([japan_axis()], 6))) & land
    hills |= warp(mask(poly_mask([FIG_HILLS]))) & land
    hills |= warp(mask(draw_kazual_hills)) & land
    mount = (warp(mask(line_mask(RL, 15)))
             | warp(mask(line_mask([japan_axis()], 3))) | warp(mask(draw_core)) | warp(mask(poly_mask([aid])))) & land
    steep = warp(mask(draw_steep)) & land
    peaks = (warp(mask(draw_peaks)) | warp(mask(line_mask(AID_RIDGES, 9)))) & land
    plateau = warp(mask(poly_mask([SIBERIA_PLATEAU, chelyaba]))) & land         # плоскогорья: Сибирь и Челяба

    small = Image.fromarray((land | lake).astype(np.uint8) * 255).resize((W // 8, H // 8), Image.BILINEAR)
    near = np.asarray(small.filter(ImageFilter.MaxFilter(13)).resize((W, H), Image.NEAREST)) > 127

    # цвета, которые программа понимает без ручной разметки (справка Land Input); ocean/deepOcean в программе перепутаны местами
    COL = {
        "deepOcean": (0, 0, 255), "ocean": (0, 0, 128), "lake": (0, 80, 140),
        "plains": (128, 128, 128), "highlands": (200, 180, 180), "lowhills": (150, 180, 150), "hills": (140, 160, 150),
        "mountains": (220, 220, 220), "peaks": (240, 240, 240),
        "steeppeaks": (255, 255, 255), "cliffs": (220, 200, 200), "valley": (180, 250, 180),
    }
    img = np.zeros((H, W, 3), np.uint8)
    img[:] = COL["deepOcean"]
    img[near] = COL["ocean"]
    img[lake] = COL["lake"]
    img[land] = COL["plains"]
    img[valley] = COL["valley"]
    img[cliffs] = COL["cliffs"]
    img[plateau] = COL["highlands"]
    img[low] = COL["lowhills"]
    img[hills] = COL["hills"]
    img[mount] = COL["mountains"]
    img[peaks] = COL["peaks"]
    img[steep] = COL["steeppeaks"]
    jg = warp(mask(poly_mask([FIG_JUNGLE]))) & land
    Image.fromarray((jg * 255).astype(np.uint8)).save(os.path.join(OUT, "stage_01_jungle_mask.png"))
    d = os.path.join(OUT, "stage_01")
    os.makedirs(d, exist_ok=True)
    Image.fromarray(img, "RGB").save(os.path.join(d, "land.png"))
    Image.fromarray(img, "RGB").resize((W // 4, H // 4), Image.NEAREST).save(os.path.join(d, "land_preview.png"))
    with open(os.path.join(d, "colors.txt"), "w", encoding="utf-8") as f:
        f.write("Цвета land.png (RGB): программа понимает их сама (справка вкладки Land Input)" + chr(10))
        for k, v in COL.items():
            f.write(f"{v[0]:3d} {v[1]:3d} {v[2]:3d}  {k}" + chr(10))

    # --- контроль площадей островов и материков (по маске, до размывки гор)
    land_all = land | lake
    sm2 = np.asarray(Image.fromarray(land_all.astype(np.uint8) * 255).resize((W // 4, H // 4), Image.NEAREST)) > 127
    seen2 = np.zeros_like(sm2, bool)

    def comp_area(x_u, y_u):
        sx, sy = int((x_u * SX + OX) / 4), int((y_u * SY + OY) / 4)
        if not sm2[sy, sx]:
            return 0
        seen2[:] = False
        q = deque([(sy, sx)]); seen2[sy, sx] = True; n = 0
        while q:
            cy, cx = q.popleft(); n += 1
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < sm2.shape[0] and 0 <= nx < sm2.shape[1] and sm2[ny, nx] and not seen2[ny, nx]:
                    seen2[ny, nx] = True; q.append((ny, nx))
        return n * 16 / (SX * SY) * KM2_PER_U2                                    # км^2

    checks = {"Чёрная Республика (Япония 378 тыс.)": centroid(japan_axis()), "Остров на юге Ирракии (Цейлон 65,6 тыс.)": centroid(CEYLON),
              "Ледышка (Гренландия 2166 тыс.)": centroid(LEDYSHKA), "Южный материк (1/2 Африки ~15100 тыс.)": centroid(SOUTH)}
    print("площади по маске, тыс. км^2 (мелкие острова считаются отдельно, материк с полуостровом Испании слит):")
    for k, c in checks.items():
        print(f"  {k}: {comp_area(*c) / 1000:.0f}")
    print("stage_01:", {k: int((img == np.array(v)).all(-1).sum()) for k, v in COL.items()})
    return {"land": land, "lake": lake, "peaks": peaks, "steep": steep}


# --- этап 2: климат (цвета из справки вкладки Climate Input; в PDF другие, сверять с экраном программы)
CLIM = {
    "ocean": (21, 39, 92), "tropicsrainforest": (64, 80, 41), "tropicsmonsoon": (69, 87, 61), "tropicssavanna": (92, 82, 54),
    "desert": (200, 163, 128), "colddesert": (176, 158, 135), "hotsemiarid": (147, 134, 107), "coldsemiarid": (140, 126, 107),
    "temperatehot": (74, 88, 66), "temperatewarm": (54, 78, 56), "temperatecold": (29, 68, 50),
    "continentalwarm": (75, 86, 75), "continentalcold": (94, 95, 84), "polartundra": (133, 116, 96),
    "polararctic": (158, 170, 187), "snow": (240, 240, 240),
}
CLIM_BY_NAME = {
    "Тямовский рейх": "temperatewarm", "Айдалия": "temperatewarm", "Северная Ассамблея": "temperatecold",
    "Федерация Депутатов": "temperatewarm", "Советский Союз": "continentalcold", "Дмитровское Княжество": "coldsemiarid",
    "Казачья Земля": "coldsemiarid", "Казуалия": "temperatecold", "Челяба": "temperatewarm", "Иракиккистан": "tropicsmonsoon",
    "Ирракия": "tropicsmonsoon", "Муси": "tropicsrainforest", "Травинная Федерация": "tropicssavanna", "Магнолия": "desert",
    "Сарайкумское Ханство": "hotsemiarid", "Кытай": "temperatewarm", "Соевая Республика": "temperatehot",
    "Зеленодольск": "temperatewarm", "Наши Болота": "temperatecold", "Заготовка": "temperatehot",
}
def cwarp(im):
    return np.asarray(im)[CSYI, CSXI] > 127


def stage2():
    m1 = stage1()
    global CSXI, CSYI
    CLIM_DX = field((30, 20), 45) + field((90, 60), 18)                                # доп. смещение: границы зон неровные, переходы мягче
    CLIM_DY = field((30, 20), 45) + field((90, 60), 18)
    CSXI = np.clip((xx_ + DX + CLIM_DX).round().astype(np.int32), 0, W - 1)
    CSYI = np.clip((yy_ + DY + CLIM_DY).round().astype(np.int32), 0, H - 1)
    land = m1["land"] | m1["lake"]
    codes = {k: i + 1 for i, k in enumerate(CLIM)}
    lab = np.zeros((H, W), np.uint8)

    def paint(polys, kind):
        mk = cwarp(mask(poly_mask(polys)))
        lab[mk] = codes[kind]

    named = []
    for m in re.finditer(r"<polygon([^>]*)points=\"([^\"]+)\"([^>]*)/>\s*<!--\s*([^>]*?)\s*-->", svg):
        attrs = m.group(1) + m.group(3)
        if 'class="c' not in attrs and "dedacb" not in attrs:
            continue
        key = next((v for k, v in CLIM_BY_NAME.items() if m.group(4).startswith(k)), None)
        if key:
            named.append((parse(m.group(2)), key))
    for poly, key in named:
        paint([poly], key)
    inf = []
    for g in re.findall(r"<g class=\"c inf\"[^>]*>(.*?)</g>", svg, re.S):
        for k, s_ in enumerate(re.findall(r"points=\"([^\"]+)\"", g)):
            inf.append([(x + (0, 20, 45)[min(k, 2)], y + 30) for x, y in parse(s_)])
    paint(inf, "tropicssavanna")
    paint([JAPAN], "temperatewarm"); paint([CEYLON], "tropicsrainforest"); paint([LEDYSHKA], "polararctic")
    paint([SPAIN, SPAIN_BRIDGE], "temperatehot"); paint([DM_WIDER], "coldsemiarid")
    paint([SOUTH], "tropicssavanna")
    paint([KAMCHATKA] + SSSR_CAPES, "polartundra")
    paint([SIBERIA_PLATEAU], "continentalcold")
    paint([parse("700,60 1460,60 1460,200 1180,215 940,190 700,170")], "polartundra")          # север СССР: тундра
    paint([parse("700,60 1460,60 1460,115 1180,125 940,110 700,105")], "polararctic")          # северный берег СССР: арктика
    paint([parse("322,60 388,60 388,305 322,305")], "polartundra")                              # горы Северной Ассамблеи
    paint([FIG_JUNGLE], "tropicsrainforest"); paint([FIG_HILLS], "tropicsmonsoon")
    jb = cwarp(mask(lambda d: d.line(px(JUNGARIK), fill=255, width=int(120 * SX), joint="curve")))
    lab[jb] = codes["temperatewarm"]                                                                     # восток Фигарии у реки: умеренный
    lab[m1["peaks"] | m1["steep"]] = codes["snow"]
    # земля без метки (кайма из-за смещения границ) берёт ближайшую метку: растим метки на 1/4 разрешения
    sm = lab[::4, ::4].copy()
    for _ in range(40):
        for sh, ax in ((1, 0), (-1, 0), (1, 1), (-1, 1)):
            nb = np.roll(sm, sh, axis=ax)
            sm = np.where((sm == 0) & (nb > 0), nb, sm)
    grown = np.repeat(np.repeat(sm, 4, axis=0), 4, axis=1)[:H, :W]
    lab = np.where(lab == 0, grown, lab)
    lab[lab == 0] = codes["temperatewarm"]

    img = np.zeros((H, W, 3), np.uint8)
    img[:] = CLIM["ocean"]
    for k, v in CLIM.items():
        if k == "ocean":
            continue
        img[(lab == codes[k]) & land] = v
    d = os.path.join(OUT, "stage_02")
    os.makedirs(d, exist_ok=True)
    Image.fromarray(img, "RGB").save(os.path.join(d, "climate.png"))
    Image.fromarray(img, "RGB").resize((W // 4, H // 4), Image.NEAREST).save(os.path.join(d, "climate_preview.png"))
    with open(os.path.join(d, "colors.txt"), "w", encoding="utf-8") as f:
        f.write("Цвета climate.png (RGB), справка вкладки Climate Input" + chr(10))
        for k, v in CLIM.items():
            f.write(f"{v[0]:3d} {v[1]:3d} {v[2]:3d}  {k}" + chr(10))
    print("stage_02:", {k: int((img == np.array(v)).all(-1).sum()) for k, v in CLIM.items()})


if __name__ == "__main__":
    st = sys.argv[1] if len(sys.argv) > 1 else "1"
    {"1": stage1, "2": stage2}[st]()
