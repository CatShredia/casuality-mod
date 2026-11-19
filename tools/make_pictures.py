"""Event pictures (210x120) and decision-category headers (420x120) from gfx_src/pictures/: copies PNGs into the mod, writes
interface/ktits_pictures.gfx and sets `picture = GFX_ktits_...` in the events / decision categories of the table below.
A post-process over the mod files (idempotent): run it AFTER every step that writes events or decision categories
(next to make_icons.py, before check in post_export.py). Subjects: image names; nothing is invented, unmatched events keep the generic picture.
Usage: python tools/make_pictures.py [--mod PATH]"""
import argparse, re, shutil
from pathlib import Path
import lore_data as L

# event id -> image
EVENTS = {
    "ktits_casuality": {1: "glob_cas01_fall", 10: "glob_cas10_fog", 11: "glob_cas11_preacher", 12: "glob_cas12_harvest",
                        13: "glob_cas13_workshop", 14: "glob_cas14_letter", 20: "glob_cas20_stakhanov", 21: "glob_cas21_drought",
                        22: "glob_cas22_bridge", 23: "glob_cas23_winter", 24: "glob_cas24_awakening", 30: "glob_cas30_arisen",
                        31: "glob_cas31_last", 32: "glob_cas32_neighbor", 33: "glob_cas33_free", 34: "glob_cas34_call",
                        35: "glob_cas35_party", 36: "glob_cas36_nobody"},
    "ktits_alliance": {1: "glob_ally1_knock", 3: "glob_ally2_alien", 4: "glob_ally2_alien", 8: "glob_ally3_guest",
                       14: "glob_ally3_guest", 9: "glob_ally4_leave", 12: "glob_ally4_leave",
                       5: "glob_ally2_alien", 6: "glob_ally3_guest", 15: "glob_ally4_leave", 16: "glob_ally4_leave"},
    "ktits_edu": {1: "plan_ev_edu", 2: "plan_ev_edu", 3: "plan_ev_edu"},
    "ktits_kz_out": {2: "plan_ev_fog", 3: "plan_ev_rebels", 20: "plan_ev_rebels", 21: "plan_ev_ambush", 22: "plan_ev_fog",
                     10: "plan_ev_rebels", 11: "plan_ev_rebels", 12: "plan_ev_rebels", 13: "plan_ev_rebels", 14: "plan_ev_rebels", 15: "plan_ev_rebels"},
    "ktits_kazualia": {1: "kaz_ev1_morning", 2: "kaz_ev2_finally", 3: "kaz_ev3_mutiny", 4: "kaz_ev4_industry",
                       5: "kaz_ev2_finally", 501: "kaz_ev3_mutiny", 502: "kaz_ev3_mutiny", 503: "kaz_ev4_industry", 504: "kaz_ev4_industry",
                       505: "kaz_ev1_morning", 506: "kaz_ev4_industry", 507: "kaz_ev1_morning", 508: "kaz_ev4_industry",
                       509: "kaz_ev4_industry", 510: "kaz_ev4_industry", 511: "kaz_ev4_industry"},
}
# decision category -> header image
CAT_W, CAT_H = 504, 120
CATS = {"ktits_alliance_category": "glob_cat_alliance", "ktits_casuality_fight_category": "glob_cat_cas_fight",
        "ktits_casuality_support_category": "glob_cat_cas_support", "ktits_education_dev_category": "glob_cat_edu_dev",
        "ktits_education_simp_category": "glob_cat_edu_simp", "ktits_kaz_faith_category": "kaz_cat_faith",
        "ktits_kaz_reform_category": "kaz_cat_reform", "ktits_kaz_britt_category": "kaz_cat_britt",
        "ktits_kaz_accept_category": "kaz_cat_accept", "ktits_kaz_outer_category": "kaz_cat_outer",
        "ktits_casuality_kaz_category": "glob_cat_cas_support", "ktits_kaz_inner_category": "kaz_cat_outer",
        "ktits_sov_buffer_category": "kaz_cat_outer"}

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
M = Path(ap.parse_args().mod)
SRC = Path(__file__).resolve().parent.parent / "gfx_src" / "pictures"

def rw(f, fn):
    raw = f.read_bytes(); bom = raw.startswith(b"\xef\xbb\xbf")
    t = raw.decode("utf-8-sig"); n = fn(t)
    if n != t: f.write_bytes((b"\xef\xbb\xbf" if bom else b"") + n.encode("utf-8"))

used_ev = {i for d in EVENTS.values() for i in d.values()}
sprites, names = [], {}
(M / "gfx/event_pictures").mkdir(parents=True, exist_ok=True)
(M / "gfx/interface/ktits").mkdir(parents=True, exist_ok=True)
for i in sorted(used_ev | set(CATS.values())):
    cat = i in CATS.values()
    dst = f"gfx/interface/ktits/{i}.png" if cat else f"gfx/event_pictures/ktits_{i}.png"
    if cat:   # the category window is 510 wide and the picture is drawn at 1:1 (vanilla, countrydecisionview.gui): cover-fit the 420x120 source to 504x120
        from PIL import Image
        im = Image.open(SRC / f"{i}.png").convert("RGBA"); k = CAT_W / im.width
        im = im.resize((CAT_W, round(im.height * k)), Image.LANCZOS); top = max(0, (im.height - CAT_H) // 2)
        im.crop((0, top, CAT_W, top + CAT_H)).save(M / dst)
    else:
        shutil.copyfile(SRC / f"{i}.png", M / dst)
    names[i] = f"GFX_{'decision_cat_picture' if cat else 'report_event'}_ktits_{i}"
    sprites.append(f'\tspriteType = {{\n\t\tname = "{names[i]}"\n\t\ttexturefile = "{dst}"\n\t}}\n')
(M / "interface/ktits_pictures.gfx").write_text("spriteTypes = {\n" + "".join(sprites) + "}\n", encoding="utf-8")

# events: replace/insert the picture line inside the event block
ev_n = 0
for ns, ids in EVENTS.items():
    files = [p for p in (M / "events").glob("ktits_*.txt") if re.search(rf"\bid = {ns}\.", p.read_text(encoding="utf-8-sig"))]
    for f in files:
        def sub(t):
            global ev_n
            for num, img in ids.items():
                hdr = f"\n\tid = {ns}.{num}\n"
                m = re.search(re.escape(hdr) + r".*?\n\}\n", t, re.S)
                if not m: continue
                blk = m.group(0); pic = f"picture = {names[img]}"
                if re.search(r"\n\tpicture = ", blk): nb = re.sub(r"\n\tpicture = \w+", "\n\t" + pic, blk, count=1)
                else: nb = blk.replace(hdr, hdr + "\t" + pic + "\n", 1)
                t = t[:m.start()] + nb + t[m.end():]; ev_n += 1
            return t
        rw(f, sub)

# decision categories: the picture line of the block
cat_n = 0
for f in (M / "common/decisions/categories").glob("ktits_*.txt"):
    def sub(t):
        global cat_n
        for c, img in CATS.items():
            t, k = re.subn(rf"(\b{c} = \{{[^{{}}]*?\bpicture = )\w+", lambda m: m.group(1) + names[img], t, count=1, flags=re.S)
            cat_n += k
        return t
    rw(f, sub)
print(f"pictures: {len(sprites)} sprites, {ev_n} events, {cat_n} categories")
if ev_n != sum(map(len, EVENTS.values())): print("WARNING: some events not patched (expected", sum(map(len, EVENTS.values())), ")")
if cat_n != len(CATS): print("WARNING: some categories not patched (expected", len(CATS), ")")
