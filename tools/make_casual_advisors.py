"""Kazualia: casuality advisors (political_advisor slot, trait with casuality_drift) and lore descriptions of the three rulers (author's request).
All names, traits and texts are INVENTED (docs/lore/Invented-Lore.md). Idempotent: advisors are added to common/characters/SCU.txt only once,
the trait file and the localisation files are overwritten. [uncertain: `casuality_drift` is the generated <group>_drift modifier of the own ideology group;
`<character id>_desc` for a country leader may not be shown by the game]
Usage: python tools/make_casual_advisors.py [--mod PATH]"""
import argparse, glob, re
from pathlib import Path
import lore_data as L

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
a = ap.parse_args()
M = Path(a.mod)

# trait -> (drift, extra modifiers, ru name, en name, ru desc of the trait is not needed)
TRAITS = {
    "ktits_casual_preacher": (0.15, "political_power_factor = -0.05", "Болотный проповедник", "Swamp Preacher"),
    "ktits_casual_dreamer": (0.10, "stability_factor = 0.05", "Мастер дрёмы", "Master of Dozing"),
    "ktits_casual_hammock": (0.20, "political_power_factor = -0.10", "Идеолог гамака", "Hammock Ideologue"),
}
# id, name, trait, portrait, ru desc, en desc
ADVISORS = [
    ("SCU_Adv_Dremin", "Дрёмин Тихонович", "ktits_casual_preacher", "GFX_Portrait_Arabia_Generic_1_small",
     "Ходит по сёлам в болотном плаще и рассказывает, что спешить некуда: всё, что нужно, придёт само. Слушатели соглашаются и ложатся.",
     "Walks the villages in a swamp cloak and tells people there is no hurry: whatever is needed will come by itself. The listeners agree and lie down."),
    ("SCU_Adv_Tina", "Тина Болотная", "ktits_casual_dreamer", "GFX_Portrait_Arabia_Generic_2_small",
     "Бывший счетовод. Считает, что любую ведомость можно сдать вовремя, если вовремя заснуть над ней: к утру цифры сходятся сами.",
     "A former bookkeeper. She holds that any ledger can be handed in on time if you fall asleep over it in time: by morning the numbers add up by themselves."),
    ("SCU_Adv_Gamak", "Гамак Иваныч", "ktits_casual_hammock", "GFX_Portrait_Arabia_Generic_3_small",
     "Написал трактат «О пользе лёжа», дочитал до второй страницы и заснул. Трактат пользуется огромным успехом именно из-за незаконченности.",
     "Wrote the treatise \"On the Use of Lying Down\", got to the second page and fell asleep. The treatise is hugely popular precisely because it is unfinished."),
]
# lore descriptions of the rulers of Kazualia (character id -> ru, en)
RULERS = {
    "SCU_casuality_leader": (
        "Тридцать лет на троне, из них двадцать девять с закрытыми глазами. Подписывает указы во сне, и ни один пока не отменили: их никто не читал. Верит, что должное случится само, а всё остальное суета.",
        "Thirty years on the throne, twenty-nine of them with his eyes closed. He signs decrees in his sleep and none has been repealed yet: nobody read them. He believes what must happen will happen by itself and everything else is bustle."),
    "SCU_Sabirov": (
        "Приехал из Ванеграда с папкой и пятилетним планом, лёг в гамак «прочитать план» и проснулся к обеду. Строит коммунизм по нормам отдыха: сперва выспаться, потом пятилетка.",
        "Came from Vanegrad with a folder and a five-year plan, lay in a hammock to \"read the plan\" and woke up at noon. He builds communism by the norms of rest: first sleep, then the five-year plan."),
    "SCU_Bulldog_Kazual": (
        "Носит бриттанский котелок набекрень и ходит с зонтиком по камышам. Парламент у него заседает в беседке, а голосуют кивком: кто задремал, тот «за».",
        "Wears a Brittanian bowler hat askew and walks the reeds with an umbrella. His parliament sits in a gazebo and votes by nodding: whoever dozes off is \"in favour\"."),
}

