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
spl_txt = (M / "common/scripted_effects/ktits_splits_effects.txt").read_text(encoding="utf-8")
rel1 = re.search(r"ktits_release_K01 = [{][\s\S]*?ktits_release_K02", spl_txt)
rel1 = rel1.group(0) if rel1 else ""
check(len(re.findall(r"target = event_target:ktits_split_target", spl_txt)) == 100 and "$T$" not in spl_txt.replace("$T$ failed","") and "keep_unit_leaders_trigger" in spl_txt and "K01 = { save_event_target_as = ktits_split_target }" in rel1 and "ktits_split_share = yes" in rel1 and 0 <= rel1.find("state_population_k") < rel1.find("transfer_state") < rel1.find("ktits_split_share") < rel1.find("puppet"), "splits: army/navy/air/stockpile are split by population (100-step ratio ladder, population read before the transfer, units moved before the puppet)", "splits: population-based unit split is missing or wrongly ordered")
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
all_foc = re.findall(r"(?m)^\tfocus = \{\r?\n\t\tid = (\w+)", gen)
check(all_foc and all(i.startswith("ktits_") for i in all_foc) and "id = generic_focus" in gen and "initial_show_position" in gen,
      f"generic tree: {len(all_foc)} focuses, all ours (vanilla generic focuses removed), header generic_focus kept", f"generic tree: foreign focuses {[i for i in all_foc if not i.startswith('ktits_')][:5]}")
gx = [int(x) for x in re.findall(r"(?m)^\t\tx = (-?\d+)\r?$", gen)]
check(gx and min(gx) == 0 and max(gx) <= 90, f"generic tree: x range {min(gx) if gx else '?'}..{max(gx) if gx else '?'} (starts at 0, branches shifted left)", "generic tree: x range wrong (must start at 0)")
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
dup_d = sorted({k for k in idea_all if not k.startswith("ktits_edu_coop_") and descs.count(all_ru.get(k + "_desc", "")) > 1})
check(len(idea_all) >= 30 and not bad_d and not dup_d, f"spirits: all {len(idea_all)} ktits_* ideas have a unique lore description", f"spirits: missing/placeholder desc {bad_d[:5]}, duplicated desc {dup_d[:5]}")
# lore descriptions of decisions, decision categories, events and focuses (rule of CLAUDE.md): non-empty, no placeholder / meta text, not a copy of the name, not shared
all_en = {}
for f_ in sorted((M / "localisation/english").glob("ktits_*.yml")): all_en.update(load_loc(f_))
dec_ids_all = [k for f_ in sorted((M / "common/decisions").glob("ktits_*.txt")) for k in re.findall(r"(?m)^	(ktits_\w+) = \{", f_.read_text(encoding="utf-8"))]
cat_ids_all = [k for f_ in sorted((M / "common/decisions/categories").glob("ktits_*.txt")) for k in re.findall(r"(?m)^(ktits_\w+) = \{", f_.read_text(encoding="utf-8"))]
ev_txt_all = "".join(f_.read_text(encoding="utf-8") for f_ in sorted((M / "events").glob("ktits_*.txt")))
ev_ids_all = re.findall(r"(?m)^	id = ([\w.]+)\r?\n(?!	hidden = yes)", ev_txt_all)  # hidden events have no text
ev_opts_all = re.findall(r"(?m)^		option|^		name = ([\w.]+)", ev_txt_all)
foc_ids_all = re.findall(r"(?m)^		id = (ktits_\w+)", (M / "common/national_focus/generic.txt").read_text(encoding="utf-8-sig"))
META = PLACEHOLDERS + ("Бонус", "бонус", "Модификатор", "модификатор", "Описание", "desc")
lore_pairs = [(k, k + "_desc") for k in dec_ids_all + cat_ids_all + foc_ids_all] + [(k, k + ".d") for k in ev_ids_all]
bad_l = [d_ for _, d_ in lore_pairs if not all_ru.get(d_, "").strip() or not all_en.get(d_, "").strip() or len(all_ru.get(d_, "")) < 30 or any(m_ in all_ru[d_] for m_ in META)]
same_l = [d_ for n_, d_ in lore_pairs if all_ru.get(d_, "") == all_ru.get(n_, "") or all_ru.get(d_, "") == all_ru.get(n_ + ".t", "x")]
cnt_l = collections.Counter(all_ru.get(d_, "") for _, d_ in lore_pairs)
dup_l = sorted(d_ for _, d_ in lore_pairs if cnt_l[all_ru.get(d_, "")] > 1)
bad_o = [k for k in ev_opts_all if k and (not all_ru.get(k, "").strip() or not all_en.get(k, "").strip())]
check(len(dec_ids_all) >= 20 and len(cat_ids_all) >= 5 and len(ev_ids_all) >= 20 and len(foc_ids_all) >= 80 and not (bad_l or same_l or dup_l or bad_o),
      f"lore: {len(dec_ids_all)} decisions, {len(cat_ids_all)} categories, {len(ev_ids_all)} events, {len(foc_ids_all)} focuses (+ event options) have a non-empty unique lore description",
      f"lore: missing/short/meta desc {bad_l[:5]}, equal to name {same_l[:5]}, duplicated {dup_l[:5]}, options without loc {bad_o[:5]}")
