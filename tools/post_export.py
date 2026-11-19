"""Run every post-export step on the freshly exported mod, check it, and zip it. Run this after each RandomParadox export.

Order: rivers -> iberia (new country Z06 split off the old Iberadia) -> population -> state names -> city names -> countries -> ideologies -> rulers -> casuality -> focuses -> game rules -> vanilla leftovers -> education -> splits -> alliances -> continuous -> terrain -> kazualia -> kazouter -> debug (journal, last of the generators) -> strategic regions -> check -> zip.
Each step is its own script and can still be run alone. The steps are idempotent, so running the whole chain twice is safe.

Rivers: RandomParadox's own rivers.bmp is saved as no_commit/temp/rivers.bmp.orig whenever the mod's file is not the one this chain built
(compared by sha256 with no_commit/temp/rivers_built.sha), so a new export is detected automatically.

Usage: python tools/post_export.py [--names-mode style|lore] [--max-idx N] [--no-zip] [--skip a,b] [--mod PATH]
  --names-mode  how states/cities without lore names are named (default: style = generated names in the country's style; lore = "<country> N")
  --max-idx     widest river palette index (default 3: width by index is not confirmed in the game yet)
  --skip        comma separated steps to skip: rivers,iberia,population,states,cities,countries,ideologies,rulers,casuality,focuses,gamerules,leftovers,education,splits,alliances,continuous,terrain,kazualia,kazouter,debug,regions,check,zip
"""
import argparse, hashlib, shutil, subprocess, sys, time
from pathlib import Path
import lore_data as L

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
ap.add_argument("--names-mode", choices=["style", "lore"], default="style")
ap.add_argument("--max-idx", type=int, default=3)
ap.add_argument("--no-zip", action="store_true")
ap.add_argument("--skip", default="")
a = ap.parse_args()
skip = {s for s in a.skip.split(",") if s}
if a.no_zip: skip.add("zip")
T = Path(__file__).resolve().parent
TMP = L.REPO / "no_commit/temp"
mod_rivers = Path(a.mod) / "map/rivers.bmp"
SHA = TMP / "rivers_built.sha"

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def run(name, *args):
    t0 = time.time()
    print(f"\n=== {name} ===", flush=True)
    r = subprocess.run([sys.executable, "-X", "utf8", str(T / args[0]), *args[1:]], cwd=str(L.REPO))
    dt = time.time() - t0
    times[name] = dt
    print(f"--- {name}: exit {r.returncode}, {dt:.1f} s", flush=True)
    return r.returncode

results = {}
times = {}      # seconds per step, printed in the summary
T_START = time.time()
m = ["--mod", a.mod]
if "rivers" not in skip:
    TMP.mkdir(parents=True, exist_ok=True)
    if not SHA.exists() or SHA.read_text().strip() != sha(mod_rivers):
        shutil.copyfile(mod_rivers, TMP / "rivers.bmp.orig")       # a fresh RandomParadox export
        print("rivers.bmp is a fresh export: saved as no_commit/temp/rivers.bmp.orig")
    results["rivers"] = run("rivers", "build_rivers.py", *m, "--max-idx", str(a.max_idx))
    if results["rivers"] == 0:
        SHA.write_text(sha(mod_rivers))
steps = [("iberia", ["make_iberia_split.py", *m]),
         ("population", ["set_population.py", *m]),
         ("states", ["make_state_names.py", *m, "--mode", a.names_mode]),
         ("cities", ["make_city_names.py", *m, "--mode", a.names_mode]),
         ("countries", ["make_countries.py", *m]),
         ("ideologies", ["make_ideologies.py", *m]),
         ("rulers", ["make_rulers.py", *m]),
         ("casuality", ["make_casuality.py", *m]),
         ("focuses", ["make_focuses.py", *m]),
         ("gamerules", ["make_game_rules.py", *m]),
         ("leftovers", ["fix_vanilla_leftovers.py", *m]),
         ("education", ["make_education.py", *m]),
         ("splits", ["make_splits.py", *m]),
         ("alliances", ["make_alliances.py", *m]),
         ("continuous", ["make_continuous.py", *m]),
         ("terrain", ["set_terrain.py", *m]),
         ("kazualia", ["make_kazualia.py", *m]),
         ("kazouter", ["make_kazualia_outer.py", *m]),
         ("debug", ["make_debug.py", *m]),
         ("regions", ["name_regions.py", *m]),
         ("icons", ["make_icons.py", *m]),
         ("check", ["check_mod.py", *m])]
for name, args in steps:
    if name not in skip:
        results[name] = run(name, *args)
if "zip" not in skip:
    results["zip"] = run("zip", "zip_mod.py")

print("\n=== summary ===")
for k, v in results.items():
    print(f"{k:11s} {'ok' if v == 0 else 'FAILED (exit ' + str(v) + ')':22s} {times.get(k, 0):6.1f} s")
print(f"{'total':11s} {'':22s} {time.time() - T_START:6.1f} s")
sys.exit(1 if any(v for v in results.values()) else 0)
