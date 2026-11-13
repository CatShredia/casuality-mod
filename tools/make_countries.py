"""Give the mod's countries their lore names and capitals.

RandomParadox's tags (CHE, MAK, ...) stay, but each tag is matched to its lore country by color (lore_data.load_mod),
then:
 * localisation: <TAG>_<ideology>, _DEF, _ADJ for fascism / communism / neutrality / democratic = lore country name
   (docs/01 gives no per-ideology names or adjectives, so none are invented; the adjective equals the name);
 * history/countries/<TAG> - *.txt: capital = state that contains the lore capital (capitals.txt pixel), if known;
 * report no_commit/temp/countries_report.csv (tag, lore tag, lore name, capital state).
Countries with no lore name or capital in capitals.txt keep what RandomParadox made and are listed.
Originals are copied to no_commit/temp/backup_countries/ before the first change.
Usage: python tools/make_countries.py [--mod PATH]
"""
import argparse, csv, glob, re, shutil
from pathlib import Path
import random
import lore_data as L
import ideologies_data as D

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
a = ap.parse_args()
M = Path(a.mod)

info = L.load_mod(M)
tag2lore, cru = info["tag2lore"], info["country_ru"]
_, _kind, _ = L.assign_state_names(info, "lore", random.Random(0))
# state that carries the lore capital name (same rule as make_state_names.py: pixel match, else biggest state)
capital_state = {tag2lore[info["states"][sid]["owner"]]: sid for sid, k in _kind.items() if k.startswith("lore capital")}
BK = L.REPO / "no_commit/temp/backup_countries"
BK.mkdir(parents=True, exist_ok=True)
IDEO = ("fascism", "communism", "neutrality", "democratic")

def loc_name(lt):
    return cru.get(lt) or L.LORE_RU.get(lt)

changed = {}
for lang, conv in (("russian", lambda s: s), ("english", L.translit)):
    path = M / f"localisation/{lang}/countries_l_{lang}.yml"
    bk = BK / path.name
    if not bk.exists():
        shutil.copy2(path, bk)
    lines = path.read_text(encoding="utf-8-sig").split("\n")
    out = [lines[0]]
    for l in lines[1:]:
        m = re.match(r'\s*([A-Z0-9]{3})_(' + "|".join(IDEO) + r')(_DEF|_ADJ)?:\d*\s*"', l)
        if m and tag2lore.get(m.group(1)) and loc_name(tag2lore[m.group(1)]):
            out.append(f' {m.group(0).strip().split(":")[0]}:0 "{conv(loc_name(tag2lore[m.group(1)]))}"')
            changed[m.group(1)] = True
        else:
            out.append(l)
    # country names under the custom ideology groups (the game shows the key itself when <TAG>_<ruling group> is missing)
    have = {m_.group(1) for l in out for m_ in [re.match(r"\s*([A-Z0-9]{3}_\w+):", l)] if m_}
    for tag in sorted(info["tags"]):
        nm = loc_name(tag2lore[tag]) if tag2lore.get(tag) else None
        if not nm: continue
        for g in D.NEW_GROUPS:
            for suf in ("", "_DEF", "_ADJ"):
                if f"{tag}_{g}{suf}" not in have:
                    out.append(f' {tag}_{g}{suf}:0 "{conv(nm)}"')
    path.write_text("\n".join(out), encoding="utf-8-sig")

rows, nocap = [], []
for tag in sorted(info["tags"]):
    lt = tag2lore.get(tag)
    sid = capital_state.get(lt)
    files = glob.glob(str(M / "history/countries" / f"{tag} - *.txt"))
    if sid and files:
        f = Path(files[0])
        bk = BK / f.name
        if not bk.exists():
            shutil.copy2(f, bk)
        t = f.read_text(encoding="utf-8", errors="ignore")
        t2, n = re.subn(r"(?m)^capital\s*=\s*\d+", f"capital = {sid}", t, count=1)
        if n:
            f.write_text(t2, encoding="utf-8", newline="")
    elif lt not in (None, "CEY"):
        nocap.append(tag)
    rows.append((tag, lt or "?", loc_name(lt) or "", sid or ""))
rep = L.REPO / "no_commit/temp/countries_report.csv"
with open(rep, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["mod_tag", "lore_tag", "lore_name", "capital_state"])
    w.writerows(rows)
print(f"tags {len(rows)}, localised {len(changed)}, with capital set {sum(1 for r in rows if r[3])}")
print("without a lore capital (kept as exported):", [(r[0], r[1]) for r in rows if not r[3]])
print("report:", rep)
