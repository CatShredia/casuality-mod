"""Unique continuous focuses of the mod (docs/global_mechanics/Casuality-Mechanic.md, section "Непрерывные фокусы"; docs/global_mechanics/Alliances.md).
 * ktits_cont_fight_lazy  "Борьба с ленью": Casuality scale -1 a month, consumer_goods_factor +10 %;
 * ktits_cont_swamp_peace "Болотный покой": stability +10 %, Casuality scale +1 a month;
 * ktits_cont_ally_strong "Укрепление альянса": cooperation scale of the alliance +1 a month, cooperation decisions 10 % cheaper.
Palette: the vanilla palette generic_focus (common/continuous_focus/generic.txt, already in the mod) gets the three focuses inside a marked block (idempotent).
No known trigger "this continuous focus is active" (not in documentation/): select_effect / cancel_effect set / clear a country flag, the monthly effect reads the flag [uncertain: in game not checked].
Writes: common/continuous_focus/generic.txt (block), common/scripted_effects/ktits_continuous_effects.txt, common/on_actions/ktits_continuous_on_actions.txt, localisation ru/en.
Run after make_alliances.py (uses ktits_ally_member_coop_p1, ktits_ally_costs, ktits_ally_in_kaz) and make_casuality.py (ktits_casuality_update).
Usage: python tools/make_continuous.py [--mod PATH]
"""
import argparse, re
from pathlib import Path
import lore_data as L

# id, flag, icon (vanilla interface/goals.gfx), ru name, en name, ru desc, en desc [invented, docs/lore/Invented-Lore.md]
FOCI = [
    ("ktits_cont_fight_lazy", "ktits_cont_f_lazy", "GFX_goal_continuous_suppression",
     "Борьба с ленью", "War on Laziness",
     "Утром у конторы собирается комиссия по бодрости и громко будит всех, кто ещё не проснулся. Работает странно: заводы дымят чуть охотнее, лавки полны чуть больше, а в тумане всё равно кто-то зевает. Лень отступает на шаг в месяц и каждый раз возвращается за забытым зонтиком.",
     "Each morning a commission for vigour gathers outside the office and loudly wakes everyone who has not yet woken up. It works oddly: the factories smoke a little more willingly, the shops are a little fuller, and somewhere in the fog someone is still yawning. Laziness retreats one step a month and comes back each time for a forgotten umbrella."),
    ("ktits_cont_swamp_peace", "ktits_cont_f_swamp", "GFX_goal_continuous_boost_freedom",
     "Болотный покой", "Swamp Calm",
     "Власти перестают торопить кого бы то ни было: над низинами стелется туман, в камышах квакает вечность, и всем вдруг становится спокойно. Налоги собираются сами, споры затихают сами, а список дел переписывается на «завтра», потом на «когда-нибудь». Болото тянет вниз ласково и без шума.",
     "The authorities stop hurrying anyone: fog spreads over the lowlands, eternity croaks in the reeds, and suddenly everyone feels calm. Taxes collect themselves, quarrels fade by themselves, and the to-do list is rewritten for tomorrow, then for someday. The swamp pulls down gently and without a sound."),
    ("ktits_cont_ally_strong", "ktits_ally_f_strong", "GFX_goal_continuous_research",
     "Укрепление альянса", "Strengthening the Alliance",
     "Союзники то и дело обмениваются письмами, чаем и обещаниями вскоре встретиться. Курьеры идут в обе стороны без спешки, но доходят, а канцеляриям стало проще: общие бланки, общие печати, общий чай. Совместные дела обходятся дешевле, потому что половину из них все уже сделали по привычке.",
     "The allies keep exchanging letters, tea and promises to meet soon. Couriers travel both ways without haste but arrive, and the chancelleries have it easier: shared forms, shared seals, shared tea. Joint ventures cost less, because by habit everybody has already done half of them."),
]
BEGIN, END = "\t# >>> ktits continuous focuses (tools/make_continuous.py)\n", "\t# <<< ktits continuous focuses\n"
CAS_AVAIL = "\t\t\tNOT = { ktits_is_kazualia = yes }\n\t\t\tNOT = { has_country_flag = ktits_casuality_fallen }\n"