check(len(sp_ids) == 14 and all(f"add_ideas = {s_}" in gen and f"remove_ideas = {s_}" in ch and pol_ru.get(s_) and pol_en.get(s_) for s_ in sp_ids), "politics: 14 spirits are given, removed by the reset focus and have loc", "politics: spirit problem")
check(all(re.search(r"\n\t\tx = (\d+)", pb[k]) and int(re.search(r"\n\t\tx = (\d+)", pb[k]).group(1)) >= 10 for k in pb), "politics: all focuses are at x >= 10 (right of the Casuality branch)", "politics: focus overlaps the Casuality columns")

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
check("target_trigger" in coop and all(f"has_idea = ktits_edu_{i}" in coop for i in (2, 3, 4, 5)) and "has_war_with = ROOT" in coop and "ktits_is_kazualia" in coop and "ktits_edu_coop_target" not in coop and "ktits_edu_coop_ref_" in coop and "ktits_edu_coop_done_" in coop
      and "cost = 100" in coop and "days_re_enable = 180" in coop and "country_event = { id = ktits_edu.1 }" in coop,
      "cooperation: targeted decision (level >= 2, not at war, not Kazualia, per-pair refusal/done flags, 100 PP, 180 days) fires ktits_edu.1", "cooperation: decision conditions or event call wrong")
check(ev_ids == ["ktits_edu.1", "ktits_edu.2", "ktits_edu.3"] and ed_ev.count("{") == ed_ev.count("}") and "has_opinion = { target = FROM value < 0 }" in ed_ev and "is_in_faction_with = FROM" in ed_ev
      and "ktits_edu.2" in ed_ev.split("name = ktits_edu.1.b")[0] and "ktits_edu.3" in ed_ev.split("name = ktits_edu.1.b")[1] and "ktits_spec_foreign" not in ed_ev and "ktits_edu_coop_accept = yes" in ed_ev and "ktits_edu_coop_accept_sender = yes" in ed_ev and "ktits_edu_coop_refuse = yes" in ed_ev
      and all(ed_loc.get(f"ktits_edu.{n}.{s}", "").strip() for n in (1, 2, 3) for s in ("t", "d", "a")) and ed_loc.get("ktits_edu.1.b", "").strip(),
      "cooperation: events 1-3 (offer with accept/refuse, answers: spirit / refusal flag) with AI conditions (opinion, rival faction) and ru loc", "cooperation: events or their loc wrong")
# cooperation treaty: spirits per tag, per-pair flags, monthly +2/+1, science bar
import itertools
tags_all = sorted(set(re.findall(r"(?m)^(\w{3})\s*=\s*\"countries", "".join(f_.read_text(encoding="utf-8", errors="ignore") for f_ in (M / "common/country_tags").glob("*.txt")))))
ed_cfx = (M / "common/scripted_effects/ktits_education_coop_effects.txt").read_text(encoding="utf-8") if (M / "common/scripted_effects/ktits_education_coop_effects.txt").exists() else ""
ed_ideas = (M / "common/ideas/ktits_education.txt").read_text(encoding="utf-8")
check(len(tags_all) >= 60 and all(f"	ktits_edu_coop_{x} = {{" in ed_ideas and ed_loc.get(f"ktits_edu_coop_{x}", "").strip() and ed_loc.get(f"ktits_edu_coop_{x}_desc", "").strip() for x in tags_all),
      f"cooperation: a spirit with name and lore description for each of {len(tags_all)} tags", "cooperation: spirit/loc missing for some tag")
check(all(f"ktits_edu_coop_ref_{x}" in dev_blk and f"ktits_edu_coop_done_{x}" in dev_blk and f"ktits_edu_coop_ref_{x} days = 365" in ed_cfx and f"ktits_edu_coop_init_{x}" in ed_cfx for x in tags_all)
      and ed_cfx.count("{") == ed_cfx.count("}") and "value = 2 }" in ed_cfx and "value = 1 }" in ed_cfx and "has_war_with" in ed_cfx and "country_exists" in ed_cfx and "ktits_is_kazualia = yes" in ed_cfx and "ktits_edu_coop_monthly = yes" in ed_fx,
      "cooperation: per-pair refusal (365 days) and done flags for every tag, monthly +2 (proposer) / +1, removal on war / no partner / Kazualia, called from the monthly effect", "cooperation: per-pair flags or monthly effect wrong")
