"""Education of the population (docs/lore/Contries-Description.md "Образованность населения", 6 levels) as national spirits.

Each country gets one spirit ktits_edu_<0..5> at the start (history/countries/<TAG> - *.txt: add_ideas = ktits_edu_N).
Levels (lore scale, docs/lore/Contries-Description.md): 0 Необразованное стадо, 1 Крестьянское образование, 2 Образованная элита, 3 Развивающееся общество,
4 Образованное общество, 5 Общество Будущего.
Lore gives levels for some countries only (LORE_LEVEL); the rest are INVENTED (INVENTED_LEVEL, docs/lore/Invented-Lore.md), as are the modifiers (docs/lore/Contries-Description.md gives none):
research speed, building speed and recruitable population trade off against each other.
Writes: common/ideas/ktits_education.txt, localisation ru/en, history add_ideas (the idea icon is the vanilla GFX_idea_generic_research_bonus).
Also writes the specialists mechanic (education_mech.py): scripted effects, two decision categories (development, simplification), the cooperation treaty events, loc.
Usage: python tools/make_education.py [--mod PATH]
"""
import argparse, glob, re
from pathlib import Path
import lore_data as L
import education_mech as E

NL, TB = chr(10), chr(9)
LEVELS = [  # (russian, english, research_speed_factor, production_speed_buildings_factor, conscription_factor) - modifiers INVENTED
    ("Необразованное стадо", "Uneducated Herd", -0.20, -0.10, 0.10),
    ("Крестьянское образование", "Peasant Education", -0.10, -0.05, 0.05),
    ("Образованная элита", "Educated Elite", 0.0, 0.0, 0.0),
    ("Развивающееся общество", "Developing Society", 0.07, 0.05, -0.03),
    ("Образованное общество", "Educated Society", 0.15, 0.10, -0.06),
    ("Общество Будущего", "Society of the Future", 0.25, 0.15, -0.10),
]
# INVENTED lore texts of the education spirits (docs/lore/Invented-Lore.md)
EDU_TXT = [
    "Читать тут умеют единицы, и те не любят хвастаться. Знания передаются из уст в уста и по дороге успевают превратиться в слухи.",
    "Грамота есть у тех, кому не лень, а пахать и сеять учат с пелёнок. Школа - это сарай с лавкой и строгим дядькой.",
    "Образование здесь для избранных: университеты полны, а деревня по-прежнему не знает, зачем нужны буквы.",
    "Школы строят, учебники печатают, и даже в глуши кто-то уже спорит о науке. Дело движется, но не слишком быстро.",
    "Грамотны почти все, и почти все имеют мнение по любому вопросу. Науке хорошо, а работать некому: все заняты чтением.",
    "Дети здесь учатся летать мыслью, а взрослые - переучиваться. Знания растут быстрее, чем успевают придумать, куда их девать.",
]
# lore (docs/lore/Contries-Description.md): lore tag -> level
LORE_LEVEL = {"CSL": 0, "SVS": 1, "KZZ": 2, "BRT": 4, "IRK": 2, "IRR": 1, "MUS": 0, "TRV": 0, "TMR": 4, "SOY": 4, "SRK": 0}
# INVENTED (docs/lore/Contries-Description.md says TODO): from analogs and hints ("Челяба - промышленный гигант", Технодемократия -> науч. советы, ...)
INVENTED_LEVEL = {"ZLD": 4, "ADL": 4, "SVA": 5, "FDP": 3, "DMK": 2, "CLB": 3, "MGN": 0, "KTY": 2, "BLK": 4, "CEY": 1,
                  "Z01": 3, "Z02": 2, "Z03": 3, "Z04": 3, "Z05": 3}
LEVEL_OF = {**INVENTED_LEVEL, **LORE_LEVEL}

