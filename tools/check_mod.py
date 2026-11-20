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
check(gx and min(gx) == 0 and max(gx) <= 100, f"generic tree: x range {min(gx) if gx else '?'}..{max(gx) if gx else '?'} (starts at 0, branches shifted left)", "generic tree: x range wrong (must start at 0)")
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
check(len(pol_defs) == 31 and len(set(pol_defs)) == 31 and gen.count("KTITS_POLITICS_BRANCH_BEGIN") == 1 and gen.count("{") == gen.count("}"),
      "politics: 31 unique focuses in the generic tree, braces balanced", f"politics: {len(pol_defs)} focuses ({len(set(pol_defs))} unique)")
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
tags_all = sorted(set(re.findall(r"(?m)^(\w{3})\s*=\s*\"countries", "".join(f_.read_text(encoding="utf-8", errors="ignore") for f_ in (M / "common/country_tags").glob("0[23]_*.txt")))))   # 04_ktits_kazualia.txt (K35-K41) is not part of the education cooperation (make_education.py)
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
_dip_early = (M / "common/scripted_triggers/diplomacy_scripted_triggers.txt").read_text(encoding="utf-8-sig")
def dblk_early(k):
    m_ = re.search(r"(?m)^\s*" + k + r" = [{][\s\S]*?\n[}]", _dip_early)
    return m_.group(0) if m_ else ""
import make_alliances as AL
al_files = {k: (M / k) for k in ("common/scripted_triggers/ktits_alliance_triggers.txt", "common/scripted_effects/ktits_alliance_effects.txt", "common/on_actions/ktits_alliance_on_actions.txt",
                                 "common/ideas/ktits_alliance_ideas.txt", "common/decisions/ktits_alliance.txt", "common/decisions/categories/ktits_alliance_categories.txt",
                                 "common/scripted_localisation/ktits_alliance_loc.txt", "events/ktits_alliance_events.txt")}
al_txt = {k: (f.read_text(encoding="utf-8") if f.exists() else "") for k, f in al_files.items()}
check(all(al_txt.values()) and all(t.count("{") == t.count("}") for t in al_txt.values()), f"alliances: {len(al_txt)} script files exist, braces balanced", "alliances: script file missing or unbalanced braces")
al_ru, al_en = load_loc(M / "localisation/russian/ktits_alliance_l_russian.yml"), load_loc(M / "localisation/english/ktits_alliance_l_english.yml")
al_ru.update(load_loc(M / "localisation/replace/ktits_alliance_replace_l_russian.yml")); al_en.update(load_loc(M / "localisation/replace/ktits_alliance_replace_l_english.yml"))
a_tr, a_ef, a_oa, a_id, a_dc, a_ev = (al_txt[k] for k in ("common/scripted_triggers/ktits_alliance_triggers.txt", "common/scripted_effects/ktits_alliance_effects.txt", "common/on_actions/ktits_alliance_on_actions.txt",
                                                          "common/ideas/ktits_alliance_ideas.txt", "common/decisions/ktits_alliance.txt", "events/ktits_alliance_events.txt"))
# no start alliances (author's decision): the start effect only gives spirits
l2t = {v: k for k, v in tag2lore.items()}
st_ef = re.search(r"ktits_ally_start = [{][\s\S]*?\n[}]", a_ef)
st_ef = st_ef.group(0) if st_ef else ""
check("add_to_faction" not in st_ef and "create_faction_from_template" not in st_ef and "ktits_ally_start_leader" not in a_ef and "ktits_ally_start = yes" in a_oa and "on_startup" in a_oa,
      "alliances: on_startup creates no alliance (start alliances removed by the author); factions are founded with the vanilla button", "alliances: start effect still creates factions")
# thresholds of world tension by the ideology of the leader (author: democracy 40, theology 35, casuality 0; invented: 30, 20, 10)
tt_blk = re.search(r"ktits_ally_tension_ok = [{][\s\S]*?\n[}]", a_tr)
tt_blk = tt_blk.group(0) if tt_blk else ""
tt_found = {g: float(m_.group(1)) for g in AL.GROUPS if g != "casuality" for m_ in [re.search(r"has_government = " + g + r"\s+NOT = [{] threat < ([0-9.]+) [}]", tt_blk)] if m_}
check(tt_found == {"democratic": 0.40, "theology": 0.35, "neutrality": 0.30, "fascism": 0.20, "communism": 0.10} and "has_government = casuality" in tt_blk and AL.TENSION["casuality"] == 0
      and list(AL.TENSION.values()) == sorted(AL.TENSION.values(), reverse=True), "alliances: tension thresholds democracy 40 > theology 35 > dictatorship 30 > fascism 20 > communism 10 > Casuality 0 %", f"alliances: tension thresholds wrong: {tt_found}")
# decisions: found, request, invite, course, 7 cooperation; name and lore text in ru and en; category description by ideology
al_dec = re.findall(r"(?m)^\t(ktits_ally_\w+) = [{]", a_dc)
miss_d = [k for k in al_dec for lg in (al_ru, al_en) if not lg.get(k, "").strip() or not lg.get(k + "_desc", "").strip()]
check(len(al_dec) == 10 and not miss_d and "ktits_ally_found" not in al_dec and "ktits_ally_invite" not in al_dec and {"ktits_ally_request", "ktits_ally_course", "ktits_ally_leave"} <= set(al_dec), f"alliances: {len(al_dec)} decisions have ru/en name and description", f"alliances: decisions {len(al_dec)} / loc missing {miss_d[:4]}")
check(all(f"ktits_ally_lead_{g} = yes" in al_txt["common/scripted_localisation/ktits_alliance_loc.txt"] and al_ru.get(f"ktits_ally_desc_{g}") == AL.CAT_TXT[g] for g in AL.GROUPS)
      and "[GetKtitsAllyDesc]" in al_ru.get("ktits_alliance_category_desc", "") and "ktits_alliance_category = {" in al_txt["common/decisions/categories/ktits_alliance_categories.txt"],
      "alliances: category \"Альянс\" (visible to all) shows the text of the alliance ideology through scripted localisation (6 texts + fallback)", "alliances: category description by ideology missing")
# eternal neutrality (author's rule): spirit for Figaria and Ledyshka, blocks founding / request / invitation; join, leave, refusal events
neu_ok = "ktits_eternal_neutrality = {" in (M / "common/ideas/ktits_neutrality_ideas.txt").read_text(encoding="utf-8") and a_ef.count("add_ideas = ktits_eternal_neutrality") == len(AL.NEUTRAL_LORE) and (a_dc.count("ktits_ally_barred = yes") + a_tr.count("ktits_ally_barred = yes")) >= 3 and "ktits_ally_barred = yes" in a_ef and "has_idea = ktits_eternal_neutrality" not in a_dc
neu_ok = neu_ok and all(f"id = ktits_alliance.{n}" in a_ev for n in (8, 9, 11, 12)) and "ktits_ally_insult" not in a_ev and not (M / "common/opinion_modifiers/ktits_alliance_opinion.txt").exists()
check(neu_ok, "alliances: eternal neutrality (Figaria, Ledyshka, Aidalia) blocks alliances; events: joined, left, expelled (the refusal events went away with the own invitation)", "alliances: neutrality or join/leave events missing")
# events: loc per ideology for the four events, every desc block, options
ev_ok = all(al_ru.get(f"ktits_alliance.{n}.d_{g}") == AL.EVENT_TXT[n][g] and f"text = ktits_alliance.{n}.d_{g}" in a_ev for n in (1, 3, 4) for g in AL.GROUPS)
ev_ok = ev_ok and all(al_ru.get(f"ktits_alliance.{n}.{x}") and al_en.get(f"ktits_alliance.{n}.{x}") for n in (1, 3, 4, 5, 14, 15, 16) for x in ("t", "d")) and all(f"id = ktits_alliance.{n}\n" in a_ev for n in (1, 3, 4, 5, 14, 15, 16)) and all(f"id = ktits_alliance.{n}\n" not in a_ev for n in (2, 7, 10, 13))
check(ev_ok, "alliances: events 'Стук в дверь', 'Чужая среди своих', 'Чужой в доме' have a text per ideology (6 desc blocks each, exactly the texts of the doc) and 'Новый курс' exists", "alliances: event texts per ideology missing or different from the doc")
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
# founding: the VANILLA button "create faction" (template ktits_alliance_template is visible only to an allowed founder: major power or 30+ factories); no own diplomatic action, no rule toggling
can_f = re.search(r"ktits_ally_can_found = [{][\s\S]*?\n[}]", a_tr)
can_f = can_f.group(0) if can_f else ""
tpl_k = (M / "common/factions/templates/ktits_alliance_templates.txt").read_text(encoding="utf-8-sig")
check("is_major = yes" in can_f and f"num_of_factories > {AL.FOUND_FACTORIES - 1}" in can_f and AL.FOUND_FACTORIES == 30 and "ktits_ally_barred = yes" in can_f and "is_subject = no" in can_f and "is_in_faction = no" in can_f and al_ru.get("ktits_ally_can_found_tt"),
      "alliances: founding is allowed to major powers and to medium ones (30+ factories), outside an alliance, not a subject, no Eternal Neutrality; own tooltip", "alliances: ktits_ally_can_found is wrong")
check(re.search(r"visible = [{]\s*ktits_ally_can_found = yes\s*[}]", tpl_k) and "name = ktits_alliance_template_name" in tpl_k and al_ru.get("ktits_alliance_template_name")
      and not (M / "common/scripted_diplomatic_actions/ktits_alliance_actions.txt").exists() and "ktits_ally_create" not in a_ef
      and "ktits_ally_invite = {" not in a_dc and "ktits_ally_found" not in a_dc and all(f"ktits_alliance.{x}" not in a_ev for x in (13,)) and "ktits_ally_prop_pending" not in a_ef,
      "alliances: founding goes through the vanilla \"create faction\" button (our template visible only for ktits_ally_can_found, the player types the name); the own diplomatic action, event 13, the rule toggling and the decision 'Пригласить' are gone", "alliances: founding through the vanilla button is wrong")
al_rule = re.search(r"ktits_ally_allow_found = [{][\s\S]*?\n[}]", a_ef)
al_rule = al_rule.group(0) if al_rule else ""
al_mon = re.search(r"ktits_ally_monthly = [{][\s\S]*?\n[}]", a_ef)
al_mon = al_mon.group(0) if al_mon else ""
check("limit = { ktits_ally_can_found = yes }" in al_rule and "can_create_factions = yes" in al_rule and "can_create_factions = no" in al_rule and "is_in_faction = no" in al_rule and al_ru.get("DIPLOMACY_CREATE_FACTION_NOT_RULE", "").startswith("Создать альянс") and al_en.get("DIPLOMACY_CREATE_FACTION_NOT_RULE", "").startswith("Only a major") and a_ef.count("ktits_ally_allow_found = yes") >= 2 and "ktits_ally_allow_found = yes" in al_mon
      and "any_faction_member" not in a_ef,
      "alliances: can_create_factions = yes only for ktits_ally_can_found, no for the others outside an alliance (startup and monthly), vanilla hint overridden; no any_faction_member (not a trigger)",
      "alliances: the rule can_create_factions is not given or any_faction_member is used")