check(ed_loc.get("ktits_edu_coop", "").startswith("§G+§!") and "[FROM.GetName]" in ed_loc.get("ktits_edu_coop", "") and "[X.GetName]" not in ed_loc.get("ktits_edu_coop_AFR", "") and "[AFR.GetName]" in ed_loc.get("ktits_edu_coop_AFR", ""),
      "cooperation: decision title shows the target ([FROM.GetName]), spirit title the partner ([TAG.GetName])", "cooperation: names do not use the country name")
bar_gui = (M / "interface/ktits_education.gui").read_text(encoding="utf-8") if (M / "interface/ktits_education.gui").exists() else ""
bar_sg = (M / "common/scripted_guis/ktits_education.txt").read_text(encoding="utf-8") if (M / "common/scripted_guis/ktits_education.txt").exists() else ""
bar_sl = (M / "common/scripted_localisation/ktits_education_scripted_loc.txt").read_text(encoding="utf-8") if (M / "common/scripted_localisation/ktits_education_scripted_loc.txt").exists() else ""
bar_gfx = (M / "interface/ktits_education.gfx").read_text(encoding="utf-8") if (M / "interface/ktits_education.gfx").exists() else ""
cat_f = (M / "common/decisions/categories/ktits_education_categories.txt").read_text(encoding="utf-8")
check(bar_gui.count('name = "ktits_edu_seg_') == 20 and all(f'name = "ktits_edu_seg_{i}"' in bar_gui and f"ktits_edu_seg_{i}_visible" in bar_sg for i in range(1, 21)) and not bar_gui.startswith(chr(0xFEFF)) and not bar_gfx.startswith(chr(0xFEFF))
      and bar_sg.count("ktits_spec_progress") == 20 and re.search(r"(?m)^ktits_education_dev_category = {[^}]*scripted_gui = ktits_education_ui", cat_f) and 'window_name = "ktits_education_ui_window"' in bar_sg and 'name = "ktits_education_ui_window"' in bar_gui
      and all(f"GFX_ktits_edu_seg_{i}" in bar_gfx for i in range(1, 5)) and all((M / f"gfx/interface/ktits/edu_seg_{i}.png").exists() for i in range(1, 5)) and (M / "gfx/interface/ktits/edu_bar_frame.png").exists(),
      "science bar: scripted GUI over the development category, 20 segments by ktits_spec_progress, 4 colours, sprites and PNGs exist", "science bar: gui/scripted gui/sprites wrong")
bar_loc = load_loc(M / "localisation/russian/ktits_education_bar_l_russian.yml")
check(bar_sl.count("localization_key") == 6 and all(f"ktits_edu_bar_{i}" in bar_sl and bar_loc.get(f"ktits_edu_bar_{i}", "").strip() for i in range(6)) and bar_loc.get("ktits_education_bar_label") == "[GetKtitsEduBar]"
      and "высший уровень" in bar_loc.get("ktits_edu_bar_5", "") and "[?ktits_spec_own|0]" in bar_loc.get("ktits_edu_bar_0", "") and "из 10 тыс." in bar_loc.get("ktits_edu_bar_0", "") and "из 150 тыс." in bar_loc.get("ktits_edu_bar_4", ""),
      "science bar: label by level via defined_text GetKtitsEduBar (6 texts, level 5 = highest level)", "science bar: label loc wrong")
check(all(f'name = "ktits_edu_st_{nm}_{i}"' in bar_gui and f"ktits_edu_st_{nm}_{i}_visible" in bar_sg and f"GFX_ktits_edu_stage_{i}_{nm}" in bar_gfx and (M / f"gfx/interface/ktits/edu_stage_{i}_{nm}.png").exists()
          for i in range(6) for nm in ("passed", "cur", "next", "future")) and bar_gui.count('pdx_tooltip = "ktits_edu_stage_tt_') == 24 and all(f"ktits_edu_stage_tt_{i}" in bar_loc and "тыс. наших специалистов" in bar_loc[f"ktits_edu_stage_tt_{i}"] for i in range(6))
      and all(f'name = "ktits_edu_st_thr_{i}"' in bar_gui and bar_loc.get(f"ktits_edu_stage_thr_{i}") == str(t) for i, t in enumerate([0, 10, 30, 60, 100, 150]) if i) and bar_loc.get("ktits_edu_stage_next") == "далее"
      and all(f'name = "ktits_edu_st_lbl_{i}"' in bar_gui and f"ktits_edu_st_lbl_{i}_visible" in bar_sg for i in range(6)) and bar_sg.count("var = ktits_edu_t") == 30,
      "stage row over the bar: 6 cells x 4 states (passed/current/next/future) by ktits_edu_t, sprites, PNGs, thresholds, 'next' label, tooltips with level modifiers", "stage row: gui/triggers/sprites/loc wrong")