def write_bar(M):
    """science bar over the category "Образование: развитие": same scheme as the Casuality bar (make_casuality.py): 20 segments, shown by the variable ktits_spec_progress (0..100)"""
    from PIL import Image, ImageDraw
    N, SW, SH, GAP, BX = 20, 22, 14, 1, 14
    CW, CH, CG, CY, DY = 52, 44, 30, 2, 50     # stage row: cell width/height, gap (threshold text), top y; DY = shift of the old bar down
    art = M / "gfx/interface/ktits"; art.mkdir(parents=True, exist_ok=True)
    bw = N * (SW + GAP) + 6
    fr = Image.new("RGB", (bw, SH + 8), (25, 28, 36)); ImageDraw.Draw(fr).rectangle([0, 0, fr.width - 1, fr.height - 1], outline=(200, 190, 150)); fr.save(art / "edu_bar_frame.png")
    cols = [(140, 140, 140), (110, 190, 235), (50, 100, 215), (235, 190, 50)]       # quarters: grey, light blue, blue, gold
    for i, c in enumerate(cols, 1):
        im = Image.new("RGB", (SW, SH), c); ImageDraw.Draw(im).rectangle([0, 0, SW - 1, SH - 1], outline=tuple(int(v * 0.6) for v in c)); im.save(art / f"edu_seg_{i}.png")
    LCOL = [(150, 150, 150), (170, 120, 70), (110, 190, 235), (90, 200, 110), (60, 110, 225), (190, 100, 220)]   # INVENTED level colours
    GOLD, NEXTC = (235, 190, 50), (110, 115, 125)
    stage = []
    for lv in range(6):
        for st in ("passed", "cur", "next", "future"):
            fc = {"passed": LCOL[lv], "cur": GOLD, "next": NEXTC, "future": LCOL[lv]}[st]
            k = 0.4 if st == "future" else 1.0
            im = Image.new("RGB", (CW, CH), tuple(int(v * 0.3 * k) for v in LCOL[lv])); d = ImageDraw.Draw(im)
            for b in range(lv + 1):      # pictogram: stack of books, level n = n+1 columns of growing height
                bx = 6 + b * 7; d.rectangle([bx, 28 - 4 - b * 3, bx + 5, 28], fill=tuple(int(v * k) for v in LCOL[lv]))
            w = 3 if st == "cur" else 2
            for o in range(w): d.rectangle([o, o, CW - 1 - o, CH - 1 - o], outline=tuple(int(v * k) for v in fc))
            im.save(art / f"edu_stage_{lv}_{st}.png"); stage.append((f"GFX_ktits_edu_stage_{lv}_{st}", f"edu_stage_{lv}_{st}.png"))
    sprites = stage + [("GFX_ktits_edu_bar_frame", "edu_bar_frame.png")] + [(f"GFX_ktits_edu_seg_{i}", f"edu_seg_{i}.png") for i in range(1, 5)]
    (M / "interface/ktits_education.gfx").write_text("spriteTypes = {\n" + "".join(f'\tspriteType = {{\n\t\tname = "{n}"\n\t\ttexturefile = "gfx/interface/ktits/{fn}"\n\t}}\n' for n, fn in sprites) + "}\n", encoding="utf-8", newline="\n")
    (M / "common/scripted_guis").mkdir(parents=True, exist_ok=True)
    stg = ""
    for i in range(6):
        for nm, cond in (("passed", f"value = {i} compare = greater_than"), ("cur", f"value = {i} compare = equals"), ("next", f"value = {i - 1} compare = equals"),
                         ("future", f"value = {i - 1} compare = less_than")):
            stg += f"\t\t\tktits_edu_st_{nm}_{i}_visible = {{\n\t\t\t\tcheck_variable = {{ var = ktits_edu_t {cond} }}\n\t\t\t}}\n"
        stg += f"\t\t\tktits_edu_st_lbl_{i}_visible = {{\n\t\t\t\tcheck_variable = {{ var = ktits_edu_t value = {i - 1} compare = equals }}\n\t\t\t}}\n"
    (M / "common/scripted_guis/ktits_education.txt").write_text("scripted_gui = {\n\n\tktits_education_ui = {\n\t\tcontext_type = decision_category\n\t\twindow_name = \"ktits_education_ui_window\"\n\n\t\ttriggers = {\n" + "".join(
        f"\t\t\tktits_edu_seg_{i}_visible = {{\n\t\t\t\tcheck_variable = {{ var = ktits_spec_progress value = {i * 5} compare = greater_than_or_equals }}\n\t\t\t}}\n" for i in range(1, N + 1)) + stg + "\t\t}\n\t}\n}\n", encoding="utf-8", newline="\n")
    g = "guiTypes = {\n\n\tcontainerWindowType = {\n\t\tname = \"ktits_education_ui_window\"\n\t\tposition = { x = 0 y = 0 }\n\t\tsize = { width = 100% height = " + str(DY + 50) + " }\n\t\tclipping = no\n\n"
    # stage row: 6 cells x 4 state sprites (shown by triggers), thresholds between cells, "next" label
    for i in range(6):
        cx = BX + i * (CW + CG)
        for nm in ("passed", "cur", "next", "future"):
            g += f"\t\ticonType = {{\n\t\t\tname = \"ktits_edu_st_{nm}_{i}\"\n\t\t\tspriteType = \"GFX_ktits_edu_stage_{i}_{nm}\"\n\t\t\tposition = {{ x = {cx} y = {CY} }}\n\t\t\tpdx_tooltip = \"ktits_edu_stage_tt_{i}\"\n\t\t}}\n"
        g += f"\t\tinstantTextBoxType = {{\n\t\t\tname = \"ktits_edu_st_lbl_{i}\"\n\t\t\tposition = {{ x = {cx} y = {CY + 29} }}\n\t\t\tfont = \"hoi_16mbs\"\n\t\t\ttext = \"ktits_edu_stage_next\"\n\t\t\tformat = center\n\t\t\tmaxHeight = 14\n\t\t\tmaxwidth = {CW}\n\t\t}}\n"
        if i:
            g += f"\t\tinstantTextBoxType = {{\n\t\t\tname = \"ktits_edu_st_thr_{i}\"\n\t\t\tposition = {{ x = {cx - CG} y = {CY + 14} }}\n\t\t\tfont = \"hoi_16mbs\"\n\t\t\ttext = \"ktits_edu_stage_thr_{i}\"\n\t\t\tformat = center\n\t\t\tmaxHeight = 16\n\t\t\tmaxwidth = {CG}\n\t\t}}\n"
    g += "\n"
    g += f"\t\tinstantTextBoxType = {{\n\t\t\tname = \"ktits_edu_label\"\n\t\t\tposition = {{ x = {BX} y = {DY + 2} }}\n\t\t\tfont = \"hoi_16mbs\"\n\t\t\ttext = \"ktits_education_bar_label\"\n\t\t\tformat = left\n\t\t\tmaxHeight = 18\n\t\t\tmaxwidth = 470\n\t\t}}\n\n"
    g += f"\t\ticonType = {{\n\t\t\tname = \"ktits_edu_frame\"\n\t\t\tspriteType = \"GFX_ktits_edu_bar_frame\"\n\t\t\tposition = {{ x = {BX} y = {DY + 22} }}\n\t\t\tpdx_tooltip = \"ktits_education_bar_tt\"\n\t\t}}\n\n"
    for i in range(1, N + 1):
        g += f"\t\ticonType = {{\n\t\t\tname = \"ktits_edu_seg_{i}\"\n\t\t\tspriteType = \"GFX_ktits_edu_seg_{(i - 1) // 5 + 1}\"\n\t\t\tposition = {{ x = {BX + 3 + (i - 1) * (SW + GAP)} y = {DY + 25} }}\n\t\t}}\n"
    (M / "interface/ktits_education.gui").write_text(g + "\t}\n}\n", encoding="utf-8", newline="\n")
    # label: one defined_text with a full text per level (level names are constants), selected by the level variable ktits_edu_t
    th, names = E.THRESH, [n for n, *_ in LEVELS]
    dt = "defined_text = {\n\tname = GetKtitsEduBar\n"
    for i in range(6):
        dt += f"\ttext = {{\n\t\ttrigger = {{ check_variable = {{ var = ktits_edu_t value = {i} compare = equals }} }}\n\t\tlocalization_key = ktits_edu_bar_{i}\n\t}}\n"
    (M / "common/scripted_localisation").mkdir(parents=True, exist_ok=True)
    (M / "common/scripted_localisation/ktits_education_scripted_loc.txt").write_text(dt + "}\n", encoding="utf-8", newline="\n")
    bru = [("ktits_education_bar_label", "[GetKtitsEduBar]"), ("ktits_education_bar_tt", "Каждое деление - 5 % пути от порога текущего уровня образованности до порога следующего. Считаются только наши специалисты. Сразу после повышения уровня шкала пустая - путь к следующему уровню только начался.")]
    ben = [("ktits_education_bar_label", "[GetKtitsEduBar]"), ("ktits_education_bar_tt", "Each segment is 5% of the way from the threshold of the current education level to the next one. Only own specialists count.")]
    bru.append(("ktits_edu_stage_next", "далее")); ben.append(("ktits_edu_stage_next", "next"))
    pc = lambda v: "0" if round(v * 100) == 0 else f"{round(v * 100):+d}"
    for i, (n_ru, n_en, rs, pb, cf) in enumerate(LEVELS):
        if i: bru.append((f"ktits_edu_stage_thr_{i}", str(th[i]))); ben.append((f"ktits_edu_stage_thr_{i}", str(th[i])))
        bru.append((f"ktits_edu_stage_tt_{i}", f"{n_ru} - с {th[i]} тыс. наших специалистов: исследования {pc(rs)} %, строительство {pc(pb)} %, пополнение {pc(cf)} %"))
        ben.append((f"ktits_edu_stage_tt_{i}", f"{n_en} - from {th[i]} k own specialists: research {pc(rs)}%, construction {pc(pb)}%, manpower {pc(cf)}%"))
    for i in range(6):
        if i < 5:
            bru.append((f"ktits_edu_bar_{i}", f"{names[i]}: [?ktits_spec_own|0] из {th[i + 1]} тыс. до следующего уровня"))  # short: the label box is one line; no '→' glyph in the game font
            ben.append((f"ktits_edu_bar_{i}", f"Level: {LEVELS[i][1]} -> {LEVELS[i + 1][1]}. Own specialists: [?ktits_spec_own|0] of {th[i + 1]} k"))
        else:
            bru.append((f"ktits_edu_bar_{i}", f"{names[5]}: высший уровень"))
            ben.append((f"ktits_edu_bar_{i}", f"{LEVELS[5][1]}: the highest level"))
    L.write_yml(str(M / "localisation/russian/ktits_education_bar_l_russian.yml"), "russian", bru)
    L.write_yml(str(M / "localisation/english/ktits_education_bar_l_english.yml"), "english", ben)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", default=L.DEFAULT_MOD)
    a = ap.parse_args()
    M = Path(a.mod)
    info = L.load_mod(M)
    TAGS = sorted(set(info["tags"]) | set(re.findall(r'(?m)^(\w{3})\s*=\s*"countries', (M / "common/country_tags/03_ktits_splits.txt").read_text(encoding="utf-8", errors="ignore"))))

    ideas = ["ideas = {\n\tcountry = {\n"]
    for i, (_, _, rs, pb, cf) in enumerate(LEVELS):
        ideas.append(f"\t\tktits_edu_{i} = {{\n\t\t\tpicture = generic_research_bonus\n\t\t\tallowed = {{ always = no }}\n\t\t\tallowed_civil_war = {{ always = yes }}\n"
                     f"\t\t\tremoval_cost = -1\n\t\t\tmodifier = {{\n\t\t\t\tresearch_speed_factor = {rs}\n\t\t\t\tproduction_speed_buildings_factor = {pb}\n"
                     f"\t\t\t\tconscription_factor = {cf}\n\t\t\t}}\n\t\t}}\n")
    sid, _sn, _sd, sv = E.SP_WARE
    ideas.append(f"\t\t{sid} = {{\n\t\t\tpicture = generic_research_bonus\n\t\t\tallowed = {{ always = no }}\n\t\t\tallowed_civil_war = {{ always = yes }}\n"
                 f"\t\t\tremoval_cost = -1\n\t\t\tmodifier = {{\n\t\t\t\tconscription_factor = {sv}\n\t\t\t}}\n\t\t}}\n")
    for x in TAGS:   # cooperation treaty: one spirit per partner country (no modifiers: the effect is the monthly foreign specialists, ktits_edu_coop_monthly)
        ideas.append(f"\t\tktits_edu_coop_{x} = {{\n\t\t\tpicture = generic_research_bonus\n\t\t\tallowed = {{ always = no }}\n\t\t\tallowed_civil_war = {{ always = yes }}\n"
                     f"\t\t\tremoval_cost = -1\n\t\t\tmodifier = {{\n\t\t\t}}\n\t\t}}\n")
    ideas.append("\t}\n}\n")
    out = M / "common/ideas/ktits_education.txt"
    out.write_text("".join(ideas), encoding="utf-8")

    ru = [(f"ktits_edu_{i}", f"Образованность: {n_ru}") for i, (n_ru, *_) in enumerate(LEVELS)] + \
         [(f"ktits_edu_{i}_desc", EDU_TXT[i]) for i in range(len(LEVELS))]
    en = [(f"ktits_edu_{i}", f"Education: {n_en}") for i, (_, n_en, *_) in enumerate(LEVELS)] + \
         [(f"ktits_edu_{i}_desc", L.translit(EDU_TXT[i])) for i in range(len(LEVELS))]
    ru += [(f"ktits_edu_coop_{x}", f"Научное сотрудничество: [{x}.GetName]") for x in TAGS] + [(f"ktits_edu_coop_{x}_desc", E.COOP_RU) for x in TAGS]
    en += [(f"ktits_edu_coop_{x}", f"Scientific cooperation: [{x}.GetName]") for x in TAGS] + [(f"ktits_edu_coop_{x}_desc", "Our scientists and theirs write letters, go to conferences and argue until hoarse. The laboratories are open, knowledge flows across the border.") for x in TAGS]
    ru += [(k, r) for k, r, _e in E.loc_entries()]
    en += [(k, e or L.translit(r)) for k, r, e in E.loc_entries()]
    L.write_yml(str(M / "localisation/russian/ktits_education_l_russian.yml"), "russian", ru)
    L.write_yml(str(M / "localisation/english/ktits_education_l_english.yml"), "english", en)

    KAZ = {lt: tg for tg, lt in info["tag2lore"].items()}["CSL"]
    (M / "common/scripted_effects/ktits_education_effects.txt").write_text(E.effects_text(KAZ), encoding="utf-8", newline="\n")
    (M / "common/scripted_effects/ktits_education_coop_effects.txt").write_text(E.coop_effects_text(KAZ, TAGS), encoding="utf-8", newline="\n")
    (M / "common/decisions/ktits_education.txt").write_text(E.decisions_text(KAZ, TAGS), encoding="utf-8", newline="\n")
    cats = "".join(f"{c} = {{{NL}{TB}icon = generic_research{NL}{TB}picture = GFX_decision_cat_picture_soviet_national_academy_of_sciences{NL}" + (f"{TB}scripted_gui = ktits_education_ui{NL}" if c == E.CAT_DEV else "") + f"}}{NL}{NL}" for c in (E.CAT_DEV, E.CAT_SIMP))
    (M / "common/decisions/categories/ktits_education_categories.txt").write_text(cats.rstrip(NL) + NL, encoding="utf-8", newline=NL)
    (M / "events").mkdir(parents=True, exist_ok=True)
    (M / "events/ktits_education_events.txt").write_text(E.events_text(TAGS), encoding="utf-8", newline=NL)
    write_bar(M)
    done, skipped = {}, []
    for tag, lt in info["tag2lore"].items():
        lvl = LEVEL_OF.get(lt)
        files = glob.glob(str(M / "history/countries" / f"{tag} - *.txt"))
        if lvl is None or not files:
            skipped.append(lt); continue
        f = Path(files[0])
        t = f.read_text(encoding="utf-8", errors="ignore")
        t = re.sub(r"(?m)^add_ideas\s*=\s*ktits_edu_\d\s*\n?", "", t).rstrip("\n") + f"\nadd_ideas = ktits_edu_{lvl}\n"
        f.write_text(t, encoding="utf-8", newline="")
        done[lt] = lvl
    print("education set for", len(done), "countries:", {k: LEVELS[v][0] for k, v in sorted(done.items())})
    print("no level (kept without):", sorted(set(map(str, skipped))))
