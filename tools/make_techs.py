"""Start technologies of the worked-out countries (docs/mechanics/Kazualia.md «Технологии», docs/mechanics/Soviet-Union.md section 15; rule of the author 2026-11-20).
- Kazualia (SCU): the minimum: only infantry_weapons (the exported basic_train is removed: no railways).
- Soviet Union (MAK): the technologies of the vanilla Soviet Union (history/countries/SOV - Soviet union.txt) with the conditions of the DLCs "No Step Back" and
  "Man the Guns"; added as a marked block at the end of the history file (idempotent).
Usage: python tools/make_techs.py [--mod PATH]"""
import argparse, glob, re
from pathlib import Path
import lore_data as L

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
a = ap.parse_args()
M = Path(a.mod)
BEGIN, END = "# KTITS_TECH_BEGIN (tools/make_techs.py, do not edit by hand)", "# KTITS_TECH_END"

def hist(tag): return Path(glob.glob(str(M / "history/countries" / f"{tag} - *.txt"))[0])
def tech(names): return "set_technology = {\n" + "".join(f"\t{n} = 1\n" for n in names.split()) + "}\n"

# Kazualia: the first set_technology block becomes {infantry_weapons}
f = hist("SCU"); t = f.read_text(encoding="utf-8", errors="ignore")
t2, n = re.subn(r"set_technology\s*=\s*\{[^}]*\}", "set_technology = {\n\tinfantry_weapons = 1\n}", t, count=1)
assert n == 1
f.write_text(t2, encoding="utf-8", newline="")

LAND = "infantry_weapons infantry_weapons1 tech_recon tech_support tech_engineers tech_military_police tech_mountaineers tech_trucks motorised_infantry paratroopers gw_artillery interwar_antiair fuel_silos fuel_refining basic_train armored_car1 synth_oil_experiments"
ARMOR_OLD = "gwtank basic_light_tank"
ARMOR_NSB = "gwtank_chassis basic_light_tank_chassis improved_light_tank_chassis engine_tech_1 engine_tech_2"
AIR_OLD = "early_fighter fighter1 early_bomber strategic_bomber1 naval_bomber1 early_transport_plane CAS1 tactical_bomber1"
AIR_NSB = "iw_small_airframe iw_medium_airframe iw_large_airframe basic_small_airframe basic_medium_airframe basic_large_airframe aircraft_construction engines_1 engines_2 aa_lmg aa_cannon_1 early_bombs air_torpedoe_1 bba_early_transport_plane"
NAVY_OLD = "early_submarine basic_submarine early_destroyer early_light_cruiser early_heavy_cruiser early_battleship early_battlecruiser transport"
NAVY_MTG = "basic_naval_mines submarine_mine_laying early_ship_hull_light basic_ship_hull_light early_ship_hull_submarine basic_ship_hull_submarine early_ship_hull_cruiser basic_ship_hull_cruiser early_ship_hull_heavy basic_battery basic_light_battery basic_torpedo basic_depth_charges mtg_transport"
def cond(dlc, yes, names):
    lim = f'has_dlc = "{dlc}"' if yes else f'NOT = {{ has_dlc = "{dlc}" }}'
    return f"if = {{\n\tlimit = {{ {lim} }}\n" + "".join("\t" + l + "\n" for l in tech(names).rstrip("\n").split("\n")) + "}\n"
block = BEGIN + "\n" + tech(LAND) + cond("No Step Back", False, ARMOR_OLD + " " + AIR_OLD) + cond("No Step Back", True, ARMOR_NSB + " " + AIR_NSB) + cond("Man the Guns", False, NAVY_OLD) + cond("Man the Guns", True, NAVY_MTG) + END + "\n"
f = hist("MAK"); t = f.read_text(encoding="utf-8", errors="ignore").replace("\r\n", "\n")
t = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", "", t, flags=re.S)
f.write_text(t.rstrip("\n") + "\n\n" + block, encoding="utf-8", newline="")
print("techs: Kazualia = infantry_weapons only; Soviet Union = vanilla set (" + str(len((LAND + ARMOR_OLD + AIR_OLD + ARMOR_NSB + AIR_NSB + NAVY_OLD + NAVY_MTG).split())) + " techs in 5 blocks)")