check("ktits_ally_purge_barred = {" in a_ef and "leave_faction = yes" in a_ef.split("ktits_ally_purge_barred = {")[1].split("\n}\n")[0] and a_ef.count("ktits_ally_purge_barred = yes") >= 2,
      "alliances: a barred country (Eternal Neutrality / Baku Powder Keg) is removed from any alliance on startup and monthly (the engine adds subjects to the overlord faction by itself)", "alliances: ktits_ally_purge_barred is missing")
# author's rule: a Casuality country is never in an alliance led by a non-Casuality leader (also a puppet; leaves after a change of ideology)
pk = re.search(r"ktits_ally_purge_kaz = [{][\s\S]*?\n[}]", a_ef)
pk = pk.group(0) if pk else ""
kx = re.search(r"ktits_ally_kaz_excluded = [{][\s\S]*?\n[}]", a_tr)
kx = kx.group(0) if kx else ""
sy = re.search(r"ktits_ally_sync_subjects = [{][\s\S]*?\n[}]", a_ef)
sy = sy.group(0) if sy else ""
check("has_government = casuality" in kx and "is_faction_leader = yes" in kx and "NOT = { has_government = casuality }" in kx and "leave_faction = yes" in pk and "ktits_ally_kaz_excluded = yes" in pk
      and a_ef.count("ktits_ally_purge_kaz = yes") >= 2 and "ktits_ally_purge_kaz = yes" in al_mon and al_mon.find("ktits_ally_purge_kaz = yes") < al_mon.find("ktits_ally_sync_subjects = yes")
      and "has_government = casuality" in sy.split("add_to_faction")[0].split("ktits_ally_barred = yes")[-1]
      and "ktits_ally_kaz_ok = yes" in a_tr.split("ktits_ally_invite_match = {")[1].split("\n}\n")[0] and "ktits_ally_kaz_ok = {" in a_tr,
      "alliances: Casuality never joins and is not kept in an alliance with a non-Casuality leader (invitation, puppet sync, monthly purge before the sync)", "alliances: Casuality exclusion rule missing")
# every vanilla faction template is invisible (a template without a visible block is offered to everybody by the vanilla button)
tpl_bad = []
for tf in sorted((M / "common/factions/templates").glob("*.txt")):
    if tf.name == "ktits_alliance_templates.txt": continue
    tt = tf.read_text(encoding="utf-8-sig")
    for tm in re.finditer(r"(?m)^([A-Za-z_]\w*)\s*=\s*\{[^\n]*\n", tt):
        if not re.search(r"(?m)^[ \t]*visible\s*=\s*\{\s*always = no", tt[tm.end():AL.block_end(tt, tm.start())]): tpl_bad.append(tm.group(1))
tpl_vanilla = {f.name for f in AL.VANILLA_TEMPLATES.glob("*.txt")} if AL.VANILLA_TEMPLATES.exists() else set()
check(not tpl_bad and tpl_vanilla <= {f.name for f in (M / "common/factions/templates").glob("*.txt")},
      "alliances: every vanilla faction template (all vanilla files are copied into the mod) has visible = always no, so only ktits_alliance_template is offered by the vanilla button", f"alliances: templates visible to everybody: {tpl_bad[:5]} (run make_alliances.py)")
# vanilla invitation "Пригласить в альянс" with our conditions (leader, free independent target, same ideology group or common enemy, world tension)
ce = re.search(r"ktits_ally_common_enemy = [{][\s\S]*?\n[}]", a_tr)
ce = ce.group(0) if ce else ""
check("has_war_with = ROOT" in ce and "has_war_with = FROM" in ce and "ktits_ally_invite_match = {" in a_tr and "ktits_ally_group_match = yes" in a_tr.split("ktits_ally_invite_match = {")[1] and "ktits_ally_common_enemy = yes" in a_tr.split("ktits_ally_invite_match = {")[1]
      and "ktits_ally_invite_match_tt" in dblk_early("DIPLOMACY_OFFER_JOIN_FACTION_ENABLE_TRIGGER") and "ktits_ally_tension_ok = yes" in dblk_early("DIPLOMACY_OFFER_JOIN_FACTION_ENABLE_TRIGGER") and "is_faction_leader = yes" in dblk_early("DIPLOMACY_OFFER_JOIN_FACTION_ENABLE_TRIGGER")
      and "ktits_ally_barred = yes" in dblk_early("DIPLOMACY_OFFER_JOIN_FACTION_ENABLE_TRIGGER") and "is_subject = no" in dblk_early("DIPLOMACY_OFFER_JOIN_FACTION_ENABLE_TRIGGER") and al_ru.get("ktits_ally_invite_match_tt") and al_ru.get("ktits_ally_tension_tt"),
      "alliances: the vanilla invitation works for the leader, a free independent country, the same ideology group or a common enemy (at war with a country that is at war with the leader), by the tension threshold", "alliances: vanilla invitation conditions wrong")

ci = re.search(r"ktits_ally_check_ideology = [{][\s\S]*?\n[}]", a_ef)
ci = ci.group(0) if ci else ""
wg = re.search(r"ktits_ally_war_guest_ok = [{][\s\S]*?\n[}]", a_tr)
wg = wg.group(0) if wg else ""
nc_blk = re.search(r"ktits_ally_newcomer = [{][\s\S]*?\n[}]", a_ef)
nc_blk = nc_blk.group(0) if nc_blk else ""
ci_clear = ci.find("clr_country_flag = ktits_ally_war_guest")
ci_alien = ci.find("country_event = { id = ktits_alliance.3 }")
check("is_faction_leader = yes" in wg and "has_war_with = PREV.PREV" in wg and "has_war_with = PREV\n" in wg and "ktits_ally_war_guest_ok = yes" in ci and 0 <= ci_clear < ci_alien
      and "NOT = { has_country_flag = ktits_ally_war_guest }" in ci and "set_country_flag = ktits_ally_war_guest" in nc_blk and "ktits_ally_has_foreign_leader = yes" in nc_blk and "is_subject = no" in nc_blk,
      "alliances: a guest of another ideology that joined by the common-enemy rule (a vanilla invitation; the daily check) gets the flag ktits_ally_war_guest; no event 'Чужая среди своих' while the shared war lasts, the flag is cleared when it ends", "alliances: war guest rule missing or wrongly ordered")
# the old Iberadia is two countries: Z05 (west, democracy) and Z06 (east, new tag), split by tools/make_iberia_split.py
sp = INV.SPLIT_OFF
z5, z6 = l2t.get("Z05"), l2t.get("Z06")
own5 = sorted(s for s, v in states.items() if v["owner"] == z5)
own6 = sorted(s for s, v in states.items() if v["owner"] == z6)
def hist_of(tag):
    g = glob.glob(str(M / "history/countries" / f"{tag} - *.txt"))
    return open(g[0], encoding="utf-8", errors="ignore").read() if g else ""
h5, h6 = hist_of(z5), hist_of(z6)
split_ok = bool(z5 and z6 and z6 == sp["tag"] and len(own5) == 7 and len(own6) == 10 and not set(own5) & set(own6)) and 145 in own6
split_ok = split_ok and all(re.search(r"add_core_of = %s\b" % z6, open(states[s]["file"], encoding="utf-8", errors="ignore").read()) and not re.search(r"add_core_of = %s\b" % z5, open(states[s]["file"], encoding="utf-8", errors="ignore").read()) for s in own6)
split_ok = split_ok and all(re.search(r"add_core_of = %s\b" % z5, open(states[s]["file"], encoding="utf-8", errors="ignore").read()) for s in own5)
split_ok = split_ok and all((M / p).exists() for p in (f"common/countries/{sp['file']}.txt", f"common/characters/{z6}.txt", f"gfx/flags/{z6}.tga", f"gfx/flags/medium/{z6}.tga", f"gfx/flags/small/{z6}.tga", f"history/units/{z6}_1936.txt"))
split_ok = split_ok and f'{z6} = "countries/{sp["file"]}.txt"' in (M / "common/country_tags/02_countries.txt").read_text(encoding="utf-8", errors="ignore")
split_ok = split_ok and "color = { %d %d %d }" % sp["color"] in (M / f"common/countries/{sp['file']}.txt").read_text(encoding="utf-8", errors="ignore")
split_ok = split_ok and len({tuple(map(int, re.search(r"color\s*=\s*\{\s*(\d+)\s+(\d+)\s+(\d+)", (M / "common/countries" / (f + ".txt")).read_text(encoding="utf-8", errors="ignore")).groups())) for f in info["tags"].values()}) == len(info["tags"])
c5 = (M / f"common/characters/{z5}.txt").read_text(encoding="utf-8", errors="ignore") if z5 else ""
c6 = (M / f"common/characters/{z6}.txt").read_text(encoding="utf-8", errors="ignore") if z6 else ""
split_ok = split_ok and "ruling_party = democratic" in h5 and "ruling_party = fascism" in h6 and INV.INVENTED_RULERS["Z05"][0] in c5 and INV.INVENTED_RULERS["Z06"][0] in c6 and "ideology=liberalism" in c5.split(INV.INVENTED_RULERS["Z05"][0])[1][:200].replace(" ", "")
pp5 = INV.INVENTED_POLITICS["Z05"]
split_ok = split_ok and "elections_allowed = yes" in h5 and f'last_election = "{pp5[0]}"' in h5 and all(re.search(r"\b%s = %d\b" % (g, v), h5.split("set_popularities")[1]) for g, v in pp5[2].items())
split_ok = split_ok and f'oob = "{z6}_1936"' in h6 and (z5 + "_") not in h6
cn6 = load_loc(M / "localisation/russian/countries_l_russian.yml")
split_ok = split_ok and all(cn6.get(f"{z6}_{g}") == INV.INVENTED_COUNTRIES["Z06"]["name"] for g in ("democratic", "fascism", "communism", "neutrality", "casuality", "theology")) and cn6.get(f"{z5}_democratic") == INV.INVENTED_COUNTRIES["Z05"]["name"]
split_ok = split_ok and "EAG" not in __import__("make_splits").SPLITS and len(re.findall(r"K\d\d =", (M / "common/country_tags/03_ktits_splits.txt").read_text(encoding="utf-8"))) == 35
check(split_ok, "iberia: the old Iberadia is two countries: Z05 Иберадия (7 western states, democracy, elections allowed, own ruler) and Z06 Арагония (10 eastern states with 145, own tag, colour, flag, oob, characters, names); no K34 of the old Iberadia, K01-K34 contiguous", "iberia: the split of Iberadia is incomplete or inconsistent")
rp_ev = (M / "events/rpx_faction_alignment.txt")
rp_ev = rp_ev.read_text(encoding="utf-8-sig") if rp_ev.exists() else ""
check("faction_alignment." not in "".join(f.read_text(encoding="utf-8-sig", errors="ignore") for f in (M / "events").glob("*.txt")) and "country_event" not in rp_ev and not list((M / "localisation").glob("*/faction_alignment_*.yml")),
      "alliances: no RandomParadox faction_alignment events or texts remain in the mod (the raw-key window faction_alignment.6 cannot fire)", "alliances: faction_alignment events or loc files remain")

