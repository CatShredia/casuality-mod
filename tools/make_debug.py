"""Debug journal of all mechanics of the mod (docs/global_mechanics/Debug-Log.md). Read the journal with tools/read_log.py.

The journal is written with the effect `log` (documentation/effects_documentation.md: "Print message to game.log") ONLY while the global flag ktits_debug is set.
Line format (the game itself adds "[time][date]: " in front): KTITS:<SEC>:<TAG>:<EVENT> key=value ...   SEC = KAZ CAS EDU ALLY CONT OUT WAR EVT DEC FOC SYS
The prefix has no square brackets: "[" starts a loc command in log strings, and "|" splits the history logger category [uncertain: both from the effects doc, not tested].
How it works: this step runs LAST among the generators (after kazouter) and does not change them; it (re)injects one-line guarded log calls
  `if = { limit = { has_global_flag = ktits_debug } log = "KTITS:..." }`  into the generated files (events, decisions, focuses, scripted effects) and
writes common/scripted_effects/ktits_debug_effects.txt (monthly summaries, on/off), common/on_actions/ktits_debug_on_actions.txt (wars), ktits_debug.txt / ktits_debug_off.txt (console `run` files, mod root).
Idempotent: its own injected lines are removed first. Writes ONLY the mod folder.
Usage: python tools/make_debug.py [--mod PATH] [--auto-on]    (--auto-on: the flag is set at game start; default: off, switch on from the console)
"""
import argparse, re
from pathlib import Path
import lore_data as L

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
ap.add_argument("--auto-on", action="store_true")
a = ap.parse_args()
M = Path(a.mod)
FLAG = "ktits_debug"
GUARD = f"limit = {{ has_global_flag = {FLAG} }}"
SIG = f"has_global_flag = {FLAG} }} log = \"KTITS:"

def rd(p): return p.read_text(encoding="utf-8-sig") if p.exists() else None
def wr(p, t, bom=False):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(("﻿" if bom else "") + t, encoding="utf-8", newline="\n")

def LOG(sec, msg, ind, tag="[THIS.GetTag]"):
    """one-line guarded log call"""
    return f'{ind}if = {{ limit = {{ has_global_flag = {FLAG} }} log = "KTITS:{sec}:{tag}:{msg}" }}\n'

def strip(t):
    """remove everything this script injected: guarded log lines, calls ktits_dbg_*, empty immediate shells"""
    t = "".join(l for l in t.splitlines(True) if SIG not in l and not re.match(r"\s*ktits_dbg_\w+ = yes\s*$", l))
    return t.replace("\timmediate = {\n\t}\n", "")

_seen = set()
def load(rel):
    p = M / rel
    t = rd(p)
    if t is not None and rel not in _seen:
        t = strip(t); _seen.add(rel)     # remove old injections once per file and run
    return p, t, (p.read_bytes().startswith(b"\xef\xbb\xbf") if p.exists() else False)

stats = {}
def count(k, n=1): stats[k] = stats.get(k, 0) + n

def cost_text(c):
    if c is None: return "?"
    if re.fullmatch(r"-?\d+(\.\d+)?", c): return c
    if re.fullmatch(r"[A-Za-z_][\w]*", c): return f"[?{c}]"
    return "expr"

