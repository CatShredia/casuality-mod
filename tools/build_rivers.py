"""Build the river network (mouths, tributaries, widths) and write it into the mod's map/rivers.bmp.

Input : tools/rp_input/stage_03/river_runs.json (38 polylines from export_rp_inputs.py),
        no_commit/temp/rivers.bmp.orig (RandomParadox export: land 255, water 254), mod map/heightmap.bmp.
Steps : 1) paint each polyline 4-connected, snapped to land; pick the mouth end (lower, nearer the sea);
        2) extend every river that stops inland to the sea or to another river (cheapest way downhill);
        3) add tributaries (random but seeded) that flow into a river;
        4) width index: source 3, +1 after each tributary joins (capped by --max-idx); tributaries stay 3;
        5) tributary last pixel gets index 1 (merge marker, [uncertain] per wiki; --no-merge-marker to disable).
Tributaries and extensions are generated, they are NOT lore.

Usage: python tools/build_rivers.py [--seed N] [--max-idx 6] [--trib-per 110] [--no-merge-marker]
The script writes no_commit/temp/rivers_new.bmp and tries to copy it into the mod; if Windows refuses the copy, use
cp no_commit/temp/rivers_new.bmp "<mod>/map/rivers.bmp".
"""
import argparse, heapq, json, random, shutil, time
from pathlib import Path
import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parent.parent
MOD = Path("C:/Users/catsh/CatshrediasDocs/Paradox Interactive/Hearts of Iron IV/mod/Ktits")
RUNS = REPO / "tools" / "rp_input" / "stage_03" / "river_runs.json"
TMP = REPO / "no_commit" / "temp"

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=str(MOD))
ap.add_argument("--seed", type=int, default=2026)
ap.add_argument("--max-idx", type=int, default=6, help="widest palette index (3..11)")
ap.add_argument("--trib-per", type=int, default=110, help="one tributary per this many river pixels")
ap.add_argument("--snap", type=int, default=2)
ap.add_argument("--no-merge-marker", action="store_true")
ap.add_argument("--no-tributaries", action="store_true")
a = ap.parse_args()
rnd = random.Random(a.seed)

orig = np.array(Image.open(TMP / "rivers.bmp.orig"))
H, W = orig.shape
water = orig == 254
land = ~water
hmap = np.array(Image.open(Path(a.mod) / "map" / "heightmap.bmp")).astype(np.int32)
pal = json.loads((REPO / "tools" / "rivers_palette.json").read_text())

