"""Pictures of the Soviet Union (MAK) from the image generator (ComfyUI output D:\\ComfyUI_windows_portable\\ComfyUI\\output\\ktits, workflows/gen_soviet.py and
gen_portraits_mak*.py of D:\\directory-git\\image_generator): spirit icons 65x67, focus-path icons (cut from the big 1024 pictures to 94x76), category headers 504x120 and the
portraits of the rulers 156x210. `--pull` copies the chosen variants into gfx_src/soviet/ (the repository keeps the sources); the build step (without --pull) copies them
into the mod, writes interface/ktits_soviet_pictures.gfx and sets the pictures: `picture = ktits_...` of the spirits, `icon = GFX_goal_ktits_sov_...` of the focuses
(common/national_focus/ktits_soviet.txt and the zone branch of generic.txt), `picture = GFX_decision_cat_picture_ktits_sov_...` of the decision categories, `portraits` of
the characters. The variant (1 or 2 of every generated pair) is chosen by VAR below by eye from the contact sheets (author: Claude, may be changed). Idempotent.
Run AFTER make_soviet.py, make_soviet_mech.py and make_guides.py (before make_icons.py). Usage: python tools/make_soviet_pictures.py [--mod PATH] [--pull] [--comfy DIR]"""
import argparse, re, shutil
from pathlib import Path
import lore_data as L

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
ap.add_argument("--pull", action="store_true")
ap.add_argument("--comfy", default=r"D:\ComfyUI_windows_portable\ComfyUI\output\ktits")
a = ap.parse_args()
M = Path(a.mod)
SRC = Path(__file__).resolve().parent.parent / "gfx_src" / "soviet"
FOCUS_W, FOCUS_H = 94, 76

# spirit image -> (variant, spirits of the mod)
SPIRITS = {
    "amnesty": (2, ["ktits_sov_sp_amnesty"]), "open_congress": (2, ["ktits_sov_sp_open_congress"]), "councils": (2, ["ktits_sov_sp_councils"]),
    "collective": (2, ["ktits_sov_sp_collective"]), "cult": (1, ["ktits_sov_sp_cult"]), "monolith": (1, ["ktits_sov_sp_monolith"]),
    "arkho_claim": (1, ["ktits_sov_sp_arkho_claim"]), "church": (1, ["ktits_sov_sp_church"]), "bone_fire": (1, ["ktits_sov_sp_bone_fire"]),
    "vertical": (2, ["ktits_sov_sp_vertical"]), "unity": (2, ["ktits_sov_sp_unity"]), "great_march": (1, ["ktits_sov_sp_great_march"]),
    "udarniki": (2, ["ktits_sov_sp_udarniki"]), "north_posts": (1, ["ktits_sov_sp_north_posts"]), "five_year": (1, ["ktits_sov_sp_five_year"]),
    "electric": (2, ["ktits_sov_sp_electric"]), "kolkhoz": (1, ["ktits_sov_sp_kolkhoz"]), "mass_army": (2, ["ktits_sov_sp_mass_army"]),
    "cadre": (2, ["ktits_sov_sp_cadre"]), "econ_bloc": (2, ["ktits_sov_sp_econ_bloc"]), "bloc_rouble": (1, ["ktits_sov_sp_bloc_rouble"]),
    "bloc_tariff": (1, ["ktits_sov_sp_bloc_tariff"]), "zone_market": (1, ["ktits_sov_sp_zone_market"]),
    "p_autocrat": (1, ["ktits_sov_sp_pw_auto"]), "p_soft": (1, ["ktits_sov_sp_pw_soft"]), "p_hard": (1, ["ktits_sov_sp_pw_hard"]),
    "p_schizo": (2, ["ktits_sov_sp_pw_schizo"]), "p_balance": (1, ["ktits_sov_sp_pw_balance"]),
    "idel": (1, ["ktits_idel_two_rivers"]), "sez_member": (1, ["ktits_sez_member"]), "sez_exit": (2, ["ktits_sez_exit"]),
    "sez_rails": (1, ["ktits_sez_rails"]), "sez_rouble": (2, ["ktits_sez_rouble"]), "sez_wall": (2, ["ktits_sez_wall"]),
    "crash": (1, ["ktits_sov_sp_crash", "ktits_sov_sp_crash_half"]), "crash_soft": (1, ["ktits_sov_sp_crash_soft"]),
}
# the cult of personality of the Balance of Power reuses the picture of the "Cult of the Secretary General"
EXTRA_SPIRIT = {"ktits_sov_sp_pcult": "cult", "ktits_sov_sp_party_dict": "collective"}
# focus-path image -> variant; focus ids (without ktits_sov_) by prefix
FOCUS = {"paranoia": 2, "unthinkable": 1, "reforms": 2, "softcomm": 1, "hardcomm": 2, "casual": 1, "church": 2, "fascism": 1, "anticas": 1, "foreign": 1, "econ": 2,
         "army": 2, "zone_stay": 2, "zone_exit": 2}