# ---------------- events: log in `immediate` of every country event ----------------
def do_events(rel):
    p, t, bom = load(rel)
    if t is None: return
    lines = t.splitlines(True)
    out, i = [], 0
    while i < len(lines):
        l = lines[i]
        out.append(l)
        if re.match(r"(country_event|news_event) = \{", l):
            j = i + 1
            while not re.match(r"\}", lines[j]): j += 1
            block = lines[i + 1:j]
            ev = next((re.match(r"\s*id = ([\w.]+)", b).group(1) for b in block if re.match(r"\tid = ", b)), None)
            hid = any(re.match(r"\thidden = yes", b) for b in block)
            has_imm = any(re.match(r"\timmediate = \{", b) for b in block)
            if ev:
                msg = f"FIRE {ev}{' hidden' if hid else ''}"
                logl = LOG("EVT", msg, "\t\t")
                done = False
                IMM = "\timmediate = {\n" + logl + "\t}\n"
                for k, b in enumerate(block):
                    if re.match(r"\timmediate = \{", b) and not done:
                        out.append(b); out.append(logl); done = True; count("events"); continue
                    if re.match(r"\toption = \{", b) and not done and not has_imm:
                        out.append(IMM); done = True; count("events")
                    out.append(b)
                if not done:
                    out.append(IMM); count("events")
                i = j
                continue
        i += 1
    wr(p, "".join(out), bom)

# ---------------- decisions: log in complete_effect (with the price) ----------------
def do_decisions(rel):
    p, t, bom = load(rel)
    if t is None: return
    lines = t.splitlines(True)
    # split into decisions: depth-1 blocks "\tname = {"
    out, cur_cost, name = [], None, None
    pend = []
    # first pass: collect (name -> cost)
    costs, nm = {}, None
    for l in lines:
        m = re.match(r"\t([A-Za-z_][\w]*) = \{", l)
        if m: nm = m.group(1)
        m = re.match(r"\t\tcost = (\S+)", l)
        if m and nm: costs[nm] = m.group(1)
        # Kazualia faith decisions: price is paid in complete_effect through a variable (no `cost` line)
        m = re.match(r"\s*subtract_from_variable = \{ var = ktits_kaz_faith value = ([A-Za-z_]\w*) \}", l)
        if m and nm and costs.get(nm, "0") in ("0", None): costs[nm] = m.group(1)
    nm = None
    # a decision without any price line costs 0 (game default)
    for l in lines:
        m = re.match(r"\t([A-Za-z_][\w]*) = \{", l)
        if m: costs.setdefault(m.group(1), "0")
    scale_s = "" if "kazualia" in rel else " scale=[?ktits_casuality]"   # Kazualia has no Casuality scale
    for l in lines:
        m = re.match(r"\t([A-Za-z_][\w]*) = \{", l)
        if m: nm = m.group(1)
        out.append(l)
        if re.match(r"\t\tcomplete_effect = \{", l) and nm:
            out.append(LOG("DEC", f"DONE {nm} cost={cost_text(costs.get(nm))}{scale_s}", "\t\t\t")); count("decisions")
    wr(p, "".join(out), bom)

# ---------------- focuses: log in completion_reward; the late-delayed events ----------------
def do_focuses(rel):
    p, t, bom = load(rel)
    if t is None: return
    out, fid = [], None
    for l in t.splitlines(True):
        m = re.match(r"\t\tid = ([\w]+)", l)
        if m: fid = m.group(1)
        m = re.match(r"(\s*)hidden_effect = \{ country_event = \{ id = ([\w.]+) days = (\d+) random_days = (\d+)", l)
        if m:
            ind = m.group(1)
            out.append(LOG("FOC", f"LATE_SCHEDULED focus={fid} event={m.group(2)} in={m.group(3)}..{int(m.group(3)) + int(m.group(4))} days inner=[?ktits_kaz_inner]", ind))
            count("late")
        out.append(l)
        if re.match(r"\t\tcompletion_reward = \{", l) and fid:
            out.append(LOG("FOC", f"DONE {fid} inner=[?ktits_kaz_inner]", "\t\t\t")); count("focuses")
    wr(p, "".join(out), bom)

# ---------------- scripted effects: prepend / append a log ----------------
def edit_effect(rel, name, pre=None, post=None):
    p, t, bom = load(rel)
    if t is None: return
    lines = t.splitlines(True)
    try:
        s = next(i for i, l in enumerate(lines) if l.startswith(f"{name} = {{"))
    except StopIteration:
        print(f"WARN: effect {name} not found in {rel}"); return
    e = next(i for i in range(s + 1, len(lines)) if lines[i].startswith("}"))
    if post: lines.insert(e, post)
    if pre: lines.insert(s + 1, pre)
    wr(p, "".join(lines), bom); count("effects")

