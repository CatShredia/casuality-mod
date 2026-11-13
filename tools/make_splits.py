"""Splittable states for big countries (> 15 states): INVENTED names, see docs/15-Splits.md.

For each big country (SPLITS) its states are divided into contiguous parts (region growing over state adjacency, parent keeps the part with
its capital). Each other part becomes a new country K01..K35 (tags file 03_ktits_splits.txt, country file, colour, flag copied from the parent,
history without states, neutral ruler, localisation). Manual release is BLOCKED: effects ktits_release_Kxx are guarded by ktits_splits_enabled (= the country fell into casuality), so only
ktits_split_on_fall (called by the fall event of make_casuality.py) releases the parts, makes them casuality countries and puppets of Kazualia.
Writes: common/country_tags/03_ktits_splits.txt, common/countries/Kxx.txt, history/countries/Kxx - *.txt, common/characters/Kxx.txt,
common/scripted_triggers/ktits_splits_triggers.txt, common/scripted_effects/ktits_splits_effects.txt, gfx/flags copies, localisation,
and no_commit/temp/splits_report.csv (+ docs table printed).
Usage: python tools/make_splits.py [--mod PATH]
"""
import argparse, colorsys, math, re, shutil
from pathlib import Path
import lore_data as L

# parent tag -> [(russian name, english name)]  INVENTED
SPLITS = {
    "MAK": ["Белорубежье", "Заозёрная Республика", "Урало-Сибирская Республика", "Северо-Полярный Край", "Степная Федерация", "Приморье-Тихоокеанск"],
    "CHE": ["Фигарийская Лига", "Вертоградия", "Нижнее Фигарье", "Горный Кантон", "Приморская Коммуна"],
    "WRM": ["Бобовая Автономия", "Северный Соевый Союз", "Тофу-Республика", "Миндальный Берег"],
    "AHA": ["Западная Палата", "Ледяной Совет", "Приречная Курия", "Восточное Собрание"],
    "AFR": ["Южный Кытай", "Чайная Империя", "Нефритовое Ханство", "Шёлковый Предел"],
    "FAR": ["Луговая Республика", "Клеверный Союз", "Полынный Край"],
    "GHI": ["Северный Тямов", "Герцогство Тямов-Ост"],
    "FIU": ["Княжество Заречное", "Дмитровская Марка"],
    "MLN": ["Ирракская Зона", "Эмират Южный Ирр"],
    "TEZ": ["Северный Бриттан"],
    "EAG": ["Каталадия"],
    "AJA": ["Верхняя Муси"],
}
GROUPS = ("fascism", "communism", "neutrality", "democratic", "casuality", "theology")


def adjacency_states(M, states):
    prov_state = {p: sid for sid, s in states.items() for p in s["provs"]}
    adj = {sid: set() for sid in states}
    for a, b in L.province_adjacency(M):
        sa, sb = prov_state.get(a), prov_state.get(b)
        if sa and sb and sa != sb:
            adj[sa].add(sb); adj[sb].add(sa)
    return adj


def partition_from(own, adj, cen, capital, k, first):
    """own: set of state ids; returns k+1 lists (index 0 = parent part with the capital)"""
    seeds = [capital] + ([first] if first != capital else [])
    while len(seeds) < k + 1:      # farthest point sampling
        best = max((s for s in own if s not in seeds), key=lambda s: min(math.dist(cen[s], cen[q]) for q in seeds))
        seeds.append(best)
    parts = [[s] for s in seeds]
    taken = set(seeds)
    while len(taken) < len(own):
        order = sorted(range(k + 1), key=lambda i: len(parts[i]))
        grew = False
        for i in order:
            cand = {n for s in parts[i] for n in adj[s] if n in own and n not in taken}
            if cand:
                c = min(cand, key=lambda n: min(math.dist(cen[n], cen[s]) for s in parts[i]))
                parts[i].append(c); taken.add(c); grew = True
                break
        if not grew:                # disconnected leftovers: nearest part
            rest = [s for s in own if s not in taken]
            s = rest[0]
            i = min(range(k + 1), key=lambda i: min(math.dist(cen[s], cen[q]) for q in parts[i]))
            parts[i].append(s); taken.add(s)
    return parts


