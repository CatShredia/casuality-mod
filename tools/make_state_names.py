"""Name every state of the exported mod after the lore country that owns it.

RandomParadox gives the mod its own tags, but the country colors equal the lore colors, so owner tag -> color -> lore
country (see lore_data.py). The state containing a lore capital gets the capital's name, the other lore cities go to the
next biggest states, the rest is "<country> N" (--mode lore, default) or a generated name in the country's cultural style
(--mode style; invented, NOT lore). All names are unique.

Writes localisation/russian and localisation/english state_names and no_commit/temp/state_names_report.csv.
Usage: python tools/make_state_names.py [--mode lore|style] [--seed N] [--mod PATH]
"""
import argparse, csv, random
import lore_data as L

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
ap.add_argument("--seed", type=int, default=2026)
ap.add_argument("--mode", choices=["lore", "style"], default="lore")
a = ap.parse_args()

info = L.load_mod(a.mod)
names, kind, _ = L.assign_state_names(info, a.mode, random.Random(a.seed))
M = a.mod
L.write_yml(f"{M}/localisation/russian/state_names_l_russian.yml", "russian", [(f"STATE_{s}", names[s]) for s in sorted(names)])
L.write_yml(f"{M}/localisation/english/state_names_l_english.yml", "english", [(f"STATE_{s}", L.translit(names[s])) for s in sorted(names)])

rep = L.REPO / "no_commit/temp/state_names_report.csv"
rep.parent.mkdir(parents=True, exist_ok=True)
with open(rep, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["state", "mod_tag", "lore_country", "name", "source"])
    for sid in sorted(names):
        o = info["states"][sid]["owner"]
        w.writerow([sid, o, info["tag2lore"].get(o, "?"), names[sid], kind[sid]])
print(f"mode {a.mode}: states {len(names)}, unique {len(set(names.values()))}, lore {sum(1 for k in kind.values() if k.startswith('lore'))}, "
      f"generated {sum(1 for k in kind.values() if k.startswith('generated'))}, numbered {sum(1 for k in kind.values() if k.startswith('numbered'))}")
print("report:", rep)
