"""In-game guides (docs/guides/Ingame-Guides.md, variant D): a button «Руководство» in the politics tab of the country (scripted gui, context player_context, parent_window_token =
politics_tab) opens a window with the pages of the guide: section «Общее» (all countries, docs/guides/Guide-Global.md, 10 pages) and section «Казуалия» (only for Kazualia,
docs/guides/Guide-Kazualia.md, 14 pages). The Soviet Union has no guide yet. Texts are INVENTED (docs/lore/Invented-Lore.md).
Every page is its own scripted gui with its own window (text, buttons, page number); only the window of the current page is visible (ui-level `visible` on the variables
ktits_guide_open, ktits_guide_sec, ktits_guide_page). Reason: with one window and a text box per page the `_visible` triggers of text boxes did not hide the old page in game
(the texts overlapped), and the scripted localisation text did not follow the page variable.
[uncertain: player_context with politics_tab is documented in common/scripted_guis/_documentation.md but not used by vanilla files; the place of the button and the size of the
text box are to be adjusted in game]
Writes: common/scripted_guis/ktits_guide.txt, interface/ktits_guide.gui, localisation ru/en ktits_guide_l_*.yml (and the unused scripted localisation GetKtitsGuideText is removed).
Usage: python tools/make_guides.py [--mod PATH]"""
import argparse, re
from pathlib import Path
import lore_data as L

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
a = ap.parse_args()
M = Path(a.mod)
NL = chr(92) + "n"   # the two characters \n of a yml value
def w(rel, text):
    p = M / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding="utf-8", newline="\n")

