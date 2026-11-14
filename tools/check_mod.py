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

# ---- Casuality mechanic (make_casuality.py) ----
cas_files = [f for pat in ("common/scripted_effects/ktits_casuality*.txt", "common/scripted_triggers/ktits_casuality*.txt", "common/ideas/ktits_casuality*.txt",
                           "common/decisions/ktits_casuality*.txt", "common/decisions/categories/ktits_casuality*.txt", "common/on_actions/ktits_casuality*.txt",
                           "events/ktits_casuality*.txt") for f in sorted(M.glob(pat))]
cas_txt = {f: f.read_text(encoding="utf-8") for f in cas_files}
unbal = [f.name for f, s in cas_txt.items() if s.count("{") != s.count("}")]
check(bool(cas_txt) and not unbal, f"casuality: {len(cas_txt)} script files, braces balanced", f"casuality: unbalanced braces in {unbal}")
loc_ru = load_loc(M / "localisation/russian/ktits_casuality_l_russian.yml")
all_cas = "\n".join(cas_txt.values())
dec_keys = [k for f, s in cas_txt.items() if "decisions" in str(f) and "categories" not in str(f) for k in re.findall(r"(?m)^\t(ktits_\w+) = \{", s)]
idea_keys = [k for f, s in cas_txt.items() if "ideas" in str(f) for k in re.findall(r"(?m)^\t\t(ktits_\w+) = \{", s)]
miss = [k for k in dec_keys + idea_keys if not loc_ru.get(k, "").strip() or not loc_ru.get(k + "_desc", "").strip()]
check(len(dec_keys) >= 13 and not miss, f"casuality: {len(dec_keys)} decisions and {len(idea_keys)} spirits have name and description in loc", f"casuality: decisions/spirits without loc: {miss[:5]}")
ev_def = set(re.findall(r"id = (ktits_casuality\.\d+)\n\ttitle", all_cas))
ev_call = set(re.findall(r"country_event = \{ id = (ktits_casuality\.\d+)", all_cas))
miss_ev = sorted(e for e in ev_call if e not in ev_def)
check(not miss_ev and all(f"ktits_casuality.{i}" in ev_def for i in range(30, 36)), f"casuality: all fired events are defined ({len(ev_def)} events incl. notifications 30-35)", f"casuality: events fired but not defined or 30-35 missing: {miss_ev}")
miss_evloc = sorted(e for e in ev_def if not loc_ru.get(e + ".t") or not loc_ru.get(e + ".d") or not loc_ru.get(e + ".a"))
check(not miss_evloc, "casuality: every event has title, text and option loc", f"casuality: events without loc: {miss_evloc}")
set_costs = set(re.findall(r"set_variable = \{ var = (ktits_cas_cost_\d) ", all_cas))
used_costs = set(re.findall(r"cost = (ktits_cas_cost_\d)", all_cas))
check(bool(used_costs) and used_costs <= set_costs, f"casuality: {len(used_costs)} variable costs of the fight decisions are set by ktits_casuality_costs", f"casuality: cost variables not set: {sorted(used_costs - set_costs)}")
ret_txt = (M / "common/scripted_effects/ktits_casuality_return_effects.txt").read_text(encoding="utf-8") if (M / "common/scripted_effects/ktits_casuality_return_effects.txt").exists() else ""
ev1 = (M / "events/ktits_casuality_events.txt").read_text(encoding="utf-8")
check("ktits_return_lands = {" in ret_txt and "transfer_state_to" in ret_txt and 0 <= ev1.find("ktits_return_lands = yes") < ev1.find("ktits_split_on_fall = yes") and not re.search(r"is_core_of = (K\d\d|"+{v: k for k, v in tag2lore.items()}["CSL"]+")\b", ret_txt), "casuality: return of conquered lands is called before the split and skips Kxx/Kazualia", "casuality: ktits_return_lands missing, wrongly ordered or touches Kxx/Kazualia")
oa = cas_txt.get(M / "common/on_actions/ktits_casuality_on_actions.txt", "")
check(all(x in oa for x in ("on_startup", "on_monthly", "on_daily")) and "ktits_casuality_monthly = {" in all_cas, "casuality: on_actions has on_startup, on_monthly, on_daily; the monthly effect is defined", "casuality: on_actions or ktits_casuality_monthly missing")
bad_edu = [i for i in range(6) if f"ktits_edu_{i}" not in all_cas]
check(not bad_edu, "casuality: monthly growth and costs use all 6 education levels", f"casuality: education levels not used: {bad_edu}")
ke = re.search(r"ktits_kaz_puppet_education = [{][\s\S]*?\r?\n[}]", all_cas)
ke = ke.group(0) if ke else ""
ev_imm = ev1.split("option = {")[0]
oa_m = oa.split("on_weekly")[0]
check("ktits_spec_own" in ke and "ktits_spec_foreign" in ke and "ktits_education_update = yes" in ke and "is_puppet_of" in ke and "ktits_kaz_puppet_education = yes" in ev_imm and "ktits_kaz_puppet_education = yes" in oa_m, "casuality: puppets of Kazualia get education 0 (effect, fall event, monthly net)", "casuality: ktits_kaz_puppet_education missing or not called from the fall event / on_monthly")

