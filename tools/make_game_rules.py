"""Leave in the game-rules screen only generic vanilla rules: override common/game_rules/00_game_rules.txt with a copy without the rules of countries that do not exist in the mod.
Removed (docs/map/build/Map-Finish-Plan.md): <TAG>_ai_behavior (all AI-behavior rules of vanilla countries), <xxx>_fragmentation_status, quebec_colonization_status (country/region specific setup rules).
Kept: foreign policy, covert actions, gameplay, UI, peace score, continent colonization status [uncertain: continents may be dropped too].
The rule of the mod itself lives in common/game_rules/ktits_casuality_rules.txt (make_casuality.py).
Usage: python tools/make_game_rules.py [--mod PATH] [--game PATH]
"""
import argparse, re
from pathlib import Path
import lore_data as L

# the data: which top-level rules are dropped (regex on the rule token)
REMOVE = re.compile(r"^(?:[A-Za-z]{3}_ai_behavior|[a-z]+_fragmentation_status|quebec_colonization_status)$", re.I)
GAME = "D:/SteamLibrary/steamapps/common/Hearts of Iron IV"

def filter_rules(text):
    """returns (new text, kept names, removed names); top-level rule = line at column 0 `name = {` up to the line `}` at column 0"""
    out, kept, removed, skip = [], [], [], False
    for line in text.split("\n"):
        m = re.match(r"^(\w+)\s*=\s*\{\s*$", line)
        if not skip and m:
            if REMOVE.match(m.group(1)):
                skip = True; removed.append(m.group(1)); continue
            kept.append(m.group(1))
        elif skip:
            if line.rstrip() == "}": skip = False
            continue
        out.append(line)
    return "\n".join(out), kept, removed

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", default=L.DEFAULT_MOD)
    ap.add_argument("--game", default=GAME)
    a = ap.parse_args()
    src = (Path(a.game) / "common/game_rules/00_game_rules.txt").read_text(encoding="utf-8-sig")
    new, kept, removed = filter_rules(src)
    dst = Path(a.mod) / "common/game_rules/00_game_rules.txt"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(new, encoding="utf-8", newline="\n")
    print(f"game rules: kept {len(kept)}, removed {len(removed)} -> {dst}")
    print("kept:", " ".join(kept))
