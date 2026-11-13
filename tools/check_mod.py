"""Consistency checks of the exported mod (read-only). Exit code 1 if there is at least one FAIL.

Checks: provinces (ids, colors, bmp), states (every land province in exactly one state, owners, population vs lore),
victory points, localisation (states, cities, countries, strategic regions: present, non-empty, unique), countries (tags,
capitals, rulers), strategic regions (every province in exactly one), rivers.bmp (format, size, palette header,
connectivity, pixels on water, sources).
Usage: python tools/check_mod.py [--mod PATH]
"""
import argparse, collections, glob, re, struct, sys
from pathlib import Path
import numpy as np
from PIL import Image
import lore_data as L
import invented_lore as INV

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
a = ap.parse_args()
M = Path(a.mod)
res = []
def ok(msg): res.append(("PASS", msg))
def warn(msg): res.append(("WARN", msg))
def fail(msg): res.append(("FAIL", msg))
def check(cond, good, bad, level=fail):
    ok(good) if cond else level(bad)

# ---- provinces ----
rows = []
for l in open(M / "map/definition.csv", encoding="latin1"):
    p = l.strip().split(";")
    if len(p) > 6 and p[0].isdigit(): rows.append((int(p[0]), (int(p[1]), int(p[2]), int(p[3])), p[4], p[6]))
ids = [r[0] for r in rows]
check(ids == list(range(len(ids))), f"definition.csv: {len(ids)} provinces, ids 0..{len(ids) - 1} contiguous", "definition.csv: ids are not contiguous from 0")
cols = [r[1] for r in rows]
check(len(set(cols)) == len(cols), "definition.csv: all colors unique", f"definition.csv: {len(cols) - len(set(cols))} duplicate colors")
ptype = {r[0]: r[2] for r in rows}
pv = np.array(Image.open(M / "map/provinces.bmp").convert("RGB")).astype(np.int64)
bmp_cols = {tuple(c) for c in np.unique(pv.reshape(-1, 3), axis=0).tolist()}
miss = set(cols[1:]) - bmp_cols
extra = bmp_cols - set(cols)
check(not miss, "provinces.bmp: every defined color appears on the map", f"provinces.bmp: {len(miss)} defined colors never appear (e.g. {sorted(miss)[:3]})")
check(not extra, "provinces.bmp: no undefined colors", f"provinces.bmp: {len(extra)} colors are not in definition.csv (e.g. {sorted(extra)[:3]})")
bad_t = [r[0] for r in rows[1:] if r[3] == "unknown"]
check(not bad_t, "definition.csv: no unknown terrain", f"definition.csv: unknown terrain in provinces {bad_t[:5]}", warn)

# ---- states ----
info = L.load_mod(M)
states, tag2lore = info["states"], info["tag2lore"]
prov_state = collections.defaultdict(list)
for sid, s in states.items():
    for p in s["provs"]: prov_state[p].append(sid)
land = {r[0] for r in rows[1:] if r[2] == "land"}
no_state = sorted(land - set(prov_state))
multi = sorted(p for p, v in prov_state.items() if len(v) > 1)
sea_in = sorted(p for p in prov_state if ptype.get(p) != "land")
check(not no_state, f"states: all {len(land)} land provinces belong to a state", f"states: {len(no_state)} land provinces without state (e.g. {no_state[:5]})")
check(not multi, "states: no province in two states", f"states: {len(multi)} provinces in several states (e.g. {multi[:5]})")
check(not sea_in, "states: no sea/lake province inside a state", f"states: sea provinces in states: {sea_in[:5]}")
no_owner = [sid for sid, s in states.items() if not s["owner"]]
check(not no_owner, f"states: {len(states)} states, all have an owner", f"states: no owner: {no_owner[:5]}")
unk_tag = sorted({s["owner"] for s in states.values() if s["owner"] not in info["tags"]})
check(not unk_tag, "states: all owners are declared tags", f"states: owners not in country_tags: {unk_tag}")
vp_out = [(sid, p) for sid, s in states.items() for p, _ in s["vps"] if p not in s["provs"]]
check(not vp_out, "victory points: all lie in their own state", f"victory points outside their state: {vp_out[:5]}")

# population against the lore
tot = collections.Counter()
for s in states.values(): tot[tag2lore.get(s["owner"])] += s["manpower"]
bad_pop = {lt: (round(tot[lt] / 1e6, 2), m) for lt, m in {**INV.INVENTED_POP, **L.LORE_POP}.items() if abs(tot[lt] - int(m * 1_000_000)) > 12}
check(not bad_pop, f"population: {len(L.LORE_POP) + len(INV.INVENTED_POP)} countries match their totals ({len(L.LORE_POP)} lore, {len(INV.INVENTED_POP)} invented)", f"population differs from the lore (now, lore, millions): {bad_pop}")