check("ktits_spec_progress value = 100 }" in ed_fx and ed_fx.count("ktits_spec_progress min = 0 max = 100") == 5 and ed_fx.count("divide_variable = { var = ktits_spec_progress") == 5 and "ktits_spec_nthr" in ed_fx,
      "science bar: ktits_spec_progress (0-100, 100 at level 5) computed in ktits_education_update", "science bar: progress computation missing")
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
check(all(int(re.search(r"\n\t\tx = (\d+)", b).group(1)) >= 44 for b in eb.values()) and "NOT = { ktits_is_kazualia = yes }" in eb.get("ktits_edu_root", "") and "is_puppet_of" in eb.get("ktits_edu_root", ""),
      "education focuses: all at x >= 44 (right of Politics), root closed for Kazualia and its puppets", "education focuses: position or Kazualia gate wrong")
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
check(all(x_ >= 60 for x_, _ in xs_.values()) and len(set(xs_.values())) == len(xs_), "economy: all at x >= 60 (right of Education), no two focuses on one cell", "economy: position clash or x < 60")
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

# ---- vanilla leftovers (fix_vanilla_leftovers.py): nothing of the vanilla world that the mod no longer has may be referenced ----
import fix_vanilla_leftovers as FV
import make_game_rules as MG
VAN = Path(MG.GAME)
def rdv(p_): return p_.read_bytes().decode("utf-8-sig", errors="replace")
# 1. no vanilla focus tree can be selected by our tags: every focus file except generic.txt / ours / title-bar styles is an empty override
trees_left = []
tree_re_ = re.compile(r"(?m)^\s*(?:focus_tree|shared_focus|joint_focus|focus)\s*=\s*\{")
for d_ in (VAN, M):
    for f_ in (d_ / "common/national_focus").glob("*.txt"):
        if f_.name == "generic.txt" or f_.name.startswith("ktits_"): continue
        mf_ = M / "common/national_focus" / f_.name
        tx_ = rdv(mf_) if mf_.exists() else rdv(f_)
        if tree_re_.search(tx_) and not re.search(r"(?m)^style\s*=", tx_):
            trees_left.append(f_.name)
check(not trees_left, "vanilla leftovers: every vanilla focus tree is an empty override (no vanilla tree for any tag)", f"vanilla leftovers: vanilla focus trees still active: {sorted(set(trees_left))[:6]}")
gen_t = rdv(M / "common/national_focus/generic.txt")
check(len(re.findall(r"(?m)^\s*focus_tree\s*=", gen_t)) == 1, "vanilla leftovers: generic.txt holds exactly one focus tree (the one all our countries get)", "vanilla leftovers: generic.txt does not hold exactly one focus tree")
# 2. loaded scripts (mod + vanilla files that the mod neither overrides nor replaces): no reference to a decision/event/template that does not exist
REPL_ = tuple(x.rstrip("/") + "/" for x in re.findall(r'(?m)^replace_path\s*=\s*"([^"]+)"', rdv(M / "descriptor.mod")))
loaded_ = {}
for d_ in (VAN, M):
    for top_ in ("common", "events"):
        for f_ in (d_ / top_).rglob("*.txt"):
            rel_ = f_.relative_to(d_).as_posix()
            if d_ == VAN and rel_.startswith(REPL_): continue
            loaded_[rel_] = f_
dec_def, ev_def, tpl_def = set(), set(), set()
for rel_, f_ in loaded_.items():
    if re.fullmatch(r"common/decisions/[^/]+\.txt", rel_): dec_def |= FV.decision_names(rdv(f_))
    if rel_.startswith("events/"): ev_def |= FV.event_ids(rdv(f_))
    if rel_.startswith("common/factions/templates/"): tpl_def |= {n_[0] for n_ in FV.parse(rdv(f_)) if n_[5] == 0 and n_[0]}
