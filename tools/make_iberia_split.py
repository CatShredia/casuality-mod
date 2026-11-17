"""Split the eastern landmass off the old Iberadia (Z05, mod tag EAG) into a new country Z06 "Арагония" (mod tag ARA).

The map was exported by RandomParadox with ONE country on both landmasses (the western peninsula south of the Soy Republic and the eastern part
next to the Tyamov Reich and the Federation of Deputies). The author wants two countries, so this step builds the new tag AFTER the export, exactly as
RandomParadox would have made it: tag, country file, colour, flag, history (copy of the exported one), oob (divisions split by location), characters,
names, portraits, localisation, ownership and cores of the eastern states. Everything else (names, rulers, population, education, Casuality, alliances)
is made by the usual steps for this tag, because the colour of the new country is in tools/rp_input/stage_04/countryMappings.txt (lore tag Z06).
The data (name, tag, colour) is invented_lore.SPLIT_OFF. Idempotent: the exported files of the parent are saved to no_commit/temp/backup_iberia on
the first run (and again whenever the tag file of the mod does not yet contain the new tag = a fresh export).
If a fresh RandomParadox export was made from the updated inputs (Z06 colour on the map), the tag with the Z06 colour already exists and nothing is built.
Usage: python tools/make_iberia_split.py [--mod PATH]
"""
import argparse, re, shutil
from pathlib import Path
import lore_data as L
import invented_lore as INV
from make_splits import adjacency_states

S = INV.SPLIT_OFF
TAG, PARENT_LORE, COLOR, FNAME = S["tag"], S["parent_lore"], S["color"], S["file"]
NAME = INV.INVENTED_COUNTRIES[S["lore"]]["name"]
BK = L.REPO / "no_commit/temp/backup_iberia"


def rd(p):
    raw = Path(p).read_bytes()
    return raw.decode("utf-8-sig"), raw.startswith(b"\xef\xbb\xbf")


