"""Generated icons for the Kazualia focus tree, one decision icon and the casuality ideology group icon (65x67 PNG from gfx_src/goals/).
A post-process over the mod (idempotent): copies PNG to gfx/interface/goals/, writes interface/ktits_goals.gfx (GFX_goal_ktits_<id> and
GFX_goal_ktits_<id>_shine, GFX_decision_ktits_kaz_decision, GFX_decision_ktits_dec_fight/_dec_support), patches `icon =` of focuses (common/national_focus/ktits_kazualia.txt) by id
prefix, `icon =` of the political-group Kazualia decisions, `icon = ktits_casuality` of the casuality decisions (common/decisions/ktits_casuality*.txt:
ktits_cas_fight_* -> ktits_dec_fight, others -> ktits_dec_support), and the texture of GFX_ideology_casuality_group in interface/ktits_ideologies.gfx.
Run AFTER the steps that write these files (make_kazualia, make_ideologies), before check. Sources: python tools/make_goals.py --pull
copies the chosen variants from the ComfyUI output into gfx_src/goals/ (run by hand when images change).
Usage: python tools/make_goals.py [--mod PATH] [--pull]"""
import argparse, re, shutil
from pathlib import Path
import lore_data as L

# icon id (file gfx_src/goals/<id>.png) -> (ComfyUI source name, chosen variant)
SRC = {"kazfocus_great": ("kazfocus_great", 2), "kazfocus_reform": ("kazfocus_reform", 1), "kazfocus_commie": ("kazfocus_commie", 1),
       "kazfocus_reserv": ("kazfocus_reserv", 2), "kazfocus_durman": ("kazfocus_durman", 1), "kazfocus_gifts": ("kazfocus_gifts", 2),
       "kazfocus_edu": ("kazfocus_edu", 1), "kazfocus_britt": ("kazfocus_britt", 1), "kazfocus_war": ("kazfocus_war", 1),
       "kaz_decision_icon": ("kaz_decision_icon", 1), "kaz_ideology_casuality": ("kaz_ideology_casuality", 2),
       "dec_fight": ("plan_dec_fight", 2), "dec_support": ("plan_dec_support", 1)}
# focus id prefix (after ktits_kaz_) -> icon. Root focuses (wake, sleep, hum, red), n_* (neutrality), z_* are left as is
# (kazfocus_root variants are nearly black; z_* = puppet branch; reserv art = gate/fence is used for it)
PREFIX = {"g_": "kazfocus_great", "r_": "kazfocus_reform", "c_": "kazfocus_commie", "z_": "kazfocus_reserv", "d_": "kazfocus_durman",
          "e_": "kazfocus_gifts", "s_": "kazfocus_edu", "b_": "kazfocus_britt", "a_": "kazfocus_war"}
FOCUS_W, FOCUS_H = 94, 76   # vanilla focus icon size (goal_generic_*.dds)
DECISION_OLD = "generic_political_address"   # decisions of the political group get the common decision icon

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
ap.add_argument("--pull", action="store_true")
ap.add_argument("--comfy", default=r"D:\ComfyUI_windows_portable\ComfyUI\output\ktits")
a = ap.parse_args()
G = Path(__file__).resolve().parent.parent / "gfx_src" / "goals"
if a.pull:
    G.mkdir(parents=True, exist_ok=True)
    from PIL import Image, ImageFilter
    for i, (n, v) in SRC.items():
        if i.startswith("kazfocus_"):   # focus icons: vanilla size 94x76 (the 65x67 spirit size looks too small in the tree), cut from the big 1024 source
            im = Image.open(Path(a.comfy) / f"{n}_full_{v:05d}_.png").convert("RGB")
            m = round(im.width * 0.06); im = im.crop((m, m, im.width - m, im.height - m))   # trim the paper frame
            h = round(im.width * FOCUS_H / FOCUS_W); top = (im.height - h) // 2
            im = im.crop((0, top, im.width, top + h)).resize((FOCUS_W, FOCUS_H), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1, percent=60, threshold=2))
            im.save(G / f"{i}.png")
        else:
            shutil.copyfile(Path(a.comfy) / f"{n}_65x67_{v:05d}_.png", G / f"{i}.png")
    print("pulled", len(SRC))
M = Path(a.mod)
(M / "gfx/interface/goals").mkdir(parents=True, exist_ok=True); (M / "interface").mkdir(exist_ok=True)
for i in SRC:
    shutil.copyfile(G / f"{i}.png", M / f"gfx/interface/goals/ktits_{i}.png")