def edit_effects_glob(rel, regex, pre):
    p, t, bom = load(rel)
    names = re.findall(rf"^({regex}) = \{{", t, flags=re.M)
    for n in names: edit_effect(rel, n, pre=pre(n))
    return names

I = "\t"
SE = "common/scripted_effects/"
# -- events
for f in ("ktits_kazualia_events", "ktits_kazualia_outer_events", "ktits_casuality_events", "ktits_education_events", "ktits_alliance_events"):
    do_events(f"events/{f}.txt")
# -- decisions
for f in ("ktits_kazualia_decisions", "ktits_kazualia_outer_decisions", "ktits_casuality", "ktits_casuality_kaz", "ktits_education", "ktits_alliance"):
    do_decisions(f"common/decisions/{f}.txt")
# -- focuses
do_focuses("common/national_focus/ktits_kazualia.txt")

# -- late events scheduled from decision gifts (days = N random_days = M inside hidden_effect), generic pattern
p, t, bom = load(SE + "ktits_kazualia_gift_effects.txt")
if t is not None:
    out = []
    for l in t.splitlines(True):
        m = re.match(r"(\s*)hidden_effect = \{ country_event = \{ id = ([\w.]+) days = (\d+) random_days = (\d+)", l)
        if m:
            out.append(LOG("FOC", f"LATE_SCHEDULED gift event={m.group(2)} in={m.group(3)}..{int(m.group(3)) + int(m.group(4))} days inner=[?ktits_kaz_inner]", m.group(1))); count("late")
        out.append(l)
    wr(p, "".join(out), bom)

# -- Kazualia
ncores = len(re.findall(r"\{ add_core_of = PREV \}", rd(M / SE / "ktits_kazualia_effects.txt") or ""))
edit_effect(SE + "ktits_kazualia_effects.txt", "ktits_kaz_start", post=LOG("KAZ", f"START cores_added_on_swamps={ncores} faith=[?ktits_kaz_faith] inner=[?ktits_kaz_inner]", I))
p, t, bom = load(SE + "ktits_kazualia_effects.txt")
DM = "\t\tadd_ideas = ktits_durmanische\n"
t = t.replace(DM, DM + LOG("KAZ", "DURMANISCHE_GRANTED (government casuality)", "\t\t"), 1)
wr(p, t, bom)
edit_effect(SE + "ktits_kazualia_effects.txt", "ktits_kaz_riot_fire", pre=LOG("KAZ", "RIOT_EVENT_FIRED reform=[?ktits_kaz_reform] inner=[?ktits_kaz_inner]", I))
edit_effect(SE + "ktits_kazualia_outer_effects.txt", "ktits_kaz_outer_update", post=I + "ktits_dbg_kaz_monthly = yes\n")
edit_effect(SE + "ktits_kazualia_outer_effects.txt", "ktits_kz_make_K35", pre=LOG("OUT", "BUFFER_K35_CREATED (decision Buffer on the swamps)", I))
# rebel start: before the variables are cleared (ktits_kz_n states, ktits_kz_d divisions); the slot is set by ktits_kz_make_K3x
for nm, kind in (("ktits_kz_rebel_raise", "REBEL_START"), ("ktits_kz_civwar_raise", "CIVWAR_START")):
    p, t, bom = load(SE + "ktits_kazualia_outer_effects.txt")
    s = t.index(f"\n{nm} = {{"); e = t.index("\n}", s)
    body = t[s:e]
    k = body.index("\tclear_variable = ktits_kz_n")
    body = body[:k] + LOG("OUT", f"{kind} slot=[?ktits_kz_slot] states_planned=[?ktits_kz_n] divisions_planned=[?ktits_kz_d] scale=[?ktits_casuality]", I) + body[k:]
    wr(p, t[:s] + body + t[e:], bom); count("effects")