# ---- game rules (make_casuality.py, make_game_rules.py) ----
gr_dir = M / "common/game_rules"
kr = (gr_dir / "ktits_casuality_rules.txt").read_text(encoding="utf-8") if (gr_dir / "ktits_casuality_rules.txt").exists() else ""
kr_opts = re.findall(r"\n\t(?:default|option) = \{\n\t\tname = (\w+)", kr)
kr_used = set(re.findall(r"rule = ktits_global_casuality option = (\w+)", all_cas))
kloc = {l: load_loc(M / f"localisation/{l}/ktits_game_rules_l_{l}.yml") for l in ("russian", "english")}
kr_keys = re.findall(r'(?:name|text|desc) = "(\w+)"', kr)
kr_miss = [k for l in kloc for k in kr_keys if not kloc[l].get(k)]
check(kr.startswith("ktits_global_casuality = {") and len(kr_opts) == 4 and kr.count("\tdefault = {") == 1 and set(kr_opts) == kr_used and kr.count("{") == kr.count("}"),
      "game rules: ktits_global_casuality has 4 options (1 default), all used by the AI effects", f"game rules: ktits_casuality_rules.txt wrong (options {kr_opts}, used {sorted(kr_used)})")
check(not kr_miss, "game rules: rule, options and descriptions have ru/en loc", f"game rules: loc missing: {sorted(set(kr_miss))[:6]}")
vg = gr_dir / "00_game_rules.txt"
vgt = vg.read_text(encoding="utf-8") if vg.exists() else ""
defined = set(re.findall(r"(?m)^(\w+)\s*=\s*\{", vgt)) | {"ktits_global_casuality"}
check(bool(vgt) and not re.search(r"(?mi)^\w+_(?:ai_behavior|fragmentation_status)\s*=", vgt) and vgt.count("{") == vgt.count("}") and "allow_wargoals" in defined,
      f"game rules: vanilla file overridden, {len(defined) - 1} generic rules, no country-specific ones", "game rules: 00_game_rules.txt missing or still has country-specific rules")
refs = collections.defaultdict(set)
for f in M.rglob("*.txt"):
    if "game_rules" in f.parts: continue
    for r in re.findall(r"has_game_rule\s*=\s*\{\s*rule\s*=\s*(\w+)", f.read_text(encoding="utf-8", errors="ignore")):
        if r not in defined: refs[f.relative_to(M).parts[1]].add((r, f.name))
bad_non_focus = sorted(x for k, v in refs.items() if k != "national_focus" for x in v)
check(not bad_non_focus, "game rules: no script outside national_focus uses a removed rule", f"game rules: removed rules used in {bad_non_focus[:6]}")
nf = refs.get("national_focus", set())
if nf: warn(f"game rules: {len(nf)} (rule, file) pairs in compat national_focus files reference removed rules ({len({r for r, _ in nf})} rules); watch error.log")

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

# ---- focus branch "Казуальность" (make_focuses.py) ----
FOC_IDS = ["ktits_cas_culture", "ktits_cas_schools", "ktits_cas_drain", "ktits_cas_ministry", "ktits_cas_anticas", "ktits_cas_service",
           "ktits_cas_rest", "ktits_cas_resorts", "ktits_cas_houses", "ktits_cas_embassy", "ktits_cas_wing"]
gen_p = M / "common/national_focus/generic.txt"
gen = gen_p.read_text(encoding="utf-8-sig") if gen_p.exists() else ""
fl_ru, fl_en = load_loc(M / "localisation/russian/ktits_focuses_l_russian.yml"), load_loc(M / "localisation/english/ktits_focuses_l_english.yml")
foc_def = re.findall(r"(?m)^\tfocus = \{\r?\n\t\tid = (ktits_cas_\w+)", gen)
check(sorted(foc_def) == sorted(FOC_IDS) and gen.count("{") == gen.count("}") and gen.count("KTITS_CASUALITY_BRANCH_BEGIN") == 1,
      "focuses: all 11 Casuality focuses defined once in the generic tree, braces balanced", f"focuses: defined {sorted(foc_def)} (need 11), braces {gen.count('{')}/{gen.count('}')}")
