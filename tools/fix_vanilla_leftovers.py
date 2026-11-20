"""Clean up vanilla leftovers that produce error.log noise in the total conversion (idempotent, run after make_game_rules.py).
1. Game rules removed by make_game_rules.py (<TAG>_ai_behavior ...) are still tested by vanilla scripts (has_game_rule = { rule = X option = Y }).
   Each such test is replaced by `always = yes` (option is the default one) or `always = no` - the same result as the game with default rules.
   Files are taken from the mod (RandomParadox copies) or from vanilla (then an override is written into the mod).
1b. `has_completed_focus = <id of a removed vanilla generic focus>` -> `always = no`.
2. Vanilla files that exist only for countries absent in the mod and reference removed content (factions, border wars, AI plans) are overridden with an empty file:
   all common/ai_strategy_plans/*, common/decisions files with start_border_war / faction_template_ / faction_goal_.
3. AST_scripted_effects.txt: the line creating the missing faction template is dropped.
4. Event namespaces used by id = NS.N but never declared (the vanilla file that declared it is not in the mod) are declared at the top of the file.
5. common/opinion_modifiers/rpx_call_to_arms.txt: `icon =` is not accepted by 1.19 -> removed.
6. Vanilla country focus trees (every common/national_focus file except generic.txt and the title-bar styles) are overridden with an empty file:
   no vanilla tag exists in the mod, so they only produce errors (factions, decisions, states); has_completed_focus of their focuses -> always = no.
7. common/ai_strategy/<TAG>.txt of tags that are not ours (the folder is replace_path-ed by the mod: only the RandomParadox copies exist) -> empty.
8. Brace-aware neutralisation (the helpers mask/parse/cut below): references to decisions/missions that no longer exist (any form:
   one line, `= { decision = X }`, multi-line activate_targeted_decision / add_days_mission_timeout ...) are removed; has_decision/has_active_mission -> always = no.
9. Vanilla common/on_actions (state ids of the vanilla map, events and characters of the vanilla game): numeric state-scope blocks `123 = { ... }`,
   calls of events that do not exist (also random_events entries) and `<VANILLATAG>_<char> = { set_unit_leader_flag ... }` blocks are removed.
10. events/rpx_generic_war.txt (RandomParadox war events: create_wargoal / declare_war_on without a justification) -> only `add_namespace = generic_war`;
   no other file in the mod fires generic_war.N (only localisation mentions them).
11. events/rpx_ideological_tension_v2.txt (free wargoals for AI fascists/communists from 1937.4.1) -> only the namespace.
12. Ids with a dash (ETH_soviet-ethiopian_trade_agreement): has_completed_focus / focus ids are matched with word-and-dash chars (before, `always = no-...` remained in ethiopia.txt,
   ETH.txt, ETH_decision_categories.txt, SOV_organization.txt). history/general and music (spain_shared_advisors, generic_advisors, mtg_songs) are processed like common/;
   AST_scripted_effects.txt: step 3 builds on the step-1 result (it used to overwrite it from vanilla).
13. load_focus_tree of removed vanilla trees (soviet_focus, italian_focus ...) -> the statement is removed; trees of our ktits_*.txt files are kept (even with a vanilla id).
14. faction_manifest_* named by templates but missing in the mod's common/factions/goals -> definitions appended from vanilla.
15. music/*.txt of vanilla music/ and of the DLC packs (DLC/*/music, integrated_dlc/*/music) are written to the mod as music/<name>.txt;
   has_completed_focus of any focus the mod does not define -> always = no (ids of ktits_* and generic.txt stay).
Usage: python tools/fix_vanilla_leftovers.py [--mod PATH] [--game PATH]
"""
import argparse, re
from pathlib import Path
import lore_data as L
import make_game_rules as G