edit_effects_glob(SE + "ktits_kazualia_outer_effects.txt", r"ktits_kz_(?:rebel|civ)_won_K\d+", lambda n: LOG("OUT", f"RESULT_WIN {n} (the rebels/Casuals win)", I))
edit_effect(SE + "ktits_kazualia_outer_effects.txt", "ktits_kz_rebel_lost", pre=LOG("OUT", "RESULT_LOSE rebels crushed, spirit Sobering 365 days, scale reset to 0", I))
edit_effect(SE + "ktits_kazualia_outer_effects.txt", "ktits_kz_civ_lost", pre=LOG("OUT", "RESULT_LOSE civil war: the Casuals lost", I))
# -- Casuality of other countries
edit_effect(SE + "ktits_casuality_monthly_effects.txt", "ktits_casuality_monthly", post=I + "ktits_dbg_cas_monthly = yes\n")
edit_effect(SE + "ktits_casuality_effects.txt", "ktits_casuality_update", post=I + "ktits_dbg_cas_tier_check = yes\n")
# -- education
edit_effect(SE + "ktits_education_effects.txt", "ktits_education_monthly", post=I + "ktits_dbg_edu_monthly = yes\n")
edit_effect(SE + "ktits_education_effects.txt", "ktits_education_update", post=I + "ktits_dbg_edu_check = yes\n")
for nm in ("ktits_edu_coop_accept", "ktits_edu_coop_refuse"):
    edit_effect(SE + "ktits_education_coop_effects.txt", nm, pre=LOG("EDU", f"{nm.upper().replace('KTITS_EDU_', '')} partner=[ROOT.GetTag] (THIS is the scope of the effect)", I))
# -- alliances
A = SE + "ktits_alliance_effects.txt"
edit_effect(A, "ktits_ally_new_alliance", pre=LOG("ALLY", "CREATED leader=[THIS.GetTag] coop=20", I))
edit_effect(A, "ktits_ally_newcomer", pre=LOG("ALLY", "JOINED leader=[PREV.GetTag] member=[THIS.GetTag] coop_of_leader=[PREV.ktits_alliance_coop]", I))
for nm, what in (("ktits_ally_dissolve", "DISSOLVED"), ("ktits_ally_dissolve_zero", "DISSOLVED_ZERO_COOP"), ("ktits_ally_dissolve_lone", "DISSOLVED_LONE")):
    edit_effect(A, nm, pre=LOG("ALLY", f"{what} leader=[THIS.GetTag] coop=[?ktits_alliance_coop] size=[?ktits_ally_size]", I))
edit_effect(A, "ktits_ally_news_leave", pre=LOG("ALLY", "LEFT_OR_EXCLUDED member=[THIS.GetTag]", I))
edit_effect(A, "ktits_ally_news_join", pre=LOG("ALLY", "JOIN_NEWS member=[THIS.GetTag]", I))
edit_effect(A, "ktits_ally_update", post=I + "ktits_dbg_ally_coop = yes\n")
edit_effect(A, "ktits_ally_leader_monthly", post=I + "ktits_dbg_ally_monthly = yes\n")
# barred countries: log when the purge fires (inside the if, before leave_faction)
p, t, bom = load(A)
t = re.sub(r"(ktits_ally_purge_barred = \{.*?\n\t\tktits_ally_forget_member = yes\n)", lambda m: m.group(1) + LOG("ALLY", "EXPELLED_BARRED member=[THIS.GetTag] (Eternal Neutrality / ideology bar)", "\t\t"), t, count=1, flags=re.S)
t = re.sub(r"(ktits_ally_purge_kaz = \{.*?\n\t\tktits_ally_forget_member = yes\n)", lambda m: m.group(1) + LOG("ALLY", "EXPELLED_CASUALITY_IDEOLOGY member=[THIS.GetTag] (Casuality ideology bar)", "\t\t"), t, count=1, flags=re.S)
wr(p, t, bom)
# -- continuous focuses
edit_effect(SE + "ktits_continuous_effects.txt", "ktits_cont_monthly", post=I + "ktits_dbg_cont_monthly = yes\n")
p, t, bom = load("common/continuous_focus/generic.txt")
b0 = t.index("# >>> ktits continuous focuses"); b1 = t.index("# <<< ktits continuous focuses")
blk = t[b0:b1]
blk = re.sub(r"(\t\t\tset_country_flag = (ktits_cont_f_\w+|ktits_ally_f_strong)\n)", lambda m: m.group(1) + LOG("CONT", f"ON focus={m.group(2)}", "\t\t\t"), blk)
blk = re.sub(r"(\t\t\tclr_country_flag = (ktits_cont_f_\w+|ktits_ally_f_strong)\n)", lambda m: m.group(1) + LOG("CONT", f"OFF focus={m.group(2)}", "\t\t\t"), blk)
wr(p, t[:b0] + blk + t[b1:], bom); count("continuous")