miss_fl = [k for f in FOC_IDS for k in (f, f + "_desc") if not fl_ru.get(k, "").strip() or not fl_en.get(k, "").strip()]
check(not miss_fl, "focuses: every focus has ru/en name and description", f"focuses: loc missing for {miss_fl[:6]}")
blk_f = {m.group(1): m.group(0) for m in re.finditer(r"\tfocus = \{\r?\n\t\tid = (ktits_cas_\w+)[\s\S]*?\r?\n\t\}", gen)}
check("mutually_exclusive = { focus = ktits_cas_rest }" in blk_f.get("ktits_cas_culture", "") and "mutually_exclusive = { focus = ktits_cas_culture }" in blk_f.get("ktits_cas_rest", ""),
      "focuses: 'Культура труда' and 'Право на отдых' are mutually exclusive both ways", "focuses: mutual exclusivity of culture/rest missing")
check("has_country_leader_ideology = total_fascism" in blk_f.get("ktits_cas_service", "") and "has_country_leader_ideology = total_communism" in blk_f.get("ktits_cas_service", ""),
      "focuses: 'Трудовая повинность' requires total fascism or total communism", "focuses: ktits_cas_service condition missing")
used_sub = set(re.findall(r"has_country_leader_ideology = (\w+)", "\n".join(blk_f.values())))
ide_txt = (M / "common/ideologies/00_ideologies.txt").read_text(encoding="utf-8-sig") if (M / "common/ideologies/00_ideologies.txt").exists() else ""
check(all(re.search(r"(?m)^\s*" + s + r"\s*=\s*\{", ide_txt) for s in used_sub), "focuses: sub-ideologies used in conditions exist", f"focuses: unknown sub-ideology in {sorted(used_sub)}")
weeks = {"ktits_cas_culture": 10, "ktits_cas_schools": 10, "ktits_cas_drain": 15, "ktits_cas_ministry": 10, "ktits_cas_anticas": 10, "ktits_cas_service": 5,
         "ktits_cas_rest": 10, "ktits_cas_resorts": 10, "ktits_cas_houses": 10, "ktits_cas_embassy": 5, "ktits_cas_wing": 15}
check(all(f"cost = {v}\n" in blk_f.get(k, "").replace("\r", "") for k, v in weeks.items()), "focuses: durations match the doc (days / 7 weeks)", "focuses: cost differs from the doc table")
dec_txt = (M / "common/decisions/ktits_casuality.txt").read_text(encoding="utf-8")
sup = re.findall(r"(?m)^\t(ktits_cas_support_\w+) = \{([\s\S]*?)\n\t\}", dec_txt)
bad_sup = [k for k, b in sup if "has_completed_focus = ktits_cas_rest" not in b]
bad_fight = [k for k, b in re.findall(r"(?m)^\t(ktits_cas_fight_\w+) = \{([\s\S]*?)\n\t\}", dec_txt) if "has_completed_focus" in b]
check(len(sup) >= 7 and not bad_sup and not bad_fight, f"focuses: all {len(sup)} support decisions require 'Право на отдых', fight decisions do not", f"focuses: support without the focus {bad_sup}, fight with it {bad_fight}")
mc = "\n".join(p.read_text(encoding="utf-8") for p in (M / "common/scripted_effects").glob("ktits_casuality*.txt")) + "\n" + (M / "events/ktits_casuality_events.txt").read_text(encoding="utf-8") + dec_txt + gen
flags_set = set(re.findall(r"set_country_flag = (?:\{ flag = )?(ktits_cas_f_\w+)", gen))
flags_read = set(re.findall(r"has_country_flag = (ktits_cas_f_\w+)", mc.replace(gen, "")))
check(flags_set == flags_read and len(flags_set) == 9, f"focuses: all {len(flags_set)} focus flags that are set are read by the mechanic", f"focuses: flags set {sorted(flags_set)} vs read {sorted(flags_read)}")
sp = (M / "common/ideas/ktits_focus_ideas.txt").read_text(encoding="utf-8") if (M / "common/ideas/ktits_focus_ideas.txt").exists() else ""
check(all(k in sp and fl_ru.get(k) and fl_ru.get(k + "_desc") for k in ("ktits_cas_sp_ministry", "ktits_cas_sp_labour")) and "ktits_cas_embassy" in (M / "common/opinion_modifiers/ktits_opinion_modifiers.txt").read_text(encoding="utf-8"),
      "focuses: both spirits and the embassy opinion modifier exist with loc", "focuses: spirits / opinion modifier missing")

# ---- focus branch "Политический курс" (make_focuses.py) ----
pol_defs = re.findall(r"(?m)^\tfocus = \{\r?\n\t\tid = (ktits_pol_\w+)", gen)
check(len(pol_defs) == 26 and len(set(pol_defs)) == 26 and gen.count("KTITS_POLITICS_BRANCH_BEGIN") == 1 and gen.count("{") == gen.count("}"),
      "politics: 26 unique focuses in the generic tree, braces balanced", f"politics: {len(pol_defs)} focuses ({len(set(pol_defs))} unique)")
