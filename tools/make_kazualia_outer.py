"""External Casuality of Kazualia and the rest of docs/mechanics/Kazualia.md (sections 1-3, 6): see the section "Реализация" of that document.
Run after make_kazualia.py (uses its spirit ktits_kaz_sobering, variables ktits_kaz_inner, flags ktits_kaz_f_outer, ktits_kaz_reformist, ktits_kaz_comm).

What it writes:
  * two decision categories with graphic scale bars (scripted GUI, same approach as the scale of the other countries in make_casuality.py):
    "Внутренняя Казуальность" (bar = ktits_kaz_inner) and "Внешняя Казуальность" (bar = ktits_kaz_outer, INVENTED: share of the other countries that are
    casuality-minded: scale >= 50, fallen, or ruled by the casuality ideology);
  * inner decisions (growth of the scale, emergency war decisions) and outer decisions (Casual rebellion, "Ничего не делать и ждать", support of rebels);
  * the Casual rebellion: slot tags K36-K41 (rebels are a new country, like the parts K01-K34 of make_splits.py), states chosen by the author's rule
    (near Kazualia / port; swamp and low development first), strength by the scale of the target and Internal Casuality, lost rebellion = scale 0 + spirit "Отрезвление",
    won rebellion = Kazualia annexes the rebels or keeps them as a puppet;
  * country "Наши Болота" K35 (decision of the Soviet Union "Буфер на болотах");
  * civil war against the Casuals (section 6): reuses the rebel slots (the tag of Kazualia must survive, so the vanilla start_civil_war is NOT used);
  * emergency military decisions.
Writes: common/country_tags/04_ktits_kazualia.txt, common/countries/K35-K41.txt, history/countries, common/characters, gfx/flags copies, common/names + portraits blocks,
common/decisions/categories/ktits_kazualia_outer_categories.txt, common/decisions/ktits_kazualia_outer_decisions.txt, common/scripted_effects/ktits_kazualia_outer_effects.txt,
common/scripted_triggers/ktits_kazualia_outer_triggers.txt, common/scripted_guis/ktits_kazualia.txt, interface/ktits_kazualia.gui, common/ideas/ktits_kazualia_outer_ideas.txt,
common/on_actions/ktits_kazualia_outer_on_actions.txt, events/ktits_kazualia_outer_events.txt, localisation ru/en.
Usage: python tools/make_kazualia_outer.py [--mod PATH]
"""
import argparse, colorsys, re, shutil
from pathlib import Path
import lore_data as L
import invented_lore as INV

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
a = ap.parse_args()
M = Path(a.mod)
info = L.load_mod(M)
lore2tag = {lt: t for t, lt in info["tag2lore"].items()}
KAZ, SOV = lore2tag["CSL"], lore2tag["SVS"]