rx_dec = re.compile(r"(?:unlock_decision_tooltip|activate_mission_tooltip|activate_mission|activate_decision|remove_mission|has_decision|has_active_mission)\s*=\s*(\w+)")
rx_blk = re.compile(r"(?:decision|mission)\s*=\s*(\w+)")
rx_ev = re.compile(r"(?:country_event|state_event|news_event)\s*=\s*(?:\{[^{}]*?\bid\s*=\s*)?([A-Za-z_]\w*\.\d+)")
rx_rnd = re.compile(r"(?m)^[ \t]*\d+[ \t]*=[ \t]*([A-Za-z_]\w*\.\d+)")
bad_dec, bad_tpl, bad_ev = [], [], []
for rel_, f_ in loaded_.items():
    if "/ktits_" in rel_ or rel_.startswith(("common/decisions/", "common/factions/")): continue
    raw_ = rdv(f_); tx_ = FV.mask(raw_)
    bad_dec += [(rel_, x_) for x_ in rx_dec.findall(tx_) if x_ not in dec_def]
    for n_ in FV.parse(raw_):
        if n_[0] in FV.BLOCK_DEC_KEYS and (m_ := rx_blk.search(tx_[n_[2]:n_[3]])) and m_.group(1) not in dec_def:
            bad_dec.append((rel_, m_.group(1)))
    bad_tpl += [(rel_, x_) for x_ in re.findall(r"has_faction_template\s*=\s*(\w+)", tx_) if x_ not in tpl_def]
    if rel_.startswith("common/on_actions/"):
        bad_ev += [(rel_, x_) for x_ in rx_ev.findall(tx_) + rx_rnd.findall(tx_) if x_ not in ev_def]
check(not bad_dec, f"vanilla leftovers: no effect or trigger refers to a decision/mission that does not exist ({len(dec_def)} decisions defined)", f"vanilla leftovers: references to missing decisions/missions: {sorted(set(bad_dec))[:5]} ({len(set(bad_dec))})")
check(not bad_tpl, "vanilla leftovers: no has_faction_template of a missing template", f"vanilla leftovers: missing faction templates: {sorted(set(bad_tpl))[:5]}")
check(not bad_ev, "vanilla leftovers: on_actions call only events that exist", f"vanilla leftovers: on_actions call missing events: {sorted(set(bad_ev))[:5]}")
# 3. on_actions: no state-scope blocks (ids of the vanilla map) in effects; ai_strategy: no country file of a vanilla tag
oa_state = []
for f_ in (M / "common/on_actions").glob("*.txt"):
    if f_.name.startswith("ktits_"): continue
    nodes_ = FV.parse(rdv(f_))
    trig_ = [(n_[1], n_[3]) for n_ in nodes_ if n_[0] in FV.TRIGGER_KEYS]
    oa_state += [f_.name for n_ in nodes_ if n_[0] and n_[0].isdigit() and n_[4] not in FV.RANDOM_PARENTS and not any(s_ < n_[1] and n_[3] <= e_ for s_, e_ in trig_)]
check(not oa_state, "vanilla leftovers: on_actions have no state-scope blocks (vanilla map ids) in effects", f"vanilla leftovers: on_actions state blocks of the vanilla map left: {sorted(set(oa_state))}")
our_t_ = set()
for f_ in (M / "common/country_tags").glob("*.txt"): our_t_ |= set(re.findall(r"(?m)^\s*([A-Z0-9]{3})\s*=", rdv(f_)))
ai_left = [f_.name for f_ in (M / "common/ai_strategy").glob("*.txt") if re.fullmatch(r"[A-Z][A-Z0-9]{2}", f_.stem) and f_.stem not in our_t_ and "emptied by Ktits" not in rdv(f_)]
check(not ai_left, "vanilla leftovers: ai_strategy holds no country file of a vanilla tag", f"vanilla leftovers: ai_strategy files of vanilla tags: {ai_left}")
# 4. tag collisions: our tags must not be vanilla tags nor be named by a vanilla script that stays active (it would fire for our country)
vt_ = set()
for f_ in (VAN / "common/country_tags").glob("*.txt"): vt_ |= set(re.findall(r"(?m)^\s*([A-Z0-9]{3})\s*=", rdv(f_)))
used_ = collections.Counter()
tag_re_ = re.compile(r"\b(" + "|".join(sorted(our_t_ - {t_ for t_ in our_t_ if t_[0] == "K" and t_[1:].isdigit()})) + r")\b")
for rel_, f_ in loaded_.items():
    if rel_.startswith(("common/names/", "common/country_tags/", "common/countries/", "common/bookmarks/", "common/characters/")) or "/ktits_" in rel_: continue
    if f_.is_relative_to(M): continue
    for t_ in tag_re_.findall(FV.mask(rdv(f_))): used_[(rel_, t_)] += 1
check(not (our_t_ & vt_) and not used_, "tags: none of our tags is a vanilla tag and no vanilla script that stays active names one (no tag collision)", f"tags: collisions {sorted(our_t_ & vt_)} / vanilla scripts naming our tags: {sorted(used_)[:6]}", warn)