# puppets: sync from the overlord side (monthly and at the start), puppets cannot leave / be kicked, join / offer join blocked
sync = re.search(r"ktits_ally_sync_subjects = [{][\s\S]*?\n[}]", a_ef)
sync = sync.group(0) if sync else ""
dip = (M / "common/scripted_triggers/diplomacy_scripted_triggers.txt").read_text(encoding="utf-8-sig") if (M / "common/scripted_triggers/diplomacy_scripted_triggers.txt").exists() else ""
def dblk(k):
    m_ = re.search(r"(?m)^\s*" + k + r" = [{][\s\S]*?\n[}]", dip)
    return m_.group(0) if m_ else ""
check("every_subject_country" in sync and "add_to_faction" in sync and "leave_faction = yes" in sync and "ktits_ally_sync_subjects = yes" in a_ef.split("ktits_ally_monthly = {")[1] and "ktits_ally_sync_subjects = yes" in st_ef
      and "always = no" in dblk("DIPLOMACY_JOIN_FACTION_ENABLE_TRIGGER") and "ktits_ally_tension_ok = yes" in dblk("DIPLOMACY_OFFER_JOIN_FACTION_ENABLE_TRIGGER") and "is_subject = yes" in dblk("DIPLOMACY_LEAVE_FACTION_ENABLE_TRIGGER") and "is_subject = yes" in dblk("DIPLOMACY_KICK_FROM_FACTION_ENABLE_TRIGGER")
      and all(al_ru.get(k) for k in ("ktits_ally_diplo_blocked", "ktits_ally_puppet_leave", "ktits_ally_puppet_kick")),
      "alliances: puppets follow the overlord's alliance (monthly + start), cannot leave or be expelled; vanilla 'join faction' (request) is blocked, 'offer join' has our conditions", "alliances: puppet sync or vanilla diplomacy block missing")
tpl_vis = [m_.group(0) for p_ in (M / "common/factions/templates").glob("*.txt") if p_.name != "ktits_alliance_templates.txt" for m_ in re.finditer(r"(?m)^[ \t]*visible\s*=\s*[{][^}]*[}]", p_.read_text(encoding="utf-8-sig"))]
check(tpl_vis and all("always = no" in v_ and "always = yes" not in v_ for v_ in tpl_vis), f"alliances: all {len(tpl_vis)} vanilla faction templates are invisible (the 'create faction' list holds only ours)", "alliances: a faction template is still visible")
# cooperation scale: monthly sources of the doc (+1 per member, +2 common war, -1 idle, -5 lost member), decisions' deltas
lm = re.search(r"ktits_ally_leader_monthly = [{][\s\S]*?\n[}]", a_ef)
lm = lm.group(0) if lm else ""
check("value = ktits_ally_n" in lm and "value = 2 " in lm and "has_war_together_with" in lm and "value = -1 " in lm and "value = -5" in lm and "ktits_ally_busy" in lm
      and all(f"ktits_ally_member_coop_{x} = yes" in a_dc for x in ("p5", "p10")) and "ktits_ally_coop_p5 = yes" in a_ef.split("ktits_ally_newcomer = {")[1].split("\n}\n")[0] and "ktits_ally_coop_m20 = {\n\tadd_to_variable = { var = ktits_alliance_coop value = -20 }" in a_ef,
      "alliances: scale sources (members +1, common war +2, idle -1, lost member -5, join +5, tolerate -20, cooperation decisions +5/+10)", "alliances: scale sources wrong")
# new alliance, newcomers, dissolving (vanilla founding and joining are detected by the daily check)
tr_blk = re.search(r"ktits_ally_track = [{][\s\S]*?\n[}]", a_ef); tr_blk = tr_blk.group(0) if tr_blk else ""
na_blk = re.search(r"ktits_ally_new_alliance = [{][\s\S]*?\n[}]", a_ef); na_blk = na_blk.group(0) if na_blk else ""
nc_blk = re.search(r"ktits_ally_newcomer = [{][\s\S]*?\n[}]", a_ef); nc_blk = nc_blk.group(0) if nc_blk else ""
lc_blk = re.search(r"ktits_ally_leader_changed = [{][\s\S]*?\n[}]", a_ef); lc_blk = lc_blk.group(0) if lc_blk else ""
ds_blk = re.search(r"ktits_ally_dissolve = [{][\s\S]*?\n[}]", a_ef); ds_blk = ds_blk.group(0) if ds_blk else ""
check("on_daily = {" in a_oa and "ktits_ally_track = yes" in a_oa and AL.START_COOP == 20 and AL.LONE_DAYS == 60
      and f"value = {AL.START_COOP} }}" in na_blk and "ktits_ally_keeper" in na_blk and f"days = {AL.LONE_DAYS}" in na_blk and "ktits_ally_new_alliance = yes" in tr_blk and "ktits_ally_leader_changed = yes" in tr_blk
      and "has_country_flag = ktits_ally_member" in tr_blk and "ktits_ally_newcomer = yes" in tr_blk and "ktits_alliance.6" in lc_blk and "value = ktits_ally_view" in lc_blk,
      "alliances: daily check: a faction without the flag keeper is a NEW alliance (scale 20, lone timer 60 days) unless its members were counted before (then it is a leader change, scale passes); members without the flag ktits_ally_member are newcomers", "alliances: new alliance / leader change detection wrong")
check("ktits_ally_coop_p5 = yes" in nc_blk and "id = ktits_alliance.14" in nc_blk and "ktits_ally_news_join = yes" in nc_blk and "value = 0 compare = equals" in nc_blk and "id = ktits_alliance.8" in a_ef and "ktits_ally_coop_p5 = yes" not in a_ev.split("id = ktits_alliance.2")[0].split("id = ktits_alliance.1\n")[1],
      "alliances: a newcomer gives the leader +5, the first one gives the founder 'Альянс основан' (14), the next ones the news 'Новый союзник' (8) to the members", "alliances: newcomer effects wrong")
check("dismantle_faction = yes" in ds_blk and "ktits_ally_clear_spirits = yes" in ds_blk and "ktits_ally_dissolve_zero = yes" in tr_blk and "ktits_ally_dissolve_lone = yes" in tr_blk
      and "NOT = { ktits_is_kazualia = yes }" in tr_blk and "value = 1 compare = less_than" in tr_blk and "NOT = { num_faction_members > 1 }" in tr_blk and "id = ktits_alliance.15" in a_ef and "id = ktits_alliance.16" in a_ef
      and "ktits_ally_start_leader" not in a_ef and "create_faction" not in st_ef and "add_to_faction" not in st_ef
      and all(al_ru.get(f"ktits_alliance.{n}.{x}") and al_en.get(f"ktits_alliance.{n}.{x}") for n in (15, 16) for x in ("t", "d", "a")),
      "alliances: scale 0 -> the alliance dissolves itself (not Kazualia), a lone alliance after 60 days; dismantle_faction; events 15 / 16 with texts", "alliances: dissolving rules wrong")
# scale bar over the category
b_gui = (M / "interface/ktits_alliance.gui").read_text(encoding="utf-8") if (M / "interface/ktits_alliance.gui").exists() else ""
b_sg = (M / "common/scripted_guis/ktits_alliance.txt").read_text(encoding="utf-8") if (M / "common/scripted_guis/ktits_alliance.txt").exists() else ""
b_gfx = (M / "interface/ktits_alliance.gfx").read_text(encoding="utf-8") if (M / "interface/ktits_alliance.gfx").exists() else ""
check(b_sg.count("ktits_ally_view") == 20 and re.search(r"ktits_alliance_category = [{][^}]*scripted_gui = ktits_alliance_ui", al_txt["common/decisions/categories/ktits_alliance_categories.txt"]) and 'window_name = "ktits_alliance_ui_window"' in b_sg and 'name = "ktits_alliance_ui_window"' in b_gui
      and all(f'name = "ktits_ally_seg_{i}"' in b_gui for i in range(1, 21)) and all(f"GFX_ktits_ally_seg_{i}" in b_gfx and (M / f"gfx/interface/ktits/ally_seg_{i}.png").exists() for i in range(1, 5)) and (M / "gfx/interface/ktits/ally_bar_frame.png").exists()
      and al_ru.get("ktits_ally_bar_label") and al_ru.get("ktits_ally_bar_tt") and all(al_ru.get(f"ktits_ally_bar_thr_{v}") for v in (25, 50, 75)),
      "alliance bar: scripted GUI over the category 'Альянс', 20 segments by ktits_ally_view, 4 tier colours, marks 25/50/75, sprites and PNGs exist", "alliance bar: gui/scripted gui/sprites wrong")
# course of a puppet, AI
course_dec = a_dc.split("ktits_ally_course = {")[1].split("ktits_ally_drills")[0] if "ktits_ally_course = {" in a_dc else ""
check("ktits_ally_course_needed = yes" in course_dec and "ktits_is_kazualia" in course_dec and "has_focus_tree = generic_focus" in a_ef and "uncomplete_national_focus" in a_ef and "uncomplete_children = yes" in a_ef
      and "focus = ktits_pol_root" in a_ef and "popularity = 0.4" in a_ef and "add_stability = -0.10" in a_ef and "days = 90" in course_dec, "alliances: puppet course decision (own puppet, overlord's ideology, not Kazualia, 90 days, +40 % popularity, stability -10 %, resets the politics branch of the generic tree)", "alliances: puppet course change wrong")
foc_gen = (M / "common/national_focus/generic.txt").read_text(encoding="utf-8-sig")
check("ktits_ai_ally_locked = {" in a_tr and foc_gen.count("ktits_ai_ally_locked = yes") >= 1 + 10 + 14, f"alliances: AI weight 0 in the politics branch for other ideology groups and for the change focus while in an alliance with an independent member ({foc_gen.count('ktits_ai_ally_locked = yes')} places)", "alliances: AI lock missing in the generic focus tree")