EMPTY_NOTE = "# emptied by Ktits (tools/fix_vanilla_leftovers.py): vanilla content for countries that do not exist in the mod\n"
EMPTY_DECISIONS = re.compile(r"start_border_war|faction_template_|faction_goal_")
HCF = re.compile(r"has_completed_focus\s*=\s*([\w-]+)")   # ids with a dash (ETH_soviet-ethiopian_trade_agreement): \w+ cut them and left `always = no-ethiopian_...`
HGR = re.compile(r"has_game_rule\s*=\s*\{([^{}]*)\}")


def rd(p):
    return p.read_bytes().decode("utf-8-sig")


def has_bom(p):
    return p.exists() and p.read_bytes()[:3] == b"\xef\xbb\xbf"


def wr(p, text, bom=False):  # keep the BOM state of the source file: a BOM where vanilla has none breaks scripted_triggers/effects
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes((b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8"))


def music_sources(game, mod):
    """music/<name>.txt -> source file: vanilla music/ first, then the DLC packs (DLC/<pack>/music, integrated_dlc/<pack>/music), then the mod's own copy.
    The same name in several packs: the first one wins (identical copies exist for mtg_songs.txt)."""
    cands = [game / "music"]
    for top in sorted(game.iterdir()):
        if top.is_dir() and top.name.lower() in ("dlc", "integrated_dlc"):
            cands += [p / "music" for p in sorted(top.iterdir()) if p.is_dir()]
    cands.append(mod / "music")
    found = {}
    for d in cands:
        if d.is_dir():
            for f in sorted(d.glob("*.txt")):
                found.setdefault(f"music/{f.name}", f)
    return found


# ---- brace-aware helpers ------------------------------------------------------------------------------------------------
TOK = re.compile(r"([A-Za-z0-9_.:@$\[\]^|\-]+)\s*(?:=|>=|<=|>|<)\s*\{|\{|\}")
BLOCK_DEC_KEYS = {"activate_targeted_decision", "remove_targeted_decision", "add_days_mission_timeout", "unlock_decision_tooltip",
                  "activate_mission_tooltip", "activate_decision", "activate_mission", "remove_mission", "force_remove_decision"}
LINE_DEC = re.compile(r"(?m)^[ \t]*(?:unlock_decision_tooltip|activate_mission_tooltip|activate_mission|activate_decision|remove_mission|activate_targeted_decision)\s*=\s*(\w+)[ \t]*(?:#[^\n]*)?\r?\n")
INLINE_DEC = re.compile(r"\b(?:unlock_decision_tooltip|activate_mission_tooltip|activate_mission|activate_decision|remove_mission)\s*=\s*(\w+)")
FOCUS_EFF = re.compile(r"(?m)^[ \t]*(?:complete_national_focus|uncomplete_national_focus|unlock_national_focus)\s*=\s*([\w-]+)[ \t]*(?:#[^\n]*)?\r?\n|\b(?:complete_national_focus|uncomplete_national_focus|unlock_national_focus)\s*=\s*([\w-]+)")
HFTPL = re.compile(r"\bhas_faction_template\s*=\s*(\w+)")
LOAD_TREE = re.compile(r"(?m)^[ \t]*load_focus_tree\s*=\s*(\w+)[ \t]*(?:#[^\n]*)?\r?\n")
HFT = re.compile(r"\bhas_focus_tree\s*=\s*(\w+)")
DEC_TEST = re.compile(r"\b(?:has_active_mission|has_decision)\s*=\s*(\w+)")
EVENT_KEYS = {"country_event", "state_event", "news_event", "unit_leader_event", "operative_leader_event", "character_event"}
LINE_EVENT = re.compile(r"(?m)^[ \t]*(?:country_event|state_event|news_event|unit_leader_event|operative_leader_event|character_event)\s*=\s*([A-Za-z_]\w*\.\d+)[ \t]*(?:#[^\n]*)?\r?\n")
INLINE_EVENT = re.compile(r"\b(?:country_event|state_event|news_event|unit_leader_event|operative_leader_event|character_event)\s*=\s*([A-Za-z_]\w*\.\d+)")
RANDOM_EVENT = re.compile(r"(?m)^[ \t]*\d+(?:\.\d+)?[ \t]*=[ \t]*([A-Za-z_]\w*\.\d+)[ \t]*(?:#[^\n]*)?\r?\n")
TRIGGER_KEYS = {"limit", "trigger", "OR", "AND", "NOT", "available", "allowed", "visible", "modifier", "ai_chance", "bypass", "cancel_trigger", "is_good", "is_bad"}
RANDOM_PARENTS = {"random_list", "random_events", "random", "weight", "modifier", "ai_chance"}


def mask(t):
    """comments and string contents replaced by blanks (same length): braces inside them do not count"""
    out, i, n = [], 0, len(t)
    while i < n:
        c = t[i]
        if c == "#":
            j = t.find("\n", i); j = n if j < 0 else j
            out.append(" " * (j - i)); i = j
        elif c == '"':
            j = t.find('"', i + 1); j = n - 1 if j < 0 else j
            out.append("x" * (j - i + 1)); i = j + 1
        else:
            out.append(c); i += 1
    return "".join(out)


def parse(t):
    """every {...} block: (key, key_start, open_brace, end, parent_key, depth); depth 0 = top level"""
    stack, nodes = [], []
    for m in TOK.finditer(mask(t)):
        s = m.group(0)
        if s == "}":
            if stack:
                k, ks, op = stack.pop()
                nodes.append((k, ks, op, m.end(), stack[-1][0] if stack else None, len(stack)))
        elif s == "{":
            stack.append((None, m.start(), m.start()))
        else:
            stack.append((m.group(1), m.start(1), m.end() - 1))
    return sorted(nodes, key=lambda n: (n[1], -n[3]))


def cut(t, spans):
    """remove the spans (a nested span goes with its outer one); a span alone on its lines takes the lines"""
    merged = []
    for s, e in sorted(spans, key=lambda x: (x[0], -x[1])):
        if merged and s < merged[-1][1]:
            continue
        merged.append((s, e))
    out, pos = [], 0
    for s, e in merged:
        ls = t.rfind("\n", 0, s) + 1
        m = re.compile(r"[ \t]*(?:#[^\n]*)?\r?\n").match(t, e)
        if t[ls:s].strip() == "" and m:
            s, e = ls, m.end()
        out.append(t[pos:s]); pos = e
    out.append(t[pos:])
    return "".join(out)


def decision_names(t):
    return {n[0] for n in parse(t) if n[5] == 1 and n[0] and re.fullmatch(r"\w+", n[0])}


def event_ids(t):
    ids = set()
    for n in parse(t):
        if n[5] == 0 and n[0] in EVENT_KEYS:
            m = re.search(r"(?m)^\s*id\s*=\s*([A-Za-z_]\w*\.\d+)", t[n[2]:n[3]])
            if m:
                ids.add(m.group(1))
    return ids


def clean_decision_refs(t, undefined, stat):
    """remove effects that use an undefined decision/mission (one-line and block forms); triggers on them -> always = no"""
    spans = [(n[1], n[3]) for n in parse(t) if n[0] in BLOCK_DEC_KEYS
             and (m := re.search(r"\b(?:decision|mission)\s*=\s*(\w+)", t[n[2]:n[3]])) and undefined(m.group(1))]
    stat["dec_blocks"] = stat.get("dec_blocks", 0) + len(spans)
    if spans:
        t = cut(t, spans)
    def line(m):
        if undefined(m.group(1)):
            stat["dec_lines"] = stat.get("dec_lines", 0) + 1
            return ""
        return m.group(0)
    t = LINE_DEC.sub(line, t)
    t = INLINE_DEC.sub(line, t)   # `ROOT = { remove_mission = X }` on one line: only the statement goes
    def test(m):
        if undefined(m.group(1)):
            stat["dec_tests"] = stat.get("dec_tests", 0) + 1
            return "always = no"
        return m.group(0)
    return DEC_TEST.sub(test, t)


def clean_focus_refs(t, gone, trees, templates, stat):
    """effects on focuses of removed vanilla trees (complete/uncomplete/unlock_national_focus) are removed, has_focus_tree of a removed tree -> always = no"""
    keys = {"complete_national_focus", "uncomplete_national_focus", "unlock_national_focus"}
    spans = [(n[1], n[3]) for n in parse(t) if n[0] in keys and (m := re.search(r"\bfocus\s*=\s*([\w-]+)", t[n[2]:n[3]])) and m.group(1) in gone]
    stat["foc_eff"] = stat.get("foc_eff", 0) + len(spans)
    if spans:
        t = cut(t, spans)
    def one(m):
        if (m.group(1) or m.group(2)) in gone:
            stat["foc_eff"] = stat.get("foc_eff", 0) + 1
            return ""
        return m.group(0)
    t = FOCUS_EFF.sub(one, t)
    def tree(m):
        if m.group(1) in trees:
            stat["foc_tree"] = stat.get("foc_tree", 0) + 1
            return "always = no"
        return m.group(0)
    t = HFT.sub(tree, t)
    lspans = [(n[1], n[3]) for n in parse(t) if n[0] == "load_focus_tree" and (m := re.search(r"\btree\s*=\s*(\w+)", t[n[2]:n[3]])) and m.group(1) in trees]
    stat["foc_load"] = stat.get("foc_load", 0) + len(lspans)
    if lspans:
        t = cut(t, lspans)
    def load1(m):
        if m.group(1) in trees:
            stat["foc_load"] = stat.get("foc_load", 0) + 1
            return ""
        return m.group(0)
    t = LOAD_TREE.sub(load1, t)
    def tpl(m):
        if m.group(1) not in templates:
            stat["foc_tpl"] = stat.get("foc_tpl", 0) + 1
            return "always = no"
        return m.group(0)
    return HFTPL.sub(tpl, t)


def clean_on_action(t, ev_defined, our_tags, stat):
    """vanilla on_actions: state blocks of the vanilla map, events and characters that do not exist"""
    spans = []
    nodes = parse(t)
    trig = [(n[1], n[3]) for n in nodes if n[0] in TRIGGER_KEYS]
    for n in nodes:
        k, body = n[0], t[n[2]:n[3]]
        if k and k.isdigit() and n[4] not in RANDOM_PARENTS and not any(s < n[1] and n[3] <= e for s, e in trig):   # effects only: a state scope inside a trigger stays
            spans.append((n[1], n[3])); stat["oa_state"] = stat.get("oa_state", 0) + 1
        elif k in EVENT_KEYS and (m := re.search(r"\bid\s*=\s*([A-Za-z_]\w*\.\d+)", body)) and m.group(1) not in ev_defined:
            spans.append((n[1], n[3])); stat["oa_event"] = stat.get("oa_event", 0) + 1
        elif k and (m := re.fullmatch(r"([A-Z][A-Z0-9]{2})_\w+", k)) and m.group(1) not in our_tags and "set_unit_leader_flag" in body:
            spans.append((n[1], n[3])); stat["oa_char"] = stat.get("oa_char", 0) + 1
    if spans:
        t = cut(t, spans)
    for rx in (LINE_EVENT, RANDOM_EVENT, INLINE_EVENT):
        def sub(m):
            if m.group(1) not in ev_defined:
                stat["oa_event"] = stat.get("oa_event", 0) + 1
                return ""
            return m.group(0)
        t = rx.sub(sub, t)
    return t


def removed_rules(game):
    src = rd(game / "common/game_rules/00_game_rules.txt")
    _new, _kept, removed = G.filter_rules(src)
    defaults = {}
    for name in removed:
        m = re.search(r"(?ms)^" + name + r"\s*=\s*\{.*?^\}", src)
        d = re.search(r"default\s*=\s*\{\s*name\s*=\s*(\w+)", m.group(0)) if m else None
        defaults[name.lower()] = d.group(1) if d else "DEFAULT"
    return defaults


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", default=L.DEFAULT_MOD)
    ap.add_argument("--game", default=G.GAME)
    a = ap.parse_args()
    M, V = Path(a.mod), Path(a.game)
    defaults = removed_rules(V)
    stat = {"rewritten": 0, "tests": 0, "emptied": 0}

    def repl(m):
        body = m.group(1)
        r = re.search(r"rule\s*=\s*(\w+)", body); o = re.search(r"option\s*=\s*(\w+)", body)
        if not r or not o or r.group(1).lower() not in defaults:
            return m.group(0)
        stat["tests"] += 1
        return "always = yes" if o.group(1) == defaults[r.group(1).lower()] else "always = no"

    # 2. empty overrides (first, so that step 1 skips them)
    emptied = set()
    for f in sorted((V / "common/ai_strategy_plans").glob("*.txt")):
        emptied.add(f"common/ai_strategy_plans/{f.name}")
    for f in sorted((V / "common/decisions").glob("*.txt")):
        if EMPTY_DECISIONS.search(rd(f)):
            emptied.add(f"common/decisions/{f.name}")
    # vanilla decision files bound to the vanilla map: >= 5 references to states that do not exist on our map
    # (country decisions, formable nations, resource prospecting; they flood error.log, e.g. "Invalid state for is_owned_and_controlled_by 942 = MAK")
    max_state = max(int(re.match(r"\d+", p.name).group(0)) for p in (M / "history/states").glob("*.txt") if re.match(r"\d+", p.name))
    ref_re = re.compile(r"(?m)(?:^\s*|\bstate\s*=\s*|owns_state\s*=\s*|controls_state\s*=\s*)(\d{3,5})\b")
    for f in sorted((V / "common/decisions").glob("*.txt")):
        if sum(1 for x in ref_re.findall(rd(f)) if int(x) > max_state) >= 5:
            emptied.add(f"common/decisions/{f.name}")
    # the vanilla 1939 scenario (bookmark "Blitzkrieg") does not work with the mod's map and countries: only 1936 stays
    emptied.add("common/bookmarks/blitzkrieg.txt")
    # vanilla country focus trees: no vanilla tag exists in the mod (only generic.txt, ours and the title-bar styles stay)
    tree_re = re.compile(r"(?m)^\s*(?:focus_tree|shared_focus|joint_focus|focus)\s*=\s*\{")
    focus_ids_v, focus_trees_v = set(), set()
    for base in (V, M):
        for f in sorted((base / "common/national_focus").glob("*.txt")):
            if f.name == "generic.txt" or f.name.startswith("ktits_") or f"common/national_focus/{f.name}" in emptied:
                continue
            tx = rd(f)
            if tree_re.search(tx) and not re.search(r"(?m)^style\s*=\s*\{", tx):
                emptied.add(f"common/national_focus/{f.name}")
                focus_ids_v |= set(re.findall(r"(?m)^\s*id\s*=\s*([\w-]+)", tx))
                focus_trees_v |= set(re.findall(r"(?m)^\s*focus_tree\s*=\s*\{[^{}]*?\bid\s*=\s*(\w+)", tx))
    # our own trees (ktits_*.txt) stay even if a vanilla tree has the same id (soviet_focus ...): load_focus_tree / has_focus_tree of them are not touched
    our_trees, our_focus_ids = set(), set()
    for f in (M / "common/national_focus").glob("ktits_*.txt"):
        tx = rd(f)
        our_trees |= set(re.findall(r"(?m)^\s*focus_tree\s*=\s*\{[^{}]*?\bid\s*=\s*(\w+)", tx))
        our_focus_ids |= set(re.findall(r"(?m)^\s*id\s*=\s*([\w-]+)", tx))
    focus_trees_v -= our_trees
    focus_ids_v -= our_focus_ids
    n_focus = sum(1 for r in emptied if r.startswith("common/national_focus/"))
    # tags: ours (mod country_tags) against the vanilla ones
    our_tags, v_tags = set(), set()
    for f in (M / "common/country_tags").glob("*.txt"):
        our_tags |= set(re.findall(r"(?m)^\s*([A-Z0-9]{3})\s*=", rd(f)))
    for f in (V / "common/country_tags").glob("*.txt"):
        v_tags |= set(re.findall(r"(?m)^\s*([A-Z0-9]{3})\s*=", rd(f)))
    print(f"  tags of the mod that are also vanilla tags: {sorted(our_tags & v_tags) or 'none'}")
    # vanilla ai_strategy files of tags that are not ours (the mod replaces the folder: only RandomParadox copies exist)
    n_ai = 0
    for f in sorted((M / "common/ai_strategy").glob("*.txt")):
        if re.fullmatch(r"[A-Z][A-Z0-9]{2}", f.stem) and f.stem not in our_tags:
            emptied.add(f"common/ai_strategy/{f.name}"); n_ai += 1
    for rel in emptied:
        wr(M / rel, EMPTY_NOTE); stat["emptied"] += 1

    # focuses of the vanilla generic tree no longer exist (make_focuses.py): has_completed_focus = <such id> can never be true
    ids_g = set(re.findall(r"(?m)^\s*id\s*=\s*([\w-]+)", rd(V / "common/national_focus/generic.txt")))
    ids_o = set()
    for f in (V / "common/national_focus").glob("*.txt"):
        if f.name != "generic.txt":
            ids_o |= set(re.findall(r"(?m)^\s*id\s*=\s*([\w-]+)", rd(f)))
    kept_ids = set(re.findall(r"(?m)^\s*id\s*=\s*([\w-]+)", rd(M / "common/national_focus/generic.txt")))
    gen_only = ((ids_g - ids_o) | focus_ids_v) - kept_ids   # every vanilla focus is gone except ids that our generic.txt still defines
    # every focus id the mod defines (generic.txt, ktits_*, RandomParadox copies); music keeps has_completed_focus only for these
    mod_focus_ids = set()
    for f in (M / "common/national_focus").glob("*.txt") if (M / "common/national_focus").is_dir() else []:
        mod_focus_ids |= set(re.findall(r"(?m)^\s*id\s*=\s*([\w-]+)", rd(f)))

    # decisions/missions that no longer exist (defined only in emptied vanilla files, or never): references are neutralised below
    # (brace-aware: depth-1 keys of decision files, whatever the indentation)
    defined = set()
    for f in (V / "common/decisions").glob("*.txt"):
        if f"common/decisions/{f.name}" not in emptied:
            defined |= decision_names(rd(f))
    for f in (M / "common/decisions").glob("*.txt"):
        if not (V / "common/decisions" / f.name).exists():
            defined |= decision_names(rd(f))
    undefined = lambda name: name not in defined
    templates = set()   # faction templates that exist (the mod replaces common/factions)
    for f in (M / "common/factions/templates").glob("*.txt"):
        templates |= {n[0] for n in parse(rd(f)) if n[5] == 0 and n[0]}
    ev_defined = set()   # events that exist (the mod replaces the events folder)
    for f in (M / "events").glob("*.txt"):
        ev_defined |= event_ids(rd(f))

    # 1. has_game_rule of removed rules
    rels = set()
    for base in (V, M):
        for f in (base / "common").rglob("*.txt"):
            rel = f.relative_to(base).as_posix()
            if rel.startswith("common/game_rules/") or "/ktits_" in rel or rel in emptied:
                continue
            rels.add(rel)
    for f in (M / "events").glob("*.txt"):   # RandomParadox copies of vanilla events (no vanilla file of that name: the mod copy is rewritten, idempotently)
        if not f.name.startswith("ktits_"):
            rels.add(f"events/{f.name}")
    # vanilla files outside common/ with has_completed_focus of removed focuses (advisors, music): override in the mod
    for base in (V, M):
        for f in (base / "history/general").glob("*.txt"):
            rels.add(f.relative_to(base).as_posix())
    # music: vanilla music/ and the DLC music packs (DLC/*/music, integrated_dlc/*/music), written to the mod as music/<name>.txt
    music_src = music_sources(V, M)
    rels |= set(music_src)
    # folders the mod replaces (descriptor.mod replace_path): vanilla files of them must NOT be copied into the mod, only RandomParadox's copies are rewritten
    replaced = re.findall(r'(?m)^replace_path\s*=\s*"([^"]+)"', rd(M / "descriptor.mod"))
    for rel in sorted(rels):
        if not (M / rel).exists() and any(rel.startswith(rp.rstrip("/") + "/") for rp in replaced):
            continue
        src = music_src[rel] if rel in music_src else (V / rel if (V / rel).exists() else M / rel)   # always from vanilla: idempotent, never re-reads our own output
        t = rd(src)
        is_oa = rel.startswith("common/on_actions/")
        if not is_oa and not any(k in t for k in ("has_game_rule", "has_completed_focus", "has_active_mission", "has_decision", "decision", "mission", "has_faction_template", "load_focus_tree")):
            continue
        t2 = HGR.sub(repl, t)
        if rel.startswith("music/"):   # music: every focus that the mod does not define (vanilla, DLC) is gone
            def mhcf(m):
                if m.group(1) in mod_focus_ids:
                    return m.group(0)
                stat["music"] = stat.get("music", 0) + 1
                return "always = no"
            t2 = HCF.sub(mhcf, t2)
        else:
            t2 = HCF.sub(lambda m: "always = no" if m.group(1) in gen_only else m.group(0), t2)
        t2 = clean_decision_refs(t2, undefined, stat)
        t2 = clean_focus_refs(t2, gen_only, focus_trees_v, templates, stat)
        if is_oa:
            t2 = clean_on_action(t2, ev_defined, our_tags, stat)
        if t2 != t:
            wr(M / rel, t2, bom=has_bom(src)); stat["rewritten"] += 1

    # 3. AST scripted effects (on top of the step-1 result if it exists: has_completed_focus of removed focuses is already neutralised there)
    p = M / "common/scripted_effects/AST_scripted_effects.txt"
    src = V / "common/scripted_effects/AST_scripted_effects.txt"
    t = rd(p if p.exists() else src)
    t2 = re.sub(r"(?m)^[ \t]*create_faction_from_template\s*=\s*faction_template_AST_nations_of_the_empire[ \t]*\r?\n", "", t)
    if t2 != t or not p.exists():
        wr(p, t2, bom=has_bom(src)); stat["AST"] = 1

    # 3b. faction manifests: the mod replaces common/factions/goals, templates (vanilla ones stay, only invisible) still name manifests that its goals file lacks
    # ("Faction goal not found in the database: faction_manifest_*"): the missing definitions are appended from vanilla (idempotent)
    gp = M / "common/factions/goals/faction_manifests.txt"
    vp = V / "common/factions/goals/faction_manifests.txt"
    if gp.exists() and vp.exists():
        have = set()
        for f in (M / "common/factions/goals").glob("*.txt"):
            have |= {n[0] for n in parse(rd(f)) if n[5] == 0 and n[0]}
        used = set()
        for f in (M / "common/factions/templates").glob("*.txt"):
            used |= set(re.findall(r"\bmanifest\s*=\s*(\w+)", rd(f)))
        vt = rd(vp)
        add = ""
        for n in parse(vt):
            if n[5] == 0 and n[0] in used and n[0] not in have:
                add += "\n" + vt[n[1]:n[3]] + "\n"; have.add(n[0]); stat["manifests"] = stat.get("manifests", 0) + 1
        if add:
            wr(gp, rd(gp).rstrip("\n") + "\n" + add, bom=has_bom(gp))
        miss = sorted(used - have)
        if miss:
            print(f"  manifests still undefined (not in vanilla either): {miss}")

    # 4. event namespaces
    ev = sorted((M / "events").glob("*.txt"))
    texts = {f: rd(f) for f in ev}
    declared = set(n for t in texts.values() for n in re.findall(r"(?m)^\s*add_namespace\s*=\s*(\w+)", t))
    for f, t in texts.items():
        used = set(re.findall(r"(?m)^\s*id\s*=\s*([A-Za-z_]\w*)\.\d+", t))
        miss = sorted(n for n in used if n not in declared)
        if miss:
            wr(f, "".join(f"add_namespace = {n}\n" for n in miss) + t, bom=has_bom(f)); declared.update(miss)
            print(f"  namespaces declared in {f.name}: {miss}")

    # 5. opinion modifiers icon
    p = M / "common/opinion_modifiers/rpx_call_to_arms.txt"
    if p.exists():
        t = rd(p)
        t2 = re.sub(r"(?m)^[ \t]*icon\s*=\s*\"[^\"]*\"[ \t]*\r?\n", "", t)
        if t2 != t:
            wr(p, t2, bom=False); stat["icon"] = 1
    # 5b. RandomParadox war events (create_wargoal / declare_war_on without a justification): only the namespace is left
    p = M / "events/rpx_generic_war.txt"
    if p.exists():
        stub = "# emptied by Ktits (tools/fix_vanilla_leftovers.py): RandomParadox war events attack without a wargoal justification\nadd_namespace = generic_war\n"
        if rd(p) != stub:
            wr(p, stub, bom=has_bom(p)); stat["generic_war"] = 1
    # 5c. RandomParadox "ideological tension" events: MTTH events (fascism/communism, from 1937.4.1) hand out a free annex_everything / take_state wargoal
    # to the AI without justification; the AI declares war at once. Only the namespace is left.
    p = M / "events/rpx_ideological_tension_v2.txt"
    if p.exists():
        stub = "# emptied by Ktits (tools/fix_vanilla_leftovers.py): RandomParadox events gave AI wargoals without a justification\nadd_namespace = ideological_tension_v2\n"
        if rd(p) != stub:
            wr(p, stub, bom=has_bom(p)); stat["ideo_tension"] = 1
    print(f"vanilla leftovers: {stat['tests']} has_game_rule tests replaced in {stat['rewritten']} files, {stat['emptied']} files emptied "
          f"({n_focus} focus trees, {n_ai} ai_strategy country files)")
    print(f"  decision refs removed: {stat.get('dec_blocks', 0)} blocks, {stat.get('dec_lines', 0)} lines, {stat.get('dec_tests', 0)} tests -> always = no")
    print(f"  focus refs: {stat.get('foc_eff', 0)} effects on removed focuses, {stat.get('foc_tree', 0)} has_focus_tree of removed trees and {stat.get('foc_tpl', 0)} has_faction_template of missing templates -> always = no")
    print(f"  load_focus_tree of removed vanilla trees removed: {stat.get('foc_load', 0)}; manifests appended: {stat.get('manifests', 0)}")
    print(f"  music: {len(music_src)} files from vanilla/DLC music, {stat.get('music', 0)} has_completed_focus of undefined focuses -> always = no")
    print(f"  on_actions: {stat.get('oa_state', 0)} vanilla state blocks, {stat.get('oa_event', 0)} calls of missing events, {stat.get('oa_char', 0)} vanilla character blocks removed")


if __name__ == "__main__":
    main()