# ---- alliances (make_alliances.py, docs/global_mechanics/Alliances.md) ----
import make_alliances as AL
al_files = {k: (M / k) for k in ("common/scripted_triggers/ktits_alliance_triggers.txt", "common/scripted_effects/ktits_alliance_effects.txt", "common/on_actions/ktits_alliance_on_actions.txt",
                                 "common/ideas/ktits_alliance_ideas.txt", "common/decisions/ktits_alliance.txt", "common/decisions/categories/ktits_alliance_categories.txt",
                                 "common/scripted_localisation/ktits_alliance_loc.txt", "events/ktits_alliance_events.txt")}
al_txt = {k: (f.read_text(encoding="utf-8") if f.exists() else "") for k, f in al_files.items()}
check(all(al_txt.values()) and all(t.count("{") == t.count("}") for t in al_txt.values()), f"alliances: {len(al_txt)} script files exist, braces balanced", "alliances: script file missing or unbalanced braces")
al_ru, al_en = load_loc(M / "localisation/russian/ktits_alliance_l_russian.yml"), load_loc(M / "localisation/english/ktits_alliance_l_english.yml")
a_tr, a_ef, a_oa, a_id, a_dc, a_ev = (al_txt[k] for k in ("common/scripted_triggers/ktits_alliance_triggers.txt", "common/scripted_effects/ktits_alliance_effects.txt", "common/on_actions/ktits_alliance_on_actions.txt",
                                                          "common/ideas/ktits_alliance_ideas.txt", "common/decisions/ktits_alliance.txt", "events/ktits_alliance_events.txt"))
# start alliances: leaders by tag, names from loc, only the leader (no add_to_faction in the start effect)
l2t = {v: k for k, v in tag2lore.items()}
st_ef = re.search(r"ktits_ally_start = [{][\s\S]*?\n[}]", a_ef)
st_ef = st_ef.group(0) if st_ef else ""
check(all(f"{l2t[lt]} = {{" in st_ef and f"ktits_ally_name_{k}" in st_ef and al_ru.get(f"ktits_ally_name_{k}") and al_en.get(f"ktits_ally_name_{k}") for lt, k in AL.START_LORE.items())
      and "add_to_faction" not in st_ef and "ktits_ally_start = yes" in a_oa and "on_startup" in a_oa and "create_faction_from_template" in st_ef,
      "alliances: on_startup creates the three start factions (Казуальная Идиллия, Интернационал, Беспредел) with loc names and only the leader", "alliances: start factions are wrong or lack names")
# thresholds of world tension by the ideology of the leader (author: democracy 40, theology 35, casuality 0; invented: 30, 20, 10)
tt_blk = re.search(r"ktits_ally_tension_ok = [{][\s\S]*?\n[}]", a_tr)
tt_blk = tt_blk.group(0) if tt_blk else ""
tt_found = {g: float(m_.group(1)) for g in AL.GROUPS if g != "casuality" for m_ in [re.search(r"has_government = " + g + r"\s+NOT = [{] threat < ([0-9.]+) [}]", tt_blk)] if m_}
check(tt_found == {"democratic": 0.40, "theology": 0.35, "neutrality": 0.30, "fascism": 0.20, "communism": 0.10} and "has_government = casuality" in tt_blk and AL.TENSION["casuality"] == 0
      and list(AL.TENSION.values()) == sorted(AL.TENSION.values(), reverse=True), "alliances: tension thresholds democracy 40 > theology 35 > dictatorship 30 > fascism 20 > communism 10 > Casuality 0 %", f"alliances: tension thresholds wrong: {tt_found}")
# decisions: found, request, invite, course, 7 cooperation; name and lore text in ru and en; category description by ideology
al_dec = re.findall(r"(?m)^\t(ktits_ally_\w+) = [{]", a_dc)
miss_d = [k for k in al_dec for lg in (al_ru, al_en) if not lg.get(k, "").strip() or not lg.get(k + "_desc", "").strip()]
check(len(al_dec) == 12 and not miss_d and {"ktits_ally_found", "ktits_ally_request", "ktits_ally_invite", "ktits_ally_course", "ktits_ally_leave"} <= set(al_dec), f"alliances: {len(al_dec)} decisions have ru/en name and description", f"alliances: decisions {len(al_dec)} / loc missing {miss_d[:4]}")
check(all(f"ktits_ally_lead_{g} = yes" in al_txt["common/scripted_localisation/ktits_alliance_loc.txt"] and al_ru.get(f"ktits_ally_desc_{g}") == AL.CAT_TXT[g] and al_ru.get(f"ktits_ally_name_{g}") for g in AL.GROUPS)
      and "[GetKtitsAllyDesc]" in al_ru.get("ktits_alliance_category_desc", "") and "ktits_alliance_category = {" in al_txt["common/decisions/categories/ktits_alliance_categories.txt"],
      "alliances: category \"Альянс\" (visible to all) shows the text of the alliance ideology through scripted localisation (6 texts + fallback)", "alliances: category description by ideology missing")