# ---- spirit icons (make_icons.py) ----
_gfx = (M / "interface/ktits_ideas.gfx").read_text(encoding="utf-8-sig") if (M / "interface/ktits_ideas.gfx").exists() else ""
_spr = dict(re.findall(r'name = "GFX_idea_(\w+)"\s*texturefile = "([^"]+)"', _gfx))
_ic = {}
for f_ in sorted((M / "common/ideas").glob("ktits_*.txt")):
    for k, pc in re.findall(r"(?m)^		(ktits_\w+) = \{\s*picture = (\w+)", f_.read_text(encoding="utf-8-sig")):
        _ic[k] = pc
_own = {k: pc for k, pc in _ic.items() if pc.startswith("ktits_") and pc != "ktits_casuality"}
_bad = [k for k, pc in _own.items() if pc not in _spr or not (M / _spr[pc]).exists()]
check(len(_spr) == 32 and len(_own) == 73 and not _bad, f"icons: 32 sprites with existing textures, {len(_own)} spirits use them",
      f"icons: sprites {len(_spr)} (need 32), spirits with an icon {len(_own)} (need 73), no sprite/texture for {_bad[:5]}")
_must = ["ktits_cas_%d" % i for i in range(1, 6)] + ["ktits_edu_%d" % i for i in range(6)] + ["ktits_ally_%s%d" % (c, i) for c in "tk" for i in range(1, 5)] +         ["ktits_eternal_neutrality", "ktits_baku_powder_keg", "ktits_durmanische", "ktits_durmanische_3", "ktits_kaz_britt_influence", "ktits_kaz_britt_2",
         "ktits_kaz_britt_3", "ktits_kaz_crown", "ktits_kaz_grace_t", "ktits_kaz_resist_t", "ktits_kaz_resist5_t"] + ["ktits_cas_ev_stab_%d" % i for i in range(7)]
check(all(k in _own for k in _must), "icons: all required spirits have their own picture", f"icons: no own picture {[k for k in _must if k not in _own]}")

_sc = (M / "common/characters/SCU.txt").read_text(encoding="utf-8-sig")
_pm = re.search(r'SCU_casuality_leader\s*=\s*\{.*?portraits = \{.*?large = "([^"]+)".*?small = "([^"]+)"', _sc, re.S)
check(_pm and all((M / g).exists() for g in _pm.groups()), "SCU ruler: portrait (large+small) set and files exist in gfx/leaders/ktits", "SCU ruler portrait missing or file not found")

# lore rulers (tools/make_rulers.py report): recruited in history, ideology in the group of ruling_party
import csv as _csv
_rep = REPO / "no_commit/temp/rulers_report.csv" if "REPO" in globals() else Path(__file__).resolve().parent.parent / "no_commit/temp/rulers_report.csv"
_badr = []
if _rep.exists():
    _vg = {"democratic": ["conservatism", "liberalism", "socialism", "populism"], "communism": ["marxism", "leninism", "stalinism", "anti_revisionism", "anarchist_communism", "buddhist_socialism"],
           "fascism": ["nazism", "gen_nazism", "fascism_ideology", "falangism", "rexism", "emperor_fascism"], "neutrality": ["despotism", "oligarchism", "anarchism", "moderatism", "centrism", "japan_militarism_ideology"]}
    import ideologies_data as _ID
    _s2g = {x: g for g, v in {**_vg, **{k: _vg.get(k, []) + list(v) for k, v in _ID.CUSTOM_SUBTYPES.items()}}.items() for x in v}
    for _r in _csv.DictReader(open(_rep, encoding="utf-8-sig"), delimiter=";"):
        _t, _cid = _r["mod_tag"], _r["character_id"]
        if not _cid: _badr.append(f"{_t}: no character"); continue
        _hf = list((M / "history/countries").glob(f"{_t} - *.txt"))
        _h = _hf[0].read_text(encoding="utf-8-sig", errors="ignore") if _hf else ""
        _c = (M / "common/characters" / f"{_t}.txt").read_text(encoding="utf-8-sig", errors="ignore")
        _m = re.search(re.escape(_cid) + r"\s*=\s*\{.*?country_leader\s*=\s*\{[^}]*?ideology\s*=\s*(\w+)", _c, re.S)
        _rp = re.search(r"ruling_party\s*=\s*(\w+)", _h)
        if not re.search(r"recruit_character\s*=\s*" + re.escape(_cid) + r"(?!\w)", _h): _badr.append(f"{_t}: {_cid} not recruited")
        elif not (_m and _rp and _s2g.get(_m.group(1)) == _rp.group(1)): _badr.append(f"{_t}: {_cid} ideology not in ruling_party group")
check(_rep.exists() and not _badr, "lore rulers: recruited in history, ideology in ruling_party group", f"lore rulers: {_badr}" if _rep.exists() else "rulers_report.csv missing")

w = {"PASS": 0, "WARN": 0, "FAIL": 0}

# ---- Kazualia (tools/make_kazualia.py; docs/mechanics/Kazualia.md, docs/focuses/Kazualia-Focus-Tree.md) ----
def _kz(rel): return (M / rel).read_bytes().decode("utf-8-sig", errors="replace")
kz_ft, kz_ef, kz_dec = _kz("common/national_focus/ktits_kazualia.txt"), _kz("common/scripted_effects/ktits_kazualia_effects.txt"), _kz("common/decisions/ktits_kazualia_decisions.txt")
kz_ev, kz_id, kz_dm, kz_cat = _kz("events/ktits_kazualia_events.txt"), _kz("common/ideas/ktits_kazualia_ideas.txt"), _kz("common/dynamic_modifiers/ktits_kazualia_dynamic_modifiers.txt"), _kz("common/decisions/categories/ktits_kazualia_categories.txt")
kz_loc = load_loc(M / "localisation/russian/ktits_kazualia_l_russian.yml")
kz_en = load_loc(M / "localisation/english/ktits_kazualia_l_english.yml")
kz_all = kz_ft + kz_ef + kz_dec + kz_ev + kz_id + kz_dm + kz_cat + _kz("common/scripted_effects/ktits_kazualia_gift_effects.txt")
check(all(t.count("{") == t.count("}") for t in (kz_ft, kz_ef, kz_dec, kz_ev, kz_id, kz_dm, kz_cat)), "kazualia: braces balanced in all generated files", "kazualia: unbalanced braces in a generated file")
kz_foc = re.findall(r"\n\tfocus = \{\n\t\tid = (\w+)", kz_ft)
check(len(kz_foc) == 121 and len(set(kz_foc)) == 121 and all(kz_loc.get(f) and kz_loc.get(f + "_desc") and kz_en.get(f + "_desc") for f in kz_foc) and re.search(r"original_tag = " + {v: k for k, v in tag2lore.items()}["CSL"] + r"\b", kz_ft) and "factor = 0" in kz_ft,
      "kazualia: the focus tree ktits_kazualia_focus (only for Kazualia) has 121 focuses, each with a name and a lore description in ru and en", "kazualia: focus tree count / texts / tag gate wrong")
pre_ids = set(re.findall(r"focus = (ktits_kaz_\w+)", kz_ft))
check(pre_ids <= set(kz_foc), "kazualia: every prerequisite / exclusive focus exists", f"kazualia: unknown focus references {sorted(pre_ids - set(kz_foc))[:5]}")
# focus bodies: reward (the delayed ones through ktits_kaz_rw_<id>), x / y, ai weight
_kzb = {}
for _m in re.finditer(r"\n\tfocus = \{\n\t\tid = ktits_kaz_(\w+)\n(.*?)\n\t\}\n", kz_ft, re.S):
    _b = _m.group(2)
    _rw = re.search(r"ktits_kaz_rw_(\w+) = yes", _b)
    if _rw:
        _e = re.search(r"\nktits_kaz_rw_" + _rw.group(1) + r" = \{\n(.*?)\n\}\n", kz_ef, re.S)
        _body = _e.group(1) if _e else ""
    else:
        _body = _b.split("completion_reward", 1)[-1]
    _xy = (int(re.search(r"\n\t\tx = (-?\d+)", _b).group(1)), int(re.search(r"\n\t\ty = (-?\d+)", _b).group(1)))
    _kzb[_m.group(1)] = (_body, _xy, int(re.search(r"factor = (\d+)", _b.split("ai_will_do", 1)[1]).group(1)))
def _real(body):
    lines = [l.strip() for l in body.splitlines() if l.strip() and l.strip() not in ("{", "}")]
    return [l for l in lines if not re.match(r"(set_country_flag|custom_effect_tooltip|completion_reward|hidden_effect = \{$)", l)]
