"""Bring province terrain (map/definition.csv, column 7) in line with explicit terrain statements in docs/lore/Contries-Description.md.

Only rules that need no map position are applied (lore is the single source, nothing else is invented):
  CSL Казуалия       "Большая часть клеток - болота, немного гор, равнины на краях"     : hills -> marsh
  ADL Айдалия        "рельеф: горы, высокогорные долины"                                : plains, forest -> hills
  MGN Магнолия       "рельеф: пустыня, горы"                                            : plains -> desert
  SVA Северная Ассамблея "холодные леса, озёра, горы на западе"                         : plains -> forest
plus a technical fix: provinces with terrain "unknown" take the most common terrain of their state.
Urban provinces are never changed. Only the gameplay type in definition.csv changes; map/terrain.bmp (the look) is not touched [uncertain: HOI4 may
show the old texture].
INVENTED position rules (invented_lore.py, docs/lore/Invented-Lore.md; lore names the places but gives no coordinates): Наши Болота (SVS provinces in a box -> marsh),
Фигарийский хребет (east-west band -> mountain), джунгли южнее хребта, холмы на западе, саванна (plains) на севере Фигарии,
кольцо гор (3 neighbours N, E, W) вокруг столичной провинции Казуалии.
Backup: no_commit/temp/backup_terrain/definition.csv. Usage: python tools/set_terrain.py [--mod PATH] [--restore]
"""
import argparse, collections, shutil
from pathlib import Path
import lore_data as L
import invented_lore as INV

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

# ---- INVENTED positions (docs/lore/Invented-Lore.md): lore names the places but gives no coordinates ----
cent, idxmap = L.province_centroids(M)
extra = {}                                           # province id -> (terrain, rule)
nb = collections.defaultdict(set)
import numpy as np
for A, B in ((idxmap[:, :-1], idxmap[:, 1:]), (idxmap[:-1], idxmap[1:])):
    m_ = A != B
    for x, y in np.unique(np.stack([A[m_], B[m_]], 1), axis=0).tolist():
        nb[x].add(y); nb[y].add(x)
nbz = INV.NASHI_BOLOTA
for pid, lt in prov_lore.items():
    x, y = cent[pid]
    if lt == nbz["country"] and nbz["x"][0] <= x <= nbz["x"][1] and nbz["y"][0] <= y <= nbz["y"][1] and terr.get(pid) in nbz["from"]:
        extra[pid] = (nbz["to"], "invented: Наши Болота (SVS)")
    if lt == "FIG" and terr.get(pid) not in ("urban",):
        if INV.FIG_RIDGE_Y[0] <= y <= INV.FIG_RIDGE_Y[1]:
            extra[pid] = ("mountain", "invented: Фигарийский хребет")
        elif y > INV.FIG_JUNGLE_SOUTH_OF_Y:
            extra[pid] = ("jungle", "invented: джунгли южнее хребта (FIG)")
        elif x < INV.FIG_WEST_HILLS_X and terr.get(pid) in ("plains", "forest"):
            extra[pid] = ("hills", "invented: холмы на западе (FIG)")
        elif terr.get(pid) == "forest":
            extra[pid] = ("plains", "invented: саванна на севере (FIG)")
# ring of mountains round the capital province of Казуалия: neighbours closest to north, east and west (not south)
cpx, cpy = INV.CSL_CAPITAL_PIXEL
cap_prov = int(idxmap[cpy, cpx])
cx0, cy0 = cent[cap_prov]
for dvx, dvy in ((0, -1), (1, 0), (-1, 0)):
    best = max((q for q in nb[cap_prov] if q in terr and q not in extra),
               key=lambda q: ((cent[q][0] - cx0) * dvx + (cent[q][1] - cy0) * dvy) / (((cent[q][0] - cx0) ** 2 + (cent[q][1] - cy0) ** 2) ** 0.5 + 1e-9), default=None)
    if best is not None and prov_lore.get(best):
        extra[best] = ("mountain", "invented: кольцо гор у столицы Казуалии")

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
        if pid in extra and p[4] == "land" and t != "urban" and pid != cap_prov:
            new = extra[pid][0]
            if new != t: changes[(extra[pid][1], t, new)] += 1
        elif new == t and t == "unknown" and prov_state.get(pid) in state_terr and state_terr[prov_state[pid]]:
            new = state_terr[prov_state[pid]].most_common(1)[0][0]; changes[("fix", t, new)] += 1
        if new != t:
            p[6] = new
            l = ";".join(p) + ("\r" if l.endswith("\r") else "")
    out.append(l)
DEF.write_bytes("\n".join(out).encode("latin1"))
for k, v in sorted(changes.items()): print(k, v)
print("total provinces changed:", sum(changes.values()))
