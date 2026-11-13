"""Education of the population (docs/lore/Contries-Description.md "Образованность населения", 6 levels) as national spirits.

Each country gets one spirit ktits_edu_<0..5> at the start (history/countries/<TAG> - *.txt: add_ideas = ktits_edu_N).
Levels (lore scale, docs/lore/Contries-Description.md): 0 Необразованное стадо, 1 Крестьянское образование, 2 Образованная элита, 3 Развивающееся общество,
4 Образованное общество, 5 Общество Будущего.
Lore gives levels for some countries only (LORE_LEVEL); the rest are INVENTED (INVENTED_LEVEL, docs/lore/Invented-Lore.md), as are the modifiers (docs/lore/Contries-Description.md gives none):
research speed, building speed and recruitable population trade off against each other.
Writes: common/ideas/ktits_education.txt, localisation ru/en, history add_ideas (the idea icon is the vanilla GFX_idea_generic_research_bonus).
Usage: python tools/make_education.py [--mod PATH]
"""
import argparse, glob, re
from pathlib import Path
import lore_data as L

LEVELS = [  # (russian, english, research_speed_factor, production_speed_buildings_factor, conscription_factor) - modifiers INVENTED
    ("Необразованное стадо", "Uneducated Herd", -0.20, -0.10, 0.10),
    ("Крестьянское образование", "Peasant Education", -0.10, -0.05, 0.05),
    ("Образованная элита", "Educated Elite", 0.0, 0.0, 0.0),
    ("Развивающееся общество", "Developing Society", 0.07, 0.05, -0.03),
    ("Образованное общество", "Educated Society", 0.15, 0.10, -0.06),
    ("Общество Будущего", "Society of the Future", 0.25, 0.15, -0.10),
]
# lore (docs/lore/Contries-Description.md): lore tag -> level
LORE_LEVEL = {"CSL": 0, "SVS": 1, "KZZ": 2, "BRT": 4, "IRK": 2, "IRR": 1, "MUS": 0, "TRV": 0, "TMR": 4, "SOY": 4, "SRK": 0}
# INVENTED (docs/lore/Contries-Description.md says TODO): from analogs and hints ("Челяба - промышленный гигант", Технодемократия -> науч. советы, ...)
INVENTED_LEVEL = {"ZLD": 4, "ADL": 4, "SVA": 5, "FDP": 3, "DMK": 2, "CLB": 3, "MGN": 0, "KTY": 2, "BLK": 4, "CEY": 1,
                  "Z01": 3, "Z02": 2, "Z03": 3, "Z04": 3, "Z05": 3}
LEVEL_OF = {**INVENTED_LEVEL, **LORE_LEVEL}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", default=L.DEFAULT_MOD)
    a = ap.parse_args()
    M = Path(a.mod)

    ideas = ["ideas = {\n\tcountry = {\n"]
    for i, (_, _, rs, pb, cf) in enumerate(LEVELS):
        ideas.append(f"\t\tktits_edu_{i} = {{\n\t\t\tpicture = generic_research_bonus\n\t\t\tallowed = {{ always = no }}\n\t\t\tallowed_civil_war = {{ always = yes }}\n"
                     f"\t\t\tremoval_cost = -1\n\t\t\tmodifier = {{\n\t\t\t\tresearch_speed_factor = {rs}\n\t\t\t\tproduction_speed_buildings_factor = {pb}\n"
                     f"\t\t\t\tconscription_factor = {cf}\n\t\t\t}}\n\t\t}}\n")
    ideas.append("\t}\n}\n")
    out = M / "common/ideas/ktits_education.txt"
    out.write_text("".join(ideas), encoding="utf-8")

    ru = [(f"ktits_edu_{i}", f"Образованность: {n_ru}") for i, (n_ru, *_) in enumerate(LEVELS)] + \
         [(f"ktits_edu_{i}_desc", f"Уровень образованности населения (шкала из 6 уровней, docs/lore/Contries-Description.md): {n_ru}.") for i, (n_ru, *_) in enumerate(LEVELS)]
    en = [(f"ktits_edu_{i}", f"Education: {n_en}") for i, (_, n_en, *_) in enumerate(LEVELS)] + \
         [(f"ktits_edu_{i}_desc", f"Education level of the population (6-level scale): {n_en}.") for i, (_, n_en, *_) in enumerate(LEVELS)]
    L.write_yml(str(M / "localisation/russian/ktits_education_l_russian.yml"), "russian", ru)
    L.write_yml(str(M / "localisation/english/ktits_education_l_english.yml"), "english", en)

    info = L.load_mod(M)
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