# ---- localisation ----
def load_loc(path):
    d = {}
    if not Path(path).exists(): return d
    for l in open(path, encoding="utf-8-sig"):
        m = re.match(r'\s*([\w.]+):\d*\s*"(.*)"\s*$', l)
        if m: d[m.group(1)] = m.group(2)
    return d
for lang in ("russian", "english"):
    base = M / "localisation" / lang
    sn = load_loc(base / f"state_names_l_{lang}.yml")
    miss = [s for s in states if f"STATE_{s}" not in sn or not sn[f"STATE_{s}"].strip()]
    check(not miss, f"{lang}: all {len(states)} state names set", f"{lang}: {len(miss)} states without a name (e.g. {miss[:5]})")
    vals = [v.lower() for v in sn.values()]
    dups = [k for k, n in collections.Counter(vals).items() if n > 1]
    check(not dups, f"{lang}: state names are unique", f"{lang}: duplicate state names: {dups[:5]}")
    vn = load_loc(base / f"victory_points_l_{lang}.yml")
    vps = {p for s in states.values() for p, _ in s["vps"]}
    missv = [p for p in vps if f"VICTORY_POINTS_{p}" not in vn or not vn[f"VICTORY_POINTS_{p}"].strip()]
    check(not missv, f"{lang}: all {len(vps)} victory points named", f"{lang}: {len(missv)} victory points without a name (e.g. {missv[:5]})")
    cn = load_loc(base / f"countries_l_{lang}.yml")
    missc = [f"{t}_{i}" for t in info["tags"] for i in ("fascism", "communism", "neutrality", "democratic", "casuality", "theology") if not cn.get(f"{t}_{i}", "").strip()]
    check(not missc, f"{lang}: all tags have names for the 6 ideology groups", f"{lang}: country names missing: {missc[:5]}")
    sr = load_loc(base / f"strategic_region_names_l_{lang}.yml")
    emp = [k for k, v in sr.items() if not v.strip()]
    check(sr and not emp, f"{lang}: {len(sr)} strategic region names set", f"{lang}: strategic region names missing or empty")

# ---- countries ----
bad_cap = []
for tag in info["tags"]:
    h = glob.glob(str(M / "history/countries" / f"{tag} - *.txt"))
    if not h:
        bad_cap.append((tag, "no history file")); continue
    t = open(h[0], encoding="utf-8", errors="ignore").read()
    c = re.search(r"^capital\s*=\s*(\d+)", t, re.M)
    if not c or int(c.group(1)) not in states or states[int(c.group(1))]["owner"] != tag:
        bad_cap.append((tag, c.group(1) if c else None))
check(not bad_cap, f"countries: {len(info['tags'])} tags, each capital state exists and belongs to its country", f"countries: capital problems: {bad_cap[:6]}")
no_chars = [t for t in info["tags"] if not (M / "common/characters" / f"{t}.txt").exists()]
check(not no_chars, "countries: every tag has a character file", f"countries: no character file for {no_chars}")
no_state_tag = [t for t in info["tags"] if t not in {s["owner"] for s in states.values()}]
check(not no_state_tag, "countries: every tag owns a state", f"countries: tags without states: {no_state_tag}", warn)

# ---- ideologies ----
itext = (M / "common/ideologies/00_ideologies.txt").read_text(encoding="utf-8", errors="ignore") if (M / "common/ideologies/00_ideologies.txt").exists() else ""
sub2grp = {}
for gm in re.finditer(r"\n\t(\w+) = \{\s*\n\s*types = \{", itext):
    start = gm.end(); depth = 1; i = start
    while depth and i < len(itext):
        depth += (itext[i] == "{") - (itext[i] == "}"); i += 1
    for t in re.findall(r"\n\t\t\t(\w+)\s*=\s*\{", itext[start:i]): sub2grp[t] = gm.group(1)