pol_ru, pol_en = load_loc(M / "localisation/russian/ktits_pol_l_russian.yml"), load_loc(M / "localisation/english/ktits_pol_l_english.yml")
miss_pl = [k for f in pol_defs for k in (f, f + "_desc") if not pol_ru.get(k, "").strip() or not pol_en.get(k, "").strip()]
check(not miss_pl, "politics: every focus has ru/en name and description", f"politics: loc missing {miss_pl[:6]}")
pb = {m.group(1): m.group(0).replace("\r", "") for m in re.finditer(r"\tfocus = \{\r?\n\t\tid = (ktits_pol_\w+)[\s\S]*?\r?\n\t\}", gen)}
pops_ = [k for k in pb if k.endswith("_pop")]
def excl_of(b):
    m = re.search(r"mutually_exclusive = \{([^}]*)\}", b)
    return set(re.findall(r"focus = (\w+)", m.group(1))) if m else set()
check(len(pops_) == 5 and all(excl_of(pb[k]) == set(pops_) - {k} for k in pops_), "politics: the 5 paths are mutually exclusive both ways", "politics: path exclusivity broken")
subs_ = {k: b for k, b in pb.items() if "set_country_leader_ideology" in b}
by_pre = {}
for k, b in subs_.items():
    by_pre.setdefault(re.search(r"prerequisite = \{ focus = (\w+) \}", b).group(1), []).append(k)
check(len(subs_) == 14 and all(excl_of(subs_[k]) == set(v) - {k} for v in by_pre.values() for k in v), "politics: 14 subtypes, mutually exclusive inside each path", "politics: subtype exclusivity broken")
sub_keys = {re.search(r"set_country_leader_ideology = (\w+)", b).group(1) for b in subs_.values()}
check(all(re.search(r"(?m)^\s*" + s_ + r"\s*=\s*\{", ide_txt) for s_ in sub_keys) and len(sub_keys) == 14, "politics: all 14 subtype keys exist in the ideologies file", f"politics: unknown subtype keys {sorted(sub_keys)}")
ch = pb.get("ktits_pol_change", "")
check("uncomplete_national_focus" in ch and "focus = ktits_pol_root" in ch and "uncomplete_children = yes" in ch and "has_war = no" in ch and all(k in ch for k in subs_), "politics: reset focus uncompletes the root with children, needs no war and any subtype", "politics: reset focus is wrong")
pid_txt = (M / "common/ideas/ktits_pol_ideas.txt").read_text(encoding="utf-8") if (M / "common/ideas/ktits_pol_ideas.txt").exists() else ""
sp_ids = set(re.findall(r"(?m)^\t\t(ktits_pol_sp_\w+) = \{", pid_txt))
# lore descriptions of all our spirits (every ktits_* idea): non-empty, not a technical placeholder, not shared between ideas
all_ru = {}
for f_ in sorted((M / "localisation/russian").glob("ktits_*.yml")): all_ru.update(load_loc(f_))
idea_all = [k for f_ in sorted((M / "common/ideas").glob("ktits_*.txt")) for k in re.findall(r"(?m)^\t\t(ktits_\w+) = \{", f_.read_text(encoding="utf-8"))]
PLACEHOLDERS = ("Временное изменение стабильности", "последствия события", "Уровень образованности населения", "Бонусы выбора подтипа", "TODO", "placeholder")
bad_d = [k for k in idea_all if not all_ru.get(k + "_desc", "").strip() or any(ph in all_ru[k + "_desc"] for ph in PLACEHOLDERS)]
descs = [all_ru.get(k + "_desc", "") for k in idea_all]
dup_d = sorted({k for k in idea_all if descs.count(all_ru.get(k + "_desc", "")) > 1})
check(len(idea_all) >= 30 and not bad_d and not dup_d, f"spirits: all {len(idea_all)} ktits_* ideas have a unique lore description", f"spirits: missing/placeholder desc {bad_d[:5]}, duplicated desc {dup_d[:5]}")
check(len(sp_ids) == 14 and all(f"add_ideas = {s_}" in gen and f"remove_ideas = {s_}" in ch and pol_ru.get(s_) and pol_en.get(s_) for s_ in sp_ids), "politics: 14 spirits are given, removed by the reset focus and have loc", "politics: spirit problem")
check(all(re.search(r"\n\t\tx = (\d+)", pb[k]) and int(re.search(r"\n\t\tx = (\d+)", pb[k]).group(1)) >= 34 for k in pb), "politics: all focuses are at x >= 34 (free columns)", "politics: focus overlaps the vanilla/Casuality columns")

sp_ids = set(re.findall(r"(?m)^		(ktits_pol_sp_\w+) = \{", pid_txt))