# ---------------- own effects ----------------
def G(body):   # guarded block
    return f"\tif = {{\n\t\tlimit = {{ has_global_flag = {FLAG} }}\n{body}\t}}\n"

ef = "# generated by tools/make_debug.py: debug journal (docs/global_mechanics/Debug-Log.md). Every body is guarded by the global flag ktits_debug.\n"
ef += f"ktits_dbg_on = {{\n\tset_global_flag = {FLAG}\n\tlog = \"KTITS:SYS:-:DEBUG_ON\"\n}}\n\n"
ef += f"ktits_dbg_off = {{\n\tlog = \"KTITS:SYS:-:DEBUG_OFF\"\n\tclr_global_flag = {FLAG}\n}}\n\n"
# Kazualia monthly (scope = Kazualia)
fl = [("ref", "ktits_kaz_reformist"), ("ind", "ktits_kaz_industrial"), ("com", "ktits_kaz_comm"), ("grt", "ktits_kaz_great"), ("neu", "ktits_kaz_neutral")]
b = "".join(f"\t\tset_variable = {{ var = ktits_dbg_p_{k} value = 0 }}\n\t\tif = {{ limit = {{ has_country_flag = {f} }} set_variable = {{ var = ktits_dbg_p_{k} value = 1 }} }}\n" for k, f in fl)
b += "\t\tset_variable = { var = ktits_dbg_brit value = 0 }\n\t\tif = { limit = { has_idea = ktits_kaz_britt_influence } set_variable = { var = ktits_dbg_brit value = 1 } }\n\t\tif = { limit = { has_idea = ktits_kaz_britt_2 } set_variable = { var = ktits_dbg_brit value = 2 } }\n\t\tif = { limit = { has_idea = ktits_kaz_britt_3 } set_variable = { var = ktits_dbg_brit value = 3 } }\n"
b += "\t\tlog = \"KTITS:KAZ:[THIS.GetTag]:MONTH faith=[?ktits_kaz_faith] faith_gain=[?ktits_kaz_faith_gain] inner=[?ktits_kaz_inner] outer=[?ktits_kaz_outer] reform=[?ktits_kaz_reform] britt=[?ktits_dbg_brit] path_ref=[?ktits_dbg_p_ref] path_ind=[?ktits_dbg_p_ind] path_com=[?ktits_dbg_p_com] path_great=[?ktits_dbg_p_grt] path_neutral=[?ktits_dbg_p_neu]\"\n"
ef += "# scope = Kazualia, once a month\nktits_dbg_kaz_monthly = {\n" + G(b) + "}\n\n"
# Casuality tier (scope = country)
t5 = "".join(f"\t\tif = {{ limit = {{ has_idea = ktits_cas_{i} }} set_variable = {{ var = ktits_dbg_tier value = {i} }} }}\n" for i in range(1, 6))
b = "\t\tif = { limit = { NOT = { has_variable = ktits_dbg_tier_prev } } set_variable = { var = ktits_dbg_tier_prev value = 0 } }\n\t\tset_variable = { var = ktits_dbg_tier value = 0 }\n" + t5
ef += "# scope = country: stores the tier 0..5 (spirit ktits_cas_N) in ktits_dbg_tier\nktits_dbg_cas_tier = {\n" + G(b) + "}\n\n"
b = "\t\tktits_dbg_cas_tier = yes\n\t\tif = {\n\t\t\tlimit = { NOT = { check_variable = { var = ktits_dbg_tier value = ktits_dbg_tier_prev compare = equals } } }\n\t\t\tlog = \"KTITS:CAS:[THIS.GetTag]:TIER prev=[?ktits_dbg_tier_prev] now=[?ktits_dbg_tier] scale=[?ktits_casuality]\"\n\t\t\tset_variable = { var = ktits_dbg_tier_prev value = ktits_dbg_tier }\n\t\t}\n"
ef += "# scope = country: called at the end of ktits_casuality_update; logs a tier change\nktits_dbg_cas_tier_check = {\n" + G(b) + "}\n\n"
b = ("\t\tif = {\n\t\t\tlimit = { check_variable = { var = ktits_casuality value = 0 compare = greater_than } }\n\t\t\tktits_dbg_cas_tier_check = yes\n"
     "\t\t\tset_variable = { var = ktits_dbg_kn value = 0 }\n\t\t\tif = { limit = { any_neighbor_country = { ktits_is_kazualia = yes } } set_variable = { var = ktits_dbg_kn value = 1 } }\n"
     "\t\t\tlog = \"KTITS:CAS:[THIS.GetTag]:MONTH scale=[?ktits_casuality] growth=[?ktits_cas_g] puppet_neighbours=[?ktits_cas_n] next_to_kaz=[?ktits_dbg_kn] tier=[?ktits_dbg_tier] edu=[?ktits_edu_t]\"\n\t\t}\n")
