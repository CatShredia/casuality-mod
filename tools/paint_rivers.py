"""Draw our rivers into the exported mod's map/rivers.bmp (1 px lines, HOI4 palette indices).

RandomParadox routes rivers itself and keeps only ~8% of ours, so after each export this script
replaces its rivers with the lines from tools/rp_input/stage_03/river_runs.json.

Indices (HOI4 rivers.bmp palette): 0 source, 1 merge into a bigger river, 2 split, 3..11 width
(thin..wide), 254 water, 255 land. Our rivers use 0 at the source and widths 3..WIDEST along the length.

Usage: python tools/paint_rivers.py [--keep-program] [--widest N] [--mod PATH]
"""
import argparse, json, shutil
from pathlib import Path
import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parent.parent
MOD = Path("C:/Users/catsh/CatshrediasDocs/Paradox Interactive/Hearts of Iron IV/mod/Ktits")
RUNS = REPO / "tools" / "rp_input" / "stage_03" / "river_runs.json"
TMP = REPO / "no_commit" / "temp"

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=str(MOD))
ap.add_argument("--keep-program", action="store_true", help="keep the rivers RandomParadox drew")
ap.add_argument("--widest", type=int, default=6, help="widest palette index used near the mouth (3..11)")
ap.add_argument("--dilate", type=int, default=0, help="thicken every river px by this radius (test only; vanilla rivers are 1 px)")
ap.add_argument("--per-river", action="store_true", help="test: river number k gets palette index 3 + k %% 6 along its whole length")
ap.add_argument("--only", type=int, default=None, help="test: paint only river number N")
ap.add_argument("--snap", type=int, default=2, help="pixels a river may be moved to reach land at the coast")
a = ap.parse_args()

bmp = Path(a.mod) / "map" / "rivers.bmp"
im = Image.open(bmp)
if im.mode != "P":
    raise SystemExit(f"rivers.bmp is {im.mode}, expected P (8 bit palette)")
pal = json.loads((REPO / 'tools' / 'rivers_palette.json').read_text())   # vanilla HOI4 palette; RandomParadox's differs and the game logs 'Palette in rivers.bmp is probably not correct'
arr = np.array(im)
H, W = arr.shape

TMP.mkdir(parents=True, exist_ok=True)
bak = TMP / "rivers.bmp.orig"
if not bak.exists():
    shutil.copy2(bmp, bak)

prog = arr < 254
print(f"rivers.bmp {W}x{H}: land {int((arr == 255).sum() + prog.sum())} px, program river px {int(prog.sum())}")
if not a.keep_program:
    arr[prog] = 255                                  # drop the program's own rivers
land = arr >= 255

runs = json.loads(RUNS.read_text(encoding="utf-8"))
if a.only is not None:
    runs = [runs[a.only]]
painted = lost = 0
unit = np.zeros((H, W), bool)
for ri, run in enumerate(runs):
    n = len(run)
    prev = None
    for i, (x, y) in enumerate(run):
        idx = 3 + min(int((i / max(n - 1, 1)) * (a.widest - 3 + 1)), a.widest - 3)
        if a.per_river:
            idx = 3 + ri % 6
        px = None
        for r in range(a.snap + 1):                  # coast of the generated map differs from land.png
            ys, xs = slice(max(y - r, 0), y + r + 1), slice(max(x - r, 0), x + r + 1)
            cand = np.argwhere(land[ys, xs])
            if len(cand):
                d = np.abs(cand[:, 0] + ys.start - y) + np.abs(cand[:, 1] + xs.start - x)
                cy, cx = cand[d.argmin()]
                px = (cx + xs.start, cy + ys.start)
                break
        if px is None:
            lost += 1
            continue
        if prev and px != prev:                      # run points can be 2-3 px apart: connect them 4-neighbour wise
            cx, cy = prev
            while (cx, cy) != px:
                if cx != px[0]:
                    cx += 1 if px[0] > cx else -1
                elif cy != px[1]:
                    cy += 1 if px[1] > cy else -1
                if land[cy, cx] and (cx, cy) != px:
                    arr[cy, cx] = idx
                    painted += 1
        arr[px[1], px[0]] = idx
        prev = px
        painted += 1
    # source marker on the first pixel that was painted
    for x, y in run:
        if 3 <= arr[y, x] <= 11:
            arr[y, x] = 0
            break

if a.dilate:
    rv = (arr >= 3) & (arr <= 11)
    for dy in range(-a.dilate, a.dilate + 1):
        for dx in range(-a.dilate, a.dilate + 1):
            sh = np.roll(np.roll(arr, dy, 0), dx, 1)
            m = (np.roll(np.roll(rv, dy, 0), dx, 1)) & (arr == 255)
            arr[m] = sh[m]
out = Image.fromarray(arr, "P")
out.putpalette(pal)
tmp = TMP / 'rivers_new.bmp'
out.save(tmp)
b = bytearray(tmp.read_bytes())                     # vanilla header has biClrUsed=biClrImportant=0, PIL writes 256
b[46:54] = bytes(8)
tmp.write_bytes(b)
import subprocess, time
for attempt in range(5):                             # Windows sometimes refuses the first open of a file in the mod folder (Errno 22)
    try:
        shutil.copyfile(tmp, bmp)
        break
    except OSError:
        time.sleep(1)
else:
    subprocess.check_call(["powershell", "-NoProfile", "-Command", f"Copy-Item -LiteralPath '{tmp}' -Destination '{bmp}' -Force"])
chk = Image.open(bmp)
assert chk.mode == "P" and chk.size == (W, H), "saved file lost its palette or size"
res = np.array(chk)
print(f"painted {painted} px, off land {lost} px, rivers {len(runs)}, sources {int((res == 0).sum())}")
print(f"river px in file now: {int((res < 254).sum())}; backup of the export: {bak}")
prev = np.full((H, W, 3), 255, np.uint8)
prev[res == 254] = (200, 215, 235)
prev[res < 254] = (0, 0, 255)
Image.fromarray(prev).resize((W // 2, H // 2), Image.NEAREST).save(TMP / "rivers_painted_preview.png")