# ---- specialists and branch "Образование" (make_education.py, education_mech.py, make_focuses.py) ----
ed_fx = (M / "common/scripted_effects/ktits_education_effects.txt").read_text(encoding="utf-8") if (M / "common/scripted_effects/ktits_education_effects.txt").exists() else ""
ths = [int(x) for x in re.findall(r"set_variable = \{ var = ktits_spec_own value = (\d+) \}\n\t\}\n", ed_fx)]
lv_th = re.findall(r"ktits_spec_own value = (\d+) compare = greater_than_or_equals \}\s*\}\n\t\tset_variable = \{ var = ktits_edu_t value = (\d)", ed_fx)
check(ths == [0, 10, 30, 60, 100, 150] and [(int(a), int(b)) for a, b in lv_th] == [(10, 1), (30, 2), (60, 3), (100, 4), (150, 5)] and all(f"add_ideas = ktits_edu_{i}" in ed_fx for i in range(6)),
      "specialists: thresholds 0/10/30/60/100/150 map to levels 0..5 (start and update effects)", f"specialists: thresholds wrong {ths} {lv_th}")
check("random_list" in ed_fx and ed_fx.count("ktits_spec_foreign value =") >= 11 and "ktits_education_update" in ed_fx and "ktits_education_monthly = {" in ed_fx and "ktits_education_costs = {" in ed_fx,
      "specialists: random foreign start, update, monthly and costs effects defined", "specialists: effects missing")
upd = ed_fx.split("ktits_education_start")[0]
check("ktits_is_kazualia = yes" in upd and "is_puppet_of" in upd and "ktits_spec_own value = 0" in upd and "ktits_spec_foreign value = 0" in upd,
      "specialists: Kazualia and its puppets are reset to 0/0 and level 0 in the update effect", "specialists: Kazualia lock missing in ktits_education_update")
mo = ed_fx.split("ktits_education_monthly = {")[1] if "ktits_education_monthly = {" in ed_fx else ""
check(all(s in mo for s in ("value = 5 }", "value = 8 }", "value = 10 }", "ktits_edu_f_mentor", "ktits_edu_mentor_dec", "ktits_cas_3", "ktits_cas_5", "ktits_edu_f_inst", "clamp_variable = { var = ktits_edu_m min = 1")),
      "specialists: monthly transfer 5/8/10 %, min 1, swamp -1 at tier 3+, institutes +1", "specialists: monthly effect incomplete")
edoa = (M / "common/on_actions/ktits_casuality_on_actions.txt").read_text(encoding="utf-8")
check("ktits_education_start = yes" in edoa.split("on_monthly = {")[0] and "ktits_education_monthly = yes" in edoa.split("on_monthly = {")[1].split("on_weekly")[0],
      "specialists: start hooked to on_startup, monthly to on_monthly", "specialists: on_actions hooks missing")
ed_dec = (M / "common/decisions/ktits_education.txt").read_text(encoding="utf-8") if (M / "common/decisions/ktits_education.txt").exists() else ""
ed_cat = (M / "common/decisions/categories/ktits_education_categories.txt").read_text(encoding="utf-8") if (M / "common/decisions/categories/ktits_education_categories.txt").exists() else ""
ed_ids = [f"ktits_edu_attr_{i}" for i in range(1, 3)] + ["ktits_edu_coop"] + [f"ktits_edu_simp_{i}" for i in range(1, 4)]
ed_loc = {}
for f_ in sorted((M / "localisation/russian").glob("ktits_education_l_russian.yml")): ed_loc.update(load_loc(f_))
miss_ed = [k for d_ in ed_ids for k in (d_, d_ + "_desc") if not ed_loc.get(k, "").strip()] + [k for k in ("ktits_education_dev_category", "ktits_education_dev_category_desc", "ktits_education_simp_category", "ktits_education_simp_category_desc", "ktits_edu_tt_kaz", "ktits_edu_req_big", "ktits_edu_tt_coop") if not ed_loc.get(k, "").strip()]
dev_blk, simp_blk = (ed_dec.split("ktits_education_simp_category = {") + [""])[:2]
check(all(re.search(r"(?m)^\t" + d_ + r" = {", ed_dec) for d_ in ed_ids) and "ktits_education_dev_category = {" in ed_cat and "ktits_education_simp_category = {" in ed_cat and not miss_ed and "[?ktits_spec_own|0]" in ed_loc.get("ktits_education_dev_category_desc", ""),
      "specialists: two categories (development, simplification) and 6 decisions defined with ru name and lore description", f"specialists: decisions/loc missing {miss_ed[:5]}")
check(dev_blk.count("ktits_edu_attr_") >= 2 and "ktits_edu_coop" in dev_blk and all(f"ktits_edu_simp_{i}" in simp_blk and f"ktits_edu_simp_{i}" not in dev_blk for i in range(1, 4)) and "ktits_edu_attr_" not in simp_blk and "ktits_edu_coop" not in simp_blk,
      "categories: attraction, mentorship and cooperation are in development, the three simplifications in simplification", "categories: education decisions in the wrong category")
