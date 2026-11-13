"""Set state population (manpower) so that each country's total equals the number given in docs/01.

Lore is the only source: countries whose population is TODO in docs/01 are left untouched and listed.
The lore total is spread over the country's states in proportion to their current manpower.
Backup of the old values: no_commit/temp/backup_manpower.json (restore with --restore).
Usage: python tools/set_population.py [--restore] [--mod PATH]
"""
import argparse, glob, json, re
from pathlib import Path
import lore_data as L

REPO = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--mod", default="C:/Users/catsh/CatshrediasDocs/Paradox Interactive/Hearts of Iron IV/mod/Ktits")
ap.add_argument("--restore", action="store_true")
a = ap.parse_args()
M = Path(a.mod)
BACKUP = REPO / "no_commit/temp/backup_manpower.json"

# docs/01-Contries-Description.md, "Население ..." lines, millions
import invented_lore as INV
LORE_POP = {**INV.INVENTED_POP, **L.LORE_POP}   # lore wins; INVENTED_POP fills the TODO gaps (docs/12)
TODO = sorted(INV.INVENTED_POP)   # lore says TODO or nothing: filled with INVENTED values
NONE = []

files = {int(re.search(r"(\d+)\.txt$", f).group(1)): f for f in glob.glob(str(M / "history/states/*.txt"))}
if a.restore:
    old = json.loads(BACKUP.read_text())
    for sid, mp in old.items():
        f = files[int(sid)]
        t = open(f, encoding="utf-8", errors="ignore").read()
        open(f, "w", encoding="utf-8", newline="").write(re.sub(r"(manpower\s*=\s*)\d+", lambda m: m.group(1) + str(mp), t, count=1))
    print("restored", len(old), "states"); raise SystemExit

lore = {}
for l in open(REPO / "tools/rp_input/stage_04/countryMappings.txt", encoding="utf-8"):
    p = l.strip().split(";")
    if len(p) >= 6 and p[0].isdigit(): lore[(int(p[0]), int(p[1]), int(p[2]))] = p[3]
tags = dict(re.findall(r'(\w{3})\s*=\s*"countries/(.+?)\.txt"', (M / "common/country_tags/02_countries.txt").read_text(encoding="utf-8", errors="ignore")))
tag2lore = {}
for t, f in tags.items():
    c = re.search(r"color\s*=\s*\{\s*(\d+)\s+(\d+)\s+(\d+)", (M / "common/countries" / (f + ".txt")).read_text(encoding="utf-8", errors="ignore"))
    if c and tuple(map(int, c.groups())) in lore: tag2lore[t] = lore[tuple(map(int, c.groups()))]

st = {}
for sid, f in files.items():
    t = open(f, encoding="utf-8", errors="ignore").read()
    o = re.search(r"owner\s*=\s*(\w+)", t); m = re.search(r"manpower\s*=\s*(\d+)", t)
    if o and m: st[sid] = (tag2lore.get(o.group(1)), int(m.group(1)))
if not BACKUP.exists():
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    BACKUP.write_text(json.dumps({str(k): v[1] for k, v in st.items()}))

report = []
for lt, mln in LORE_POP.items():
    sids = [s for s, (c, _) in st.items() if c == lt]
    cur = sum(st[s][1] for s in sids)
    if not sids or cur == 0:
        report.append((lt, mln, cur, "no states")); continue
    target = int(mln * 1_000_000)
    new = {s: int(st[s][1] * target / cur) for s in sids}
    new[max(sids, key=lambda s: st[s][1])] += target - sum(new.values())   # exact total
    for s in sids:
        f = files[s]
        t = open(f, encoding="utf-8", errors="ignore").read()
        open(f, "w", encoding="utf-8", newline="").write(re.sub(r"(manpower\s*=\s*)\d+", lambda m: m.group(1) + str(new[s]), t, count=1))
    report.append((lt, mln, cur, f"{len(sids)} states -> {sum(new.values())}"))
for r in report: print(r)
print("INVENTED population (not lore, docs/12):", TODO)