def pages(fn):
    md = (L.REPO / "docs/guides" / fn).read_text(encoding="utf-8").replace("\r\n", "\n")
    out = []
    for m in re.finditer(r"(?ms)^## Страница (\d+)\. ([^\n]+)\n(.*?)(?=^## |\Z)", md):
        body = m.group(3).strip()
        body = re.sub(r"\*\*([^*]+)\*\*", r"§Y\1§!", body)
        body = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", body).replace("`", "").replace('"', "'")
        out.append((int(m.group(1)), m.group(2).strip(), body))
    return out

DYN = {("g", 2): "Ваша шкала Казуальности сейчас: §Y[?ktits_casuality|0]§!", ("k", 4): "Ваша Внутренняя Казуальность сейчас: §Y[?ktits_kaz_inner|0] %§!",
       ("k", 7): "Ваша Казуальная Вера сейчас: §Y[?ktits_kaz_faith|0]§!"}
ru, en = [], []
SEC = {"g": ("Guide-Global.md", 1), "k": ("Guide-Kazualia.md", 2)}
counts = {}
for s, (fn, num) in SEC.items():
    pg = pages(fn); counts[s] = len(pg)
    for n, title, body in pg:
        assert "[" not in body, (s, n)
        txt = f"§Y{title}§!{NL}{NL}" + body.replace("\n\n", NL + NL).replace("\n", NL)
        if (s, n) in DYN: txt += NL + NL + DYN[(s, n)]
        ru.append((f"ktits_guide_{s}_{n}", txt)); en.append((f"ktits_guide_{s}_{n}", txt))
for k, r in (("ktits_guide_title", "Руководство"), ("ktits_guide_open_btn", "Руководство"), ("ktits_guide_sec_g_btn", "Общее"), ("ktits_guide_sec_k_btn", "Казуалия"),
             ("ktits_guide_prev_btn", "« Назад"), ("ktits_guide_next_btn", "Дальше »"), ("ktits_guide_pageno", "Страница [?ktits_guide_page|0]"),
             ("ktits_guide_open_tt", "Открыть руководство по механикам мода.")):
    ru.append((k, r)); en.append((k, L.translit(r) if "[" not in r else "Page [?ktits_guide_page|0]"))
L.write_yml(str(M / "localisation/russian/ktits_guide_l_russian.yml"), "russian", ru)
L.write_yml(str(M / "localisation/english/ktits_guide_l_english.yml"), "english", en)
old = M / "common/scripted_localisation/ktits_guide_loc.txt"
if old.exists(): old.unlink()

def cv(v, val, cmp=None): return f"check_variable = {{ var = {v} value = {val}" + (f" compare = {cmp}" if cmp else "") + " }"
def dbg(name): return f"if = {{ limit = {{ has_global_flag = ktits_debug }} log = \"KTITS:SYS:[THIS.GetTag]:guide {name}\" }}"
SG = "\t\tcontext_type = player_context\n\t\tparent_window_token = politics_tab\n\t\tai_enabled = { always = no }\n"
sg = ("scripted_gui = {\n\n"
      "\tktits_guide_btn_ui = {\n" + SG + "\t\twindow_name = \"ktits_guide_btn_window\"\n\t\tvisible = { always = yes }\n\n"
      "\t\teffects = {\n\t\t\tktits_guide_open_click = {\n\t\t\t\t" + dbg("open") + "\n\t\t\t\tset_variable = { var = ktits_guide_open value = 1 }\n"
      "\t\t\t\tif = {\n\t\t\t\t\tlimit = { " + cv("ktits_guide_sec", 0) + " }\n\t\t\t\t\tset_variable = { var = ktits_guide_sec value = 1 }\n\t\t\t\t\tset_variable = { var = ktits_guide_page value = 1 }\n\t\t\t\t}\n\t\t\t}\n\t\t}\n\t}\n\n")
BTN = lambda name, x, y, text, sprite="GFX_button_123x34": (f"\t\tbuttonType = {{\n\t\t\tname = \"{name}\"\n\t\t\tquadTextureSprite = \"{sprite}\"\n\t\t\tposition = {{ x = {x} y = {y} }}\n\t\t\tbuttonFont = \"hoi_18mbs\"\n\t\t\tbuttonText = \"{text}\"\n\t\t}}\n\n")
gui = ("guiTypes = {\n\n"
       "\tcontainerWindowType = {\n\t\tname = \"ktits_guide_btn_window\"\n\t\tposition = { x = 290 y = 2 }\n\t\tsize = { width = 130 height = 36 }\n\t\tclipping = no\n\n"
       + BTN("ktits_guide_open", 0, 0, "ktits_guide_open_btn") + "\t}\n\n")
for s, (fn, num) in SEC.items():
    for n in range(1, counts[s] + 1):
        p = f"ktits_guide_pg_{s}{n}"
        # ui: the page is visible only while the guide is open on this section and page
        sg += (f"\t{p}_ui = {{\n" + SG + f"\t\twindow_name = \"{p}_window\"\n\t\tvisible = {{\n\t\t\t{cv('ktits_guide_open', 1)}\n\t\t\t{cv('ktits_guide_sec', num)}\n\t\t\t{cv('ktits_guide_page', n)}\n\t\t}}\n\n"
               f"\t\ttriggers = {{\n\t\t\t{p}_seck_visible = {{ ktits_is_kazualia = yes }}\n\t\t}}\n\n\t\teffects = {{\n"
               f"\t\t\t{p}_close_click = {{\n\t\t\t\t{dbg('close')}\n\t\t\t\tset_variable = {{ var = ktits_guide_open value = 0 }}\n\t\t\t}}\n"
               + (f"\t\t\t{p}_prev_click = {{\n\t\t\t\t{dbg('prev')}\n\t\t\t\tset_variable = {{ var = ktits_guide_page value = {n - 1} }}\n\t\t\t}}\n" if n > 1 else "")
               + (f"\t\t\t{p}_next_click = {{\n\t\t\t\t{dbg('next')}\n\t\t\t\tset_variable = {{ var = ktits_guide_page value = {n + 1} }}\n\t\t\t}}\n" if n < counts[s] else "")
               + f"\t\t\t{p}_secg_click = {{\n\t\t\t\tset_variable = {{ var = ktits_guide_sec value = 1 }}\n\t\t\t\tset_variable = {{ var = ktits_guide_page value = 1 }}\n\t\t\t}}\n"
               f"\t\t\t{p}_seck_click = {{\n\t\t\t\tset_variable = {{ var = ktits_guide_sec value = 2 }}\n\t\t\t\tset_variable = {{ var = ktits_guide_page value = 1 }}\n\t\t\t}}\n\t\t}}\n\t}}\n\n")
        gui += (f"\tcontainerWindowType = {{\n\t\tname = \"{p}_window\"\n\t\tposition = {{ x = 0 y = 36 }}\n\t\tsize = {{ width = 550 height = 500 }}\n\t\tclipping = no\n\n"
                "\t\tbackground = {\n\t\t\tname = \"Background\"\n\t\t\tspriteType = \"GFX_tiled_window\"\n\t\t}\n\n"
                "\t\tinstantTextBoxType = {\n\t\t\tname = \"" + p + "_title\"\n\t\t\tposition = { x = 20 y = 14 }\n\t\t\tfont = \"hoi_18mbs\"\n\t\t\ttext = \"ktits_guide_title\"\n\t\t\tformat = left\n\t\t\tmaxWidth = 400\n\t\t\tmaxHeight = 26\n\t\t}\n\n"
                f"\t\tbuttonType = {{\n\t\t\tname = \"{p}_close\"\n\t\t\tquadTextureSprite = \"GFX_closebutton\"\n\t\t\tposition = {{ x = 512 y = 10 }}\n\t\t}}\n\n"
                + BTN(p + "_secg", 20, 48, "ktits_guide_sec_g_btn") + BTN(p + "_seck", 150, 48, "ktits_guide_sec_k_btn")
                + f"\t\tinstantTextBoxType = {{\n\t\t\tname = \"{p}_text\"\n\t\t\tposition = {{ x = 22 y = 96 }}\n\t\t\tfont = \"hoi_16mbs\"\n\t\t\ttext = \"ktits_guide_{s}_{n}\"\n\t\t\tformat = left\n\t\t\tmaxWidth = 506\n\t\t\tmaxHeight = 340\n\t\t}}\n\n"
                + (BTN(p + "_prev", 20, 452, "ktits_guide_prev_btn") if n > 1 else "") + (BTN(p + "_next", 407, 452, "ktits_guide_next_btn") if n < counts[s] else "")
                + f"\t\tinstantTextBoxType = {{\n\t\t\tname = \"{p}_pageno\"\n\t\t\tposition = {{ x = 230 y = 462 }}\n\t\t\tfont = \"hoi_16mbs\"\n\t\t\ttext = \"ktits_guide_pageno\"\n\t\t\tformat = left\n\t\t\tmaxWidth = 150\n\t\t\tmaxHeight = 20\n\t\t}}\n\t}}\n\n")
w("common/scripted_guis/ktits_guide.txt", sg + "}\n")
w("interface/ktits_guide.gui", gui + "}\n")
print(f"guides: {counts['g']} global pages + {counts['k']} Kazualia pages (one scripted gui and window per page), button in the politics tab")
