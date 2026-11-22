"""Generals of the worked-out countries (docs/countries/Generals.md; rule of the author 2026-11-20: 20 generals per country, 4 portraits per country shared by them).
Reads the tables of Generals.md (key, rank, name, portrait slot P1..P4), writes the characters into common/characters/<tag>.txt (field_marshal / corps_commander) and
recruits them in history/countries/<tag> - *.txt. Idempotent (a character is added once). Names, skills and traits are INVENTED (docs/lore/Invented-Lore.md).
PORTRAITS: the four generated portraits per country are not made yet: the slots P1..P4 use vanilla generic land-leader portraits (placeholders); when the images
exist (gfx_src/portraits/<tag>_P1..P4.png) the slot maps below must point to them. Usage: python tools/make_generals.py [--mod PATH]"""
import argparse, glob, re
from pathlib import Path
import lore_data as L

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
a = ap.parse_args()
M = Path(a.mod)
doc = (L.REPO / "docs/countries/Generals.md").read_text(encoding="utf-8").replace("\r\n", "\n")
SECTIONS = {"SCU": "## Казуалия (`SCU`)", "MAK": "## Советский Союз (`MAK`)"}
# placeholder slots: vanilla generic land portraits (large + small)
PORT = {"P1": "GFX_Portrait_Africa_Generic_land_1", "P2": "GFX_Portrait_Africa_Generic_land_2", "P3": "GFX_Portrait_Africa_Generic_land_3", "P4": "GFX_Portrait_Africa_Generic_land_1"}
FM_TRAITS = {"SCU": [["old_guard", "defensive_doctrine"], ["trait_cautious", "defensive_doctrine"]],
             "MAK": [["old_guard", "inspirational_leader"], ["harsh_leader", "offensive_doctrine"]]}
CORPS_TRAITS = {"SCU": ["infantry_officer", "trait_cautious", "organizer", "old_guard"],
                "MAK": ["infantry_officer", "organizer", "politically_connected", "career_officer", "harsh_leader", "trait_reckless"]}

def rows(tag):
    i = doc.index(SECTIONS[tag]); j = doc.find("\n## ", i + 5)
    sec = doc[i:j if j != -1 else len(doc)]
    out = []
    for l in sec.split("\n"):
        m = re.match(r"\|\s*(\d+)\s*\|\s*`(\w+)`\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*[^|]*\|\s*(P\d)\s*\|", l)
        if m: out.append((int(m.group(1)), m.group(2), m.group(3), m.group(4), m.group(5)))
    return out

total = 0
for tag in SECTIONS:
    gl = rows(tag)
    assert len(gl) == 20, (tag, len(gl))
    chf = M / "common/characters" / f"{tag}.txt"
    hist = glob.glob(str(M / "history/countries" / f"{tag} - *.txt"))
    if not chf.exists() or not hist:
        print("generals: no files for", tag); continue
    ct = chf.read_text(encoding="utf-8"); hf = Path(hist[0]); ht = hf.read_text(encoding="utf-8", errors="ignore")
    fm = 0; cc = 0
    for n, key, rank, name, slot in gl:
        if key not in ct:
            p = PORT[slot]
            if rank == "Фельдмаршал":
                tr = " ".join(FM_TRAITS[tag][fm % 2]); fm += 1
                role = f"\t\tfield_marshal = {{\n\t\t\ttraits = {{ {tr} }}\n\t\t\tskill = 4\n\t\t\tattack_skill = 3\n\t\t\tdefense_skill = 4\n\t\t\tplanning_skill = 4\n\t\t\tlogistics_skill = 3\n\t\t}}\n"
            else:
                tr = CORPS_TRAITS[tag][cc % len(CORPS_TRAITS[tag])]; cc += 1
                sk = 2 + (n % 2)
                role = f"\t\tcorps_commander = {{\n\t\t\ttraits = {{ {tr} }}\n\t\t\tskill = {sk}\n\t\t\tattack_skill = {sk}\n\t\t\tdefense_skill = {sk}\n\t\t\tplanning_skill = {sk}\n\t\t\tlogistics_skill = {sk}\n\t\t}}\n"
            blk = f"\t{key} = {{\n\t\tname = \"{name}\"\n\t\tportraits = {{\n\t\t\tarmy = {{\n\t\t\t\tlarge = {p}\n\t\t\t\tsmall = {p}_small\n\t\t\t}}\n\t\t}}\n{role}\t}}\n"
            k = ct.rindex("}"); ct = ct[:k] + blk + ct[k:]
        if not re.search(r"^\s*recruit_character\s*=\s*" + key + r"\s*$", ht, re.M):
            ht = re.sub(r"^(recruit_character[^\n]*)$", lambda m: m.group(1) + "\nrecruit_character = " + key, ht, count=1, flags=re.M) if re.search(r"^recruit_character", ht, re.M) else ht.rstrip() + "\n\nrecruit_character = " + key + "\n"
        total += 1
    chf.write_text(ct, encoding="utf-8", newline=""); hf.write_text(ht, encoding="utf-8", newline="")
    print(f"generals: {tag}: {len(gl)} generals ({fm} field marshals, {cc} corps commanders)")
print(f"generals: {total} in total; portraits are vanilla placeholders until the 4 generated portraits per country exist")