FOCUS_RULES = [(r"p[0a-z]", "paranoia"), (r"cong|u\d+|g\d+", "unthinkable"), (r"r\d+", "reforms"), (r"m\d+", "softcomm"), (r"t\d+", "hardcomm"), (r"k\d+", "casual"),
               (r"ch\d+", "church"), (r"f\d+", "fascism"), (r"a\d+", "anticas"), (r"x\d+|r[adckyfgmhs]\d+", "foreign"), (r"eb\d+", "zone_stay"), (r"e\d+", "econ"), (r"ar\d+", "army")]
def focus_img(i):
    for pat, img in FOCUS_RULES:
        if re.fullmatch(pat, i): return img
    return None
# headers: image -> variant; categories
HEADS = {"unity": 1, "paranoia": 1, "balance": 1, "church": 1, "export": 1, "stroyki": 1}
CATS = {"ktits_sov_integrity_category": "unity", "ktits_sov_paranoia_category": "paranoia", "ktits_sov_balance_category": "balance", "ktits_sov_church_category": "church",
        "ktits_sov_export_category": "export", "ktits_sov_builds_category": "stroyki"}
# portraits (the generated file of the ruler): character -> (image, variant of the file name)
PORT = {"MAK_Vijay_Vidam": ("gensek", 1), "MAK_Vanya_Pim": ("kormchiy", 2), "MAK_Pimestrov": ("pimestrov", 2), "MAK_Ioann_Pimenov": ("president", 2), "MAK_casuality_leader": ("casual", 2)}

def src_name(kind, n, v):
    return {"sp": f"sov_sp_{n}_65x67_{v:05d}_.png", "f": f"sov_f_{n}_full_{v:05d}_.png", "h": f"sov_h_{n}_504x120_{v:05d}_.png", "p": f"portrait_mak_{n}_156x210_{v:05d}_.png"}[kind]

if a.pull:
    from PIL import Image, ImageFilter
    for sub_ in ("spirits", "focus", "heads", "portraits"): (SRC / sub_).mkdir(parents=True, exist_ok=True)
    C = Path(a.comfy)
    for n, (v, _) in SPIRITS.items(): shutil.copyfile(C / src_name("sp", n, v), SRC / "spirits" / f"{n}.png")
    for n, v in FOCUS.items():   # cut from the big picture: trim the paper frame, vanilla focus size 94x76
        im = Image.open(C / src_name("f", n, v)).convert("RGB")
        m = round(im.width * 0.06); im = im.crop((m, m, im.width - m, im.height - m))
        h = round(im.width * FOCUS_H / FOCUS_W); top = (im.height - h) // 2
        im.crop((0, top, im.width, top + h)).resize((FOCUS_W, FOCUS_H), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1, percent=60, threshold=2)).save(SRC / "focus" / f"{n}.png")
    for n, v in HEADS.items(): shutil.copyfile(C / src_name("h", n, v), SRC / "heads" / f"{n}.png")
    for ch, (n, v) in PORT.items(): shutil.copyfile(C / src_name("p", n, v), SRC / "portraits" / f"{n}.png")
    print(f"soviet pictures pulled: {len(SPIRITS)} spirits, {len(FOCUS)} focus icons, {len(HEADS)} headers, {len(PORT)} portraits")
    raise SystemExit

from PIL import Image
GI = M / "gfx/interface/soviet"; GI.mkdir(parents=True, exist_ok=True)
(M / "gfx/leaders/ktits").mkdir(parents=True, exist_ok=True)
sprites = []
def sprite(name, tex): sprites.append(f'\tspriteType = {{\n\t\tname = "{name}"\n\t\ttexturefile = "{tex}"\n\t}}\n')
for n in SPIRITS:
    shutil.copyfile(SRC / "spirits" / f"{n}.png", GI / f"idea_{n}.png"); sprite(f"GFX_idea_ktits_sov_{n}", f"gfx/interface/soviet/idea_{n}.png")
for n in FOCUS:
    shutil.copyfile(SRC / "focus" / f"{n}.png", GI / f"goal_{n}.png"); sprite(f"GFX_goal_ktits_sov_{n}", f"gfx/interface/soviet/goal_{n}.png")