check(bool(sub2grp) and {"casuality_ideology", "theology_ideology", "technocracy"} <= set(sub2grp), f"ideologies: {len(sub2grp)} sub-ideologies in {len(set(sub2grp.values()))} groups, custom ones present", "ideologies: common/ideologies/00_ideologies.txt missing or without the custom ideologies")
bad_rule = []
for tag in info["tags"]:
    h = glob.glob(str(M / "history/countries" / f"{tag} - *.txt"))
    cf = M / "common/characters" / f"{tag}.txt"
    if not h or not cf.exists(): continue
    rp = re.search(r"ruling_party\s*=\s*(\w+)", open(h[0], encoding="utf-8", errors="ignore").read())
    leaders = [sub2grp.get(x) for x in re.findall(r"country_leader\s*=\s*\{[^}]*?ideology\s*=\s*(\w+)", open(cf, encoding="utf-8", errors="ignore").read(), re.S)]
    if not rp or rp.group(1) not in leaders: bad_rule.append((tag, rp.group(1) if rp else None))
check(not bad_rule, "ideologies: every country has a leader of its ruling group", f"ideologies: ruling group without a leader: {bad_rule[:6]}")

# education spirits
no_edu = []
for tag, lt in info["tag2lore"].items():
    h = glob.glob(str(M / "history/countries" / f"{tag} - *.txt"))
    if lt not in ("FIG", "LED") and h and not re.search(r"(?m)^add_ideas\s*=\s*ktits_edu_[0-5]\s*$", open(h[0], encoding="utf-8", errors="ignore").read()): no_edu.append(tag)
check(not no_edu, "education: every country has an education level spirit", f"education: no level for {no_edu}")

# ---- strategic regions ----
reg = collections.defaultdict(list)
for f in glob.glob(str(M / "map/strategicregions/*.txt")):
    t = open(f, encoding="utf-8", errors="ignore").read()
    rid = int(re.search(r"\bid\s*=\s*(\d+)", t).group(1))
    for p in re.search(r"provinces\s*=\s*\{([^}]*)\}", t).group(1).split(): reg[int(p)].append(rid)
all_p = set(range(1, len(ids)))
no_reg = sorted(all_p - set(reg)); multi_reg = sorted(p for p, v in reg.items() if len(v) > 1)
check(not no_reg, "strategic regions: every province has a region", f"strategic regions: {len(no_reg)} provinces without region (e.g. {no_reg[:5]})")
check(not multi_reg, "strategic regions: no province in two regions", f"strategic regions: {len(multi_reg)} provinces in several regions (e.g. {multi_reg[:5]})")

# ---- rivers ----
rf = M / "map/rivers.bmp"
im = Image.open(rf)
check(im.mode == "P" and im.size == (pv.shape[1], pv.shape[0]), f"rivers.bmp: 8 bit palette, {im.size[0]}x{im.size[1]} like provinces.bmp", f"rivers.bmp: mode {im.mode} size {im.size} (provinces.bmp {pv.shape[1]}x{pv.shape[0]})")
hdr = open(rf, "rb").read(54)
check(struct.unpack("<II", hdr[46:54]) == (0, 0), "rivers.bmp: header colors-used = 0 like vanilla", "rivers.bmp: header colors-used != 0 (game logs 'Palette in rivers.bmp is probably not correct')")
ra = np.array(im); riv = ra < 254
n = np.zeros(ra.shape, int); n[1:] += riv[:-1]; n[:-1] += riv[1:]; n[:, 1:] += riv[:, :-1]; n[:, :-1] += riv[:, 1:]
iso = int((riv & (n == 0)).sum())
check(iso == 0, f"rivers.bmp: {int(riv.sum())} river pixels, none isolated", f"rivers.bmp: {iso} isolated river pixels (rivers need 4-neighbour continuity)")
check(int((ra == 0).sum()) > 0, f"rivers.bmp: {int((ra == 0).sum())} river sources", "rivers.bmp: no river sources (index 0)")
orig = L.REPO / "no_commit/temp/rivers.bmp.orig"
if orig.exists():
    water = np.array(Image.open(orig)) == 254
    on_water = int((riv & water).sum())
    check(on_water == 0, "rivers.bmp: no river pixel on water", f"rivers.bmp: {on_water} river pixels on water")
bad_idx = sorted(set(np.unique(ra[riv]).tolist()) - set(range(0, 12)))
check(not bad_idx, "rivers.bmp: only palette indices 0-11 used for rivers", f"rivers.bmp: unexpected indices {bad_idx}")

w = {"PASS": 0, "WARN": 0, "FAIL": 0}
for lvl, msg in res:
    w[lvl] += 1
    print(f"[{lvl}] {msg}")
print(f"\n{w['PASS']} passed, {w['WARN']} warnings, {w['FAIL']} failed")
sys.exit(1 if w["FAIL"] else 0)