ed_n = lambda k_: ed_loc.get(k_, "")
mk_ok = all(ed_n(k_).startswith("§G+§!") for k_ in ("ktits_edu_attr_1", "ktits_edu_attr_2", "ktits_edu_coop")) and all(ed_n(f"ktits_edu_simp_{i}").startswith("§R−§!") for i in range(1, 4))
cs_loc = load_loc(M / "localisation/russian/ktits_casuality_l_russian.yml")
cs_dec = (M / "common/decisions/ktits_casuality.txt").read_text(encoding="utf-8")
cs_fight, cs_sup = (cs_dec.split("ktits_casuality_support_category = {") + [""])[:2]
cs_cat = (M / "common/decisions/categories/ktits_casuality_categories.txt").read_text(encoding="utf-8")
mk_ok = mk_ok and all(cs_loc.get(f"ktits_cas_fight_{i}", "").startswith("§R−§!") for i in range(0, 6)) and all(cs_loc.get(f"ktits_cas_support_{i}", "").startswith("§G+§!") for i in range(1, 7)) and cs_loc.get("ktits_cas_support_6_free", "").startswith("§G+§!")
check(mk_ok, "markers: raising decisions start with §G+§!, lowering with §R−§! (no ▲/▼ glyphs in the vanilla fonts)", "markers: decision names without the coloured marker")
check("ktits_casuality_fight_category = {" in cs_cat and "ktits_casuality_support_category = {" in cs_cat and re.search(r"ktits_casuality_fight_category = [{][^}]*scripted_gui = ktits_casuality_ui", cs_cat) and cs_cat.count("scripted_gui") == 1
      and all(f"ktits_cas_fight_{i} = {{" in cs_fight for i in range(0, 6)) and "ktits_cas_fight_" not in cs_sup and cs_sup.count("ktits_cas_support_") >= 7 and "ktits_cas_support_6_free = {" in cs_sup and "ktits_cas_support_" not in cs_fight
      and all(cs_loc.get(k_, "").strip() for k_ in ("ktits_casuality_fight_category", "ktits_casuality_fight_category_desc", "ktits_casuality_support_category", "ktits_casuality_support_category_desc")) and "[?ktits_casuality|0]" in cs_loc.get("ktits_casuality_fight_category_desc", ""),
      "casuality: split into fight and support categories, the scale bar (scripted GUI) is on the fight one, both have loc and lore description", "casuality: category split / scale bar / loc wrong")
att = [b for k_, b in re.findall(r"(?m)^\t(ktits_edu_(?:attr_\d|coop)) = {([\s\S]*?)\n\t}", dev_blk)]
check(len(att) == 3 and all("ktits_edu_tt_kaz" in b and "is_puppet_of" in b and "ktits_is_kazualia" in b for b in att),
      "specialists: refuge, mentorship and cooperation are closed for Kazualia and its puppets (tooltip 'Ставке Казуала специалисты не нужны')", "specialists: Kazualia lock missing in an attraction decision")
check(all("ktits_is_big_country = yes" in b and "ktits_edu_req_big" in b and "has_completed_focus = ktits_edu_imp" in b for b in att),
      "education: attraction decisions need the focus 'Импорт умов' and a big country (readable tooltip)", "education: attraction decisions without big-country / 'Импорт умов' condition")
burn = re.search(r"(?m)^\tktits_edu_simp_3 = {([\s\S]*?)\n\t}", ed_dec)
burn = burn.group(1) if burn else ""
check("fire_only_once = yes" in burn and "total_fascism" in burn and "total_communism" in burn and "has_country_leader_ideology" in burn, "specialists: 'Сожжение книг' fires once and needs total fascism/communism", "specialists: book burning conditions wrong")
check(all(f"ktits_edu_cost_{i}" in ed_dec for i in range(1, 3)) and "ktits_edu_f_self" in ed_dec, "specialists: variable costs and the halving flag are used by the decisions", "specialists: costs/flag missing in decisions")
coop = re.search(r"(?m)^\tktits_edu_coop = {([\s\S]*?)\n\t}", dev_blk)
coop = coop.group(1) if coop else ""
ed_ev = (M / "events/ktits_education_events.txt").read_text(encoding="utf-8") if (M / "events/ktits_education_events.txt").exists() else ""
ev_ids = re.findall(r"id = (ktits_edu.\d+)\n", ed_ev)
check("target_trigger" in coop and all(f"has_idea = ktits_edu_{i}" in coop for i in (2, 3, 4, 5)) and "has_war_with = ROOT" in coop and "ktits_is_kazualia" in coop and "ktits_edu_coop_target" in coop
      and "cost = 100" in coop and "days_re_enable = 180" in coop and "days = 365" in coop and "country_event = { id = ktits_edu.1 }" in coop,
      "cooperation: targeted decision (level >= 2, not at war, not Kazualia, 365-day flag on the target, 100 PP, 180 days) fires ktits_edu.1", "cooperation: decision conditions or event call wrong")
