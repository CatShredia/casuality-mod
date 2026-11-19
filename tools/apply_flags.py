"""Hand-made country flags (from image_generator/flags, 32-bit TGA 82x52 / 41x26 / 10x7): copies gfx_src/flags/**/<TAG>.tga into the mod's gfx/flags/**.
Overrides the RandomParadox flags and the plain stripes of make_iberia_split.py (run after it; idempotent). Update the sources with
`python tools/apply_flags.py --pull` (copies D:/directory-git/image_generator/flags/out/gfx/flags/** into gfx_src/flags/).
Usage: python tools/apply_flags.py [--mod PATH] [--pull]"""
import argparse, shutil
from pathlib import Path
import lore_data as L

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
ap.add_argument("--pull", action="store_true")
a = ap.parse_args()
M = Path(a.mod)
SRC = Path(__file__).resolve().parent.parent / "gfx_src" / "flags"
if a.pull:
    out = Path(r"D:\directory-git\image_generator\flags\out\gfx\flags")
    for f in out.rglob("*.tga"):
        dst = SRC / f.relative_to(out); dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(f, dst)
n, tags = 0, set()
for f in sorted(SRC.rglob("*.tga")):
    dst = M / "gfx/flags" / f.relative_to(SRC)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists() or dst.read_bytes() != f.read_bytes():
        shutil.copyfile(f, dst); n += 1
    tags.add(f.stem)
print(f"flags: {len(tags)} hand-made ({', '.join(sorted(tags))}), {n} files written")
