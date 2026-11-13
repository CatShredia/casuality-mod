"""Add the custom ideologies of docs/13 to the mod (data: ideologies_data.py, mostly INVENTED, see docs/12).

 * common/ideologies/00_ideologies.txt: the vanilla file of the installed game plus extra sub-ideologies in the vanilla groups
   and two new groups (casuality, theology). The file has the vanilla name, so it replaces the vanilla one.
 * localisation/russian|english/ktits_ideologies_l_*.yml: names and descriptions of the new groups and sub-ideologies.
 * interface/countrypoliticsview.gui: copy of the vanilla file with smaller rows in the party list (6 groups fit; vanilla shows 5).
 * interface/ktits_ideologies.gfx: sprites GFX_ideology_<group>_group of the new groups (they reuse the vanilla neutrality icon until own art exists).
Countries get the ideologies through make_rulers.py (run it after this script).
Usage: python tools/make_ideologies.py [--mod PATH] [--game PATH]
"""
import argparse
from pathlib import Path
import lore_data as L
import ideologies_data as D

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
ap.add_argument("--game", default="D:/SteamLibrary/steamapps/common/Hearts of Iron IV")
a = ap.parse_args()
M, G = Path(a.mod), Path(a.game)
text = (G / "common/ideologies/00_ideologies.txt").read_text(encoding="utf-8-sig")
text = text.replace("\r\n", "\n")


def match_brace(s, open_idx):
    depth = 0
    for i in range(open_idx, len(s)):
        if s[i] == "{": depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0: return i
    raise ValueError("unbalanced braces")


# 1. extra sub-ideologies inside the vanilla groups
for grp in ("democratic", "communism", "fascism", "neutrality"):
    subs = D.CUSTOM_SUBTYPES.get(grp, {})
    g0 = text.index(f"\n\t{grp} = {{")
    t0 = text.index("types = {", g0)
    t_end = match_brace(text, t0 + len("types = "))
    add = "".join(f"\n\t\t\t{k} = {{\n\t\t\t\tcan_be_randomly_selected = no\n\t\t\t}}\n" for k in subs)
    text = text[:t_end] + add + "\t\t" + text[t_end:]

# 2. two new groups (copied from the neutrality group's rules; colors differ)
neu0 = text.index("\n\tneutrality = {")
neu_end = match_brace(text, neu0 + len("\n\tneutrality = ")) + 1
neu = text[neu0:neu_end]
new_blocks = ""
for grp in D.NEW_GROUPS:
    r, g, b = D.NEW_GROUP_INFO[grp][5]
    sub = next(iter(D.CUSTOM_SUBTYPES[grp]))
    blk = neu.replace("neutrality = {", f"{grp} = {{", 1)
    t0 = blk.index("types = {")
    t_end = match_brace(blk, t0 + len("types = "))
    blk = blk[:t0] + f"types = {{\n\n\t\t\t{sub} = {{\n\t\t\t}}\n\n\t\t}}" + blk[t_end + 1:]
    blk = blk.replace("color = { 124 124 124 }", f"color = {{ {r} {g} {b} }}")
    new_blocks += blk
text = text[:neu_end] + "\n" + new_blocks + text[neu_end:]

out = M / "common/ideologies/00_ideologies.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(text, encoding="utf-8")

# 3. localisation
ru, en = [], []
for grp in D.NEW_GROUPS:
    adj_ru, noun_ru, desc_ru, adj_en, noun_en, _ = D.NEW_GROUP_INFO[grp]
    ru += [(grp, noun_ru), (f"{grp}_noun", noun_ru), (f"{grp}_desc", desc_ru)]
    en += [(grp, noun_en), (f"{grp}_noun", noun_en), (f"{grp}_desc", {"casuality": "Relaxed State", "theology": "Religious State"}[grp])]
for grp, subs in D.CUSTOM_SUBTYPES.items():
    for key, (nru, nen, dru) in subs.items():
        ru += [(key, nru), (f"{key}_desc", dru)]
        en += [(key, nen), (f"{key}_desc", dru)]       # descriptions are Russian in both languages (no English text in docs)
L.write_yml(str(M / "localisation/russian/ktits_ideologies_l_russian.yml"), "russian", ru)
L.write_yml(str(M / "localisation/english/ktits_ideologies_l_english.yml"), "english", en)

# 4. sprites
gfx = M / "interface/ktits_ideologies.gfx"
gfx.parent.mkdir(parents=True, exist_ok=True)
gfx.write_text("spriteTypes = {\n" + "".join(
    f'\tspriteType = {{\n\t\tname = "GFX_ideology_{g}_group"\n\t\ttexturefile = "gfx/interface/ideologies/neutrality_group.dds"\n\t}}\n' for g in D.NEW_GROUPS) + "}\n",
    encoding="utf-8")
# 5. politics screen: the list of parties shows 5 rows only; 6 groups need smaller rows (vanilla file copied, one number changed)
gui_src = (G / "interface/countrypoliticsview.gui").read_bytes()          # bytes: no BOM / line-ending change (a BOM made the game fail with "Undefined GUI_TYPE")
old = b"slotsize = { width = 230 height = 16 }"
assert gui_src.count(old) == 1, "countrypoliticsview.gui changed in this game version: check the parties_grid"
(M / "interface/countrypoliticsview.gui").write_bytes(gui_src.replace(old, b"slotsize = { width = 230 height = 13 }"))
print("ideologies file:", out)
print("new sub-ideologies:", {g: list(v) for g, v in D.CUSTOM_SUBTYPES.items()})
print("loc entries:", len(ru), "ru /", len(en), "en; sprites:", len(D.NEW_GROUPS))