def wr(p, text, bom=False):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_bytes((b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", default=L.DEFAULT_MOD)
    a = ap.parse_args()
    M = Path(a.mod)
    info = L.load_mod(M)
    lore2tag = {lt: t for t, lt in info["tag2lore"].items()}
    parent = lore2tag.get(PARENT_LORE)
    assert parent, "the tag of the old Iberadia is not found (colour of Z05)"
    if lore2tag.get(S["lore"]) not in (None, TAG):
        print(f"iberia: the export already has a country with the colour of {S['lore']}: {lore2tag[S['lore']]}; nothing to build")
        return
    states = info["states"]
    adj = adjacency_states(M, states)
    pc, _ = L.province_centroids(M)
    own = {sid for sid, s in states.items() if s["owner"] in (parent, TAG)}
    # connected landmasses of the old country; the eastern one (bigger mean x of the province centroids) becomes the new country
    comps, seen = [], set()
    for s0 in sorted(own):
        if s0 in seen: continue
        comp, todo = set(), [s0]
        while todo:
            x = todo.pop()
            if x in comp: continue
            comp.add(x); todo += [n for n in adj[x] if n in own and n not in comp]
        seen |= comp; comps.append(comp)
    assert len(comps) == 2, f"expected two landmasses, found {len(comps)}: {[sorted(c) for c in comps]}"
    mx = lambda c: sum(pc[p][0] for sid in c for p in states[sid]["provs"]) / sum(len(states[sid]["provs"]) for sid in c)
    east, west = sorted(comps, key=mx, reverse=True)
    east_provs = {p for sid in east for p in states[sid]["provs"]}
    print(f"iberia: {parent} -> west {sorted(west)}; {TAG} <- east {sorted(east)}")

    tags_f = M / "common/country_tags/02_countries.txt"
    ttxt, tbom = rd(tags_f)
    fresh = f'{TAG} = "countries/{FNAME}.txt"' not in ttxt
    BK.mkdir(parents=True, exist_ok=True)
    pfile = info["tags"][parent]
    save = [f"history/countries/{parent} - {pfile.replace('Eagh', 'Eagh')}.txt"]
    hist_p = next((M / "history/countries").glob(f"{parent} - *.txt"))
    srcs = [hist_p, M / f"common/characters/{parent}.txt", *sorted((M / "history/units").glob(f"{parent}_1936*.txt")),
            M / f"common/countries/{pfile}.txt"]
    for f in srcs:
        if fresh or not (BK / f.name).exists():
            shutil.copy2(f, BK / f.name)
    B = lambda name: (BK / name)

    # 1. tag, country file, colours
    if fresh:
        wr(tags_f, ttxt.rstrip("\r\n") + f'\r\n{TAG} = "countries/{FNAME}.txt"\r\n', tbom)
    ctxt, _ = rd(B(f"{pfile}.txt"))
    ctxt = re.sub(r"color\s*=\s*\{[^}]*\}", "color = { %d %d %d }" % COLOR, ctxt, count=1)
    wr(M / "common/countries" / f"{FNAME}.txt", ctxt)
    cf = M / "common/countries/colors.txt"
    ctx, cbom = rd(cf)
    crlf = "\r\n" in ctx
    ctx = ctx.replace("\r\n", "\n")
    ctx = re.sub(r"(?ms)^%s = \{.*?^\}\n?" % TAG, "", ctx)
    blk = "%s = {\n\tcolor = rgb { %d %d %d }\n\tcolor_ui = rgb { %d %d %d }\n}\n" % ((TAG,) + COLOR + COLOR)
    m = re.search(r"(?ms)^%s = \{.*?^\}\n?" % parent, ctx)
    ctx = ctx[:m.end()] + blk + ctx[m.end():]
    wr(cf, ctx.replace("\n", "\r\n") if crlf else ctx, cbom)

    # 2. ownership and cores of the eastern states
    for sid in east:
        f = Path(states[sid]["file"])
        t, bom = rd(f)
        t = re.sub(r"(?m)^([ \t]*owner\s*=\s*)\w+", lambda mm: mm.group(1) + TAG, t, count=1)
        t = re.sub(r"(?m)^([ \t]*add_core_of\s*=\s*)%s\b" % parent, lambda mm: mm.group(1) + TAG, t)
        wr(f, t, bom)
    for sid in west:
        f = Path(states[sid]["file"])
        t, bom = rd(f)
        t2 = re.sub(r"(?m)^([ \t]*owner\s*=\s*)\w+", lambda mm: mm.group(1) + parent, t, count=1)
        if t2 != t: wr(f, t2, bom)

    # 3. history of the country: the exported file of the parent, the oob names and characters renamed
    ht, _ = rd(B(hist_p.name))
    ht = ht.replace(parent + "_", TAG + "_")
    cap = max(east, key=lambda s: states[s]["manpower"])
    ht = re.sub(r"(?m)^capital\s*=\s*\d+", f"capital = {cap}", ht, count=1)
    ht = re.sub(r"(?m)^add_ideas\s*=\s*ktits_edu_\d\s*\n?", "", ht)
    wr(M / "history/countries" / f"{TAG} - {FNAME}.txt", ht)

    # 4. characters (copies with the new prefix; advisors and generals), leaders are set by make_rulers.py
    ch, chbom = rd(B(f"{parent}.txt"))
    wr(M / f"common/characters/{TAG}.txt", ch.replace(parent + "_", TAG + "_"), chbom)

    # 5. oob: divisions are split by the province of their location; fleets by the naval base; templates are copied
    div_re = re.compile(r"\tdivision\s*=\s*\{[^{}]*\}[ \t]*\r?\n")
    n_div = {parent: 0, TAG: 0}
    for f in sorted(BK.glob(f"{parent}_1936*.txt")):
        t, bom = rd(f)
        crlf = "\r\n" in t
        t = t.replace("\r\n", "\n")
        if div_re.search(t):
            def keep(side):
                def sub(mm):
                    loc = int(re.search(r"location\s*=\s*(\d+)", mm.group(0)).group(1))
                    inside = loc in east_provs
                    ok = inside if side == TAG else not inside
                    if ok: n_div[side] += 1
                    return mm.group(0) if ok else ""
                return sub
            tp = div_re.sub(keep(parent), t)
            tn = div_re.sub(keep(TAG), t).replace(parent + "_", TAG + "_")
            tn = tn.replace("owner = " + parent, "owner = " + TAG)
        else:
            base = re.search(r"naval_base\s*=\s*(\d+)", t)
            if base:                                             # a fleet: it goes to the owner of the naval base
                is_east = int(base.group(1)) in east_provs
                empty = "units = {\n}\n"
                full_n = t.replace(parent + "_", TAG + "_").replace("owner = " + parent, "owner = " + TAG).replace("Eagh Fleet", FNAME + " Fleet")
                tp, tn = (empty, full_n) if is_east else (t, empty)
            else:                                                # air wings and others: both countries get the file
                tp, tn = t, t.replace(parent + "_", TAG + "_")
        for name, txt in ((f.name, tp), (f.name.replace(parent + "_", TAG + "_", 1), tn)):
            wr(M / "history/units" / name, txt.replace("\n", "\r\n") if crlf else txt, bom)
    print(f"iberia: divisions {parent} {n_div[parent] // 2}, {TAG} {n_div[TAG] // 2} (counted over both oob files)")

    # 6. flags: three stripes in the colour of the country (the parent's flag is not reused)
    from PIL import Image
    col = COLOR + (255,)
    gold = (232, 190, 70, 255)
    for d, (w, h) in (("gfx/flags", (82, 52)), ("gfx/flags/medium", (41, 26)), ("gfx/flags/small", (10, 7))):
        im = Image.new("RGBA", (w, h), col)
        for y in range(h * 3 // 8, h * 5 // 8 + (1 if h < 10 else 0)):
            for x in range(w):
                im.putpixel((x, y), gold)
        (M / d).mkdir(parents=True, exist_ok=True)
        im.save(M / d / f"{TAG}.tga")

    # 7. names and portraits: the parent's blocks under the new tag
    for rel in ("common/names/00_names.txt", "portraits/00_portraits.txt", "portraits/998_scientist_portraits.txt"):
        fp = M / rel
        if not fp.exists(): continue
        txt, bom = rd(fp)
        crlf = "\r\n" in txt
        txt = txt.replace("\r\n", "\n")
        txt = re.sub(r"(?ms)^%s = \{\n.*?^\}[ \t]*(?:\n|$)" % TAG, "", txt)
        m = re.search(r"(?ms)^%s = \{\n.*?^\}[ \t]*(?:\n|$)" % parent, txt)
        if m:
            b = m.group(0); b = b if b.endswith("\n") else b + "\n"
            if txt and not txt.endswith("\n"): txt += "\n"
            txt += re.sub(r"^" + parent, TAG, b, count=1)
        wr(fp, txt.replace("\n", "\r\n") if crlf else txt, bom)

    # 8. country names (all languages; ru/en are finished by make_countries.py, the others get the transliteration)
    for f in sorted((M / "localisation").glob("*/countries_l_*.yml")):
        lang = f.parent.name
        txt, bom = rd(f)
        crlf = "\r\n" in txt
        txt = txt.replace("\r\n", "\n")
        nm = NAME if lang == "russian" else L.translit(NAME)
        lines = [l for l in txt.split("\n") if not re.match(r"\s*%s(_\w+)?:" % TAG, l)]
        extra = []
        for l in lines:
            m = re.match(r"(\s*)%s((?:_\w+)?):(\d*)\s" % parent, l)
            if m: extra.append(f'{m.group(1)}{TAG}{m.group(2)}:{m.group(3) or 0} "{nm}"')
        while lines and not lines[-1].strip(): lines.pop()
        txt = "\n".join(lines + extra) + "\n"
        wr(f, txt.replace("\n", "\r\n") if crlf else txt, True if bom else False)
    print(f"iberia: new country {TAG} ({NAME}), colour {COLOR}, capital state {cap}, flag and files written; fresh export: {fresh}")


if __name__ == "__main__":
    main()