for n in HEADS:
    shutil.copyfile(SRC / "heads" / f"{n}.png", GI / f"cat_{n}.png"); sprite(f"GFX_decision_cat_picture_ktits_sov_{n}", f"gfx/interface/soviet/cat_{n}.png")
(M / "interface/ktits_soviet_pictures.gfx").write_text("spriteTypes = {\n" + "".join(sprites) + "}\n", encoding="utf-8")

def patch(f, fn):
    raw = f.read_bytes(); bom = raw.startswith(b"\xef\xbb\xbf"); t = raw.decode("utf-8-sig"); crlf = "\r\n" in t; t = t.replace("\r\n", "\n")
    n, c = fn(t)
    if n != t: f.write_bytes((b"\xef\xbb\xbf" if bom else b"") + (n.replace("\n", "\r\n") if crlf else n).encode("utf-8"))
    return c
# spirits
pic = {sp: f"ktits_sov_{n}" for n, (_, sps) in SPIRITS.items() for sp in sps}
pic.update({sp: f"ktits_sov_{n}" for sp, n in EXTRA_SPIRIT.items()})
done = set()
def spirits(t):
    def sub(m):
        if m.group(2) in pic: done.add(m.group(2)); return m.group(1) + m.group(2) + m.group(3) + pic[m.group(2)]
        return m.group(0)
    return re.sub(r"(\n\t\t)(ktits_\w+)( = \{\s*picture = )[\w]+", sub, t), 0
for fn in ("ktits_soviet_ideas.txt", "ktits_soviet_mech_ideas.txt"): patch(M / "common/ideas" / fn, spirits)
# focuses
nf = [0]
def foc(t):
    def sub(m):
        i = m.group(2); img = focus_img(i) if m.group(1) == "sov_" else {"stay": "zone_stay", "market": "zone_stay", "rails": "zone_stay", "0": "foreign", "exit": "zone_exit", "rouble": "zone_exit", "wall": "zone_exit"}.get(i)
        if not img: return m.group(0)
        nf[0] += 1
        return f"id = ktits_{m.group(1)}{i}\n{m.group(3)}icon = GFX_goal_ktits_sov_{img}"
    t2 = re.sub(r"id = ktits_(sov_|zone_)(\w+)\n(\s*)icon = GFX_\w+", sub, t)
    return t2, 0
patch(M / "common/national_focus/ktits_soviet.txt", foc); patch(M / "common/national_focus/generic.txt", foc)
# categories
def cats(t):
    for cat, img in CATS.items():
        t = re.sub(r"(" + cat + r" = \{[^}]*?picture = )GFX_\w+", r"\1GFX_decision_cat_picture_ktits_sov_" + img, t, flags=re.S)
    return t, 0
for fn in ("ktits_soviet_categories.txt", "ktits_soviet_builds_category.txt"): patch(M / "common/decisions/categories" / fn, cats)
# portraits
for ch, (n, v) in PORT.items():
    name = f"portrait_mak_{n}"
    big = Image.open(SRC / "portraits" / f"{n}.png").convert("RGB"); big.save(M / f"gfx/leaders/ktits/{name}.png"); big.resize((38, 51), Image.LANCZOS).save(M / f"gfx/leaders/ktits/{name}_small.png")
    def port(t, ch=ch, name=name):
        blk = f'\t\tportraits = {{\n\t\t\tcivilian = {{\n\t\t\t\tlarge = "gfx/leaders/ktits/{name}.png"\n\t\t\t\tsmall = "gfx/leaders/ktits/{name}_small.png"\n\t\t\t}}\n\t\t}}\n'
        m = re.search(r"(\t" + ch + r"\s*=\s*\{\n)(.*?)(\n\t\}\n)", t, re.S)
        if not m: print("WARNING: character not found:", ch); return t, 0
        body = re.sub(r"\t\tportraits = \{.*?\n\t\t\}\n", "", m.group(2) + "\n", flags=re.S).rstrip("\n")
        body = re.sub(r"(\t\tname\s*=\s*\"[^\"]*\"\n)", lambda x: x.group(1) + blk, body, count=1)
        return t[:m.start()] + m.group(1) + body + m.group(3) + t[m.end():], 0
    patch(M / "common/characters/MAK.txt", port)
miss = sorted(set(pic) - done)
print(f"soviet pictures: {len(sprites)} sprites; {len(done)} spirits, {nf[0]} focuses, {len(CATS)} categories, {len(PORT)} portraits" + (f"; spirits not found: {', '.join(miss)}" if miss else ""))