check(ev_ids == ["ktits_edu.1", "ktits_edu.2", "ktits_edu.3"] and ed_ev.count("{") == ed_ev.count("}") and "has_opinion = { target = FROM value < 0 }" in ed_ev and "is_in_faction_with = FROM" in ed_ev
      and "ktits_edu.2" in ed_ev.split("name = ktits_edu.1.b")[0] and "ktits_edu.3" in ed_ev.split("name = ktits_edu.1.b")[1] and "ktits_spec_foreign value = 5 }" in ed_ev and "ktits_spec_foreign value = 15 }" in ed_ev
      and all(ed_loc.get(f"ktits_edu.{n}.{s}", "").strip() for n in (1, 2, 3) for s in ("t", "d", "a")) and ed_loc.get("ktits_edu.1.b", "").strip(),
      "cooperation: events 1-3 (offer with accept/refuse, answers +15 / refusal) with AI conditions (opinion, rival faction) and ru loc", "cooperation: events or their loc wrong")
dv = ed_loc.get("ktits_education_dev_category_desc", "")
check(dv.count(chr(92) + "n") == 3 and all(s_ in dv for s_ in ("£research_icon£", "£manpower_texticon£", "£right_arrow£", "[?ktits_spec_own|0]", "[?ktits_spec_foreign|0]", "[?ktits_spec_next|0]"))
      and "ktits_spec_next value = 0 }" in ed_fx and ed_fx.count("ktits_spec_next value = ktits_spec_own") == 5,
      "specialists: development category shows own / foreign / until next level on three lines with text icons; ktits_spec_next computed in the update", "specialists: three-line description or ktits_spec_next wrong")
# branch "Образование"
EDU_F = ["root", "own", "rural", "workers", "inst", "imp", "open", "mentor", "citizen", "univ", "academy", "society", "cure"]
eb = {m.group(1): m.group(0).replace("\r", "") for m in re.finditer(r"\tfocus = \{\r?\n\t\tid = (ktits_edu_\w+)[\s\S]*?\r?\n\t\}", gen)}
efl = {**load_loc(M / "localisation/russian/ktits_edu_focus_l_russian.yml")}
check(sorted(eb) == sorted("ktits_edu_" + s for s in EDU_F) and gen.count("KTITS_EDUCATION_BRANCH_BEGIN") == 1 and gen.count("{") == gen.count("}"),
      "education focuses: 13 focuses defined once in the generic tree, braces balanced", f"education focuses: {sorted(eb)}")
check(all(efl.get(k, "").strip() for f_ in eb for k in (f_, f_ + "_desc")), "education focuses: every focus has ru name and description", "education focuses: loc missing")
check("ktits_is_big_country = yes" in eb.get("ktits_edu_imp", "") and "ktits_edu_req_big" in eb.get("ktits_edu_imp", "") and "ktits_is_big_country" not in eb.get("ktits_edu_own", ""),
      "education focuses: 'Импорт умов' only for big countries (readable tooltip), 'Своими силами' for all", "education focuses: big-country condition of 'Импорт умов' missing")
check("mutually_exclusive = { focus = ktits_edu_imp }" in eb.get("ktits_edu_own", "") and "mutually_exclusive = { focus = ktits_edu_own }" in eb.get("ktits_edu_imp", ""),
      "education focuses: 'Своими силами' and 'Импорт умов' are mutually exclusive both ways", "education focuses: exclusivity broken")
check("focus = ktits_edu_rural" in eb.get("ktits_edu_univ", "") and "focus = ktits_edu_open" in eb.get("ktits_edu_univ", "") and "ktits_edu_3" in eb.get("ktits_edu_society", "") and "ktits_edu_5" in eb.get("ktits_edu_society", "") and "ktits_cas_f_cure" in eb.get("ktits_edu_cure", ""),
      "education focuses: 'Университеты' needs school or open borders, 'Общество знаний' needs level 3+, 'Лекарство от лени' sets the growth flag", "education focuses: prerequisites/conditions wrong")
check(all(int(re.search(r"\n\t\tx = (\d+)", b).group(1)) >= 68 for b in eb.values()) and "NOT = { ktits_is_kazualia = yes }" in eb.get("ktits_edu_root", "") and "is_puppet_of" in eb.get("ktits_edu_root", ""),
      "education focuses: all at x >= 68 (free columns), root closed for Kazualia and its puppets", "education focuses: position or Kazualia gate wrong")
ew = {"root": 10, "own": 10, "rural": 10, "workers": 10, "inst": 15, "imp": 10, "open": 10, "mentor": 10, "citizen": 15, "univ": 15, "academy": 15, "society": 20, "cure": 10}
check(all(f"cost = {v}\n" in eb.get("ktits_edu_" + k, "") for k, v in ew.items()), "education focuses: durations match the doc (days / 7 weeks)", "education focuses: cost differs from the doc")
check("ktits_spec_own value = 30" in blk_f.get("ktits_cas_schools", "") and "ktits_edu_{" not in blk_f.get("ktits_cas_schools", ""), "focuses: 'Школы труда' gives own specialists +30 (not a level)", "focuses: schools reward wrong")

