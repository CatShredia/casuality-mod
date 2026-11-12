"""Name the victory-point cities (VICTORY_POINTS_<province id>) of the exported mod.

Same logic as make_state_names.py (run with the same --mode and --seed so both agree):
 * in a state that got a lore capital/city name, its biggest victory point carries that name (the state is named after
   its main city);
 * every other victory point gets a unique name: generated in the country's style (--mode style, invented, NOT lore),
   or "<state name>, город N" (--mode lore, default).
Names never repeat across cities, and never repeat a state name (except the lore city that gives its state its name).

Writes localisation/russian and localisation/english victory_points and no_commit/temp/city_names_report.csv.
Usage: python tools/make_city_names.py [--mode lore|style] [--seed N] [--mod PATH]
"""
import argparse, csv, random
import lore_data as L

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
ap.add_argument("--seed", type=int, default=2026)
ap.add_argument("--mode", choices=["lore", "style"], default="lore")
a = ap.parse_args()

rnd = random.Random(a.seed)
info = L.load_mod(a.mod)
snames, skind, used = L.assign_state_names(info, a.mode, rnd)        # same call as make_state_names.py
states, tag2lore = info["states"], info["tag2lore"]

vp_names, vp_kind = {}, {}
for sid in sorted(states):
    vps = sorted(states[sid]["vps"], key=lambda pv: (-pv[1], pv[0]))
    lt = tag2lore.get(states[sid]["owner"])
    style = L.COUNTRY_STYLE.get(lt, L.STYLE_DEFAULT) if a.mode == "style" else "numbered"
    for i, (prov, val) in enumerate(vps):
        if i == 0 and skind[sid].startswith("lore"):
            vp_names[prov] = snames[sid]; vp_kind[prov] = "lore (same as its state)"; continue
        if style == "numbered":
            n = i + (0 if skind[sid].startswith("lore") else 1)
            nm = f"{snames[sid]}, город {n + 1}" if skind[sid].startswith("lore") else f"{snames[sid]}, город {i + 1}"
            vp_names[prov] = nm; vp_kind[prov] = "numbered"; continue
        for _ in range(300):
            nm = L.gen(style, rnd)
            if nm not in used: break
        else:
            nm = L.gen(style, rnd) + f"-{prov}"
        used.add(nm); vp_names[prov] = nm; vp_kind[prov] = f"generated ({style})"

M = a.mod
L.write_yml(f"{M}/localisation/russian/victory_points_l_russian.yml", "russian", [(f"VICTORY_POINTS_{p}", vp_names[p]) for p in sorted(vp_names)])
L.write_yml(f"{M}/localisation/english/victory_points_l_english.yml", "english", [(f"VICTORY_POINTS_{p}", L.translit(vp_names[p])) for p in sorted(vp_names)])

rep = L.REPO / "no_commit/temp/city_names_report.csv"
rep.parent.mkdir(parents=True, exist_ok=True)
prov_state = {p: s for s, v in states.items() for p, _ in v["vps"]}
with open(rep, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["province", "state", "state_name", "name", "source"])
    for p in sorted(vp_names):
        w.writerow([p, prov_state[p], snames[prov_state[p]], vp_names[p], vp_kind[p]])
vals = list(vp_names.values())
lore_pairs = sum(1 for k in vp_kind.values() if k.startswith("lore"))
print(f"mode {a.mode}: victory points {len(vals)}, unique {len(set(vals))} (the {lore_pairs} lore cities repeat their state name), "
      f"generated {sum(1 for k in vp_kind.values() if k.startswith('generated'))}, numbered {sum(1 for k in vp_kind.values() if k.startswith('numbered'))}")
print("report:", rep)