ef += "# scope = country (not Kazualia, not fallen), once a month, only with scale > 0\nktits_dbg_cas_monthly = {\n" + G(b) + "}\n\n"
# Education
b = "\t\tif = {\n\t\t\tlimit = {\n\t\t\t\tOR = {\n\t\t\t\t\tcheck_variable = { var = ktits_spec_own value = 0 compare = greater_than }\n\t\t\t\t\tcheck_variable = { var = ktits_spec_foreign value = 0 compare = greater_than }\n\t\t\t\t}\n\t\t\t}\n\t\t\tlog = \"KTITS:EDU:[THIS.GetTag]:MONTH level=[?ktits_edu_t] own=[?ktits_spec_own] foreign=[?ktits_spec_foreign] progress=[?ktits_spec_progress] next=[?ktits_spec_next]\"\n\t\t}\n"
ef += "# scope = country, once a month: specialists (thousands), only with specialists > 0\nktits_dbg_edu_monthly = {\n" + G(b) + "}\n\n"
b = "\t\tif = { limit = { NOT = { has_variable = ktits_dbg_edu_prev } } set_variable = { var = ktits_dbg_edu_prev value = 0 } }\n\t\tif = {\n\t\t\tlimit = { NOT = { check_variable = { var = ktits_edu_t value = ktits_dbg_edu_prev compare = equals } } }\n\t\t\tlog = \"KTITS:EDU:[THIS.GetTag]:LEVEL prev=[?ktits_dbg_edu_prev] now=[?ktits_edu_t] own=[?ktits_spec_own]\"\n\t\t\tset_variable = { var = ktits_dbg_edu_prev value = ktits_edu_t }\n\t\t}\n"
ef += "# scope = country: called at the end of ktits_education_update; logs a level change\nktits_dbg_edu_check = {\n" + G(b) + "}\n\n"
# Alliances
b = "\t\tif = { limit = { NOT = { has_variable = ktits_dbg_coop_prev } } set_variable = { var = ktits_dbg_coop_prev value = -1 } }\n\t\tif = {\n\t\t\tlimit = { NOT = { check_variable = { var = ktits_alliance_coop value = ktits_dbg_coop_prev compare = equals } } }\n\t\t\tlog = \"KTITS:ALLY:[THIS.GetTag]:COOP prev=[?ktits_dbg_coop_prev] now=[?ktits_alliance_coop] size=[?ktits_ally_size]\"\n\t\t\tset_variable = { var = ktits_dbg_coop_prev value = ktits_alliance_coop }\n\t\t}\n"
ef += "# scope = alliance leader: called from ktits_ally_update; logs a change of the cooperation scale\nktits_dbg_ally_coop = {\n" + G(b) + "}\n\n"
b = "\t\tlog = \"KTITS:ALLY:[THIS.GetTag]:MONTH coop=[?ktits_alliance_coop] size=[?ktits_ally_size] members=[?ktits_ally_n]\"\n"
ef += "# scope = alliance leader, once a month\nktits_dbg_ally_monthly = {\n" + G(b) + "}\n\n"
# continuous
b = "".join(f"\t\tif = {{ limit = {{ has_country_flag = {f} }} log = \"KTITS:CONT:[THIS.GetTag]:MONTH focus={f} scale=[?ktits_casuality] coop=[?ktits_alliance_coop]\" }}\n" for f in ("ktits_cont_f_lazy", "ktits_cont_f_swamp", "ktits_ally_f_strong"))
ef += "# scope = country, once a month: active unique continuous focuses\nktits_dbg_cont_monthly = {\n" + G(b) + "}\n"
wr(M / SE / "ktits_debug_effects.txt", ef)