# ---- focus branch "Экономика" (make_focuses.py) ----
eco = {m.group(1): m.group(0).replace("\r", "") for m in re.finditer(r"\tfocus = \{\r?\n\t\tid = (ktits_eco_\w+)[\s\S]*?\r?\n\t\}", gen)}
eco_ru, eco_en = load_loc(M / "localisation/russian/ktits_eco_l_russian.yml"), load_loc(M / "localisation/english/ktits_eco_l_english.yml")
check(len(eco) == 36 and gen.count("KTITS_ECONOMY_BRANCH_BEGIN") == 1 and gen.count("{") == gen.count("}"), "economy: 36 unique focuses (the doc table), braces balanced", f"economy: {len(eco)} focuses")
miss_e = [k for f_ in eco for k in (f_, f_ + "_desc") if not eco_ru.get(k, "").strip() or not eco_en.get(k, "").strip()]
check(not miss_e, "economy: every focus has ru/en name and description", f"economy: loc missing {miss_e[:6]}")
check("mutually_exclusive = { focus = ktits_eco_market }" in eco.get("ktits_eco_plan", "") and "mutually_exclusive = { focus = ktits_eco_plan }" in eco.get("ktits_eco_market", ""),
      "economy: 'Плановая экономика' and 'Рыночная экономика' are mutually exclusive both ways", "economy: exclusivity broken")
def eco_pre(k): return re.findall(r"prerequisite = \{ ([^}]*) \}", eco.get(k, ""))
check(eco_pre("ktits_eco_five2") == ["focus = ktits_eco_heavy focus = ktits_eco_collect"] and eco_pre("ktits_eco_invest") == ["focus = ktits_eco_stock focus = ktits_eco_tax"]
      and len(eco_pre("ktits_eco_belt")) == 2 and eco_pre("ktits_eco_road") == ["focus = ktits_eco_great focus = ktits_eco_flower focus = ktits_eco_quarters"],
      "economy: OR prerequisites in one block, AND prerequisites in separate blocks", "economy: prerequisites differ from the doc")
xs_ = {k: (int(re.search(r"\n\t\tx = (\d+)", b).group(1)), int(re.search(r"\n\t\ty = (\d+)", b).group(1))) for k, b in eco.items()}
check(all(x_ >= 84 for x_, _ in xs_.values()) and len(set(xs_.values())) == len(xs_), "economy: all at x >= 84 (free columns), no two focuses on one cell", "economy: position clash or x < 84")
eco_ideas = (M / "common/ideas/ktits_eco_ideas.txt").read_text(encoding="utf-8")
sp_def = set(re.findall(r"(?m)^\t\t(ktits_eco_sp_\w+) = \{", eco_ideas))
sp_used = set(re.findall(r"(?:add_ideas|idea|add_timed_idea = \{ idea|remove_ideas|has_idea) = (ktits_eco_sp_\w+)", "\n".join(eco.values())))
check(sp_used <= sp_def and all(eco_ru.get(k, "").strip() and eco_ru.get(k + "_desc", "").strip() and eco_en.get(k + "_desc", "").strip() for k in sp_def) and {"ktits_eco_sp_plan", "ktits_eco_sp_market", "ktits_eco_sp_reserve"} <= sp_def,
      f"economy: {len(sp_def)} spirits defined, used ones exist, all with lore description", f"economy: spirits undefined {sorted(sp_used - sp_def)} or without loc")
tt_used = set(re.findall(r"custom_effect_tooltip = (ktits_eco_tt_\w+)", "\n".join(eco.values())))
check(all(eco_ru.get(k, "").strip() for k in tt_used) and "ktits_eco_investment" in (M / "common/opinion_modifiers/ktits_opinion_modifiers.txt").read_text(encoding="utf-8") and "ktits_cas_tt_m5" in "\n".join(load_loc(M / "localisation/russian/ktits_casuality_l_russian.yml")) if (M / "localisation/russian/ktits_casuality_l_russian.yml").exists() else True,
      "economy: tooltips and the opinion modifier exist", "economy: tooltip loc / opinion modifier missing")
check("ktits_spec_own value = 15" in eco.get("ktits_eco_bureau", "") and "add_research_slot = 1" in eco.get("ktits_eco_bureau", "") and "has_country_flag = ktits_cas_f_dry" in mc,
      "economy: 'Научно-промышленные бюро' gives a research slot and own specialists +15; 'Сухие дома' flag is read by the growth", "economy: bureau / dry houses wiring missing")

w = {"PASS": 0, "WARN": 0, "FAIL": 0}
for lvl, msg in res:
    w[lvl] += 1
    print(f"[{lvl}] {msg}")
print(f"\n{w['PASS']} passed, {w['WARN']} warnings, {w['FAIL']} failed")
sys.exit(1 if w["FAIL"] else 0)
