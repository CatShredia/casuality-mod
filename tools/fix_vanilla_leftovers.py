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
Usage: python tools/fix_vanilla_leftovers.py [--mod PATH] [--game PATH]
"""
import argparse, re
from pathlib import Path
import lore_data as L
import make_game_rules as G

EMPTY_NOTE = "# emptied by Ktits (tools/fix_vanilla_leftovers.py): vanilla content for countries that do not exist in the mod\n"
EMPTY_DECISIONS = re.compile(r"start_border_war|faction_template_|faction_goal_")
HCF = re.compile(r"has_completed_focus\s*=\s*(\w+)")
HGR = re.compile(r"has_game_rule\s*=\s*\{([^{}]*)\}")


def rd(p):
    return p.read_bytes().decode("utf-8-sig")


def has_bom(p):
    return p.exists() and p.read_bytes()[:3] == b"\xef\xbb\xbf"


def wr(p, text, bom=False):  # keep the BOM state of the source file: a BOM where vanilla has none breaks scripted_triggers/effects
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes((b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8"))


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
    # the vanilla 1939 scenario (bookmark "Blitzkrieg") does not work with the mod's map and countries: only 1936 stays
    emptied.add("common/bookmarks/blitzkrieg.txt")
    for rel in emptied:
        wr(M / rel, EMPTY_NOTE); stat["emptied"] += 1

    # focuses of the vanilla generic tree no longer exist (make_focuses.py): has_completed_focus = <such id> can never be true
    ids_g = set(re.findall(r"(?m)^\s*id\s*=\s*(\w+)", rd(V / "common/national_focus/generic.txt")))
    ids_o = set()
    for f in (V / "common/national_focus").glob("*.txt"):
        if f.name != "generic.txt":
            ids_o |= set(re.findall(r"(?m)^\s*id\s*=\s*(\w+)", rd(f)))
    gen_only = ids_g - ids_o

    # 1. has_game_rule of removed rules
    rels = set()
    for base in (V, M):
        for f in (base / "common").rglob("*.txt"):
            rel = f.relative_to(base).as_posix()
            if rel.startswith("common/game_rules/") or "/ktits_" in rel or rel in emptied:
                continue
            rels.add(rel)
    for rel in sorted(rels):
        src = V / rel if (V / rel).exists() else M / rel   # always from vanilla: idempotent, never re-reads our own output
        t = rd(src)
        if "has_game_rule" not in t and "has_completed_focus" not in t:
            continue
        t2 = HGR.sub(repl, t)
        t2 = HCF.sub(lambda m: "always = no" if m.group(1) in gen_only else m.group(0), t2)
        if t2 != t:
            wr(M / rel, t2, bom=has_bom(src)); stat["rewritten"] += 1

    # 3. AST scripted effects
    p = M / "common/scripted_effects/AST_scripted_effects.txt"
    src = V / "common/scripted_effects/AST_scripted_effects.txt"
    t = rd(src)
    t2 = re.sub(r"(?m)^[ \t]*create_faction_from_template\s*=\s*faction_template_AST_nations_of_the_empire[ \t]*\r?\n", "", t)
    if t2 != t or not p.exists():
        wr(p, t2, bom=has_bom(src)); stat["AST"] = 1

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
    print(f"vanilla leftovers: {stat['tests']} has_game_rule tests replaced in {stat['rewritten']} files, {stat['emptied']} files emptied")


if __name__ == "__main__":
    main()
