"""Put the lore rulers (docs/01 "Изначальный правитель") into the mod.

Per lore country with a named ruler: in common/characters/<TAG>.txt the leader of the ruling ideology group gets the
lore name; if the lore names an ideology group, that group becomes ruling_party in history/countries and its popularity
is swapped with the previous ruling group's (so the lore ruler really rules). Lore sub-ideologies that do not exist in
vanilla (Технодемократия, Меритократия, Интегрализм, Технократия, Степной ханизм, Казуальность) are mapped to a vanilla
sub-ideology of the same group as a PLACEHOLDER (listed in the report) until custom ideologies are made.
Countries whose ruler is TODO / absent in docs/01 keep the leaders RandomParadox made and are listed.
Backups: no_commit/temp/backup_rulers/. Usage: python tools/make_rulers.py [--mod PATH]
"""
import argparse, csv, glob, re, shutil
from pathlib import Path
import lore_data as L
import invented_lore as INV
import ideologies_data as IDEO

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
a = ap.parse_args()
M = Path(a.mod)

GROUP = {  # vanilla 1.19 sub-ideologies, from common/ideologies/00_ideologies.txt
    "democratic": ["conservatism", "liberalism", "socialism", "populism"],
    "communism": ["marxism", "leninism", "stalinism", "anti_revisionism", "anarchist_communism", "buddhist_socialism"],
    "fascism": ["nazism", "gen_nazism", "fascism_ideology", "falangism", "rexism", "emperor_fascism"],
    "neutrality": ["despotism", "oligarchism", "anarchism", "moderatism", "centrism", "japan_militarism_ideology"],
}
for _g, _v in IDEO.CUSTOM_SUBTYPES.items():
    GROUP[_g] = GROUP.get(_g, []) + [t for t in _v if t not in GROUP.get(_g, [])]
SUB2GROUP = {s: g for g, v in GROUP.items() for s in v}

# docs/01: lore tag -> (name exactly as written, ideology group or None, lore ideology text, vanilla placeholder sub or None)
RULERS = {
    "CSL": ("Священный-Архо-Казуал", "casuality", "Казуальность (привязка придумана, docs/13)", "casuality_ideology"),
    "SVS": ("Генсек Ваня Пименов", "communism", "Коммунизм (вывод из docs/01: Советский Союз)", "leninism"),
    "KZZ": ("Атаман Даша Юзеева", "neutrality", "атаманская власть (придумано: в docs/01 идеология не названа)", "oligarchism"),
    "BRT": ("Джон Бульдог", None, "", None),
    "TMR": ("Ахтямов Камиль", "fascism", "фашизм (docs/01: «распространяет влияние фашизма»)", "fascism_ideology"),
    "SOY": ("Ефимов Александр", "democratic", "Соевая Демократия (вывод из docs/01: соевые либералы)", "liberalism"),
    "ZLD": ("Сабирова Альфия Расилевна", "democratic", "Социал-демократия", "socialism"),
    "ADL": ("Айдов Матвей", "democratic", "Центристский консерватизм", "conservatism"),
    "SVA": ("Арифуллин Саид Аскарович", "democratic", "Технодемократия", "technodemocracy"),
    "FDP": ("Багаутдинов Булат Рамилевич", "neutrality", "Меритократия", "meritocracy"),
    "DMK": ("Сидоров Дмитрий Рустамович", "fascism", "Интегрализм", "integralism"),
    "CLB": ("Иванов Константин Алексеевич", "neutrality", "Технократия", "technocracy"),
    "SRK": ("Хан Тимур Алпамысович Сарайский", "neutrality", "Степной ханизм", "steppe_khanate"),
}
LORE_ONLY = set(RULERS)
RULERS = {**INV.INVENTED_RULERS, **RULERS}      # lore wins; INVENTED_RULERS fill the TODO gaps (docs/12)
PLACEHOLDER = {"TMR": False, "ZLD": False, "ADL": False}

BK = L.REPO / "no_commit/temp/backup_rulers"
BK.mkdir(parents=True, exist_ok=True)
def backup(p):
    p = Path(p)
    if not (BK / p.name).exists():
        shutil.copy2(p, BK / p.name)

def blocks(text):
    """top-level character blocks inside 'characters = { ... }': list of (id, start, end)"""
    out, depth, i, start, cid = [], 0, 0, None, None
    first = text.index("{")
    i = first + 1; depth = 1
    while i < len(text) and depth > 0:
        c = text[i]
        if c == "{":
            if depth == 1:
                m = re.search(r"(\w+)\s*=\s*$", text[:i]); cid = m.group(1); start = text.rfind(cid, 0, i)
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 1: out.append((cid, start, i + 1))
        i += 1
    return out