def T(s):
    return re.sub(r"(?m)^( {4})+", lambda m: "\t" * (len(m.group()) // 4), s)


def w(rel, text, enc="utf-8"):
    p = M / rel; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(T(text), encoding=enc, newline="\n")


ru, en = [], []
def add(k, r, e=None):
    ru.append((k, r)); en.append((k, e or L.translit(r)))


# ---------------- map data ----------------
cent, idxmap = L.province_centroids(M)
terr = {}
for l in open(M / "map/definition.csv", encoding="latin1"):
    p = l.strip().split(";")
    if len(p) > 6 and p[0].isdigit():
        terr[int(p[0])] = p[6]
nb = INV.NASHI_BOLOTA
swamp_sov = []
swampy = []
kaz_states = []
for sid, s in info["states"].items():
    if not s["provs"]:
        continue
    m_ = sum(1 for p in s["provs"] if terr.get(p) == "marsh")
    if m_ >= 1 and m_ * 3 >= len(s["provs"]):
        swampy.append(sid)
    lt = info["tag2lore"].get(s["owner"])
    if lt == nb["country"]:
        n = [p for p in s["provs"] if nb["x"][0] <= cent[p][0] <= nb["x"][1] and nb["y"][0] <= cent[p][1] <= nb["y"][1] and terr.get(p) == "marsh"]
        if n:
            swamp_sov.append(sid)
    if lt == "CSL":
        kaz_states.append(sid)
swampy.sort(); swamp_sov.sort(); kaz_states.sort()
# K35 gets only about half of the Soviet swamp states (author: 23 was too many): ~12 nearest to Kazualia and the most swampy (rank sum: distance, marsh share)
NB_KEEP = 12
_kp = [cent[p_] for sid in kaz_states for p_ in info["states"][sid]["provs"]]
_kx, _ky = (sum(c[0] for c in _kp) / len(_kp), sum(c[1] for c in _kp) / len(_kp)) if _kp else (0, 0)
def _score(sid):
    pv = info["states"][sid]["provs"]
    dx = sum(cent[p_][0] for p_ in pv) / len(pv) - _kx; dy = sum(cent[p_][1] for p_ in pv) / len(pv) - _ky
    return (dx * dx + dy * dy) ** 0.5, sum(1 for p_ in pv if terr.get(p_) == "marsh") / len(pv)
_sc = {sid: _score(sid) for sid in swamp_sov}
_rd = {sid: i for i, sid in enumerate(sorted(swamp_sov, key=lambda s_: _sc[s_][0]))}
_rm = {sid: i for i, sid in enumerate(sorted(swamp_sov, key=lambda s_: -_sc[s_][1]))}
swamp_all = list(swamp_sov)
swamp_sov = sorted(sorted(swamp_sov, key=lambda s_: (_rd[s_] + _rm[s_], _rd[s_]))[:NB_KEEP], key=lambda s_: _rd[s_])
NB_EXCLUDE = {102, 125}                   # author: these two states stay with the Soviet Union (cores of Kazualia remain)
swamp_sov = [s_ for s_ in swamp_sov if s_ not in NB_EXCLUDE]
NB_CAP = swamp_sov[0]                     # nearest to Kazualia: the capital of K35
swamp_sov.sort()
print(f"kazualia outer: swampy states {len(swampy)}; swamp states of Наши Болота {swamp_sov}; Kazualia states {len(kaz_states)}")

# ---------------- new tags (INVENTED names) ----------------
SLOTS = [("K36", "Болотная Вольница"), ("K37", "Камышовая Республика"), ("K38", "Туманная Община"), ("K39", "Лежачая Рать"), ("K40", "Тихий Фронт"), ("K41", "Трясинное Братство")]
K35 = ("K35", "Наши Болота")
GROUPS = ("fascism", "communism", "neutrality", "democratic", "casuality", "theology")
SLOT_TAGS = [t for t, _ in SLOTS]
CIV_SLOT = "K41"                      # the civil war takes the last free slot (any), rebellion the first free one


# K35 rulers (INVENTED by the author, docs/lore/Invented-Lore.md): id, name, ideology (sub-ideology), the title and the description go to the localisation
K35_RULERS = [
    ("K35_frol_tinnikov", "Фрол Тинников", "leninism", "Председатель Временного Совета",
     "Усталый строгий ставленник Союза в болотных сапогах. Присланный из центра, он уверен, что болото можно осушить циркуляром, и каждое утро проверяет, не проснулось ли оно."),
    ("K35_eryoma_kamyshov", "Ерёма Камышов", "casuality_ideology", "Старейшина",
     "Сонный старик с камышовым венком, лидер казуальной диаспоры. Говорит медленно, и к концу его фразы собеседник обычно уже согласился или заснул."),
    ("K35_vasilisa_gatina", "Василиса Гатина", "liberalism", "Агроном",
     "Решительная женщина с картой осушения под мышкой. Она не против болота, она против того, чтобы в нём тонули урожаи, и уже знает, где прорыть первую канаву."),
]
K35_POP = {"communism": 60, "casuality": 20, "democratic": 20, "neutrality": 0, "fascism": 0, "theology": 0}


def mk_country(tag, nm, parent, col, cap, ruler_ideo="oligarchism"):
    ptxt = (M / "common/countries" / (info["tags"][parent] + ".txt")).read_text(encoding="utf-8", errors="ignore")
    gc = re.findall(r"(graphical_culture\w*\s*=\s*\w+)", ptxt)
    (M / "common/countries" / f"{tag}.txt").write_text("\n".join(gc) + f"\n\ncolor = {{ {col[0]} {col[1]} {col[2]} }}\n", encoding="utf-8")
    (M / "history/countries").mkdir(parents=True, exist_ok=True)
    for f in (M / "history/countries").glob(f"{tag} - *.txt"):
        f.unlink()
    k35 = tag == "K35"
    pops = K35_POP if k35 else {"democratic": 0, "fascism": 0, "communism": 0, "neutrality": 100, "casuality": 0, "theology": 0}
    rp = "communism" if k35 else "neutrality"
    rec = "".join(f"recruit_character = {c[0]}\n" for c in K35_RULERS) if k35 else f"recruit_character = {tag}_leader\n"
    (M / "history/countries" / f"{tag} - {L.translit(nm).replace(' ', '_')}.txt").write_text(
        f"capital = {cap}\n\nset_politics = {{\n\truling_party = {rp}\n\tlast_election = \"1936.1.1\"\n\telection_frequency = 48\n\telections_allowed = no\n}}\n"
        "set_popularities = {\n" + "".join(f"\t{g} = {v}\n" for g, v in pops.items()) + "}\n\n" + rec, encoding="utf-8", newline="\n")
    if k35:
        leader = "".join(f"\t{cid} = {{\n\t\tname = \"{n}\"\n\t\tcountry_leader = {{\n\t\t\tideology = {ide}\n\t\t\ttraits = {{ }}\n\t\t\texpire = \"1965.1.1.1\"\n\t\t\tid = -1\n\t\t}}\n\t}}\n"
                         for cid, n, ide, _t, _d in K35_RULERS)
    else:
        leader = ("\t{t}_leader = {{\n\t\tname = \"Правитель {n}\"\n\t\tcountry_leader = {{\n\t\t\tideology = {ri}\n\t\t\ttraits = {{ }}\n\t\t\texpire = \"1965.1.1.1\"\n\t\t\tid = -1\n\t\t}}\n\t}}\n"
                  "\t{t}_casuality_leader = {{\n\t\tname = \"Казуал-Предводитель\"\n\t\tcountry_leader = {{\n\t\t\tideology = casuality_ideology\n\t\t\ttraits = {{ }}\n\t\t\texpire = \"1965.1.1.1\"\n\t\t\tid = -1\n\t\t}}\n\t}}\n").format(t=tag, n=nm, ri=ruler_ideo)
    (M / "common/characters" / f"{tag}.txt").write_text("characters = {\n" + leader + "}\n", encoding="utf-8-sig")
    for d in ("gfx/flags", "gfx/flags/medium", "gfx/flags/small"):
        for f in (M / d).glob(f"{parent}*.tga"):
            shutil.copy2(f, M / d / f.name.replace(parent, tag, 1))


s_cap = NB_CAP if swamp_sov else info["capital_state"].get("SVS", 1)
k_cap = kaz_states[0] if kaz_states else 1
h, _s, _v = colorsys.rgb_to_hsv(0.45, 0.55, 0.25)
mk_country("K35", K35[1], SOV, (150, 150, 60), s_cap)
for i, (tag, nm) in enumerate(SLOTS):
    col = tuple(round(c * 255) for c in colorsys.hsv_to_rgb((0.25 + 0.03 * i) % 1, 0.55, 0.55 + 0.05 * (i % 3)))
    mk_country(tag, nm, KAZ, col, k_cap)
ALL_NEW = [K35] + SLOTS
(M / "common/country_tags/04_ktits_kazualia.txt").write_text("".join(f'{t} = "countries/{t}.txt"\n' for t, _ in ALL_NEW), encoding="utf-8")
for lang, conv in (("russian", lambda s: s), ("english", L.translit)):
    ent = []
    for tag, nm in ALL_NEW:
        for g in GROUPS:
            for suf in ("", "_DEF", "_ADJ"):
                ent.append((f"{tag}_{g}{suf}", conv(nm)))
        ent += [(tag, conv(nm)), (f"{tag}_DEF", conv(nm)), (f"{tag}_ADJ", conv(nm))]
    L.write_yml(str(M / f"localisation/{lang}/ktits_kazualia_tags_l_{lang}.yml"), lang, ent)
# names and scientist portraits (the game logs errors when it creates scientists for a tag without them): the parent's blocks under the new tags
for rel in ("common/names/00_names.txt", "portraits/998_scientist_portraits.txt"):
    fp = M / rel
    if not fp.exists():
        continue
    raw = fp.read_bytes(); bom = raw.startswith(b"\xef\xbb\xbf")
    txt = raw.decode("utf-8-sig"); crlf = "\r\n" in txt
    txt = txt.replace("\r\n", "\n")
    txt = re.sub(r"(?ms)^K(3[5-9]|4[0-9]) = \{\n.*?^\}[ \t]*\n?", "", txt)
    blocks = {m.group(1): m.group(0) for m in re.finditer(r"(?ms)^([A-Z0-9]{3}) = \{\n.*?^\}[ \t]*(?:\n|$)", txt)}
    if txt and not txt.endswith("\n"):
        txt += "\n"
    for tag, _nm in ALL_NEW:
        parent = SOV if tag == "K35" else KAZ
        if parent in blocks:
            b = blocks[parent]; b = b if b.endswith("\n") else b + "\n"
            txt += re.sub(r"^[A-Z0-9]{3}", tag, b, count=1)
    if crlf:
        txt = txt.replace("\n", "\r\n")
    fp.write_bytes((b"\xef\xbb\xbf" if bom else b"") + txt.encode("utf-8"))

# ---------------- scripted triggers ----------------
OR_SW = " ".join(f"state = {s}" for s in swampy)
trig = f"""# generated by tools/make_kazualia_outer.py (docs/mechanics/Kazualia.md, section 3): choice of the states of a Casual rebellion
ktits_kz_swampy = {{
    OR = {{ {OR_SW} }}
}}
# low development (state categories of the base game)
ktits_kz_lowdev = {{
    OR = {{
        has_state_category = wasteland
        has_state_category = pastoral
        has_state_category = rural
        has_state_category = town
    }}
}}
ktits_kz_free_state = {{
    NOT = {{ is_capital = yes }}
    NOT = {{ has_state_flag = ktits_kz_pick }}
}}
# the pool of the rebellion: a target that borders Kazualia or its alliance -> the states next to them; otherwise the coastal states (the rebels come by sea);
# the civil war of Kazualia: any state
ktits_kz_in_pool = {{
    OR = {{
        AND = {{
            OWNER = {{ has_country_flag = ktits_kz_borders }}
            any_neighbor_state = {{
                OWNER = {{
                    OR = {{
                        original_tag = {KAZ}
                        is_in_faction_with = {KAZ}
                        is_puppet_of = {KAZ}
                    }}
                }}
            }}
        }}
        AND = {{
            NOT = {{ OWNER = {{ has_country_flag = ktits_kz_borders }} }}
            NOT = {{ OWNER = {{ has_country_flag = ktits_kz_civ_pool }} }}
            is_coastal = yes
        }}
        OWNER = {{ has_country_flag = ktits_kz_civ_pool }}
    }}
}}
# is there a free rebel slot
ktits_kz_slot_free = {{
    OR = {{
""" + "".join(f"        {t} = {{ exists = no }}\n" for t in SLOT_TAGS) + """    }
}
"""
w("common/scripted_triggers/ktits_kazualia_outer_triggers.txt", trig)

# ---------------- scripted effects ----------------
TIERS = [("ktits_kz_in_pool = yes ktits_kz_swampy = yes ktits_kz_lowdev = yes"), ("ktits_kz_in_pool = yes ktits_kz_swampy = yes"),
         ("ktits_kz_in_pool = yes ktits_kz_lowdev = yes"), ("ktits_kz_in_pool = yes"), ("ktits_kz_swampy = yes ktits_kz_lowdev = yes"), ("ktits_kz_swampy = yes"), ("")]
pick = "# scope = the target country: marks ONE state by the author's rule (pool, then swamp, then low development; the capital is never taken); variable ktits_kz_n = how many are left\nktits_kz_pick = {\n    if = {\n        limit = { check_variable = { var = ktits_kz_n value = 0 compare = greater_than } }\n"
for i, t in enumerate(TIERS):
    lim = "ktits_kz_free_state = yes " + t
    kw = "if" if i == 0 else "else_if"
    pick += (f"        {kw} = {{\n            limit = {{ any_owned_state = {{ {lim} }} }}\n            random_owned_state = {{\n                limit = {{ {lim} }}\n"
             "                set_state_flag = ktits_kz_pick\n            }\n            add_to_variable = { var = ktits_kz_n value = -1 }\n        }\n")
pick += "        else = {\n            set_variable = { var = ktits_kz_n value = 0 }\n        }\n    }\n}\n\n"
# sizes: rebellion (scale of the target, stability, Internal Casuality) -> ktits_kz_n states, ktits_kz_d divisions
sizes = """# scope = the target country, ROOT = Kazualia: strength of the rebellion (docs/mechanics/Kazualia.md, section 3)
ktits_kz_rebel_size = {
    set_variable = { var = ktits_kz_n value = 2 }
    set_variable = { var = ktits_kz_d value = 3 }
    if = {
        limit = { check_variable = { var = ktits_casuality value = 85 compare = greater_than_or_equals } }
        set_variable = { var = ktits_kz_n value = 4 }
        set_variable = { var = ktits_kz_d value = 6 }
    }
    if = {
        limit = { check_variable = { var = ktits_casuality value = 95 compare = greater_than_or_equals } }
        set_variable = { var = ktits_kz_n value = 6 }
        set_variable = { var = ktits_kz_d value = 10 }
        add_stability = -0.10
    }
    # +1 division for every full 10 % of Internal Casuality of Kazualia above 50 (the higher it is, the easier it is to raise rebellions)
    set_variable = { var = ktits_kz_b value = ROOT.ktits_kaz_inner }
    add_to_variable = { var = ktits_kz_b value = -50 }
    clamp_variable = { var = ktits_kz_b min = 0 max = 50 }
    set_variable = { var = ktits_kz_r value = ktits_kz_b }
    modulo_variable = { var = ktits_kz_r value = 10 }
    subtract_from_variable = { var = ktits_kz_b value = ktits_kz_r }
    divide_variable = { var = ktits_kz_b value = 10 }
    clear_variable = ktits_kz_r
    add_to_variable = { var = ktits_kz_d value = ktits_kz_b }
    if = {
        limit = { ROOT = { has_country_flag = ktits_kaz_f_rebel_plus } }
        add_to_variable = { var = ktits_kz_d value = 1 }
    }
    # a stable target resists: -1 state and -2 divisions
    if = {
        limit = { has_stability > 0.6 }
        add_to_variable = { var = ktits_kz_n value = -1 }
        add_to_variable = { var = ktits_kz_d value = -2 }
    }
    clamp_variable = { var = ktits_kz_n min = 1 max = 6 }
    clamp_variable = { var = ktits_kz_d min = 1 max = 20 }
}

"""
ladder = "".join(
    f"    if = {{\n        limit = {{ check_variable = {{ var = ktits_kz_d value = {k} compare = greater_than_or_equals }} }}\n        capital_scope = {{\n        create_unit = {{\n"
    f"            division = \"name = \\\"Казуальное ополчение\\\" division_template = \\\"Болотные повстанцы\\\" start_experience_factor = 0.1 start_equipment_factor = 0.7\"\n"
    f"            owner = THIS\n        }}\n        }}\n    }}\n" for k in range(1, 21))
setup_t = """# scope = the new rebel country, PREV = the country it rises against (target of the rebellion or Kazualia in the civil war); variable ktits_kz_d is passed by the caller
ktits_kz_rebel_setup_@T@ = {
    clr_country_flag = ktits_kz_rebel_won
    set_country_flag = ktits_kz_rebel
    set_country_flag = ktits_casuality_fallen
    set_variable = { var = ktits_casuality value = 100 }
    set_politics = { ruling_party = casuality }
    add_popularity = { ideology = casuality popularity = 0.8 }
    random_owned_state = { OWNER = { set_capital = { state = PREV } } }
    # no Dur debuff for the rebels (author's rule): the last stage of the spirit, only the buff on their own land
    if = { limit = { NOT = { has_idea = ktits_durmanische_3 } } add_ideas = ktits_durmanische_3 }
    set_technology = { infantry_weapons = 1 }
    division_template = {
        name = "Болотные повстанцы"
        regiments = {
            infantry = { x = 0 y = 0 }
            infantry = { x = 0 y = 1 }
            infantry = { x = 1 y = 0 }
            infantry = { x = 1 y = 1 }
        }
    }
@LADDER@    ktits_education_start = yes
    declare_war_on = { target = PREV type = annex_everything }
}

"""
setup = "".join(setup_t.replace("@T@", t).replace("@LADDER@", ladder.replace("owner = THIS", f"owner = {t}")) for t in SLOT_TAGS)
make = ""
for t in SLOT_TAGS:
    make += (f"# scope = the target (or Kazualia in the civil war): the marked states go to {t}, the rebels get units and declare war\nktits_kz_make_{t} = {{\n"
             f"    every_owned_state = {{\n        limit = {{ has_state_flag = ktits_kz_pick }}\n        clr_state_flag = ktits_kz_pick\n        add_core_of = {t}\n        transfer_state_to = {t}\n    }}\n"
             f"    {t} = {{\n        set_variable = {{ var = ktits_kz_d value = PREV.ktits_kz_d }}\n        ktits_kz_rebel_setup_{t} = yes\n        clear_variable = ktits_kz_d\n    }}\n"
             f"    set_variable = {{ var = ktits_kz_slot value = {t[1:]} }}\n}}\n\n")
choose = "".join(f"        {'if' if i == 0 else 'else_if'} = {{\n            limit = {{ {t} = {{ exists = no }} }}\n            ktits_kz_make_{t} = yes\n        }}\n" for i, t in enumerate(SLOT_TAGS))
raise_ = f"""# scope = the target country, ROOT = Kazualia (called from the decision): the Casual rebellion
ktits_kz_rebel_raise = {{
    clr_country_flag = ktits_kz_borders
    if = {{
        limit = {{
            any_neighbor_country = {{
                OR = {{
                    original_tag = {KAZ}
                    is_in_faction_with = {KAZ}
                    is_puppet_of = {KAZ}
                }}
            }}
        }}
        set_country_flag = ktits_kz_borders
    }}
    ktits_kz_rebel_size = yes
    ktits_kz_pick = yes
    ktits_kz_pick = yes
    ktits_kz_pick = yes
    ktits_kz_pick = yes
    ktits_kz_pick = yes
    ktits_kz_pick = yes
    if = {{
        limit = {{ any_owned_state = {{ has_state_flag = ktits_kz_pick }} }}
{choose}        set_country_flag = ktits_kz_rebel_active
    }}
    clear_variable = ktits_kz_n
    clear_variable = ktits_kz_d
    clear_variable = ktits_kz_b
    clr_country_flag = ktits_kz_borders
}}

"""
# civil war (section 6): the rebels rise inside Kazualia
civ = f"""# scope = Kazualia: the civil war against the Casuals (docs/mechanics/Kazualia.md, section 6); reuses the rebel slots
ktits_kz_civwar_raise = {{
    set_country_flag = ktits_kz_civ_pool
    set_variable = {{ var = ktits_kz_n value = 6 }}
    set_variable = {{ var = ktits_kz_d value = 10 }}
    ktits_kz_pick = yes
    ktits_kz_pick = yes
    ktits_kz_pick = yes
    ktits_kz_pick = yes
    ktits_kz_pick = yes
    ktits_kz_pick = yes
    if = {{
        limit = {{ any_owned_state = {{ has_state_flag = ktits_kz_pick }} }}
{choose}        set_country_flag = ktits_kz_civ_active
        set_country_flag = ktits_kaz_civwar_done
    }}
    clear_variable = ktits_kz_n
    clear_variable = ktits_kz_d
    clr_country_flag = ktits_kz_civ_pool
}}

"""
# monthly resolution
mon = ("# scope = any country, every month: the rebellion against it (won / lost), the civil war of Kazualia, waiting for the fall (+1 to the scale)\nktits_kz_rebel_monthly = {\n"
       "    if = {\n        limit = {\n            has_country_flag = ktits_kz_waiting\n            NOT = { has_country_flag = ktits_casuality_fallen }\n            check_variable = { var = ktits_casuality value = 100 compare = less_than }\n        }\n"
       "        add_to_variable = { var = ktits_casuality value = 1 }\n        clamp_variable = { var = ktits_casuality min = 0 max = 100 }\n        ktits_casuality_update = yes\n    }\n")
for flag, won, lost in (("ktits_kz_rebel_active", "ktits_kz_rebel_won_", "ktits_kz_rebel_lost"), ("ktits_kz_civ_active", "ktits_kz_civ_won_", "ktits_kz_civ_lost")):
    mon += f"    if = {{\n        limit = {{ has_country_flag = {flag} }}\n"
    for i, t in enumerate(SLOT_TAGS):
        mon += (f"        {'if' if i == 0 else 'else_if'} = {{\n            limit = {{ check_variable = {{ var = ktits_kz_slot value = {t[1:]} compare = equals }} }}\n"
                f"            if = {{\n                limit = {{ {t} = {{ exists = yes }} NOT = {{ has_war_with = {t} }} }}\n                {won}{t} = yes\n            }}\n"
                f"            else_if = {{\n                limit = {{ {t} = {{ exists = no }} }}\n                {lost} = yes\n            }}\n        }}\n")
    mon += "    }\n"
mon += "}\n\n"
res = ""
for t in SLOT_TAGS:
    n = int(t[1:]) - 36
    res += (f"# scope = the target: the rebels {t} are alive and the war is over = the rebellion won; Kazualia chooses\nktits_kz_rebel_won_{t} = {{\n    clr_country_flag = ktits_kz_rebel_active\n"
            f"    set_variable = {{ var = ktits_kz_slot value = 0 }}\n    {t} = {{ set_country_flag = ktits_kz_rebel_won }}\n    {KAZ} = {{ country_event = {{ id = ktits_kz_out.{10 + n} }} }}\n}}\n\n"
            f"# scope = Kazualia: the rebels {t} (civil war) survived the war = the Casuals win\nktits_kz_civ_won_{t} = {{\n    clr_country_flag = ktits_kz_civ_active\n    set_variable = {{ var = ktits_kz_slot value = 0 }}\n"
            f"    {t} = {{ every_owned_state = {{ add_core_of = {KAZ} }} }}\n    annex_country = {{ target = {t} transfer_troops = yes }}\n"
            "    clr_country_flag = ktits_kaz_reformist\n    clr_country_flag = ktits_kaz_comm\n    set_politics = { ruling_party = casuality }\n    add_popularity = { ideology = casuality popularity = 0.5 }\n"
            "    add_to_variable = { var = ktits_kaz_inner value = 15 }\n    add_to_variable = { var = ktits_kaz_reform value = -30 }\n    clamp_variable = { var = ktits_kaz_reform min = 0 max = 100 }\n"
            "    ktits_kaz_inner_update = yes\n    country_event = { id = ktits_kz_out.22 }\n}\n\n")
res += """# scope = the target: the rebellion was crushed (rebels gone): the scale falls to 0, the spirit "Отрезвление" for a year forbids a new rebellion
ktits_kz_rebel_lost = {
    clr_country_flag = ktits_kz_rebel_active
    set_variable = { var = ktits_kz_slot value = 0 }
    set_variable = { var = ktits_casuality value = 0 }
    ktits_casuality_update = yes
    add_timed_idea = { idea = ktits_kaz_sobering days = 365 }
    country_event = { id = ktits_kz_out.2 }
""" + f"    {KAZ} = {{\n        add_to_variable = {{ var = ktits_kaz_inner value = -5 }}\n        ktits_kaz_inner_update = yes\n        country_event = {{ id = ktits_kz_out.3 }}\n    }}\n}}\n\n"
res += """# scope = Kazualia: the rebels of the civil war are gone = the government wins
ktits_kz_civ_lost = {
    clr_country_flag = ktits_kz_civ_active
    set_variable = { var = ktits_kz_slot value = 0 }
    add_stability = 0.10
    add_to_variable = { var = ktits_kaz_inner value = -10 }
    ktits_kaz_inner_update = yes
    country_event = { id = ktits_kz_out.21 }
}

"""
# the monthly check of the civil war
civ_chk = """# scope = Kazualia, every month: the civil war against the Casuals on the Reform and Communist paths (section 6; chance INVENTED: 4 % a month, 2 % after the focus "Красная гвардия болот")
ktits_kz_civwar_check = {
    if = {
        limit = {
            OR = {
                has_country_flag = ktits_kaz_reformist
                has_country_flag = ktits_kaz_comm
            }
            NOT = { has_country_flag = ktits_kaz_civwar_done }
            NOT = { has_country_flag = ktits_kz_civ_active }
            is_subject = no
            ktits_kz_slot_free = yes
            check_variable = { var = ktits_kaz_inner value = 40 compare = greater_than_or_equals }
        }
        if = {
            limit = { has_country_flag = ktits_kaz_f_civwar_half }
            random_list = { 2 = { country_event = { id = ktits_kz_out.20 } } 98 = { } }
        }
        else = {
            random_list = { 4 = { country_event = { id = ktits_kz_out.20 } } 96 = { } }
        }
    }
}

"""
# outer scale
outer = f"""# scope = Kazualia, every month: the scale of External Casuality (INVENTED): the share (%) of the other countries that are casuality-minded
ktits_kaz_outer_update = {{
    set_variable = {{ var = ktits_kaz_o_n value = 0 }}
    set_variable = {{ var = ktits_kaz_o_all value = 0 }}
    every_other_country = {{
        limit = {{ NOT = {{ has_country_flag = ktits_kz_rebel }} }}
        PREV = {{ add_to_variable = {{ var = ktits_kaz_o_all value = 1 }} }}
        if = {{
            limit = {{
                OR = {{
                    has_country_flag = ktits_casuality_fallen
                    has_government = casuality
                    check_variable = {{ var = ktits_casuality value = 50 compare = greater_than_or_equals }}
                }}
            }}
            PREV = {{ add_to_variable = {{ var = ktits_kaz_o_n value = 1 }} }}
        }}
    }}
    set_variable = {{ var = ktits_kaz_outer value = ktits_kaz_o_n }}
    multiply_variable = {{ var = ktits_kaz_outer value = 100 }}
    if = {{
        limit = {{ check_variable = {{ var = ktits_kaz_o_all value = 0 compare = greater_than }} }}
        divide_variable = {{ var = ktits_kaz_outer value = ktits_kaz_o_all }}
    }}
    round_variable = ktits_kaz_outer
    clamp_variable = {{ var = ktits_kaz_outer min = 0 max = 100 }}
    ktits_kaz_ol_calc = yes
}}

"""
# list of target countries in the category description: top 8 by the scale, "Name: 42 (st. 2, +3)" (docs/mechanics/Kazualia.md, "Внешняя Казуальность")
# global variables ktits_kaz_ol_{c,v,t,d}N (country / scale / tier / change in a month) are read by scripted localisation; the previous scale is kept in the country variable ktits_kaz_ol_prev
OL_ROWS = 8
OL_ELIG = ("NOT = { has_country_flag = ktits_casuality_fallen } NOT = { has_country_flag = ktits_kz_rebel } NOT = { ktits_is_kazualia = yes } "
           "NOT = { is_subject_of = ROOT } NOT = { original_tag = K35 } NOT = { has_country_flag = ktits_kaz_ol_taken }")
ol = "# scope = Kazualia, every month (called from ktits_kaz_outer_update): the top 8 countries by the Casuality scale for the description of the category\nktits_kaz_ol_calc = {\n"
for r_ in range(1, OL_ROWS + 1):
    ol += (f"    set_variable = {{ global.ktits_kaz_ol_best = 0 }}\n"
           f"    set_variable = {{ global.ktits_kaz_ol_v{r_} = 0 }}\n"
           f"    every_other_country = {{\n        limit = {{\n            {OL_ELIG}\n            check_variable = {{ var = ktits_casuality value = global.ktits_kaz_ol_best compare = greater_than }}\n        }}\n"
           f"        set_variable = {{ global.ktits_kaz_ol_best = ktits_casuality }}\n    }}\n"
           f"    if = {{\n        limit = {{ check_variable = {{ var = global.ktits_kaz_ol_best value = 0 compare = greater_than }} }}\n"
           f"        random_other_country = {{\n            limit = {{\n                {OL_ELIG}\n                check_variable = {{ var = ktits_casuality value = global.ktits_kaz_ol_best compare = equals }}\n            }}\n"
           f"            set_country_flag = ktits_kaz_ol_taken\n"
           f"            if = {{ limit = {{ NOT = {{ check_variable = {{ var = ktits_kaz_ol_prev value = 0 compare = greater_than }} }} }} set_variable = {{ ktits_kaz_ol_prev = ktits_casuality }} }}\n"
           f"            set_variable = {{ global.ktits_kaz_ol_c{r_} = THIS }}\n"
           f"            set_variable = {{ global.ktits_kaz_ol_v{r_} = ktits_casuality }}\n"
           f"            set_variable = {{ global.ktits_kaz_ol_d{r_} = ktits_casuality }}\n"
           f"            subtract_from_variable = {{ var = global.ktits_kaz_ol_d{r_} value = ktits_kaz_ol_prev }}\n"
           f"            set_variable = {{ global.ktits_kaz_ol_t{r_} = 0 }}\n")
    for thr_, tier_ in ((1, 1), (25, 2), (50, 3), (75, 4), (95, 5)):
        ol += f"            if = {{ limit = {{ check_variable = {{ var = ktits_casuality value = {thr_} compare = greater_than_or_equals }} }} set_variable = {{ global.ktits_kaz_ol_t{r_} = {tier_} }} }}\n"
    ol += "        }\n    }\n"
ol += ("    # the scale of this month becomes the base for the next change; the marks are removed\n"
       "    every_other_country = {\n        limit = { has_country_flag = ktits_kaz_ol_taken }\n        clr_country_flag = ktits_kaz_ol_taken\n    }\n"
       "    every_other_country = {\n        set_variable = { ktits_kaz_ol_prev = ktits_casuality }\n    }\n}\n\n")
sl = ""
for r_ in range(1, OL_ROWS + 1):
    sl += (f"defined_text = {{\n    name = GetKtitsKazOlD{r_}\n    text = {{\n        trigger = {{ check_variable = {{ var = global.ktits_kaz_ol_d{r_} value = 0 compare = greater_than }} }}\n        localization_key = ktits_kaz_ol_dp{r_}\n    }}\n"
           f"    text = {{\n        localization_key = ktits_kaz_ol_dn{r_}\n    }}\n}}\n\n"
           f"defined_text = {{\n    name = GetKtitsKazOl{r_}\n    text = {{\n        trigger = {{ check_variable = {{ var = global.ktits_kaz_ol_v{r_} value = 0 compare = greater_than }} }}\n        localization_key = ktits_kaz_olrow{r_}\n    }}\n"
           f"    text = {{\n        localization_key = ktits_kaz_olrow_empty\n    }}\n}}\n\n")
    add(f"ktits_kaz_ol_dp{r_}", f"+[?global.ktits_kaz_ol_d{r_}|0]")
    add(f"ktits_kaz_ol_dn{r_}", f"[?global.ktits_kaz_ol_d{r_}|0]")
    add(f"ktits_kaz_olrow{r_}", f"§Y[?global.ktits_kaz_ol_c{r_}.GetName]§!: [?global.ktits_kaz_ol_v{r_}|0] (ст. [?global.ktits_kaz_ol_t{r_}|0], [GetKtitsKazOlD{r_}])" + chr(92) + "n",
        f"§Y[?global.ktits_kaz_ol_c{r_}.GetName]§!: [?global.ktits_kaz_ol_v{r_}|0] (tier [?global.ktits_kaz_ol_t{r_}|0], [GetKtitsKazOlD{r_}])" + chr(92) + "n")
add("ktits_kaz_olrow_empty", "")
w("common/scripted_localisation/ktits_kazualia_outer_loc.txt", sl)
# country Наши Болота
SW_OR = " ".join(f"state = {s}" for s in swamp_sov)
nbl = f"""# scope = the Soviet Union: the decision "Буфер на болотах" creates the puppet "Наши Болота" (K35) on the swamp states (docs/mechanics/Kazualia.md, section 1)
ktits_kz_make_K35 = {{
    every_owned_state = {{
        limit = {{ OR = {{ {SW_OR} }} }}
        add_core_of = K35
        transfer_state_to = K35
    }}
    K35 = {{
        set_capital = {{ state = {NB_CAP} }}
        set_variable = {{ var = ktits_casuality value = 25 }}
        ktits_casuality_costs = yes
        ktits_casuality_ai_start = yes
        ktits_casuality_update = yes
        ktits_education_start = yes
    }}
    puppet = K35
}}

"""
w("common/scripted_effects/ktits_kazualia_outer_effects.txt", "# generated by tools/make_kazualia_outer.py (docs/mechanics/Kazualia.md)\n" + pick + sizes + setup + make + raise_ + civ + mon + res + civ_chk + outer + ol + nbl)

# ---------------- ideas (timed spirits of the emergency decisions) ----------------
def idea(name, mods):
    body = "".join(f"            {k} = {v:g}\n" for k, v in mods.items())
    return f"        {name} = {{\n            picture = ktits_casuality\n            allowed = {{ always = no }}\n            allowed_civil_war = {{ always = yes }}\n            removal_cost = -1\n            modifier = {{\n{body}            }}\n        }}\n"
EMG = [
    ("ambush", "Лечь в засаду", "Приказ прост: лечь и ждать. Враг идёт по болоту, а болото смотрит на него снизу вверх.", 30, 60,
     {"army_defence_factor": 0.20, "dig_in_speed_factor": 0.30}, "Защита дивизий +20 %, скорость окапывания +30 % на 30 дней"),
    ("fog", "Туман на фронт", "Туман идёт впереди казуальных колонн. Враг не видит, куда стрелять, и на всякий случай ложится сам.", 50, 90,
     {"army_attack_factor": 0.20, "army_org_factor": 0.10}, "Атака дивизий +20 %, организация +10 % на 30 дней"),
]
ideas = "".join(idea(f"ktits_kaz_em_{k}_t", mods) for k, _n, _d, _p, _c, mods, _t in EMG)
ideas += idea("ktits_kaz_rebels_t", {"army_attack_factor": 0.05})
w("common/ideas/ktits_kazualia_outer_ideas.txt", "ideas = {\n    country = {\n" + ideas + "    }\n}\n")
for k, nm, desc, *_ in EMG:
    add(f"ktits_kaz_em_{k}_t", nm); add(f"ktits_kaz_em_{k}_t_desc", desc)
add("ktits_kaz_rebels_t", "Снабжение повстанцев"); add("ktits_kaz_rebels_t_desc", "Из Ставки идут обозы: муку, вилы и немного уверенности. Лишнего не присылают, чтобы повстанцы не обленились раньше срока.")

# ---------------- decisions ----------------
def tt(k, r):
    add(k, r)
    return k
INNER = [
    ("nap", "Тихий час", "Ставка объявляет тихий час. Он длится до вечера, потом до утра, потом до следующей недели.", 25, 30, 3),
    ("feast", "Праздник безделья", "Целый день никто ничего не делает, и это называется праздником. Народ доволен, а чиновники особенно: праздник не надо было готовить.", 50, 90, 6),
]
cat = """ktits_kaz_inner_category = {
    icon = generic_propaganda
    picture = GFX_decision_cat_picture_ktits_casuality
    scripted_gui = ktits_kin_ui
    visible = {
        ktits_is_kazualia = yes
    }
}

ktits_kaz_outer_category = {
    icon = generic_propaganda
    picture = GFX_decision_cat_picture_ktits_casuality
    scripted_gui = ktits_kout_ui
    visible = {
        ktits_is_kazualia = yes
        has_country_flag = ktits_kaz_f_outer
    }
}

ktits_sov_buffer_category = {
    icon = generic_propaganda
    picture = GFX_decision_cat_picture_ktits_casuality
    visible = {
        original_tag = """ + SOV + """
    }
}
"""
w("common/decisions/categories/ktits_kazualia_outer_categories.txt", cat)
add("ktits_kaz_inner_category", "Внутренняя Казуальность")
add("ktits_kaz_inner_category_desc", "Казуал не ленится — он ждёт. Ждёт урожая, приказа, конца света. Пока он ждёт, ружьё у него всегда под рукой, а болото за спиной знает каждую его тропу. Шкала: [?ktits_kaz_inner|0] %. [GetKtitsKazLate]")
add("ktits_kaz_outer_category", "Внешняя Казуальность")
add("ktits_kaz_outer_category_desc", "Лень не знает границ. Она переходит реки вместе с туманом, просачивается в газеты и кабаки, и вот уже соседний чиновник смотрит в окно вместо отчёта. Казуальные страны: [?ktits_kaz_outer|0] % из остальных. §YВ очереди на лень (шкала, ступень, изменение за месяц):§!\\n[GetKtitsKazOl1][GetKtitsKazOl2][GetKtitsKazOl3][GetKtitsKazOl4][GetKtitsKazOl5][GetKtitsKazOl6][GetKtitsKazOl7][GetKtitsKazOl8]")
add("ktits_sov_buffer_category", "Граница с Казуалией")
add("ktits_sov_buffer_category_desc", "Здесь кончаются советские дороги и начинается туман. Казуалы-переселенцы живут тут веками и не очень понимают, чья это земля.")

dec = "ktits_kaz_inner_category = {\n\n"
for k, nm, lore, pp_, cd, d in INNER:
    did = f"ktits_kaz_in_{k}"
    add(did, nm); add(did + "_desc", f"{lore} (Внутренняя Казуальность +{d} %; {pp_} ПВ, перезарядка {cd} дн.)")
    add(f"ktits_kaz_tt_inner_p{d}", f"Внутренняя Казуальность: §Y+{d} %§!")
    dec += T(f"""    {did} = {{
        icon = generic_propaganda
        visible = {{
            ktits_is_kazualia = yes
        }}
        available = {{
            custom_trigger_tooltip = {{
                tooltip = ktits_kaz_tt_cd
                NOT = {{ has_country_flag = ktits_kaz_cd_{k} }}
            }}
        }}
        cost = {pp_}
        fire_only_once = no
        complete_effect = {{
            set_country_flag = {{ flag = ktits_kaz_cd_{k} days = {cd} value = 1 }}
            custom_effect_tooltip = ktits_kaz_tt_inner_p{d}
            add_to_variable = {{ var = ktits_kaz_inner value = {d} }}
            hidden_effect = {{ ktits_kaz_inner_update = yes }}
        }}
        ai_will_do = {{
            base = 1
            modifier = {{ factor = 0 check_variable = {{ var = ktits_kaz_inner value = 60 compare = greater_than_or_equals }} }}
        }}
    }}

""")
# emergency war decisions (section 2: during a war or at war support > 95 %); never delayed (section 2.1)
EM_VIS = "OR = {\n                has_war = yes\n                has_war_support > 0.95\n            }"
for k, nm, desc, pp_, cd, mods, eff in EMG:
    did = f"ktits_kaz_em_{k}"
    add(did, nm); add(did + "_desc", f"{desc} ({eff}; {pp_} ПВ, перезарядка {cd} дн.; только во время войны или при поддержке войны выше 95 %)")
    dec += T(f"""    {did} = {{
        icon = generic_propaganda
        visible = {{
            ktits_is_kazualia = yes
        }}
        available = {{
            custom_trigger_tooltip = {{
                tooltip = ktits_kaz_tt_cd
                NOT = {{ has_country_flag = ktits_kaz_cd_em_{k} }}
            }}
            custom_trigger_tooltip = {{
                tooltip = ktits_kaz_tt_war
                {EM_VIS}
            }}
        }}
        cost = {pp_}
        fire_only_once = no
        complete_effect = {{
            set_country_flag = {{ flag = ktits_kaz_cd_em_{k} days = {cd} value = 1 }}
            add_timed_idea = {{ idea = ktits_kaz_em_{k}_t days = 30 }}
        }}
        ai_will_do = {{
            base = 2
            modifier = {{ factor = 0 has_war = no }}
        }}
    }}

""")
add("ktits_kaz_tt_cd", "Решение ещё перезаряжается")
add("ktits_kaz_tt_war", "Идёт война или поддержка войны выше 95 %")
add("ktits_kaz_em_call", "Крик из камышей")
add("ktits_kaz_em_call_desc", "Над болотом раздаётся клич, и из камышей поднимаются люди с вилами. Их никто не звал, но они услышали. (3 дивизии ополчения; 40 ПВ, перезарядка 120 дн.; только во время войны или при поддержке войны выше 95 %)")
dec += T(f"""    ktits_kaz_em_call = {{
        icon = generic_propaganda
        visible = {{
            ktits_is_kazualia = yes
        }}
        available = {{
            custom_trigger_tooltip = {{
                tooltip = ktits_kaz_tt_cd
                NOT = {{ has_country_flag = ktits_kaz_cd_em_call }}
            }}
            custom_trigger_tooltip = {{
                tooltip = ktits_kaz_tt_war
                {EM_VIS}
            }}
        }}
        cost = 40
        fire_only_once = no
        complete_effect = {{
            set_country_flag = {{ flag = ktits_kaz_cd_em_call days = 120 value = 1 }}
            custom_effect_tooltip = ktits_kaz_tt_div_militia3
            hidden_effect = {{
""" + "                capital_scope = {\n" + "".join('                    create_unit = { division = "name = \\"Казуальная дивизия\\" division_template = \\"Болотное ополчение\\" start_experience_factor = 0.1 start_equipment_factor = 0.7" owner = PREV }\n' for _ in range(3)) + "                }\n" + """            }
        }
        ai_will_do = {
            base = 2
            modifier = { factor = 0 has_war = no }
        }
    }
}

""")
# outer decisions: ALL of them are listed for every plausible target (neighbours, countries with the scale 25+, waiting ones); the conditions live in `available`
# (custom_trigger_tooltip), so a decision that cannot be taken is greyed instead of vanishing; cooldowns are flags (days_re_enable is not used)
add("ktits_kz_tt_slot", "Есть место для нового восстания (не более шести одновременно)")
add("ktits_kz_tt_need75", "Шкала Казуальности страны-цели от 75 до 99")
add("ktits_kz_tt_calm", "В стране-цели нет восстания, «ожидания» Казуалии и духа «Отрезвление»")
add("ktits_kz_tt_wait10", "Шкала Казуальности страны-цели от 10 до 99, нет восстания и «ожидания»")
add("ktits_kz_tt_scale99", "Шкала Казуальности страны-цели ниже 100")
add("ktits_kz_tt_scale25", "Шкала Казуальности страны-цели не ниже 25 (в ней уже есть кому слушать)")
add("ktits_kz_tt_border", "Страна-цель граничит с Казуалией")
add("ktits_kz_tt_war_rebels", "Повстанцы страны-цели воюют")
add("ktits_kaz_rebel", "Начать Казуальное восстание")
add("ktits_kaz_rebel_desc", "Однажды утром целый уезд не вышел на работу. К обеду вышел — но уже с вилами и под зелёным болотным знаменем. (Часть штатов страны-цели ближе всего к Казуалии, а если границы нет — портовых, с болотом и меньшим развитием, отделяется в новую страну и воюет с ней; сила — по шкале Казуальности цели, стабильности цели и Внутренней Казуальности Казуалии; 75 ПВ, перезарядка 30 дн.)")
add("ktits_kaz_wait", "Ничего не делать и ждать")
add("ktits_kaz_wait_desc", "Зачем воевать, если можно подождать? Соседи сами придут. Рано или поздно все приходят. (Шкала Казуальности страны +1 в месяц; на 100 она сама перейдёт в Казуальность и станет марионеткой Казуалии; пока Казуалия ждёт, восстание в этой стране недоступно)")
add("ktits_kaz_unwait", "Передумать")
add("ktits_kaz_unwait_desc", "Ждать надоело даже казуалам. Туман пора подталкивать. (Снимает «ждать»: восстание снова доступно)")
add("ktits_kaz_support", "Снабдить повстанцев")
add("ktits_kaz_support_desc", "Из Ставки идут обозы: мука, вилы и немного уверенности. (+1000 пехотного снаряжения повстанцам, их атака +5 % на 60 дней; 30 ПВ, перезарядка 60 дн.)")
add("ktits_kaz_prop", "Пропаганда лени")
add("ktits_kaz_prop_desc", "В газетах страны-цели вдруг появляются заметки: «Работа не волк», «Утро вечера мудренее», «Завтра тоже будет день». Редакторы клянутся, что не писали, но печатают. (Шкала Казуальности страны-цели +5; 40 ПВ, перезарядка 45 дн.)")
add("ktits_kaz_party", "Поддержка казуальной партии")
add("ktits_kaz_party_desc", "Казуальная партия в чужой стране вчера не собралась на съезд, сегодня не выдвинула кандидатов, а завтра, по слухам, наберёт больше голосов, чем все. Ставка присылает ей чай, мёд и тёплые пледы. (Популярность Казуальности в стране-цели +5 %; 50 ПВ, перезарядка 90 дн.)")
add("ktits_kaz_unrest", "Убаюкать власть")
add("ktits_kaz_unrest_desc", "К чиновникам цели приходят посланцы с калачами и колыбельными. Через неделю министры зевают на заседаниях, через месяц заседания переносят на после обеда, который никогда не наступает. (Стабильность страны-цели −5 %, поддержка войны −5 %; 60 ПВ, перезарядка 90 дн.)")
add("ktits_kaz_tt_waitset", "Казуалия ждёт: шкала страны растёт на 1 в месяц")
add("ktits_kaz_tt_rebel_go", "В стране-цели начнётся Казуальное восстание")
add("ktits_kaz_tt_prop", "Шкала Казуальности страны-цели: §Y+5§!")
add("ktits_kaz_tt_party", "Популярность Казуальности в стране-цели: §G+5 %§!")
add("ktits_kaz_tt_unrest", "Стабильность страны-цели: §R−5 %§!, поддержка войны: §R−5 %§!")
# who is listed: not Kazualia, not an own subject, not K35, not a rebel country, not fallen; plus a neighbour / scale 25+ / waiting
TARGET_BASE = """FROM = {
                exists = yes
                NOT = { has_country_flag = ktits_casuality_fallen }
                NOT = { has_country_flag = ktits_kz_rebel }
                NOT = { ktits_is_kazualia = yes }
                NOT = { is_subject_of = ROOT }
                NOT = { original_tag = K35 }
                OR = {
                    is_neighbor_of = ROOT
                    has_country_flag = ktits_kz_waiting
                    check_variable = { var = ktits_casuality value = 25 compare = greater_than_or_equals }
                }
            }"""
CD = lambda f_: f"""            custom_trigger_tooltip = {{
                tooltip = ktits_kaz_tt_cd
                NOT = {{ has_country_flag = {f_} }}
            }}
"""
OUT_VIS = "visible = {\n            ktits_is_kazualia = yes\n            has_country_flag = ktits_kaz_f_outer\n        }"
# AI of the Great Casuality path acts on weak bordering countries first (docs/mechanics/Kazualia.md, "ИИ Внешней Казуальности"):
# neighbour x3; weaker than Kazualia (army strength ratio, [uncertain] direction of strength_ratio) x2; target scale 50+ x2; far or strong x0.2
AIT = ("\n            modifier = { factor = 3 has_country_flag = ktits_kaz_great FROM = { is_neighbor_of = ROOT } }"
       "\n            modifier = { factor = 2 has_country_flag = ktits_kaz_great FROM = { strength_ratio = { tag = ROOT ratio < 1 } } }"
       "\n            modifier = { factor = 2 has_country_flag = ktits_kaz_great FROM = { check_variable = { var = ktits_casuality value = 50 compare = greater_than_or_equals } } }"
       "\n            modifier = {"
       "\n                factor = 0.2"
       "\n                has_country_flag = ktits_kaz_great"
       "\n                FROM = { OR = { NOT = { is_neighbor_of = ROOT } strength_ratio = { tag = ROOT ratio > 2 } } }"
       "\n            }")
def tdec(did, avail, cost, cdflag, cd, effect, ai):
    cost_s = f"        cost = {cost}\n" if cost else ""
    return f"""    {did} = {{
        icon = generic_propaganda
        {OUT_VIS}
        target_trigger = {{
            {TARGET_BASE}
        }}
        available = {{
{CD(cdflag) if cdflag else ""}{avail}        }}
{cost_s}        fire_only_once = no
        complete_effect = {{
{("            set_country_flag = { flag = " + cdflag + " days = " + str(cd) + " value = 1 }" + chr(10)) if cdflag else ""}{effect}        }}
        ai_will_do = {{ {ai}{AIT} }}
    }}

"""
FR = lambda inner_: "            FROM = {\n" + inner_ + "            }\n"
def ctt(tip, body):
    return f"                custom_trigger_tooltip = {{\n                    tooltip = {tip}\n" + "".join(f"                    {l}\n" for l in body) + "                }\n"
SCALE = lambda lo, hi: [f"check_variable = {{ var = ktits_casuality value = {lo} compare = greater_than_or_equals }}", f"check_variable = {{ var = ktits_casuality value = {hi} compare = less_than }}"]
NOTACT = ["NOT = { has_country_flag = ktits_kz_rebel_active }", "NOT = { has_country_flag = ktits_kz_waiting }"]
mission_cost = "            custom_trigger_tooltip = {\n                tooltip = ktits_kaz_need_mission\n                check_variable = { var = ktits_kaz_faith value = ktits_kaz_c_mission compare = greater_than_or_equals }\n            }\n"
dec += "ktits_kaz_outer_category = {\n\n"
dec += T(
    tdec("ktits_kaz_rebel",
         "            custom_trigger_tooltip = {\n                tooltip = ktits_kz_tt_slot\n                ktits_kz_slot_free = yes\n            }\n"
         + FR(ctt("ktits_kz_tt_need75", SCALE(75, 100)) + ctt("ktits_kz_tt_calm", NOTACT + ["NOT = { has_idea = ktits_kaz_sobering }"])),
         75, "ktits_kaz_cd_rebel", 30,
         "            custom_effect_tooltip = ktits_kaz_tt_rebel_go\n            FROM = { ktits_kz_rebel_raise = yes }\n",
         "base = 1\n            modifier = { add = 3 has_country_flag = ktits_kaz_great }")
    + tdec("ktits_kaz_wait", FR(ctt("ktits_kz_tt_wait10", SCALE(10, 100) + NOTACT)), 0, None, 0,
           "            custom_effect_tooltip = ktits_kaz_tt_waitset\n            FROM = { set_country_flag = ktits_kz_waiting }\n", "base = 2")
    + f"""    ktits_kaz_unwait = {{
        icon = generic_propaganda
        {OUT_VIS}
        target_trigger = {{
            FROM = {{
                exists = yes
                has_country_flag = ktits_kz_waiting
            }}
        }}
        cost = 0
        fire_only_once = no
        complete_effect = {{
            FROM = {{ clr_country_flag = ktits_kz_waiting }}
        }}
        ai_will_do = {{ base = 0 }}
    }}

"""
    + f"""    ktits_kaz_support = {{
        icon = generic_propaganda
        {OUT_VIS}
        target_trigger = {{
            FROM = {{
                exists = yes
                has_country_flag = ktits_kz_rebel
            }}
        }}
        available = {{
{CD("ktits_kaz_cd_support")}{FR(ctt("ktits_kz_tt_war_rebels", ["has_war = yes"]))}        }}
        cost = 30
        fire_only_once = no
        complete_effect = {{
            set_country_flag = {{ flag = ktits_kaz_cd_support days = 60 value = 1 }}
            FROM = {{
                add_equipment_to_stockpile = {{ type = infantry_equipment_1 amount = 1000 }}
                add_timed_idea = {{ idea = ktits_kaz_rebels_t days = 60 }}
            }}
        }}
        ai_will_do = {{ base = 2 }}
    }}

"""
    + tdec("ktits_kaz_gift_mission",
           mission_cost + FR(ctt("ktits_kz_tt_border", ["is_neighbor_of = ROOT"]) + ctt("ktits_kz_tt_scale99", SCALE(0, 100))),
           0, "ktits_kaz_cd_mission", 60,
           "            subtract_from_variable = { var = ktits_kaz_faith value = ktits_kaz_c_mission }\n            FROM = {\n                add_to_variable = { var = ktits_casuality value = 10 }\n                clamp_variable = { var = ktits_casuality min = 0 max = 100 }\n                ktits_casuality_update = yes\n            }\n",
           "base = 1")
    + tdec("ktits_kaz_prop", FR(ctt("ktits_kz_tt_scale99", SCALE(0, 100))), 40, "ktits_kaz_cd_prop", 45,
           "            custom_effect_tooltip = ktits_kaz_tt_prop\n            FROM = {\n                add_to_variable = { var = ktits_casuality value = 5 }\n                clamp_variable = { var = ktits_casuality min = 0 max = 100 }\n                ktits_casuality_update = yes\n            }\n",
           "base = 1")
    + tdec("ktits_kaz_party", FR(ctt("ktits_kz_tt_scale25", ["check_variable = { var = ktits_casuality value = 25 compare = greater_than_or_equals }"])), 50, "ktits_kaz_cd_party", 90,
           "            custom_effect_tooltip = ktits_kaz_tt_party\n            FROM = { add_popularity = { ideology = casuality popularity = 0.05 } }\n", "base = 0.5")
    + tdec("ktits_kaz_unrest", FR(ctt("ktits_kz_tt_scale25", ["check_variable = { var = ktits_casuality value = 25 compare = greater_than_or_equals }"])), 60, "ktits_kaz_cd_unrest", 90,
           "            custom_effect_tooltip = ktits_kaz_tt_unrest\n            FROM = {\n                add_stability = -0.05\n                add_war_support = -0.05\n            }\n", "base = 0.2")
) + "}\n\n"
# Soviet Union: buffer on the swamps
add("ktits_sov_buffer", "Буфер на болотах")
add("ktits_sov_buffer_desc", "Союз решил: пусть лучше у казуалов-переселенцев будет своя земля, и стоит она между ним и Ставкой. (Болотные штаты на границе с Казуалией становятся марионеткой «Наши Болота»; шкала Казуальности у неё 25, идеология не Казуальность; 100 ПВ)")
add("ktits_kz_tt_nb", "Советский Союз создаёт марионетку «Наши Болота» на болотных штатах у границы с Казуалией")
add("ktits_kz_tt_nb_state", "Советскому Союзу принадлежит хотя бы один болотный штат Наших Болот")
dec += "ktits_sov_buffer_category = {\n\n" + T(f"""    ktits_sov_buffer = {{
        icon = generic_propaganda
        visible = {{
            original_tag = {SOV}
            K35 = {{ exists = no }}
        }}
        available = {{
            is_subject = no
            custom_trigger_tooltip = {{
                tooltip = ktits_kz_tt_nb_state
                any_owned_state = {{ OR = {{ {SW_OR} }} }}
            }}
        }}
        cost = 100
        fire_only_once = yes
        complete_effect = {{
            custom_effect_tooltip = ktits_kz_tt_nb
            hidden_effect = {{ ktits_kz_make_K35 = yes }}
        }}
        ai_will_do = {{ base = 0.5 }}
    }}
}}
""")
w("common/decisions/ktits_kazualia_outer_decisions.txt", dec)

# ---------------- events ----------------
EVT = [
    (2, "Туман рассеялся", "Восстание подавлено, туман рассеялся. Люди протирают глаза и с удивлением смотрят на заросшие поля и брошенные станки. Ещё долго никто не захочет даже слышать о том, чтобы прилечь «на минутку». (Шкала Казуальности обнулена; дух «Отрезвление» на год запрещает новое восстание.)", "Протереть глаза", ""),
    (3, "Восстание подавлено", "Повстанцев загнали обратно в камыши, а оттуда — в тишину. Ставка вздыхает: туман придётся сгущать заново. (Внутренняя Казуальность −5 %.)", "Переживём", ""),
    (20, "Старая Казуалия не хочет просыпаться", "Старая Казуалия не захотела просыпаться. Реакционные казуалы ушли в болота, подняли зелёное знамя и объявили новую власть ересью беспокойства. (Часть штатов отделяется и воюет с правительством.)", "Подавить мятеж", "ktits_kz_civwar_raise = yes"),
    (21, "Победа правительства", "Последние реакционеры вышли из тумана сдаваться. Многие честно признались, что просто устали прятаться. (Стабильность +10 %, Внутренняя Казуальность −10 %.)", "Слава бодрствованию", ""),
    (22, "Победа Казуалов", "Болото поглотило реформы. Ставка снова спит, и всем снова хорошо. (Казуальность вернулась на трон; Внутренняя Казуальность +15 %, прогресс реформ −30.)", "Всё как раньше", ""),
]
ev = "add_namespace = ktits_kz_out\n\n"
for eid, ti, de, op, eff in EVT:
    add(f"ktits_kz_out.{eid}.t", ti); add(f"ktits_kz_out.{eid}.d", de); add(f"ktits_kz_out.{eid}.a", op)
    ev += T(f"""country_event = {{
    id = ktits_kz_out.{eid}
    title = ktits_kz_out.{eid}.t
    desc = ktits_kz_out.{eid}.d
    picture = GFX_report_event_ktits_casuality
    is_triggered_only = yes
    fire_only_once = no

    option = {{
        name = ktits_kz_out.{eid}.a
{('        ' + eff + chr(10)) if eff else ''}    }}
}}

""")
for i, (t, nm) in enumerate(SLOTS):
    eid = 10 + i
    add(f"ktits_kz_out.{eid}.t", f"Восстание победило: {nm}")
    add(f"ktits_kz_out.{eid}.d", f"Повстанцы устояли, и страна-цель не смогла их задавить. Над болотами снова зелёное знамя, а в камышах поют. Ставка раскрывает объятия: места в тумане хватит всем. ({nm}: принять в Ставку или оставить марионеткой.)")
    add(f"ktits_kz_out.{eid}.a", "Принять в Ставку")
    add(f"ktits_kz_out.{eid}.b", "Оставить марионеткой")
    ev += T(f"""country_event = {{
    id = ktits_kz_out.{eid}
    title = ktits_kz_out.{eid}.t
    desc = ktits_kz_out.{eid}.d
    picture = GFX_report_event_ktits_casuality
    is_triggered_only = yes
    fire_only_once = no

    option = {{
        name = ktits_kz_out.{eid}.a
        trigger = {{ {t} = {{ exists = yes }} }}
        {t} = {{ every_owned_state = {{ add_core_of = {KAZ} }} }}
        annex_country = {{ target = {t} transfer_troops = yes }}
        add_to_variable = {{ var = ktits_kaz_inner value = 5 }}
        ktits_kaz_inner_update = yes
    }}
    option = {{
        name = ktits_kz_out.{eid}.b
        trigger = {{ {t} = {{ exists = yes }} }}
        puppet = {t}
    }}
}}

""")
w("events/ktits_kazualia_outer_events.txt", "﻿" + ev)

# ---------------- on_actions ----------------
w("common/on_actions/ktits_kazualia_outer_on_actions.txt", """on_actions = {
    on_monthly = {
        effect = {
            ktits_kz_rebel_monthly = yes
            if = {
                limit = { ktits_is_kazualia = yes }
                ktits_kaz_outer_update = yes
                ktits_kz_civwar_check = yes
            }
        }
    }
}
""")

# ---------------- scripted GUI: two scale bars (segments of the scale of make_casuality.py) ----------------
SEG_N, SEG_W, GAP, BAR_X = 20, 22, 1, 14
def gui_pair(prefix, var, label_key, tip_key):
    trg = "".join(f"            {prefix}_seg_{i}_visible = {{\n                check_variable = {{ var = {var} value = {i * 5} compare = greater_than_or_equals }}\n            }}\n" for i in range(1, SEG_N + 1))
    sg = f"    {prefix}_ui = {{\n        context_type = decision_category\n        window_name = \"{prefix}_ui_window\"\n\n        triggers = {{\n{trg}        }}\n    }}\n"
    g = f"    containerWindowType = {{\n        name = \"{prefix}_ui_window\"\n        position = {{ x = 0 y = 0 }}\n        size = {{ width = 100% height = 50 }}\n        clipping = no\n\n"
    g += f"        instantTextBoxType = {{\n            name = \"{prefix}_label\"\n            position = {{ x = {BAR_X} y = 2 }}\n            font = \"hoi_16mbs\"\n            text = \"{label_key}\"\n            format = left\n            maxHeight = 18\n            maxwidth = 470\n        }}\n\n"
    g += f"        iconType = {{\n            name = \"{prefix}_frame\"\n            spriteType = \"GFX_ktits_cas_bar_frame\"\n            position = {{ x = {BAR_X} y = 22 }}\n            pdx_tooltip = \"{tip_key}\"\n        }}\n\n"
    for i in range(1, SEG_N + 1):
        g += f"        iconType = {{\n            name = \"{prefix}_seg_{i}\"\n            spriteType = \"GFX_ktits_cas_seg_{(i - 1) // 5 + 1}\"\n            position = {{ x = {BAR_X + 3 + (i - 1) * (SEG_W + GAP)} y = 25 }}\n        }}\n"
    return sg, g + "    }\n"
sg1, g1 = gui_pair("ktits_kin", "ktits_kaz_inner", "ktits_kin_bar_label", "ktits_kin_bar_tt")
sg2, g2 = gui_pair("ktits_kout", "ktits_kaz_outer", "ktits_kout_bar_label", "ktits_kout_bar_tt")
w("common/scripted_guis/ktits_kazualia.txt", "scripted_gui = {\n\n" + sg1 + "\n" + sg2 + "}\n")
w("interface/ktits_kazualia.gui", "guiTypes = {\n\n" + g1 + "\n" + g2 + "}\n", "utf-8")
add("ktits_kin_bar_label", "Внутренняя Казуальность: [?ktits_kaz_inner|0] %")
add("ktits_kin_bar_tt", "Каждое деление — 5 %. Даёт армии баффы, режет производство и строительство; выше 80 % фокусы и решения опаздывают.")
add("ktits_kout_bar_label", "Внешняя Казуальность: [?ktits_kaz_outer|0] % стран")
add("ktits_kout_bar_tt", "Доля остальных стран, где Казуальность уже живёт: шкала не ниже 50, пала в Казуальность или правит идеология Казуальность. Каждое деление — 5 %.")

# rulers of K35: title and description (the key <id>_desc is the usual character description key) [uncertain: whether the leader window shows it]
for _cid, _n, _ide, _title, _d in K35_RULERS:
    add(_cid, _n)
    add(_cid + "_title", _title)
    add(_cid + "_desc", f"{_title}. {_d}")

# ---------------- localisation ----------------
seen = set(); ru2, en2 = [], []
for (k, r), (_k, e) in zip(ru, en):
    if k in seen:
        continue
    seen.add(k); ru2.append((k, r)); en2.append((k, e))
L.write_yml(str(M / "localisation/russian/ktits_kazualia_outer_l_russian.yml"), "russian", ru2)
L.write_yml(str(M / "localisation/english/ktits_kazualia_outer_l_english.yml"), "english", en2)
print(f"kazualia outer: {len(ru2)} loc keys; slots {SLOT_TAGS}; K35 on {len(swamp_sov)} states")
