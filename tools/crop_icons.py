"""Manual helper (NOT a build step): rebuilds gfx_src/ideas/<id>.png (65x67) from the big ComfyUI sources
spirit_<id>_full_00001_.png (or spirit_<id>_full.png). The sources are full-frame illustrations with a paper/green frame, not
cut-outs on black, so the frame is trimmed (CROP share per side), the rest is cut to 65:67 around the centre of mass of the
picture (no distortion, no padding needed), shrunk with LANCZOS and lightly sharpened. Compare sheet: no_commit/temp/icons_compare.png.
Usage: python tools/crop_icons.py [--src DIR] [--crop 0.06]"""
import argparse, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "gfx_src/ideas"
W, H = 65, 67
ap = argparse.ArgumentParser()
ap.add_argument("--src", default=r"D:\ComfyUI_windows_portable\ComfyUI\output\ktits")
ap.add_argument("--crop", type=float, default=0.06)
a = ap.parse_args()
S = Path(a.src)

def frac(im, thr=25):
    """share of the frame covered by the bounding box of pixels differing from the background (black for old icons, border colour otherwise)"""
    g = np.asarray(im.convert("RGB")).astype(int)
    d = g.sum(2) > thr * 3
    ys, xs = np.where(d)
    return 0.0 if len(ys) == 0 else (ys.max() - ys.min() + 1) * (xs.max() - xs.min() + 1) / (g.shape[0] * g.shape[1])

def src_of(i):
    for n in (f"spirit_{i}_full_00001_.png", f"spirit_{i}_full.png"):
        if (S / n).exists(): return S / n

rows = []
for f in sorted(ICONS.glob("*.png")):
    i = f.stem
    if i.startswith(("spirit", "portrait")): continue
    p = src_of(i)
    if p is None: print("no source:", i); continue
    old = Image.open(f).convert("RGB")
    old.save(ICONS.parent.parent / "no_commit/temp" / f"old_{i}.png")
    im = Image.open(p).convert("RGB"); w, h = im.size
    m = int(w * a.crop); im = im.crop((m, m, w - m, h - m)); w, h = im.size
    # 65:67 window (taller than wide): full width, height w*67/65
    ch = round(w * H / W)
    top = max(0, min(h - ch, (h - ch) // 2))
    im = im.crop((0, top, w, top + ch)).resize((W, H), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=0.8, percent=60, threshold=2))
    im.save(f)
    rows.append((i, frac(old), frac(im)))
print("id; share of frame occupied by the picture (bbox of non-black), before -> after")
for i, o, n in rows: print(f"{i}: {o*100:.0f}% -> {n*100:.0f}%")