def tex(i): return f"gfx/interface/goals/ktits_{i}.png"
def shine(name, t):   # copy of the vanilla shine sprite (goals_shine.gfx) [uncertain: mask from PNG, not checked in game]
    anim = lambda rot: (f'\t\tanimation = {{\n\t\t\tanimationmaskfile = "{t}"\n\t\t\tanimationtexturefile = "gfx/interface/goals/shine_overlay.dds"\n'
                        f'\t\t\tanimationrotation = {rot}\n\t\t\tanimationlooping = no\n\t\t\tanimationtime = 0.75\n\t\t\tanimationdelay = 0\n'
                        f'\t\t\tanimationblendmode = "add"\n\t\t\tanimationtype = "scrolling"\n\t\t\tanimationrotationoffset = {{ x = 0.0 y = 0.0 }}\n'
                        f'\t\t\tanimationtexturescale = {{ x = 1.0 y = 1.0 }}\n\t\t}}\n')
    return (f'\tspriteType = {{\n\t\tname = "{name}_shine"\n\t\ttexturefile = "{t}"\n\t\teffectFile = "gfx/FX/buttonstate.lua"\n'
            + anim(-90.0) + anim(90.0) + "\t}\n")
sp = []
for i in sorted(set(PREFIX.values())):
    n = f"GFX_goal_ktits_{i}"
    sp.append(f'\tspriteType = {{\n\t\tname = "{n}"\n\t\ttexturefile = "{tex(i)}"\n\t}}\n' + shine(n, tex(i)))
sp.append(f'\tspriteType = {{\n\t\tname = "GFX_decision_ktits_kaz_decision"\n\t\ttexturefile = "{tex("kaz_decision_icon")}"\n\t}}\n')
for i in ("dec_fight", "dec_support"):
    sp.append(f'\tspriteType = {{\n\t\tname = "GFX_decision_ktits_{i}"\n\t\ttexturefile = "{tex(i)}"\n\t}}\n')
(M / "interface/ktits_goals.gfx").write_text("spriteTypes = {\n" + "".join(sp) + "}\n", encoding="utf-8")

def patch(f, fn):
    if not f.exists(): print("WARNING: no file", f.name); return 0
    raw = f.read_bytes(); bom = raw.startswith(b"\xef\xbb\xbf"); t = raw.decode("utf-8-sig")
    n, c = fn(t)
    if n != t: f.write_bytes((b"\xef\xbb\xbf" if bom else b"") + n.encode("utf-8"))
    return c

def foc(t):
    c = [0]
    def sub(m):
        for p, i in PREFIX.items():
            if m.group(2).startswith(p): c[0] += 1; return m.group(1) + f"GFX_goal_ktits_{i}"
        return m.group(0)
    return re.sub(r"(\tid = ktits_kaz_(\w+)\n\t\ticon = )GFX_\w+", sub, t), c[0]
nf = patch(M / "common/national_focus/ktits_kazualia.txt", foc)
nd = patch(M / "common/decisions/ktits_kazualia_decisions.txt",
           lambda t: (re.sub(r"(\n\t\ticon = )" + DECISION_OLD + r"\n", r"\1ktits_kaz_decision\n", t), t.count("icon = " + DECISION_OLD)))
CAS_OLD = "ktits_casuality"   # placeholder icon (mosque photo) of the casuality decisions
CAS_FILES = ["common/decisions/ktits_casuality.txt", "common/decisions/ktits_casuality_kaz.txt"]
cas_cnt = {"dec_fight": 0, "dec_support": 0}
def cas(t):   # idempotent: only `icon = ktits_casuality` lines are touched; counts are decisions patched in this run
    def sub(m):
        k = "dec_fight" if "_fight_" in m.group(2) else "dec_support"
        cas_cnt[k] += 1
        return m.group(1) + "ktits_" + k + "\n"
    n = re.sub(r"(^\t(\w+) = \{\r?\n\t\ticon = )" + CAS_OLD + r"\r?\n", sub, t, flags=re.M)
    return n, sum(cas_cnt.values())
for f in CAS_FILES:
    patch(M / f, cas)
def ideo(t):
    n = re.sub(r'(name = "GFX_ideology_casuality_group"\s*texturefile = )"[^"]*"', r'\1"' + tex("kaz_ideology_casuality") + '"', t)
    return n, 1
patch(M / "interface/ktits_ideologies.gfx", ideo)
print(f"goals: {len(sp)} sprites, {nf} focus icons, {nd} decision icons, ideology casuality icon set")
print(f"casuality decisions patched: dec_fight={cas_cnt['dec_fight']}, dec_support={cas_cnt['dec_support']} (0 = already patched)")
