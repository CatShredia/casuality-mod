"""Name the strategic regions (localisation/*/strategic_region_names_l_*.yml).

Lore (docs/lore/Contries-Description.md, docs/map/Geography.md) names only four seas: Синее море, Кряхтское море, Среднее море, Океан. Land regions have no names in the lore.
 * land region -> "<lore country>, район N" (the country that owns most of its provinces);
 * sea region  -> the lore sea chosen by which countries touch it (this is an inference from the lore geography, listed in the report):
     Синее море   : touches Северная Ассамблея (SVA) and one of Федерация Депутатов / Советский Союз / Тямовский рейх;
     Кряхтское    : touches Казачья Земля (KZZ);
     Среднее      : touches Соевая Республика / Фигария / заготовки Z01-Z04 (and none of the above);
     Океан        : everything else;
   when a sea gets several regions they are numbered ("Синее море, район 2").
Usage: python tools/name_regions.py [--mod PATH]
"""
import argparse, collections, csv, glob, re
from pathlib import Path
import lore_data as L

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
a = ap.parse_args()
M = Path(a.mod)

info = L.load_mod(M)
ptype = {}
for l in open(M / "map/definition.csv", encoding="latin1"):
    p = l.strip().split(";")
    if len(p) > 4 and p[0].isdigit(): ptype[int(p[0])] = p[4]
prov_country = {}
for sid, s in info["states"].items():
    for p in s["provs"]: prov_country[p] = info["tag2lore"].get(s["owner"])
adj = L.province_adjacency(M)
nb = collections.defaultdict(set)
for x, y in adj:
    nb[x].add(y); nb[y].add(x)

regions = {}
for f in glob.glob(str(M / "map/strategicregions/*.txt")):
    t = open(f, encoding="utf-8", errors="ignore").read()
    rid = int(re.search(r"\bid\s*=\s*(\d+)", t).group(1))
    provs = [int(x) for x in re.search(r"provinces\s*=\s*\{([^}]*)\}", t).group(1).split()]
    regions[rid] = provs

def sea_name(countries):
    c = countries
    if "SVA" in c and c & {"FDP", "SVS", "TMR"}: return "Синее море"
    if "KZZ" in c: return "Кряхтское море"
    if c & {"SOY", "FIG", "Z01", "Z02", "Z03", "Z04"}: return "Среднее море"
    return "Океан"

names, kind = {}, {}
land_count, sea_count = collections.Counter(), collections.Counter()
for rid in sorted(regions):
    provs = regions[rid]
    land = [p for p in provs if ptype.get(p) == "land"]
    if land:
        c = collections.Counter(prov_country.get(p) for p in land if prov_country.get(p))
        lt = c.most_common(1)[0][0] if c else None
        base = info["country_ru"].get(lt) or L.LORE_RU.get(lt) or "Ничейные земли"
        land_count[base] += 1
        names[rid] = f"{base}, район {land_count[base]}"; kind[rid] = "land"
    else:
        touching = set()
        for p in provs:
            for q in nb[p]:
                if ptype.get(q) == "land" and prov_country.get(q): touching.add(prov_country[q])
        base = sea_name(touching)
        sea_count[base] += 1
        names[rid] = base if sea_count[base] == 1 else f"{base}, район {sea_count[base]}"; kind[rid] = "sea"
# first region of each sea that ended up with several gets a number too, so that every name is unique and parallel
for base, n in sea_count.items():
    if n > 1:
        first = [r for r in sorted(names) if names[r] == base]
        for r in first: names[r] = f"{base}, район 1"

L.write_yml(M / "localisation/russian/strategic_region_names_l_russian.yml", "russian", [(f"STRATEGICREGION_{r}", names[r]) for r in sorted(names)])
L.write_yml(M / "localisation/english/strategic_region_names_l_english.yml", "english", [(f"STRATEGICREGION_{r}", L.translit(names[r])) for r in sorted(names)])
rep = L.REPO / "no_commit/temp/region_names_report.csv"
with open(rep, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";"); w.writerow(["region", "name", "kind"])
    for r in sorted(names): w.writerow([r, names[r], kind[r]])
print(f"regions {len(names)}, land {sum(1 for k in kind.values() if k == 'land')}, sea {sum(1 for k in kind.values() if k == 'sea')}, unique {len(set(names.values()))}")
print("sea regions per lore sea:", dict(sea_count))
print("report:", rep)