def focus(fid, flag, icon, mod, avail, enable, extra_sel=""):
    return (f"\tfocus = {{\n\t\tid = {fid}\n\t\ticon = {icon}\n\n\t\tavailable = {{\n{avail}\t\t}}\n\n\t\tenable = {{\n{enable}\t\t}}\n\n"
            f"\t\tmodifier = {{\n{mod}\t\t}}\n\n\t\tai_will_do = {{\n\t\t\tfactor = 0\n\t\t}}\n\n\t\tdaily_cost = 1\n\t\tavailable_if_capitulated = no\n\n"
            f"\t\tselect_effect = {{\n\t\t\tset_country_flag = {flag}\n{extra_sel}\t\t}}\n\n\t\tcancel_effect = {{\n\t\t\tclr_country_flag = {flag}\n{extra_sel}\t\t}}\n\t}}\n\n")

BLOCK = BEGIN
BLOCK += focus("ktits_cont_fight_lazy", "ktits_cont_f_lazy", FOCI[0][2], "\t\t\tconsumer_goods_factor = 0.1\n", CAS_AVAIL, CAS_AVAIL)
BLOCK += focus("ktits_cont_swamp_peace", "ktits_cont_f_swamp", FOCI[1][2], "\t\t\tstability_factor = 0.1\n", CAS_AVAIL, CAS_AVAIL)
ALLY = "\t\t\tis_in_faction = yes\n\t\t\tNOT = { ktits_ally_in_kaz = yes }\n"
BLOCK += focus("ktits_cont_ally_strong", "ktits_ally_f_strong", FOCI[2][2], "", ALLY, ALLY, "\t\t\tktits_ally_costs = yes\n")
BLOCK += END

ap = argparse.ArgumentParser()
ap.add_argument("--mod", default=L.DEFAULT_MOD)
a = ap.parse_args()
M = Path(a.mod)
def w(rel, text):
    p = M / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding="utf-8", newline="\n")

# palette: replace the old block, else insert before the last closing brace
pal = M / "common/continuous_focus/generic.txt"
t = pal.read_text(encoding="utf-8-sig")
t = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), "", t, flags=re.S)
# vanilla leftover: fix_vanilla_leftovers cut the hyphenated id ETH_anti-italian_propaganda to "always = no-italian_propaganda" (invalid); the focus is gone, so it is always = no
t = re.sub(r"always = no-[\w-]*", "always = no", t)
i = t.rstrip().rfind("}")
t = t[:i].rstrip("\n") + "\n\n" + BLOCK + "}\n"
pal.write_text(t, encoding="utf-8", newline="\n")

w("common/scripted_effects/ktits_continuous_effects.txt", """# scope = a country, once a month (docs/global_mechanics/Casuality-Mechanic.md "Непрерывные фокусы"). Flags are set by select_effect / cleared by cancel_effect of the focus
ktits_cont_monthly = {
	if = {
		limit = {
			OR = {
				ktits_is_kazualia = yes
				has_country_flag = ktits_casuality_fallen
			}
		}
		clr_country_flag = ktits_cont_f_lazy
		clr_country_flag = ktits_cont_f_swamp
	}
	if = {
		limit = { has_country_flag = ktits_cont_f_lazy }
		add_to_variable = { var = ktits_casuality value = -1 }
		clamp_variable = { var = ktits_casuality min = 0 max = 100 }
		ktits_casuality_update = yes
	}
	if = {
		limit = { has_country_flag = ktits_cont_f_swamp }
		add_to_variable = { var = ktits_casuality value = 1 }
		clamp_variable = { var = ktits_casuality min = 0 max = 100 }
		ktits_casuality_update = yes
	}
	if = {
		limit = { has_country_flag = ktits_ally_f_strong }
		if = {
			limit = {
				is_in_faction = yes
				NOT = { ktits_ally_in_kaz = yes }
			}
			ktits_ally_member_coop_p1 = yes
		}
		else = {
			clr_country_flag = ktits_ally_f_strong
			ktits_ally_costs = yes
		}
	}
}
""")
w("common/on_actions/ktits_continuous_on_actions.txt", "on_actions = {\n\ton_monthly = {\n\t\teffect = {\n\t\t\tktits_cont_monthly = yes\n\t\t}\n\t}\n}\n")
ru, en = [], []
for fid, _fl, _ic, rn, en_n, rd, ed in FOCI:
    ru += [(fid, rn), (fid + "_desc", rd)]; en += [(fid, en_n), (fid + "_desc", ed)]
L.write_yml(str(M / "localisation/russian/ktits_continuous_l_russian.yml"), "russian", ru)
L.write_yml(str(M / "localisation/english/ktits_continuous_l_english.yml"), "english", en)
print("continuous focuses:", ", ".join(f[0] for f in FOCI))