info = L.load_mod(M)
lore2tag = {}
for tag, lt in info["tag2lore"].items():
    lore2tag[lt] = tag
rows, missing = [], []
for lt, (name, grp, lore_ideo, sub) in RULERS.items():
    tag = lore2tag.get(lt)
    if not tag:
        missing.append(lt); continue
    hist = glob.glob(str(M / "history/countries" / f"{tag} - *.txt"))
    chf = M / "common/characters" / f"{tag}.txt"
    if not hist or not chf.exists():
        missing.append(lt); continue
    hf = Path(hist[0]); backup(hf); backup(chf)
    ht = hf.read_text(encoding="utf-8", errors="ignore")
    bt = (BK / hf.name).read_text(encoding="utf-8", errors="ignore")     # idempotent: start from the exported ruling party and popularities
    for pat in (r"ruling_party\s*=\s*\w+", r"set_popularities\s*=\s*\{[^}]*\}"):
        ht = re.sub(pat, lambda mm, v=re.search(pat, bt).group(0): v, ht, count=1)
    rp = re.search(r"ruling_party\s*=\s*(\w+)", ht).group(1)
    target = grp or rp
    ct = (BK / chf.name).read_text(encoding="utf-8", errors="ignore")       # idempotent: characters start from the exported file
    done = ""
    for cid, s, e in blocks(ct):
        blk = ct[s:e]
        m = re.search(r"country_leader\s*=\s*\{[^}]*?ideology\s*=\s*(\w+)", blk, re.S)
        if not m or SUB2GROUP.get(m.group(1)) != target: continue
        nb = re.sub(r'name\s*=\s*"[^"]*"', f'name="{name}"', blk, count=1)
        if sub and SUB2GROUP.get(sub) == target:
            nb = re.sub(r"(country_leader\s*=\s*\{[^}]*?ideology\s*=\s*)\w+", lambda mm: mm.group(1) + sub, nb, count=1, flags=re.S)
        ct = ct[:s] + nb + ct[e:]
        done = cid
        break
    if not done and target in IDEO.NEW_GROUPS:
        cid = f"{tag}_{target}_leader"
        blk = "\t" + cid + "={\n\t\tname=\"" + name + "\"\n\n\t\tcountry_leader={\n\t\t\tideology=" + sub + "\n\t\t\ttraits = { }\n\t\t\texpire=\"1965.1.1.1\"\n\t\t\tid=-1\n\t\t}\n\n\t}\n"
        if cid not in ct:
            k = ct.rindex("}")
            ct = ct[:k] + blk + ct[k:]
        done = cid
    chf.write_text(ct, encoding="utf-8", newline="")
    ruling_note = f"ruling_party {rp}"
    if grp and grp != rp:
        ht = re.sub(r"ruling_party\s*=\s*\w+", f"ruling_party = {grp}", ht, count=1)
        pops = {g: int(v) for g, v in re.findall(r"(\w+)\s*=\s*(\d+)", re.search(r"set_popularities\s*=\s*\{([^}]*)\}", ht).group(1))}
        pops[grp], pops[rp] = pops.get(rp, 0), pops.get(grp, 0)
        newblk = "set_popularities = {\n" + "".join(f"\t{g} = {pops[g]}\n" for g in IDEO.GROUP_ORDER if g in pops and (pops[g] or g in ("democratic", "fascism", "communism", "neutrality"))) + "}"
        ht = re.sub(r"set_popularities\s*=\s*\{[^}]*\}", newblk, ht, count=1)
        hf.write_text(ht, encoding="utf-8", newline="")
        ruling_note = f"ruling_party {rp} -> {grp}"
    rows.append((tag, lt, name, target, lore_ideo, sub or "", ("INVENTED " if lt in INV.INVENTED_RULERS and lt not in LORE_ONLY else "") + ("placeholder sub-ideology" if PLACEHOLDER.get(lt) else ""), done, ruling_note))

rep = L.REPO / "no_commit/temp/rulers_report.csv"
with open(rep, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["mod_tag", "lore_tag", "ruler", "group", "lore_ideology", "vanilla_sub", "note", "character_id", "ruling_party"])
    w.writerows(rows)
have = {r[1] for r in rows}
print(f"rulers set: {len(rows)}; character not found for: {[r[1] for r in rows if not r[7]]}; tags missing: {missing}")
print("no ruler in docs/01 (kept as exported):", sorted(set(info['tag2lore'].values()) - have))
print("report:", rep)
