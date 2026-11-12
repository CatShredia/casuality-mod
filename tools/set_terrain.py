"""Bring province terrain (map/definition.csv, column 7) in line with explicit terrain statements in docs/01.

Only rules that need no map position are applied (lore is the single source, nothing else is invented):
  CSL Казуалия       "Большая часть клеток - болота, немного гор, равнины на краях"     : hills -> marsh
  ADL Айдалия        "рельеф: горы, высокогорные долины"                                : plains, forest -> hills
  MGN Магнолия       "рельеф: пустыня, горы"                                            : plains -> desert
  SVA Северная Ассамблея "холодные леса, озёра, горы на западе"                         : plains -> forest
plus a technical fix: provinces with terrain "unknown" take the most common terrain of their state.
Urban provinces are never changed. Only the gameplay type in definition.csv changes; map/terrain.bmp (the look) is not touched [uncertain: HOI4 may
show the old texture]. Not applied (need a map position, see the report): Наши Болота (SVS), Фигарийский хребет и джунгли (FIG),
capital of CSL ringed by mountains.
Backup: no_commit/temp/backup_terrain/definition.csv. Usage: python tools/set_terrain.py [--mod PATH] [--restore]
"""
import argparse, collections, shutil
from pathlib import Path
import lore_data as L

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
ap.add_argument("--restore", action="store_true")
a = ap.parse_args()
M = Path(a.mod)
DEF = M / "map/definition.csv"
BK = L.REPO / "no_commit/temp/backup_terrain/definition.csv"
if a.restore:
    shutil.copyfile(BK, DEF); print("restored"); raise SystemExit
BK.parent.mkdir(parents=True, exist_ok=True)
if not BK.exists():
    shutil.copy2(DEF, BK)

RULES = {"CSL": {"hills": "marsh"}, "ADL": {"plains": "hills", "forest": "hills"},
         "MGN": {"plains": "desert"}, "SVA": {"plains": "forest"}}

info = L.load_mod(M)
prov_lore, prov_state = {}, {}
for sid, s in info["states"].items():
    lt = info["tag2lore"].get(s["owner"])
    for p in s["provs"]:
        prov_lore[p] = lt; prov_state[p] = sid

raw = DEF.read_bytes().decode("latin1")
rows = raw.split("\n")
terr = {}
for l in rows:
    p = l.strip().split(";")
    if len(p) > 6 and p[0].isdigit(): terr[int(p[0])] = p[6]
state_terr = collections.defaultdict(collections.Counter)
for p, t in terr.items():
    if p in prov_state and t not in ("unknown", "urban"): state_terr[prov_state[p]][t] += 1

changes = collections.Counter()
out = []
for l in rows:
    p = l.rstrip("\r").split(";")
    if len(p) > 6 and p[0].isdigit():
        pid, t = int(p[0]), p[6]
        new = t
        rule = RULES.get(prov_lore.get(pid))
        if rule and t in rule and p[4] == "land":
            new = rule[t]; changes[(prov_lore[pid], t, new)] += 1
        elif t == "unknown" and prov_state.get(pid) in state_terr and state_terr[prov_state[pid]]:
            new = state_terr[prov_state[pid]].most_common(1)[0][0]; changes[("fix", t, new)] += 1
        if new != t:
            p[6] = new
            l = ";".join(p) + ("\r" if l.endswith("\r") else "")
    out.append(l)
DEF.write_bytes("\n".join(out).encode("latin1"))
for k, v in sorted(changes.items()): print(k, v)
print("total provinces changed:", sum(changes.values()))
