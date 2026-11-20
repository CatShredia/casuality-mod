"""National spirit icons (65x67 PNG from gfx_src/ideas/): copies them into the mod, writes interface/ktits_ideas.gfx
and sets `picture = ktits_<id>` for the spirits of the table below. A post-process over the mod's idea files (idempotent):
run it AFTER every step that writes ideas (it is the last step before check in post_export.py).
Usage: python tools/make_icons.py [--mod PATH]"""
import argparse, re, shutil
from pathlib import Path
import lore_data as L

ICONS = {  # icon id -> spirits (ids without the ktits_ prefix are written in full)
    "cas1_lenca": ["ktits_cas_1"], "cas2_rasslabon": ["ktits_cas_2"], "cas3_bolotnaya_len": ["ktits_cas_3", "ktits_eco_casual_society"],
    "cas4_durmanische": ["ktits_cas_4", "ktits_cas_call_1", "ktits_cas_call_2", "ktits_durmanische", "ktits_durmanische_1", "ktits_durmanische_2", "ktits_durmanische_3"],
    "cas5_idilliya": ["ktits_cas_5"],
    "edu0_stado": ["ktits_edu_0"], "edu1_krestyanskoe": ["ktits_edu_1"], "edu2_elita": ["ktits_edu_2"],
    "edu3_razvivayusheesya": ["ktits_edu_3"], "edu4_obrazovannoe": ["ktits_edu_4"], "edu5_buduschee": ["ktits_edu_5"],
    "ally1_sovmestnoe": ["ktits_ally_t1", "ktits_ally_k1"], "ally2_solidarnost": ["ktits_ally_t2", "ktits_ally_k2"],
    "ally3_tuman": ["ktits_ally_t3", "ktits_ally_k3"], "ally4_boloto": ["ktits_ally_t4", "ktits_ally_k4"],
    "neutral_eternal": ["ktits_eternal_neutrality"], "baku_powder": ["ktits_baku_powder_keg"],
    "kaz_britt2": ["ktits_kaz_britt_2", "ktits_kaz_britt_influence"], "kaz_britt3": ["ktits_kaz_britt_3"],
    "kaz_crown": ["ktits_kaz_crown"], "kaz_grace": ["ktits_kaz_grace_t"],
    "kaz_resist": ["ktits_kaz_resist_t", "ktits_kaz_resist5_t", "ktits_kaz_rebels_t"],
    "pol_democracy": [f"ktits_pol_sp_{s}" for s in ("liberal", "socdem", "conserv", "techdem")],
    "pol_communism": ["ktits_pol_sp_lenin", "ktits_pol_sp_totcom"],
    "pol_nationalism": [f"ktits_pol_sp_{s}" for s in ("natstate", "totfas", "integral")],
    "pol_authoritarian": [f"ktits_pol_sp_{s}" for s in ("merit", "technoc", "steppe", "despot", "theocr")],
    "kaz_army": [f"ktits_kaz_sp_{s}" for s in ("army1", "army2", "army3", "levy", "hold", "posts", "paths", "march")],
    "kaz_siesta": [f"ktits_kaz_sp_{s}" for s in ("siesta", "watch", "calm", "fog")],
    "kaz_papers": ["ktits_kaz_sp_pp1", "ktits_kaz_sp_pp2"], "kaz_sobering": ["ktits_kaz_sobering"],
    "event_rise": [], "event_fall": [],   # filled below from the sign of stability_factor of ktits_cas_ev_stab_*
}
ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
a = ap.parse_args()
M = Path(a.mod)
SRC = Path(__file__).resolve().parent.parent / "gfx_src" / "ideas"
ideas_dir = M / "common/ideas"

# event spirits: stability up -> event_rise, down -> event_fall
evf = ideas_dir / "ktits_casuality_event_ideas.txt"
if evf.exists():
    for name, val in re.findall(r"(ktits_cas_ev_stab_\d+) = \{.*?stability_factor = (-?[\d.]+)", evf.read_text(encoding="utf-8"), re.S):
        ICONS["event_fall" if float(val) < 0 else "event_rise"].append(name)