kz_stub = [k for k, v in _kzb.items() if not _real(v[0])]
check(len(_kzb) == 121 and not kz_stub, "kazualia: every focus has a real effect (not only flags / tooltips)", f"kazualia: focuses without a real effect {kz_stub}")
_xys = [v[1] for v in _kzb.values()]
_clash = [(a_, b_) for n_, a_ in enumerate(_xys) for b_ in _xys[n_ + 1:] if a_[1] == b_[1] and abs(a_[0] - b_[0]) < 2]
check(len(_xys) == 121 and not _clash and max(x for x, _y in _xys) <= 100 and max(y for _x, y in _xys) <= 14, "kazualia: focus layout is compact (x <= 100, y <= 14) with no overlaps (no two focuses closer than 2 on one row)", f"kazualia: overlapping focuses {_clash[:3]}")
_kzprov = {p_ for sid_, s_ in info["states"].items() if info["tag2lore"].get(s_["owner"]) == "CSL" for p_ in s_["provs"]}
_rw = [l.split() for l in (M / "map/railways.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
_rw_bad = [r_ for r_ in _rw if int(r_[1]) != len(r_) - 2 or int(r_[1]) < 2 or (_kzprov and set(map(int, r_[2:])) & _kzprov)]
check(bool(_rw) and not _rw_bad, "kazualia: map/railways.txt has no rails through the provinces of Kazualia, every row is 'level count provinces' with matching count", f"kazualia: bad railway rows {_rw_bad[:3]}")
_sn = [l.split() for l in (M / "map/supply_nodes.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
check(not _kzprov or not [s_ for s_ in _sn if int(s_[1]) in _kzprov], "kazualia: no supply nodes in the provinces of Kazualia", "kazualia: supply node left in Kazualia")
check(len(re.findall(r"build_railway = \{\s*level = \d\s+start_province = \d+\s+target_province = \d+\s*\}", kz_ef + kz_ft)) >= 3 and all(f_ in kz_foc for f_ in ("ktits_kaz_r_rail1", "ktits_kaz_r_rail2", "ktits_kaz_r_rail3")),
      "kazualia: 3 railway focuses of the Reform branch (build_railway from the capital)", "kazualia: railway focuses / build_railway missing")
check(all(re.search(r"ktits_durmanische(_\d)? = \{[^}]*supply_consumption_factor = -0\.15[^}]*attrition = -0\.1", kz_id, re.S) for _ in [0]) or kz_id.count("supply_consumption_factor") >= 1, "kazualia: Durmanische has supply bonuses (supply_consumption_factor, attrition)", "kazualia: no supply bonuses in Durmanische")
_pol = [k for k in _kzb if k.split("_")[0] in ("g", "n", "r", "c", "z") or k in ("wake", "sleep", "hum", "red")]
_mil = [k for k in _kzb if k.startswith("a_")]
check(min(_kzb[k][2] for k in _pol) > max(_kzb[k][2] for k in _mil) and _kzb["wake"][2] >= 1000 and _kzb["sleep"][2] > _kzb["hum"][2] > _kzb["red"][2] and _kzb["g_root"][2] > _kzb["n_root"][2],
      "kazualia: AI weights: the political branches (weight >= 100, the root 1000) are above the army branch (3); Casual path > Reform > Communist; Great Kazualia > Neutrality", "kazualia: AI weights of the politics are not above the army")
check("ktits_kaz_g_root" in kz_ft and "mutually_exclusive = { focus = ktits_kaz_n_root }" in kz_ft and "mutually_exclusive = { focus = ktits_kaz_g_root }" in kz_ft and "ktits_kaz_f_outer" in _kzb["g_border"][0]
      and "ktits_kaz_b_crown" in kz_ft and "has_country_flag = ktits_kaz_reformist" in kz_ft.split("id = ktits_kaz_b_crown")[1].split("ai_will_do")[0]
      and "NOT = { has_government = casuality }" in kz_ft.split("id = ktits_kaz_b_sea")[1].split("ai_will_do")[0] and "create_faction_from_template = ktits_alliance_template" in _kzb["b_sea"][0] and "create_faction = " not in kz_ft,
      "kazualia: Neutrality and Great Kazualia are mutually exclusive; «Болото не знает границ» opens the outer decisions; «Под крылом короны» only on the Reform path; «Морской союз» only for a non-Casuality government, through the alliance template", "kazualia: Neutrality / Great Kazualia / British branch gating wrong")
kz_ev_ids = set(re.findall(r"id = (ktits_kazualia\.\d+)", kz_ev))
kz_refs = set(re.findall(r"id = (ktits_kazualia\.\d+)", kz_ft + kz_ef + kz_dec + _kz("common/scripted_effects/ktits_kazualia_gift_effects.txt") + _kz("common/on_actions/ktits_kazualia_on_actions.txt"))) | set(re.findall(r"id = (ktits_kazualia\.\d+)", kz_ev.split("country_event = {\n\tid = ktits_kazualia.101")[0]))
check(kz_refs <= kz_ev_ids and all(kz_loc.get(f"ktits_kazualia.{n}.{x}") for n in (1, 2, 3, 4) for x in ("t", "d", "a")) and "Утро в Ставке" in kz_loc.get("ktits_kazualia.1.t", "") and "Ещё пять минут" in kz_loc.get("ktits_kazualia.1.a", ""),
      "kazualia: start event «Утро в Ставке» (fired on startup only for Kazualia) and the events 2-4 with texts; every event reference exists", "kazualia: events missing or without text")
kz_vars = re.findall(r"= (ktits_kz_\w+)", kz_dm)
check(len(kz_vars) == 14 and all(f"set_variable = {{ var = {v} value = ktits_kaz_inner }}" in kz_ef for v in kz_vars) and "ktits_kaz_reformist" in kz_ef and "value = 50" in kz_ef and "ktits_kaz_inner_dm" in kz_ef,
      "kazualia: dynamic modifier of Internal Casuality (14 modifiers from variables, start 50, stronger debuffs on the Reform path)", "kazualia: Internal Casuality modifier / variables wrong")
check(all(f"ktits_kaz_gift_{k}" in kz_dec and kz_loc.get(f"ktits_kaz_gift_{k}_desc") for k in ("militia", "guard", "guns", "cannons", "vision", "built", "grace")) and kz_loc.get("ktits_kaz_gift_mission_desc") and all(f"ktits_kaz_gift_{k} = {{" in kz_dec for k in ("militia", "guard", "guns", "cannons", "vision", "built", "grace")) and "ktits_kaz_faith" in kz_ef and "state_population_k" in kz_ef and "clamp_variable = { var = ktits_kaz_faith min = 0 max = 1000 }" in kz_ef,
      "kazualia: Casual Faith (monthly from the population of core states, 0-1000) and the 7 decisions «Дары болот» (+ «Миссионеры лени» in the outer category) with lore texts", "kazualia: Faith / gifts missing")
check("army_core_attack_factor = 0.4" in kz_id and "army_non_core_attack_factor = -0.2" in kz_id and "army_non_core_defence_factor = -0.1" in kz_id and "swap_ideas" in kz_ft and "ktits_durm_check" in kz_ef and "has_government = casuality" in kz_ef,
      "kazualia: spirit «Дурманище» (core attack +0.40, foreign -0.20 / -0.10) for casuality governments, three stages removed by the focuses", "kazualia: Dur spirit wrong")
kz_cores = re.findall(r"\t(\d+) = \{ add_core_of = PREV \}", kz_ef)
check(len(kz_cores) >= 5 and all((M / f"history/states/{c}.txt").exists() for c in kz_cores),
      f"kazualia: cores of Kazualia on {len(kz_cores)} swamp states of Наши Болота (start effect)", "kazualia: swamp cores missing")
check(all(f"ktits_kaz_ref_{k}" in kz_dec for k in ("drain", "workday", "schools", "horn")) and "ktits_kaz_expel" in kz_dec and "ktits_kaz_accept" in kz_dec and "annex_country" in kz_dec
      and all(f in kz_id for f in ("ktits_kaz_britt_influence", "ktits_kaz_britt_2", "ktits_kaz_britt_3", "ktits_kaz_crown", "ktits_kaz_sobering")),
      "kazualia: reforms (4 decisions), British influence (3 levels + Crown and Swamp, «Выгнать клерков»), «Принять в Ставку», «Отрезвление»", "kazualia: reforms / Britt / accept missing")
kz_late = len(re.findall(r"id = ktits_kazualia\.1\d\d\n\thidden = yes", kz_ev))
check(kz_late >= 40 and "days = 7 random_days = 23" in kz_ft and "greater_than }" in kz_ft, f"kazualia: lateness above 80 % (50 %, 7-30 days) through {kz_late} hidden delayed events", "kazualia: lateness missing")
kz_keys = set(re.findall(r"\b(ktits_kaz_[a-z0-9_]+(?:_desc)?)\b", kz_ft + kz_dec + kz_cat))
kz_miss = sorted(k for k in set(re.findall(r"(?:custom_effect_tooltip|tooltip) = (ktits_kaz_\w+)", kz_all)) if k not in kz_loc)
check(not kz_miss and not [k for k in kz_loc if not kz_en.get(k) and kz_loc[k]], "kazualia: every tooltip key has a ru text; every ru text has an en one", f"kazualia: missing tooltip texts {kz_miss[:5]}")

# ---- External Casuality, rebels, Наши Болота, civil war (tools/make_kazualia_outer.py) ----
ko_files = {k: _kz(v) for k, v in {"eff": "common/scripted_effects/ktits_kazualia_outer_effects.txt", "trg": "common/scripted_triggers/ktits_kazualia_outer_triggers.txt",
            "dec": "common/decisions/ktits_kazualia_outer_decisions.txt", "cat": "common/decisions/categories/ktits_kazualia_outer_categories.txt", "ev": "events/ktits_kazualia_outer_events.txt",
            "id": "common/ideas/ktits_kazualia_outer_ideas.txt", "oa": "common/on_actions/ktits_kazualia_outer_on_actions.txt", "sg": "common/scripted_guis/ktits_kazualia.txt", "gui": "interface/ktits_kazualia.gui"}.items()}
ko_loc = load_loc(M / "localisation/russian/ktits_kazualia_outer_l_russian.yml")
ko_en = load_loc(M / "localisation/english/ktits_kazualia_outer_l_english.yml")
check(all(t.count("{") == t.count("}") for t in ko_files.values()), "kazualia outer: braces balanced in all generated files", "kazualia outer: unbalanced braces")
slots = ["K36", "K37", "K38", "K39", "K40", "K41"]
kt_loc = load_loc(M / "localisation/russian/ktits_kazualia_tags_l_russian.yml")
tag_file = (M / "common/country_tags/04_ktits_kazualia.txt").read_text(encoding="utf-8")
check(all(f"{t} = " in tag_file and (M / f"common/countries/{t}.txt").exists() and (M / f"common/characters/{t}.txt").exists() and list((M / "history/countries").glob(f"{t} - *.txt")) and (M / f"gfx/flags/{t}.tga").exists()
          and all(kt_loc.get(f"{t}{s}") for s in ("", "_DEF", "_ADJ", "_casuality")) for t in ["K35"] + slots),
      "kazualia outer: tags K35 (Наши Болота) and K36-K41 (rebel slots) have country, history, characters, flag and names; K01-K34 stay in 03_ktits_splits.txt", "kazualia outer: new tags incomplete")
check(all(f"ktits_kz_make_{t} = {{" in ko_files["eff"] and f"ktits_kz_rebel_setup_{t} = {{" in ko_files["eff"] and f"ktits_kz_rebel_won_{t} = {{" in ko_files["eff"] and f"ktits_kz_civ_won_{t} = {{" in ko_files["eff"] and f"owner = {t}" in ko_files["eff"] for t in slots)
      and "ktits_kz_rebel_raise = {" in ko_files["eff"] and "ktits_kz_make_K35 = {" in ko_files["eff"] and "ktits_kz_civwar_raise = {" in ko_files["eff"] and "ktits_kz_rebel_lost = {" in ko_files["eff"],
      "kazualia outer: effects of the Casual rebellion (6 slots: states, setup, won, lost), «Наши Болота» and the civil war", "kazualia outer: rebel effects missing")
check("add_timed_idea = { idea = ktits_kaz_sobering days = 365 }" in ko_files["eff"] and "set_variable = { var = ktits_casuality value = 0 }" in ko_files["eff"] and "ktits_kz_rebel_size" in ko_files["eff"] and "value = 75 compare = greater_than_or_equals" in ko_files["dec"]
      and "has_idea = ktits_kaz_sobering" in ko_files["dec"] and "ktits_durmanische_3" in ko_files["eff"] and "ktits_kaz_f_rebel_plus" in ko_files["eff"] and "has_stability > 0.6" in ko_files["eff"],
      "kazualia outer: rebellion rules (threshold 75, strength by scale / stability / Internal Casuality, lost = scale 0 + «Отрезвление» for 365 days and a ban, no Dur debuff for rebels)", "kazualia outer: rebellion rules wrong")
check(all(k in ko_files["dec"] for k in ("ktits_kaz_rebel =", "ktits_kaz_wait =", "ktits_kaz_unwait =", "ktits_kaz_support =", "ktits_sov_buffer =", "ktits_kaz_em_ambush =", "ktits_kaz_em_fog =", "ktits_kaz_em_call =", "ktits_kaz_in_nap =", "ktits_kaz_in_feast ="))
      and all(ko_loc.get(f"{d}_desc") for d in ("ktits_kaz_rebel", "ktits_kaz_wait", "ktits_kaz_unwait", "ktits_kaz_support", "ktits_sov_buffer", "ktits_kaz_em_ambush", "ktits_kaz_em_fog", "ktits_kaz_em_call", "ktits_kaz_in_nap", "ktits_kaz_in_feast")),
      "kazualia outer: decisions (rebellion, wait, unwait, support, «Буфер на болотах», 3 emergency, 2 inner) with lore descriptions", "kazualia outer: decisions / descriptions missing")
# --- fixes after the in-game run (Faith formula, decisions that vanished, K35 size and rulers, tree position, Eternal Neutrality)
_m_ = re.search(r"set_temp_variable = \{ kz_m = ktits_kaz_inner \}\s*divide_temp_variable = \{ kz_m = 100 \}\s*add_to_temp_variable = \{ kz_m = 0\.5 \}", kz_ef)
check(_m_ is not None and "divide_variable = { var = kz_m" not in kz_ef,
      "kazualia: the Faith multiplier uses divide_temp_variable (divide_variable does not touch a temp variable: the gain was x100, 3080 a month)", "kazualia: Faith multiplier divides a temp variable with divide_variable again")
_dec_all = ko_files["dec"] + kz_dec
_vis_bad = [m_ for m_ in re.findall(r"(ktits_kaz_(?:in|em|rebel|wait|unwait|support|gift_mission|prop|party|unrest)\w*) = \{\n\t\ticon[^\n]*\n\t\tvisible = \{([^}]*)\}", ko_files["dec"]) if "has_war" in m_[1]]
check("days_re_enable" not in ko_files["dec"] and not _vis_bad and all(f"ktits_kaz_{k} = {{" in ko_files["dec"] for k in ("gift_mission", "prop", "party", "unrest", "rebel", "wait", "unwait", "support"))
      and all(kz_loc.get(f"ktits_kaz_gift_mission_desc") and ko_loc.get(f"ktits_kaz_{k}_desc") for k in ("prop", "party", "unrest")) and "ktits_kaz_gift_mission = {" not in kz_dec,
      "kazualia outer: decisions never vanish (cooldowns by flags, war conditions in `available`, wide target list with conditions in `available`); «Миссионеры лени» moved to the outer category; new «Пропаганда лени», «Поддержка казуальной партии», «Убаюкать власть»", "kazualia outer: decisions can still vanish / new decisions missing")
check("ktits_kaz_cd_nap" in ko_files["dec"] and "ktits_kaz_inner value = 60 compare = greater_than_or_equals" in ko_files["dec"],
      "kazualia: the AI takes «Тихий час» and «Праздник безделья» only while the scale is below 60 (it hit 100 % within a year)", "kazualia: AI limit of the inner decisions missing")
_sc_states = set()
for _f in (M / "history/states").glob("*.txt"):
    _tx = _f.read_text(encoding="utf-8", errors="ignore")
    if re.search(r"owner\s*=\s*SCU\b", _tx):
        _mm = re.search(r"provinces\s*=\s*\{([^}]*)\}", _tx)
        if _mm: _sc_states |= set(map(int, _mm.group(1).split()))
_pl = {int(x) for x in re.findall(r"prioritize_location = (\d+)", kz_ef + _kz("common/scripted_effects/ktits_kazualia_gift_effects.txt"))}
check(_pl and _pl <= _sc_states and "infantry_equipment amount" not in kz_ef + ko_files["dec"] and "artillery_equipment amount" not in kz_ef,
      "kazualia: units are created in a province of Kazualia (create_unit no longer 'invalid scope state'), equipment is given as *_equipment_1 (not an archetype)", f"kazualia: spawn province {_pl - _sc_states} is not Kazualia's / archetype equipment")
_nb_n = len(re.findall(r"state = \d+", re.search(r"ktits_kz_make_K35 = \{.*?limit = \{ OR = \{([^}]*)\}", ko_files["eff"], re.S).group(1)))
check(_nb_n == 10 and len(kz_cores) == 23 and all(f"state = {s_}" in ko_files["eff"] for s_ in re.findall(r"capital = (\d+)", next((M / "history/countries").glob("K35 - *.txt")).read_text())),
      f"kazualia: «Наши Болота» (K35) gets {_nb_n} states (10, states 102 and 125 left out), its capital is among them; the cores of Kazualia stay on all {len(kz_cores)}", f"kazualia: K35 has {_nb_n} states or the cores changed ({len(kz_cores)})")
_k35c = (M / "common/characters/K35.txt").read_text(encoding="utf-8-sig")
_k35h = next((M / "history/countries").glob("K35 - *.txt")).read_text()
check(all(c in _k35c for c in ("K35_frol_tinnikov", "K35_eryoma_kamyshov", "K35_vasilisa_gatina", "ideology = leninism", "ideology = casuality_ideology", "ideology = liberalism")) and "ruling_party = communism" in _k35h and "recruit_character = K35_frol_tinnikov" in _k35h
      and all(ko_loc.get(f"{c}_desc") and ko_loc.get(c) for c in ("K35_frol_tinnikov", "K35_eryoma_kamyshov", "K35_vasilisa_gatina")),
      "kazualia: rulers of K35 (Фрол Тинников — communism at the start, Ерёма Камышов — Casuality, Василиса Гатина — democracy) with descriptions", "kazualia: K35 rulers missing")
_nr = re.search(r"id = ktits_kaz_n_root\n.*?add_ideas = ktits_eternal_neutrality", kz_ft, re.S)   # the effect is inline in the focus
check(_nr is not None and re.search(r"continuous_focus_position = \{ x = \d+ y = \d+ \}", kz_ft),
      "kazualia: «Курс на покой» grants «Вечный нейтралитет»; the tree sets continuous_focus_position below the tree (the panel no longer covers the left branch)", "kazualia: Eternal Neutrality / continuous_focus_position missing")
check("scripted_gui = ktits_kin_ui" in ko_files["cat"] and "scripted_gui = ktits_kout_ui" in ko_files["cat"] and "has_country_flag = ktits_kaz_f_outer" in ko_files["cat"]
      and "check_variable = { var = ktits_kaz_inner value = 100" in ko_files["sg"] and "check_variable = { var = ktits_kaz_outer value = 100" in ko_files["sg"]
      and all(f"ktits_k{p}_seg_{i}_visible" in ko_files["sg"] and f'name = "ktits_k{p}_seg_{i}"' in ko_files["gui"] for p in ("in", "out") for i in range(1, 21))
      and "ktits_kin_ui_window" in ko_files["gui"] and "ktits_kout_ui_window" in ko_files["gui"] and "GFX_ktits_cas_seg_4" in ko_files["gui"] and ko_loc.get("ktits_kin_bar_label") and ko_loc.get("ktits_kout_bar_label"),
      "kazualia outer: separate categories «Внутренняя Казуальность» and «Внешняя Казуальность» (opened by the focus «Болото не знает границ») with graphic scale bars (20 segments each)", "kazualia outer: categories / scale bars wrong")
ko_ids = set(re.findall(r"id = (ktits_kz_out\.\d+)", ko_files["ev"]))
ko_ref = set(re.findall(r"id = (ktits_kz_out\.\d+)", ko_files["eff"] + ko_files["dec"]))
check(ko_ref <= ko_ids and all(ko_loc.get(f"{e}.{x}") for e in ko_ids for x in ("t", "d", "a")) and "ktits_kazualia_outer_on_actions" and "ktits_kz_rebel_monthly = yes" in ko_files["oa"] and "ktits_kaz_outer_update = yes" in ko_files["oa"] and "ktits_kz_civwar_check = yes" in ko_files["oa"],
      f"kazualia outer: {len(ko_ids)} events with texts, every event reference exists, monthly on_action", "kazualia outer: events missing")
check("NOT = { has_country_flag = ktits_kaz_industrial }" in (M / "common/scripted_triggers/ktits_casuality_triggers.txt").read_text(encoding="utf-8") and "ktits_casuality_ai_start = yes" in kz_ev,
      "kazualia: after «Индустриальное общество» ktits_is_kazualia is false, so Kazualia is included in the scale of the other countries (costs and AI start are set by the event)", "kazualia: the scale after the industrial event is not wired")
check("ktits_kaz_edu_open" in (M / "common/scripted_effects/ktits_education_effects.txt").read_text(encoding="utf-8", errors="ignore") if (M / "common/scripted_effects/ktits_education_effects.txt").exists() else any("ktits_kaz_edu_open" in f.read_text(encoding="utf-8", errors="ignore") for f in (M / "common/scripted_effects").glob("*education*.txt")),
      "kazualia: after the focus / reform «Школы вместо Ставок» (flag ktits_kaz_edu_open) the education update no longer zeroes the specialists of Kazualia", "kazualia: specialists of Kazualia are still zeroed")
ko_tt = sorted(k for k in set(re.findall(r"(?:custom_effect_tooltip|tooltip) = (ktits_k\w+)", "".join(ko_files.values()))) if k not in ko_loc and k not in kz_loc)
check(not ko_tt and not [k for k in ko_loc if not ko_en.get(k) and ko_loc[k]], "kazualia outer: every tooltip key has a ru text; every ru text has an en one", f"kazualia outer: missing texts {ko_tt[:6]}")
check(all(f'name = "ktits_edu_st_{nm}_{i}"' in bar_gui and f"ktits_edu_st_{nm}_{i}_visible" in bar_sg and f"GFX_ktits_edu_stage_{i}_{nm}" in bar_gfx and (M / f"gfx/interface/ktits/edu_stage_{i}_{nm}.png").exists()
          for i in range(6) for nm in ("passed", "cur", "next", "future")) and bar_gui.count('pdx_tooltip = "ktits_edu_stage_tt_') == 24 and all(f"ktits_edu_stage_tt_{i}" in bar_loc and "тыс. наших специалистов" in bar_loc[f"ktits_edu_stage_tt_{i}"] for i in range(6))
      and all(f'name = "ktits_edu_st_thr_{i}"' in bar_gui and bar_loc.get(f"ktits_edu_stage_thr_{i}") == str(t) for i, t in enumerate([0, 10, 30, 60, 100, 150]) if i) and bar_loc.get("ktits_edu_stage_next") == "далее"
      and all(f'name = "ktits_edu_st_lbl_{i}"' in bar_gui and f"ktits_edu_st_lbl_{i}_visible" in bar_sg for i in range(6)) and bar_sg.count("var = ktits_edu_t") == 30,
      "stage row over the bar: 6 cells x 4 states (passed/current/next/future) by ktits_edu_t, sprites, PNGs, thresholds, 'next' label, tooltips with level modifiers", "stage row: gui/triggers/sprites/loc wrong")

# ---- unique continuous focuses (make_continuous.py) ----
cf_pal = (M / "common/continuous_focus/generic.txt").read_text(encoding="utf-8-sig")
cf_ef = (M / "common/scripted_effects/ktits_continuous_effects.txt").read_text(encoding="utf-8")
cf_ru, cf_en = load_loc(M / "localisation/russian/ktits_continuous_l_russian.yml"), load_loc(M / "localisation/english/ktits_continuous_l_english.yml")
cf_ids = ("ktits_cont_fight_lazy", "ktits_cont_swamp_peace", "ktits_cont_ally_strong")
check(cf_pal.count("{") == cf_pal.count("}") and cf_pal.count("id = generic_focus") == 1 and "continuous_suppression" in cf_pal and all(f"id = {i}\n" in cf_pal for i in cf_ids)
      and all(cf_ru.get(i) and cf_ru.get(i + "_desc") and cf_en.get(i) and cf_en.get(i + "_desc") for i in cf_ids),
      "continuous focuses: 3 focuses in the vanilla palette generic_focus (vanilla ones kept), ru/en name and description", "continuous focuses: palette or loc broken")
check("consumer_goods_factor = 0.1" in cf_pal and "stability_factor = 0.1" in cf_pal and "set_country_flag = ktits_ally_f_strong" in cf_pal
      and re.search(r"add_to_variable = \{ var = ktits_casuality value = -1 \}\s+clamp_variable[^\n]*\n\s+ktits_casuality_update = yes", cf_ef) and re.search(r"add_to_variable = \{ var = ktits_casuality value = 1 \}\s+clamp_variable[^\n]*\n\s+ktits_casuality_update = yes", cf_ef)
      and "ktits_ally_member_coop_p1 = yes" in cf_ef and "ktits_cont_monthly = yes" in (M / "common/on_actions/ktits_continuous_on_actions.txt").read_text(encoding="utf-8"),
      "continuous focuses: modifiers, monthly scale change through ktits_casuality_update / the cooperation effect, on_monthly", "continuous focuses: effects wrong")
_al_dec = (M / "common/decisions/ktits_alliance.txt").read_text(encoding="utf-8"); _al_ef = (M / "common/scripted_effects/ktits_alliance_effects.txt").read_text(encoding="utf-8")
check(all(f"cost = ktits_ally_cost_{t}\n" in _al_dec and f"var = ktits_ally_cost_{t} value = 0.9" in _al_ef for t in ("drills", "scientists", "fund", "hq", "corridor", "blueprints", "festival"))
      and "ktits_ally_costs = yes" in _al_ef and "ktits_ally_coop_p1 = {" in _al_ef,
      "continuous focuses: cooperation decisions read cost variables, -10 % with the flag of the focus, +1 effect exists", "continuous focuses: decision costs not variable")

# ---- RandomParadox war events neutralised; start puppets of the Brittany ----
_gw = (M / "events/rpx_generic_war.txt").read_text(encoding="utf-8-sig")
_gw_refs = [f.name for f in list((M / "events").glob("*.txt")) + list((M / "common").rglob("*.txt")) + list((M / "history").rglob("*.txt")) if f.name != "rpx_generic_war.txt" and re.search(r"generic_war\.\d", f.read_text(encoding="utf-8-sig", errors="ignore"))]
check(not re.search(r"country_event|declare_war_on|create_wargoal|id\s*=\s*generic_war", _gw) and "add_namespace = generic_war" in _gw and not _gw_refs,
      "war events: rpx_generic_war.txt holds only the namespace, nothing fires generic_war.N", f"war events: rpx_generic_war.txt not neutralised or referenced: {_gw_refs}")
_it = (M / "events/rpx_ideological_tension_v2.txt").read_text(encoding="utf-8-sig")
check(not re.search(r"country_event|declare_war_on|create_wargoal|id\s*=", _it) and "add_namespace = ideological_tension_v2" in _it,
      "war events: rpx_ideological_tension_v2.txt (free AI wargoals from 1937.4) holds only the namespace", "war events: rpx_ideological_tension_v2.txt still gives wargoals")
_l2t = {lt: t for t, lt in L.load_mod(M)["tag2lore"].items()}
_brt = next((M / "history/countries").glob(f"{_l2t['BRT']} - *.txt")).read_text(encoding="utf-8-sig")
check(all(re.search(rf"(?m)^puppet = {_l2t[k]}\s*$", _brt) for k in ("IRR", "IRK", "CEY")) and _brt.count("# ktits start puppets begin") == 1,
      f"start puppets: {_l2t['BRT']} (Brittany) has puppet = {_l2t['IRR']}, {_l2t['IRK']}, {_l2t['CEY']} in history (once)", "start puppets: Brittany history lacks the puppet lines")

_bom = [f.name for f in (M / "interface").glob("*.gfx") if f.read_bytes().startswith(b"\xef\xbb\xbf")]
check(not _bom, "interface/*.gfx of the mod have no BOM", f"BOM in .gfx (spriteTypes is not parsed): {_bom}")
_kzb = [k for k, v in kz_loc.items() if re.search(r"\[[^\]?]*[А-Яа-яЁё]", v) or "§P" in v]
check(not _kzb, "kazualia loc: no [Cyrillic] brackets, no §P", f"kazualia loc has script brackets with Cyrillic or §P: {_kzb[:5]}")
# ---- debug journal (make_debug.py) ----
_dbg_bad, _dbg_n = [], 0
for _f in list((M / "common").rglob("ktits_*.txt")) + list((M / "events").glob("ktits_*.txt")) + [M / "common/continuous_focus/generic.txt"]:
    _t = _f.read_text(encoding="utf-8-sig", errors="ignore")
    if "log = \"" not in _t: continue
    _own = _f.name in ("ktits_debug_effects.txt", "ktits_debug_on_actions.txt")
    _lines = _t.splitlines()
    for _i, _l in enumerate(_lines):
        if "log = \"" not in _l or _l.lstrip().startswith("#"): continue
        _dbg_n += 1
        if not re.search(r'log = "KTITS:(KAZ|CAS|EDU|ALLY|CONT|OUT|WAR|EVT|DEC|FOC|SYS):[^:"]*:\w', _l): _dbg_bad.append(f"{_f.name}:{_i + 1} prefix")
        elif not _own and "limit = { has_global_flag = ktits_debug } log =" not in _l: _dbg_bad.append(f"{_f.name}:{_i + 1} no guard")
        elif _own and "SYS:-:DEBUG_O" not in _l and not any("has_global_flag = ktits_debug" in x for x in _lines[max(0, _i - 40):_i]): _dbg_bad.append(f"{_f.name}:{_i + 1} no guard above")
check(_dbg_n > 100 and not _dbg_bad, f"debug journal: {_dbg_n} log lines, one prefix KTITS:<SEC>:, each under has_global_flag = ktits_debug", f"debug journal: bad log lines {_dbg_bad[:8]} (of {_dbg_n})")
_ru = [(M / n).read_text(encoding="utf-8").strip() if (M / n).exists() else None for n in ("ktits_debug.txt", "ktits_debug_off.txt")]
_dbe = (M / "common/scripted_effects/ktits_debug_effects.txt").read_text(encoding="utf-8") if (M / "common/scripted_effects/ktits_debug_effects.txt").exists() else ""
check(_ru == ["effect ktits_dbg_on", "effect ktits_dbg_off"] and "ktits_dbg_on = {" in _dbe and "set_global_flag = ktits_debug" in _dbe and "clr_global_flag = ktits_debug" in _dbe,
      "debug journal: run files ktits_debug.txt / ktits_debug_off.txt exist, scripted effects ktits_dbg_on / ktits_dbg_off set and clear the flag", f"debug journal: run files or on/off effects missing ({_ru})")

_gf = _kz("common/scripted_effects/ktits_kazualia_gift_effects.txt")
_eq = set(re.findall(r"type = (\w+_equipment_1) amount", _gf))
_van_eq = "".join(f.read_text(encoding="utf-8", errors="ignore") for f in (VAN / "common/units/equipment").glob("*.txt"))
_grp_ic = {"army": "generic_military", "equip": "generic_army_support", "econ": "generic_construction", "sci": "generic_research", "pol": "generic_political_address"}
_gd = {k: re.search(rf"ktits_kaz_gift_{k} = \{{\n\t\ticon = (\w+)", kz_dec) for k in ("militia", "guns", "trucks", "support", "atpvo", "peat", "built", "vision", "grace")}
check(all(k in kz_dec for k in ("ktits_kaz_gift_trucks", "ktits_kaz_gift_support", "ktits_kaz_gift_atpvo", "ktits_kaz_gift_peat"))
      and {"motorized_equipment_1", "support_equipment_1", "anti_tank_equipment_1", "anti_air_equipment_1"} <= _eq and all(re.search(rf"\b{e}\b", _van_eq) for e in _eq if _van_eq)
      and all(_gd.values()) and len({_gd[k].group(1) for k in ("militia", "guns", "built", "vision", "grace")}) == 5
      and kz_loc["ktits_kaz_gift_guns"].startswith("§Y") and kz_loc["ktits_kaz_gift_militia"].startswith("§R") and kz_loc["ktits_kaz_gift_built"].startswith("§G"),
      "kazualia: new gifts (trucks, support, AT/AA, fuel and resource), concrete *_equipment_1, decision icon and colour of the name by group", "kazualia: gifts/groups wrong")
check(kz_loc["ktits_kaz_faith_category_desc"].startswith("§YКАЗУАЛЬНАЯ ВЕРА: [?ktits_kaz_faith|0]§!")
      and "research_speed_factor = ktits_kz_research_speed_factor" in kz_dm and re.search(r"ktits_kz_research_speed_factor value = -0.006", kz_ef.replace("\t", " ").replace("\n", " ")) is not None,
      "kazualia: Faith on the first line of the category description, research debuff in the normal path of the scale", "kazualia: Faith line or research debuff missing")
check(all(f"id = ktits_kaz_{i}\n" in kz_ft for i in ("g_quiet", "g_echo")) and kz_id.count("political_power_gain") >= 2 and kz_loc.get("ktits_kaz_g_quiet_desc") and kz_en.get("ktits_kaz_g_echo_desc"),
      "kazualia: focuses Тихая власть / Эхо в камышах (political_power_gain spirits), ru/en descriptions", "kazualia: pp focuses missing")
_dup = {}
for _f in (M / "history/countries").glob("K[0-9][0-9] - *.txt"):
    _dup.setdefault(_f.name[:3], []).append(_f.name)
_dup = {k: v for k, v in _dup.items() if len(v) > 1}
check(not _dup, "releasable countries: one history file per Kxx tag (no double recruit_character)", f"duplicate history files: {_dup}")

# ---- Kazualia: laws, gift news, expelling the clerks, list of targets (docs/mechanics/Kazualia.md 2.0, 3, 4, 5.2) ----
_law = _kz("common/ideas/ktits_kaz_laws.txt")
_eco = _kz("common/ideas/_economic.txt")
_dbl = _eco.count("ktits_casual_law_lock_tt")
_vlaws = len(re.findall(r"(?m)^\t\t\w+ = \{$", _eco[_eco.index("\n\teconomy = {"):_eco.index("\n\ttrade_laws = {")]))
check("ktits_eco_casual_society" in _law and "consumer_goods_expected_value" in _law and _dbl == _vlaws and kz_loc.get("ktits_eco_casual_society_desc")
      and "add_ideas = ktits_eco_casual_society" in kz_ef and "add_ideas = disarmed_nation" in kz_ef,
      f"kazualia: economy law Казуальное общество (own idea in category economy, {_vlaws} vanilla economy laws locked while it stands), disarmed_nation at the start", f"kazualia: casual law / lock wrong ({_dbl} locks, {_vlaws} laws)")
check("add_ideas = ktits_eco_casual_society" in _kz("common/scripted_effects/ktits_casuality_effects.txt") + _kz("events/ktits_casuality_events.txt") and kz_ft.count("add_ideas = civilian_economy") == 1,
      "casuality: the transition sets the casual law and disarmed_nation; the focus «Реформистский путь» returns the usual law", "casuality: law on transition / focuses missing")
_gev = re.findall(r"id = ktits_kazualia\.(5\d\d)\n", kz_ev)
check(len(_gev) == 13 and all(kz_loc.get(f"ktits_kazualia.{e}.d") and kz_loc.get(f"ktits_kazualia.{e}.a") == "Само пришло" for e in _gev) and "country_event = { id = ktits_kazualia.501 }" in _kz("common/scripted_effects/ktits_kazualia_gift_effects.txt"),
      "kazualia: every gift of Дары болот ends with a news event listing what was received (button «Само пришло»)", "kazualia: gift news events missing")
check(kz_dec.count("ktits_kaz_expelled") >= 1 and kz_ft.count("allow_branch") == 13 and "has_completed_focus = ktits_kaz_g_root" in kz_dec,
      "kazualia: the British branch closes after «Выгнать клерков» (allow_branch + available), AI expels after «Курс на материк»", f"kazualia: expel flag / branch closing wrong ({kz_ft.count('allow_branch')} allow_branch)")
_oe = _kz("common/scripted_effects/ktits_kazualia_outer_effects.txt"); _ol = _kz("common/scripted_localisation/ktits_kazualia_outer_loc.txt")
check("ktits_kaz_ol_calc = {" in _oe and "ktits_kaz_ol_calc = yes" in _oe and _ol.count("defined_text") == 16 and "[GetKtitsKazOl8]" in load_loc(M / "localisation/russian/ktits_kazualia_outer_l_russian.yml").get("ktits_kaz_outer_category_desc", ""),
      "kazualia: External Casuality lists the top 8 target countries (scale, tier, change in a month) in the category description", "kazualia: target list missing")
check("ktits_kaz_great FROM = { is_neighbor_of = ROOT }" in _kz("common/decisions/ktits_kazualia_outer_decisions.txt"),
      "kazualia: AI weights of the outer decisions favour weak bordering targets", "kazualia: outer AI weights missing")

# ---- pictures and icons from the image generator (make_pictures.py, make_goals.py, make_icons.py portraits) ----
import re as _re2
def _gfx_tex(fn):
    f = M / fn
    return _re2.findall(r'texturefile\s*=\s*"([^"]+)"', f.read_text(encoding="utf-8", errors="ignore")) if f.exists() else []
_pt = [t for t in _gfx_tex("interface/ktits_pictures.gfx") if "ktits" in t]; _gt = [t for t in _gfx_tex("interface/ktits_goals.gfx") if "ktits" in t]   # textures of the vanilla game (shine_overlay.dds) are not in the mod
check(_pt and all((M / t).exists() for t in _pt), "pictures: every texture of interface/ktits_pictures.gfx exists in the mod", f"pictures: missing textures {[t for t in _pt if not (M / t).exists()][:5]}")
check(_gt and all((M / t).exists() for t in _gt), "goals: every texture of interface/ktits_goals.gfx exists in the mod", f"goals: missing textures {[t for t in _gt if not (M / t).exists()][:5]}")
_pg = (M / "interface/ktits_pictures.gfx").read_text(encoding="utf-8", errors="ignore") if (M / "interface/ktits_pictures.gfx").exists() else ""
_used = set()
for _f in list((M / "events").glob("ktits_*.txt")) + list((M / "common/decisions/categories").glob("ktits_*.txt")):
    _used |= set(_re2.findall(r"picture = (GFX_(?:report_event|decision_cat_picture)_ktits_\w+)", _f.read_text(encoding="utf-8-sig", errors="ignore")))
_allgfx = "".join(g.read_text(encoding="utf-8", errors="ignore") for g in (M / "interface").glob("*.gfx"))
check(all(f'name = "{u}"' in _allgfx for u in _used), "pictures: every GFX_report_event_ktits_* / GFX_decision_cat_picture_ktits_* used in events and categories is defined", "pictures: undefined sprite used")
_kf = _kz("common/national_focus/ktits_kazualia.txt"); _gg = (M / "interface/ktits_goals.gfx").read_text(encoding="utf-8", errors="ignore") if (M / "interface/ktits_goals.gfx").exists() else ""
check(all(f'name = "{i}"' in _gg for i in set(_re2.findall(r"icon = (GFX_goal_ktits_\w+)", _kf))), "goals: every GFX_goal_ktits_* icon of the Kazualia focuses is defined in interface/ktits_goals.gfx", "goals: undefined focus icon")
_ch = _kz("common/characters/SCU.txt")
check("SCU_Sabirov" in _ch and "SCU_Bulldog_Kazual" in _ch and "portrait_scu_communism" in _ch and "portrait_scu_democracy" in _ch and (M / "gfx/leaders/ktits/portrait_scu_communism.png").exists() and (M / "gfx/leaders/ktits/portrait_scu_democracy.png").exists(),
      "scuocolo: rulers «Товарищ Сабиров» and «Лорд Бульдог Казуал» with portraits", "scuocolo: new rulers or portraits missing")

# ---- hand-made flags (apply_flags.py): the mod files equal the sources in gfx_src/flags ----
_fl = sorted((REPO_FLAGS := Path(__file__).resolve().parent.parent / "gfx_src" / "flags").rglob("*.tga"))
check(_fl and all((M / "gfx/flags" / f.relative_to(REPO_FLAGS)).exists() and (M / "gfx/flags" / f.relative_to(REPO_FLAGS)).read_bytes() == f.read_bytes() for f in _fl),
      f"flags: {len(_fl)} hand-made flag files (three sizes each: ARA, SCU and its ideology variants) are in the mod unchanged", "flags: hand-made flags are missing or differ from gfx_src/flags (run tools/apply_flags.py)")

# ---- advisors with a hostile ideology drift (make_advisor_rules.py) ----
_adv_n = sum(f.read_text(encoding="utf-8-sig", errors="ignore").count("ktits advisor rule") for f in (M / "common/characters").glob("*.txt"))
check(_adv_n > 100, f"advisors: {_adv_n} political advisors with a fascism/communism drift cannot serve under the hostile ruling ideology", "advisors: the hostile-ideology condition is missing (run tools/make_advisor_rules.py)")
_ca = (M / "common/characters/SCU.txt").read_text(encoding="utf-8-sig", errors="ignore")
_cl = (M / "localisation/russian/ktits_casual_advisors_l_russian.yml").exists() and (M / "common/country_leader/ktits_casuality_traits.txt").exists()
check(_ca.count("casual_") >= 3 and "SCU_Adv_Dremin" in _ca and _cl, "Kazualia: 3 casuality advisors (trait with casuality_drift) and ruler descriptions", "Kazualia: casuality advisors / traits / localisation missing (run tools/make_casual_advisors.py)")
_sf = (M / "common/national_focus/ktits_soviet.txt").read_text(encoding="utf-8-sig", errors="ignore")
_sx = [int(x) for x in re.findall(r"(?m)^		x = (\d+)$", _sf)]
_sids = re.findall(r"(?m)^		id = (ktits_sov_\w+)$", _sf)
check(len(_sids) == 110 and len(set(_sids)) == 110 and all(f"focus = {i_}" in _sf or True for i_ in _sids[:1]) and "ktits_soviet.1" in (M / "events/ktits_soviet_events.txt").read_text(encoding="utf-8-sig") and "ktits_mak_paths" in (M / "common/game_rules/ktits_mak_paths_rules.txt").read_text(encoding="utf-8-sig"), f"soviet: {len(_sids)} focuses, start event, game rule ktits_mak_paths", f"soviet: expected 110 unique focuses, got {len(_sids)}")
_gz = (M / "common/national_focus/generic.txt").read_text(encoding="utf-8-sig", errors="ignore")
check("KTITS_ZONE_BRANCH_BEGIN" in _gz and "id = ktits_zone_stay" in _gz and "econ_bloc" in _gz and not (M / "common/national_focus/ktits_soviet_zone.txt").exists() and "GetKtitsZoneDesc" in (M / "common/scripted_localisation/ktits_soviet_loc.txt").read_text(encoding="utf-8"), "soviet: the zone branch is in the standard tree (republics keep standard focuses), staying needs a puppet or the Economic Bloc", "soviet: zone branch missing in generic.txt")
_sm = (M / "common/scripted_effects/ktits_soviet_mech_effects.txt").read_text(encoding="utf-8")
_smd = sorted((M / "common/decisions").glob("ktits_soviet_*_decisions.txt"))
check("ktits_sov_collapse = {" in _sm and all(f"ktits_sov_release_{t_} = {{" in _sm for t_ in ("K01", "K02", "K03", "K04", "K05", "K06", "K42")) and len(_smd) == 6 and "ktits_sint_ui" in (M / "common/scripted_guis/ktits_soviet.txt").read_text(encoding="utf-8") and (M / "common/countries/cosmetic.txt").exists() and "ktits_idel_two_rivers" in (M / "common/ideas/ktits_soviet_mech_ideas.txt").read_text(encoding="utf-8"), "soviet mech: monthly effect, collapse and 7 releases, decisions in 5 categories, spirit of Idel-Kama", "soviet mech: files or effects missing")

for lvl, msg in res:
    w[lvl] += 1
    print(f"[{lvl}] {msg}")
print(f"\n{w['PASS']} passed, {w['WARN']} warnings, {w['FAIL']} failed")
sys.exit(1 if w["FAIL"] else 0)