# eternal neutrality (author's rule): spirit for Figaria and Ledyshka, blocks founding / request / invitation; join, leave, refusal events
neu_ok = "ktits_eternal_neutrality = {" in (M / "common/ideas/ktits_neutrality_ideas.txt").read_text(encoding="utf-8") and a_ef.count("add_ideas = ktits_eternal_neutrality") == 2 and a_dc.count("has_idea = ktits_eternal_neutrality") >= 4
neu_ok = neu_ok and all(f"id = ktits_alliance.{n}" in a_ev for n in (7, 8, 9, 10, 11, 12)) and "modifier = ktits_ally_insult" in a_ev and "ktits_ally_insult = {" in (M / "common/opinion_modifiers/ktits_alliance_opinion.txt").read_text(encoding="utf-8")
check(neu_ok, "alliances: eternal neutrality (Figaria, Ledyshka) blocks alliances; events: refusal (soft / insult -50), joined, left, expelled", "alliances: neutrality or join/leave events missing")
# events: loc per ideology for the four events, every desc block, options
ev_ok = all(al_ru.get(f"ktits_alliance.{n}.d_{g}") == AL.EVENT_TXT[n][g] and f"text = ktits_alliance.{n}.d_{g}" in a_ev for n in (1, 2, 3, 4) for g in AL.GROUPS)
ev_ok = ev_ok and all(al_ru.get(f"ktits_alliance.{n}.{x}") and al_en.get(f"ktits_alliance.{n}.{x}") for n in (1, 2, 3, 4, 5) for x in ("t", "d")) and all(f"id = ktits_alliance.{n}\n" in a_ev for n in range(1, 6))
check(ev_ok, "alliances: events 'Стук в дверь', 'Приглашение', 'Чужая среди своих', 'Чужой в доме' have a text per ideology (6 desc blocks each, exactly the texts of the doc) and 'Новый курс' exists", "alliances: event texts per ideology missing or different from the doc")
check("ktits_ally_has_foreign_leader" in a_ef and "set_country_flag = ktits_ally_alien" in a_ef and "ktits_ally_coop_m20 = yes" in a_ev and "leave_faction = yes" in a_ev and "id = ktits_alliance.11 }" in a_ev
      and "is_subject = no" in a_ev and "ktits_ally_forget_member" in a_ev, "alliances: ideology change -> event for the member (leave / stay), leader event (expel / tolerate -20); no -5 for the ideology flow; puppets cannot leave or be expelled", "alliances: ideology-change flow incomplete")
# Kazualia always 100, no cooperation decisions in its alliance
check(re.search(r"ktits_ally_update = [{]\s+if = [{]\s+limit = [{] ktits_is_kazualia = yes [}]\s+set_variable = [{] var = ktits_alliance_coop value = 100", a_ef) and "ktits_ally_monthly" in a_oa
      and "ktits_ally_kz" in a_ef and all(f"ktits_ally_k{i}" in a_id and al_ru.get(f"ktits_ally_k{i}") == AL.TIERS[i - 1][3] for i in range(1, 5)) and a_dc.count("NOT = { ktits_ally_in_kaz = yes }") >= 7,
      "alliances: the scale of Kazualia is reset to 100 on every update and monthly, own tier names, the 7 cooperation decisions are hidden in its alliance", "alliances: Kazualia 100 / tier names / hidden decisions wrong")
# tiers: names of the doc, research sharing and doctrine cost modifiers, top tier experience; 8 spirits with lore
tiers_ok = all(al_ru.get(f"ktits_ally_{t}") == n and al_ru.get(f"ktits_ally_{k}") == kn and al_ru.get(f"ktits_ally_{t}_desc") and al_ru.get(f"ktits_ally_{k}_desc") for t, k, n, kn, *_ in AL.TIERS)
check(tiers_ok and a_id.count("research_sharing_per_country_bonus = 0.05") == 2 and a_id.count("research_sharing_per_country_bonus = 0.1\n") == 2 and a_id.count("research_sharing_per_country_bonus = 0.15") == 2
      and a_id.count("land_doctrine_cost_factor = -0.15") == 2 and a_id.count("naval_doctrine_cost_factor = -0.05") == 2 and a_id.count("air_doctrine_cost_factor = -0.1\n") == 2 and a_id.count("experience_gain_army = 0.05") == 2
      and "experience_gain_navy = 0.05" in a_id and "experience_gain_air = 0.05" in a_id, "alliances: 4+4 tier spirits with research sharing +5/10/15 %, doctrine cost -5/10/15 %, top tier +0.05 experience", "alliances: tier spirit modifiers wrong")