pic = {s: "ktits_" + i for i, sp in ICONS.items() for s in sp}
(M / "gfx/interface/ideas").mkdir(parents=True, exist_ok=True)
sprites = []
for i in ICONS:
    shutil.copyfile(SRC / (i + ".png"), M / f"gfx/interface/ideas/ktits_{i}.png")
    sprites.append(f'\tspriteType = {{\n\t\tname = "GFX_idea_ktits_{i}"\n\t\ttexturefile = "gfx/interface/ideas/ktits_{i}.png"\n\t}}\n')
(M / "interface/ktits_ideas.gfx").write_text("spriteTypes = {\n" + "".join(sprites) + "}\n", encoding="utf-8")

done = set()
for f in sorted(ideas_dir.glob("*.txt")):
    t = f.read_text(encoding="utf-8"); raw = f.read_bytes(); bom = raw.startswith(b"\xef\xbb\xbf")
    def sub(m):
        if m.group(2) in pic:
            done.add(m.group(2))
            return m.group(1) + m.group(2) + m.group(3) + pic[m.group(2)]
        return m.group(0)
    n = re.sub(r"(\n\t\t)(ktits_\w+)( = \{\s*picture = )[\w]+", sub, t)
    if n != t:
        f.write_bytes((b"\xef\xbb\xbf" if bom else b"") + n.encode("utf-8"))
miss = sorted(set(pic) - done)
print(f"icons: {len(ICONS)} sprites, {len(done)} spirits got a picture; event_rise {len(ICONS['event_rise'])}, event_fall {len(ICONS['event_fall'])}")
if miss: print("WARNING: spirits not found in idea files:", ", ".join(miss))

# ruler portraits (gfx_src/portraits/<name>.png, 156x210 large): copied to gfx/leaders/ktits/, small 38x51 is made from large;
# the character gets `portraits = { civilian = { large = "..." small = "..." } }` (idempotent). The emperor portrait is only stored (no crown focus yet).
from PIL import Image
PORTRAITS = {"SCU_casuality_leader": "portrait_scu_peasant", "SCU_Sabirov": "portrait_scu_communism", "SCU_Bulldog_Kazual": "portrait_scu_democracy"}   # SCU_Sabirov, SCU_Bulldog_Kazual are made by make_rulers.py (must run before)
PSRC = SRC.parent / "portraits"
(M / "gfx/leaders/ktits").mkdir(parents=True, exist_ok=True)
for name in PORTRAITS.values():
    big = Image.open(next(q for q in (PSRC / f"{name}_156x210.png", PSRC / f"{name}.png") if q.exists())).convert("RGB")
    big.save(M / f"gfx/leaders/ktits/{name}.png")
    big.resize((38, 51), Image.LANCZOS).save(M / f"gfx/leaders/ktits/{name}_small.png")
for char, name in PORTRAITS.items():
    cf = M / f"common/characters/{char.split('_')[0]}.txt"
    t = cf.read_text(encoding="utf-8-sig"); raw = cf.read_bytes(); bom = raw.startswith(b"\xef\xbb\xbf")
    blk = (f'\t\tportraits = {{\n\t\t\tcivilian = {{\n\t\t\t\tlarge = "gfx/leaders/ktits/{name}.png"\n\t\t\t\tsmall = "gfx/leaders/ktits/{name}_small.png"\n\t\t\t}}\n\t\t}}\n')
    m = re.search(r"(\t" + char + r"\s*=\s*\{\n)(.*?)(\n\t\}\n)", t, re.S)
    if not m: print("WARNING: character not found:", char); continue
    body = re.sub(r"\t\tportraits = \{.*?\n\t\t\}\n", "", m.group(2) + "\n", flags=re.S).rstrip("\n")
    # portraits go before country_leader, right after name
    body = re.sub(r"(\t\tname\s*=\s*\"[^\"]*\"\n)", lambda x: x.group(1) + blk, body, count=1)
    n = t[:m.start()] + m.group(1) + body + m.group(3) + t[m.end():]
    if n != t: cf.write_bytes((b"\xef\xbb\xbf" if bom else b"") + n.encode("utf-8"))
print("portraits:", ", ".join(PORTRAITS))