def partition(own, adj, cen, capital, k):
    """best of several starting seeds: smallest spread of part sizes"""
    best = None
    for first in sorted(own):
        pp = partition_from(own, adj, cen, capital, k, first)
        sc = max(map(len, pp)) - min(map(len, pp))
        if best is None or sc < best[0]: best = (sc, pp)
    return best[1]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", default=L.DEFAULT_MOD)
    a = ap.parse_args()
    M = Path(a.mod)
    info = L.load_mod(M)
    states = info["states"]
    adj = adjacency_states(M, states)
    pc, _ = L.province_centroids(M)
    cen = {sid: (sum(pc[p][0] for p in s["provs"]) / len(s["provs"]), sum(pc[p][1] for p in s["provs"]) / len(s["provs"]))
           for sid, s in states.items() if s["provs"]}
    tags = info["tags"]

    # original (unsplit) ownership comes from history/states, which this script never modifies
    entries, rows = [], []
    n = 0
    for parent, names in SPLITS.items():
        own = {sid for sid, s in states.items() if s["owner"] == parent and sid in cen}
        lt = info["tag2lore"].get(parent)
        capital = info["capital_state"].get(lt) if info["capital_state"].get(lt) in own else max(own, key=lambda s: states[s]["manpower"])
        parts = partition(own, adj, cen, capital, len(names))
        pfile = tags[parent]
        ptxt = (M / "common/countries" / (pfile + ".txt")).read_text(encoding="utf-8", errors="ignore")
        pcol = tuple(map(int, re.search(r"color\s*=\s*\{\s*(\d+)\s+(\d+)\s+(\d+)", ptxt).groups()))
        gc = re.findall(r"(graphical_culture\w*\s*=\s*\w+)", ptxt)
        h, s_, v = colorsys.rgb_to_hsv(*(c / 255 for c in pcol))
        rows.append((parent, lt or "?", info["country_ru"].get(lt, ""), "(остаётся)", len(parts[0]), ""))
        for i, nm in enumerate(names):
            n += 1
            tag = f"K{n:02d}"
            sts = sorted(parts[i + 1])
            cap = max(sts, key=lambda s: (sum(x[1] for x in states[s]["vps"]), states[s]["manpower"]))
            col = tuple(round(c * 255) for c in colorsys.hsv_to_rgb((h + 0.07 * (i + 1)) % 1, min(1, s_ * 0.9 + 0.1), max(0.35, v * (0.85 if i % 2 else 1.0))))
            entries.append((tag, parent, nm, sts, cap, col, gc))
            rows.append((tag, "", nm, parent, len(sts), " ".join(map(str, sts))))

    for tag, parent, nm, sts, cap, col, gc in entries:
        fname = tag
        (M / "common/countries" / f"{fname}.txt").write_text("\n".join(gc) + f"\n\ncolor = {{ {col[0]} {col[1]} {col[2]} }}\n", encoding="utf-8")
        hist = (M / "history/countries" / f"{tag} - {L.translit(nm).replace(' ', '_')}.txt")
        hist.write_text(
            f"capital = {cap}\n\nset_politics = {{\n\truling_party = neutrality\n\tlast_election = \"1936.1.1\"\n\telection_frequency = 48\n\telections_allowed = no\n}}\n"
            "set_popularities = {\n\tdemocratic = 0\n\tfascism = 0\n\tcommunism = 0\n\tneutrality = 100\n\tcasuality = 0\n\ttheology = 0\n}\n\n"
            f"recruit_character = {tag}_leader\n", encoding="utf-8", newline="\n")
        leader = ("\t{t}_leader = {{\n\t\tname = \"Правитель {n}\"\n\t\tcountry_leader = {{\n\t\t\tideology = oligarchism\n\t\t\ttraits = {{ }}\n\t\t\texpire = \"1965.1.1.1\"\n\t\t\tid = -1\n\t\t}}\n\t}}\n"
                  "\t{t}_casuality_leader = {{\n\t\tname = \"Казуал-Предводитель\"\n\t\tcountry_leader = {{\n\t\t\tideology = casuality_ideology\n\t\t\ttraits = {{ }}\n\t\t\texpire = \"1965.1.1.1\"\n\t\t\tid = -1\n\t\t}}\n\t}}\n").format(t=tag, n=nm)
        (M / "common/characters" / f"{tag}.txt").write_text("characters = {\n" + leader + "}\n", encoding="utf-8-sig")
        for d in ("gfx/flags", "gfx/flags/medium", "gfx/flags/small"):
            for f in (M / d).glob(f"{parent}*.tga"):
                shutil.copy2(f, M / d / f.name.replace(parent, tag, 1))

    # national territory: the new country gets a core on each state of its part (owner stays the parent; idempotent)
    cores = {sid: tag for tag, _p, _n, sts, *_ in entries for sid in sts}
    for sid, st in states.items():
        f = Path(st["file"]); t = f.read_text(encoding="utf-8", errors="ignore")
        t2 = re.sub(r"(?m)^[ \t]*add_core_of\s*=\s*K\d\d[ \t]*\r?\n", "", t)
        if sid in cores:
            t2, k = re.subn(r"(?m)^([ \t]*)owner\s*=\s*\w+[ \t]*\r?\n", lambda m: m.group(0) + m.group(1) + "add_core_of = " + cores[sid] + "\n", t2, count=1)
            assert k == 1, f
        if t2 != t: f.write_text(t2, encoding="utf-8", newline="")

    (M / "common/country_tags/03_ktits_splits.txt").write_text("".join(f'{t} = "countries/{t}.txt"\n' for t, *_ in entries), encoding="utf-8")
    (M / "common/scripted_triggers/ktits_splits_triggers.txt").write_text(
        "# release of the parts of a big country is allowed only for a country that has fallen into casuality (the manual release mechanic is blocked)\nktits_splits_enabled = {\n\thas_country_flag = ktits_casuality_fallen\n}\n", encoding="utf-8")
    KAZ = {v: k for k, v in info["tag2lore"].items()}["CSL"]
    eff = ""
    for t, p, nm, sts, *_ in entries:
        moves = "".join("\t\tif = {\n\t\t\tlimit = { %d = { is_owned_by = ROOT } }\n\t\t\t%s = { transfer_state = %d }\n\t\t}\n" % (x, t, x) for x in sts)
        eff += ("ktits_release_%s = {\n\tif = {\n\t\tlimit = { ktits_splits_enabled = yes }\n%s"
                "\t\tif = {\n\t\t\tlimit = { country_exists = %s }\n\t\t\t%s = {\n\t\t\t\tset_country_flag = ktits_casuality_fallen\n\t\t\t\tset_variable = { var = ktits_casuality value = 100 }\n"
                "\t\t\t\tset_politics = { ruling_party = casuality }\n\t\t\t\tadd_popularity = { ideology = casuality popularity = 0.5 }\n\t\t\t}\n"
                "\t\t\tif = {\n\t\t\t\tlimit = { country_exists = %s }\n\t\t\t\t%s = { puppet = %s }\n\t\t\t}\n\t\t}\n\t}\n}\n\n") % (t, moves, t, t, KAZ, KAZ, t)
    by_parent = {}
    for t, p, *_ in entries: by_parent.setdefault(p, []).append(t)
    eff += ("# called by the fall event ktits_casuality.1: every part of the fallen big country is released and becomes a puppet of Kazualia\nktits_split_on_fall = {\n" +
            "".join("\tif = {\n\t\tlimit = { original_tag = %s }\n%s\t}\n" % (p, "".join("\t\tktits_release_%s = yes\n" % t for t in ts)) for p, ts in by_parent.items()) + "}\n")
    (M / "common/scripted_effects/ktits_splits_effects.txt").write_text(eff, encoding="utf-8")

    for lang, conv in (("russian", lambda s: s), ("english", L.translit)):
        ent = []
        for tag, parent, nm, *_ in entries:
            for g in GROUPS:
                for suf in ("", "_DEF", "_ADJ"):
                    ent.append((f"{tag}_{g}{suf}", conv(nm)))
            ent += [(tag, conv(nm)), (f"{tag}_DEF", conv(nm)), (f"{tag}_ADJ", conv(nm))]
        L.write_yml(str(M / f"localisation/{lang}/ktits_splits_l_{lang}.yml"), lang, ent)

    import csv
    rep = L.REPO / "no_commit/temp/splits_report.csv"
    with open(rep, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";"); w.writerow(["tag", "lore", "name", "parent", "states", "state ids"]); w.writerows(rows)
    print(f"{len(entries)} split countries; report {rep}")
    for r in rows:
        if r[3] == "(остаётся)": print(f"  {r[0]} {r[2]}: stays with {r[4]} states")
        else: print(f"    {r[0]} {r[2]} <- {r[3]}: {r[4]} states")
