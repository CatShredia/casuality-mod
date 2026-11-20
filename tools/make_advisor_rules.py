"""Political advisors that push the popularity of an ideology hostile to the ruling one (author's rule): a country that rules with communism cannot hire
(or at once loses) an advisor whose trait drifts fascism up, and the other way round. Post-process over common/characters/*.txt of the mod (idempotent).
Drift of a trait: `<ideology>_drift = N` in common/country_leader/*.txt (mod first, then vanilla). An advisor with a positive fascism drift gets
`available = { NOT = { has_government = communism } }` inside its advisor block, one with a positive communism drift `... = fascism`
(an advisor with both drifts is left alone). An existing `available = { ... }` of the block gets the NOT inside. [uncertain: whether the game
fires an already hired advisor when `available` turns false; the engine at least forbids hiring]
Usage: python tools/make_advisor_rules.py [--mod PATH] [--game PATH]"""
import argparse, glob, re
from pathlib import Path
import lore_data as L

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
ap.add_argument("--game", default="D:/SteamLibrary/steamapps/common/Hearts of Iron IV")
a = ap.parse_args()
M, V = Path(a.mod), Path(a.game)
MARK = "# ktits advisor rule"
HOSTILE = {"fascism": ["communism", "casuality"], "communism": ["fascism"]}   # advisor drifts to key -> forbidden while the ruling group is value

def block_end(t, i):
    """index after the brace block whose '{' is at t[i]"""
    d = 0
    while i < len(t):
        d += (t[i] == "{") - (t[i] == "}")
        i += 1
        if d == 0: return i
    return len(t)

drift = {}   # trait -> set of ideologies with positive drift
for root in (M, V):   # the mod copy wins
    for f in glob.glob(str(root / "common/country_leader/*.txt")):
        t = open(f, encoding="utf-8-sig", errors="ignore").read()
        for m in re.finditer(r"(?m)^\t(\w+) = \{", t):
            if m.group(1) in drift: continue
            b = t[m.start():block_end(t, m.end() - 1)]
            ids = {i for i, v in re.findall(r"(\w+)_drift = (-?[\d.]+)", b) if float(v) > 0}
            if ids: drift[m.group(1)] = ids

total = hit = 0
for f in sorted(glob.glob(str(M / "common/characters/*.txt"))):
    raw = open(f, "rb").read(); bom = raw.startswith(b"\xef\xbb\xbf")
    t = raw.decode("utf-8-sig").replace("\r\n", "\n"); crlf = b"\r\n" in raw
    t, nold = re.subn(r"\n[ \t]*(?:available = \{ )?NOT = \{[^\n]*?\}(?: \})? " + re.escape(MARK) + r"[^\n]*", "", t)   # old rules are rebuilt
    out, pos, changed = [], 0, bool(nold)
    for m in re.finditer(r"advisor\s*=\s*\{", t):
        if m.start() < pos: continue
        end = block_end(t, m.end() - 1); b = t[m.start():end]
        if "slot = political_advisor" not in b: continue
        total += 1
        if MARK in b: continue
        ids = set()
        for tr in re.findall(r"traits\s*=\s*\{([^}]*)\}", b):
            for x in tr.split(): ids |= drift.get(x, set())
        if len(ids & set(HOSTILE)) != 1: continue
        gl = HOSTILE[(ids & set(HOSTILE)).pop()]
        gov = " ".join(f"has_government = {g}" for g in gl)
        if len(gl) > 1: gov = f"OR = {{ {gov} }}"
        am = re.search(r"\n([ \t]*)available\s*=\s*\{", b)
        if am:   # existing available: the condition goes inside at its start
            ins = am.end(); nb = b[:ins] + f"\n{am.group(1)}\tNOT = {{ {gov} }} {MARK}" + b[ins:]
        else:
            im = re.search(r"\n([ \t]*)idea_token\s*=\s*[^\n]*", b)
            if not im: continue
            nb = b[:im.end()] + f"\n{im.group(1)}available = {{ NOT = {{ {gov} }} }} {MARK}" + b[im.end():]
        out.append(t[pos:m.start()] + nb); pos = end; changed = True; hit += 1
    if changed:
        t2 = "".join(out) + t[pos:]
        open(f, "wb").write((b"\xef\xbb\xbf" if bom else b"") + (t2.replace("\n", "\r\n") if crlf else t2).encode("utf-8"))
print(f"advisor rules: {hit} of {total} political advisors got a hostile-ideology condition ({len(drift)} traits with a drift)")