# personal traits of the rulers (the game shows no description of a leader, only the name and the traits: the lore text goes to the trait)
RULER_TRAITS = {"SCU_casuality_leader": ("ktits_ruler_archo", "Спящий на троне", "Asleep on the Throne", "stability_factor = 0.05"),
                "SCU_Sabirov": ("ktits_ruler_sabirov", "Нормы отдыха", "Norms of Rest", "political_power_factor = 0.05"),
                "SCU_Bulldog_Kazual": ("ktits_ruler_bulldog", "Парламент в беседке", "Parliament in a Gazebo", "political_power_factor = 0.05")}
# trait file
t = "leader_traits = {\n" + "".join(f"\t{k} = {{\n\t\trandom = no\n\t\tcasuality_drift = {d}\n\t\t{mod}\n\t}}\n\n" for k, (d, mod, _, _) in TRAITS.items())
t += "".join(f"\t{k} = {{\n\t\trandom = no\n\t\t{mod}\n\t}}\n\n" for k, _, _, mod in RULER_TRAITS.values()) + "}\n"
(M / "common/country_leader").mkdir(parents=True, exist_ok=True)
(M / "common/country_leader/ktits_casuality_traits.txt").write_text(t, encoding="utf-8", newline="\n")

# characters
chf = M / "common/characters/SCU.txt"; hist = glob.glob(str(M / "history/countries/SCU - *.txt"))
if not chf.exists() or not hist: raise SystemExit("make_casual_advisors: no SCU files")
ct = chf.read_text(encoding="utf-8"); ht = Path(hist[0]).read_text(encoding="utf-8", errors="ignore"); nadd = 0
for cid, nm, tr, pic, _, _ in ADVISORS:
    if cid not in ct:
        blk = (f"\t{cid}={{\n\t\tname=\"{nm}\"\n\n\t\tadvisor={{\n\t\t\tslot = political_advisor\n\t\t\tidea_token = {cid}\n"
               f"\t\t\tavailable = {{ has_government = casuality }}\n\t\t\ttraits = {{ {tr} }}\n\t\t}}\n\t\tportraits = {{\n\t\t\tcivilian = {{\n\t\t\t\tsmall = {pic}\n\t\t\t}}\n\t\t}}\n\t}}\n")
        k = ct.rindex("}"); ct = ct[:k] + blk + ct[k:]; nadd += 1
    if not re.search(r"^\s*recruit_character\s*=\s*" + cid + r"\s*$", ht, re.M):
        ht = re.sub(r"^(recruit_character[^\n]*)$", lambda m: m.group(1) + "\nrecruit_character = " + cid, ht, count=1, flags=re.M)
for cid, (tk, _, _, _) in RULER_TRAITS.items():   # the ruler blocks: traits = { } -> the personal trait
    ct = re.sub(r"(\t" + cid + r"=\{.*?country_leader=\{.*?traits = \{)[^}]*(\})", lambda m: m.group(1) + " " + tk + " " + m.group(2), ct, count=1, flags=re.S)
chf.write_text(ct, encoding="utf-8", newline=""); Path(hist[0]).write_text(ht, encoding="utf-8", newline="")

# localisation (UTF-8 BOM)
def loc(lang, idx):
    rows = [f"l_{lang}:"]
    for k, v in TRAITS.items(): rows.append(f' {k}:0 "{v[2 + idx]}"')
    for cid, nm, _, _, rd, ed in ADVISORS: rows.append(f' {cid}:0 "{nm}"'); rows.append(f' {cid}_desc:0 "{(rd, ed)[idx]}"')
    for cid, (rd, ed) in RULERS.items():
        tk, tr, te, _ = RULER_TRAITS[cid]
        rows.append(f' {cid}_desc:0 "{(rd, ed)[idx]}"'); rows.append(f' {tk}:0 "{(tr, te)[idx]}"'); rows.append(f' {tk}_desc:0 "{(rd, ed)[idx]}"')
    return "\n".join(rows) + "\n"
for lang, idx in (("russian", 0), ("english", 1)):
    p = M / f"localisation/{lang}/ktits_casual_advisors_l_{lang}.yml"; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(loc(lang, idx), encoding="utf-8-sig", newline="\n")
print(f"casual advisors: {nadd} new in SCU.txt ({len(ADVISORS)} total), {len(TRAITS)} traits, {len(RULERS)} ruler descriptions")