# smooth noise so that routes on flat ground meander instead of running straight
_g = np.random.RandomState(a.seed).rand(H // 24 + 2, W // 24 + 2).astype(np.float32)
noise = np.array(Image.fromarray(_g).resize((W // 24 * 24 + 48, H // 24 * 24 + 48), Image.BICUBIC))[:H, :W]

# coast pixels (land touching water), sampled, for distance to sea
touch = np.zeros_like(water)
touch[1:] |= water[:-1]; touch[:-1] |= water[1:]; touch[:, 1:] |= water[:, :-1]; touch[:, :-1] |= water[:, 1:]
cy, cx = np.nonzero(touch & land)
cy, cx = cy[::3], cx[::3]
def dsea(p):
    return float(np.sqrt((cx - p[0]) ** 2 + (cy - p[1]) ** 2).min())

def at_water(p):
    x, y = p
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        xx, yy = x + dx, y + dy
        if 0 <= xx < W and 0 <= yy < H and water[yy, xx]:
            return True
    return False

def snap(p):
    x, y = p
    for r in range(a.snap + 1):
        ys, xs = slice(max(y - r, 0), y + r + 1), slice(max(x - r, 0), x + r + 1)
        cand = np.argwhere(land[ys, xs])
        if len(cand):
            d = np.abs(cand[:, 0] + ys.start - y) + np.abs(cand[:, 1] + xs.start - x)
            c = cand[d.argmin()]
            return (int(c[1] + xs.start), int(c[0] + ys.start))
    return None

def connect(path, q):
    """append q to path with a 4-connected walk (x first, then y)"""
    if not path:
        path.append(q); return
    cx_, cy_ = path[-1]
    while (cx_, cy_) != q:
        if cx_ != q[0]: cx_ += 1 if q[0] > cx_ else -1
        else: cy_ += 1 if q[1] > cy_ else -1
        if land[cy_, cx_] and (cx_, cy_) != path[-1]:
            path.append((cx_, cy_))

# 1) main rivers
runs = json.loads(RUNS.read_text(encoding="utf-8"))
mains = []
for run in runs:
    path = []
    for pt in run:
        q = snap(pt)
        if q: connect(path, q)
    if len(path) < 2: continue
    s, e = path[0], path[-1]
    hs, he = hmap[s[1], s[0]], hmap[e[1], e[0]]
    flip = he > hs + 3 or (abs(hs - he) <= 3 and dsea(s) + 20 < dsea(e))
    if flip: path.reverse()
    mains.append(path)

owner = {}                                           # pixel -> (river id, index in its path)
paths = []                                           # all rivers, mains first
def register(path):
    rid = len(paths); paths.append(path)
    for i, p in enumerate(path): owner.setdefault(p, (rid, i))
    return rid
for p in mains: register(p)

def route(start, own_ids, limit=250000):
    """cheapest way from start over land to the sea or to a pixel of another river; downhill preferred.
    returns (path excluding the target, target) where target is ('sea',) or ('river', rid, idx)"""
    dist = {start: 0.0}; prev = {}; pq = [(0.0, start)]; n = 0
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, 1e18): continue
        n += 1
        if n > limit: return None
        x, y = u
        if u != start and at_water(u):
            out = [u]
            while out[-1] in prev: out.append(prev[out[-1]])
            return out[::-1], ("sea",)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            v = (x + dx, y + dy)
            if not (0 <= v[0] < W and 0 <= v[1] < H) or not land[v[1], v[0]]: continue
            o = owner.get(v)
            if o and o[0] not in own_ids:
                out = [u]
                while out[-1] in prev: out.append(prev[out[-1]])
                return out[::-1], ("river", o[0], o[1])
            if o: continue                          # never run along our own river
            dh = int(hmap[v[1], v[0]]) - int(hmap[y, x])
            nd = d + 1.0 + 3.0 * float(noise[v[1], v[0]]) + (4.0 * dh if dh > 0 else 0.0)
            if nd < dist.get(v, 1e18):
                dist[v] = nd; prev[v] = u; heapq.heappush(pq, (nd, v))
    return None

joins = []                                           # (river id joined into, index in it)
parent = {}                                          # river id -> (target river id, index) it flows into
stats = {"to_sea": 0, "to_river": 0, "already": 0, "failed": 0, "trib": 0}
# 2) mouths
for rid in range(len(mains)):
    path = paths[rid]
    if at_water(path[-1]):
        stats["already"] += 1; continue
    res = route(path[-1], {rid})
    if not res:
        stats["failed"] += 1; continue
    ext, tgt = res
    for p in ext[1:]:
        owner.setdefault(p, (rid, len(path))); path.append(p)
    if tgt[0] == "sea": stats["to_sea"] += 1
    else:
        stats["to_river"] += 1; parent[rid] = (tgt[1], tgt[2])
        paths[rid] = path

# 3) tributaries
if not a.no_tributaries:
    for rid in range(len(mains)):
        path = paths[rid]
        n = len(path) // a.trib_per
        for k in range(n):
            i = int((k + 0.5 + rnd.uniform(-0.25, 0.25)) * len(path) / max(n, 1))
            i = min(max(i, 20), len(path) - 21)
            a0, a1 = path[i - 15], path[i + 15]
            tx, ty = a1[0] - a0[0], a1[1] - a0[1]
            nl = (tx * tx + ty * ty) ** 0.5 or 1
            nx, ny = -ty / nl, tx / nl
            side = 1 if (k % 2 == 0) else -1
            if rnd.random() < 0.3: side = -side
            L = rnd.randint(45, 130)
            sx, sy = int(path[i][0] + side * nx * L), int(path[i][1] + side * ny * L)
            if not (0 <= sx < W and 0 <= sy < H): continue
            s = snap((sx, sy))
            if not s or s in owner: continue
            res = route(s, set(), limit=60000)
            if not res: continue
            ext, tgt = res
            if tgt[0] != "river" or len(ext) < 25 or len(ext) > L * 2.2 + 30: continue
            if any(p in owner for p in ext): continue
            tid = register([s] + ext[1:])
            parent[tid] = (tgt[1], tgt[2]); stats["trib"] += 1
            paths[tid] = paths[tid]

# 4) widths: 3 at the source, +1 each time a river joins (counted along the receiving river)
idx_of = {}
nrivers = len(paths)
joins_at = {r: [] for r in range(nrivers)}
for child, (par, pi) in parent.items():
    joins_at[par].append(pi)
canvas = np.full((H, W), 255, np.uint8)
canvas[water] = 254
for rid in sorted(range(nrivers), key=lambda r: -r):  # tributaries first, mains last: mains keep the junction pixel
    path = paths[rid]
    js = sorted(joins_at[rid])
    for i, p in enumerate(path):
        w = min(3 + sum(1 for j in js if j <= i), a.max_idx)
        canvas[p[1], p[0]] = w
for rid in range(nrivers):
    path = paths[rid]
    if rid in parent and not a.no_merge_marker:
        p = path[-1]
        canvas[p[1], p[0]] = 1
    s = path[0]
    canvas[s[1], s[0]] = 0                          # source

out = Image.fromarray(canvas, "P")
out.putpalette(pal)
TMP.mkdir(parents=True, exist_ok=True)
tmp = TMP / "rivers_new.bmp"
out.save(tmp)
b = bytearray(tmp.read_bytes()); b[46:54] = bytes(8); tmp.write_bytes(b)   # vanilla header: biClrUsed = biClrImportant = 0

dst = Path(a.mod) / "map" / "rivers.bmp"
for attempt in range(3):
    try:
        shutil.copyfile(tmp, dst); copied = True; break
    except OSError:
        copied = False; time.sleep(1)
r = canvas < 254
print(f"mains {len(mains)}, tributaries {stats['trib']}, mouths: already at sea {stats['already']}, extended to sea {stats['to_sea']}, "
      f"into another river {stats['to_river']}, failed {stats['failed']}")
print(f"river px {int(r.sum())}, sources {int((canvas == 0).sum())}, idx counts "
      f"{dict(zip(*[v.tolist() for v in np.unique(canvas[r], return_counts=True)]))}")
print("written to the mod" if copied else f"copy failed (Windows Errno 22): cp {tmp} \"{dst}\"")
prev_img = np.full((H, W, 3), 255, np.uint8)
prev_img[water] = (200, 215, 235)
for w_, col in ((3, (0, 120, 255)), (4, (0, 80, 255)), (5, (0, 0, 220)), (6, (0, 0, 120))):
    prev_img[canvas == w_] = col
prev_img[canvas == 1] = (255, 0, 0); prev_img[canvas == 0] = (0, 200, 0)
Image.fromarray(prev_img).resize((W // 2, H // 2), Image.NEAREST).save(TMP / "rivers_network_preview.png")