# puppets: sync from the overlord side (monthly and at the start), puppets cannot leave / be kicked, join / offer join blocked
sync = re.search(r"ktits_ally_sync_subjects = [{][\s\S]*?\n[}]", a_ef)
sync = sync.group(0) if sync else ""
dip = (M / "common/scripted_triggers/diplomacy_scripted_triggers.txt").read_text(encoding="utf-8-sig") if (M / "common/scripted_triggers/diplomacy_scripted_triggers.txt").exists() else ""
def dblk(k):
    m_ = re.search(r"(?m)^\s*" + k + r" = [{][\s\S]*?\n[}]", dip)
    return m_.group(0) if m_ else ""
check("every_subject_country" in sync and "add_to_faction" in sync and "leave_faction = yes" in sync and "ktits_ally_sync_subjects = yes" in a_ef.split("ktits_ally_monthly = {")[1] and "ktits_ally_sync_subjects = yes" in st_ef
      and "always = no" in dblk("DIPLOMACY_JOIN_FACTION_ENABLE_TRIGGER") and "always = no" in dblk("DIPLOMACY_OFFER_JOIN_FACTION_ENABLE_TRIGGER") and "is_subject = yes" in dblk("DIPLOMACY_LEAVE_FACTION_ENABLE_TRIGGER") and "is_subject = yes" in dblk("DIPLOMACY_KICK_FROM_FACTION_ENABLE_TRIGGER")
      and all(al_ru.get(k) for k in ("ktits_ally_diplo_blocked", "ktits_ally_puppet_leave", "ktits_ally_puppet_kick")),
      "alliances: puppets follow the overlord's alliance (monthly + start), cannot leave or be expelled; vanilla 'join / invite to faction' diplomacy is blocked", "alliances: puppet sync or vanilla diplomacy block missing")
tpl_vis = [m_.group(0) for p_ in (M / "common/factions/templates").glob("*.txt") for m_ in re.finditer(r"(?m)^[ \t]*visible\s*=\s*[{][^}]*[}]", p_.read_text(encoding="utf-8-sig"))]
check(tpl_vis and all("always = no" in v_ and "always = yes" not in v_ for v_ in tpl_vis), f"alliances: all {len(tpl_vis)} vanilla faction templates are invisible (no 'create faction' list)", "alliances: a faction template is still visible")
# cooperation scale: monthly sources of the doc (+1 per member, +2 common war, -1 idle, -5 lost member), decisions' deltas
lm = re.search(r"ktits_ally_leader_monthly = [{][\s\S]*?\n[}]", a_ef)
lm = lm.group(0) if lm else ""
check("value = ktits_ally_n" in lm and "value = 2 " in lm and "has_war_together_with" in lm and "value = -1 " in lm and "value = -5" in lm and "ktits_ally_busy" in lm
      and all(f"ktits_ally_member_coop_{x} = yes" in a_dc for x in ("p5", "p10")) and "ktits_ally_coop_p5 = yes" in a_ev and "ktits_ally_coop_m20 = {\n\tadd_to_variable = { var = ktits_alliance_coop value = -20 }" in a_ef,
      "alliances: scale sources (members +1, common war +2, idle -1, lost member -5, join +5, tolerate -20, cooperation decisions +5/+10)", "alliances: scale sources wrong")
# course of a puppet, AI
course_dec = a_dc.split("ktits_ally_course = {")[1].split("ktits_ally_drills")[0] if "ktits_ally_course = {" in a_dc else ""
check("ktits_ally_course_needed = yes" in course_dec and "ktits_is_kazualia" in course_dec and "has_focus_tree = generic_focus" in a_ef and "uncomplete_national_focus" in a_ef and "uncomplete_children = yes" in a_ef
      and "focus = ktits_pol_root" in a_ef and "popularity = 0.4" in a_ef and "add_stability = -0.10" in a_ef and "days = 90" in course_dec, "alliances: puppet course decision (own puppet, overlord's ideology, not Kazualia, 90 days, +40 % popularity, stability -10 %, resets the politics branch of the generic tree)", "alliances: puppet course change wrong")
foc_gen = (M / "common/national_focus/generic.txt").read_text(encoding="utf-8-sig")
check("ktits_ai_ally_locked = {" in a_tr and foc_gen.count("ktits_ai_ally_locked = yes") >= 1 + 10 + 14, f"alliances: AI weight 0 in the politics branch for other ideology groups and for the change focus while in an alliance with an independent member ({foc_gen.count('ktits_ai_ally_locked = yes')} places)", "alliances: AI lock missing in the generic focus tree")

w = {"PASS": 0, "WARN": 0, "FAIL": 0}
for lvl, msg in res:
    w[lvl] += 1
    print(f"[{lvl}] {msg}")
print(f"\n{w['PASS']} passed, {w['WARN']} warnings, {w['FAIL']} failed")
sys.exit(1 if w["FAIL"] else 0)