# ---------------- on_actions: wars ----------------
oa = "on_actions = {\n"
oa += "\t# ROOT = the country that declares, FROM = the target (vanilla 00_on_actions.txt)\n\ton_declare_war = {\n\t\teffect = {\n\t\t\tif = {\n\t\t\t\tlimit = { has_global_flag = " + FLAG + " }\n"
oa += "\t\t\t\tset_variable = { var = ktits_dbg_wg value = 0 }\n\t\t\t\tif = { limit = { has_wargoal_against = FROM } set_variable = { var = ktits_dbg_wg value = 1 } }\n\t\t\t\tif = { limit = { has_war_with_wargoal_against = FROM } set_variable = { var = ktits_dbg_wg value = 2 } }\n"
oa += "\t\t\t\tlog = \"KTITS:WAR:[ROOT.GetTag]:DECLARE target=[FROM.GetTag] wargoal_code=[?ktits_dbg_wg]\"\n\t\t\t}\n\t\t}\n\t}\n"
oa += "\ton_war = {\n\t\teffect = {\n\t\t\tif = {\n\t\t\t\tlimit = { has_global_flag = " + FLAG + " }\n\t\t\t\tlog = \"KTITS:WAR:[ROOT.GetTag]:WAR_ENTERED\"\n\t\t\t}\n\t\t}\n\t}\n"
if a.auto_on:
    oa += f"\ton_startup = {{\n\t\teffect = {{\n\t\t\tset_global_flag = {FLAG}\n\t\t\tlog = \"KTITS:SYS:-:DEBUG_ON_AT_START\"\n\t\t}}\n\t}}\n"
oa += "}\n"
wr(M / "common/on_actions/ktits_debug_on_actions.txt", oa)

# ---------------- console run files ----------------
wr(M / "ktits_debug.txt", "effect ktits_dbg_on\n")
wr(M / "ktits_debug_off.txt", "effect ktits_dbg_off\n")
print("debug journal:", stats, "| auto-on" if a.auto_on else "| off by default")
