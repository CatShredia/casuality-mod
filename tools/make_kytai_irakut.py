"""Restore pre-export borders or apply the starting Kytai split and existing enclaves."""
import argparse
import colorsys
import re
import shutil
from pathlib import Path

import kytai_irakut_data as D
import lore_data as L

ap = argparse.ArgumentParser()
ap.add_argument('--mod', default=L.DEFAULT_MOD)
ap.add_argument('--restore', action='store_true')
a = ap.parse_args()
M = Path(a.mod)
tags_file = M / 'common/country_tags/02_countries.txt'
states_dir = M / 'history/states'
backup_dir = L.REPO / 'no_commit/temp/backup_kytai_start'

def state_path(sid):
    p = states_dir / f'{sid}.txt'
    assert p.is_file(), f'missing state {sid}; map changed, review starting borders'
    return p

def replace_owner(sid, permitted, owner):
    p = state_path(sid)
    raw = p.read_bytes()
    text = raw.decode('utf-8-sig')
    m = re.search(r'(?m)^(\s*owner\s*=\s*)(\w+)', text)
    assert m and m.group(2) in permitted, f'{sid}: unexpected owner {m.group(2) if m else None}'
    text = text[:m.start(2)] + owner + text[m.end(2):]
    p.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'') + text.encode('utf-8'))

extra_tags = set(D.KYT) - {'AFR'}
if a.restore:
    previously_split = bool(re.search(r'(?m)^X01\s*=', tags_file.read_text(encoding='utf-8-sig')))
    if previously_split:
        for filename in ('AFR_1936.txt', 'AFR_1936_nsb.txt', 'AFR_1936_naval.txt', 'AFR_1936_naval_mtg.txt'):
            src = backup_dir / filename
            assert src.exists(), f'missing original unit backup {src}'
            shutil.copyfile(src, M / 'history/units' / filename)
    for tag, (_, _, ids) in D.KYT.items():
        for sid in ids:
            replace_owner(sid, {'AFR', tag}, 'AFR')
    for sid, (old, new) in D.ENCLAVES.items():
        replace_owner(sid, {old, new}, old)
    raw = tags_file.read_bytes()
    text = raw.decode('utf-8-sig')
    text = re.sub(r'(?m)^X0[1-9]\s*=\s*"countries/X0[1-9]\.txt"\s*\r?\n?', '', text)
    tags_file.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'') + text.encode('utf-8'))
    print('starting borders restored for population and post-export generators')
    raise SystemExit

info = L.load_mod(M)
actual = {sid for sid, st in info['states'].items() if st['owner'] == 'AFR'}
expected = {sid for _, _, ids in D.KYT.values() for sid in ids}
assert len(expected) == sum(len(ids) for _, _, ids in D.KYT.values()) and actual == expected, f'Kytai states changed: missing={sorted(expected-actual)}, extra={sorted(actual-expected)}'
assert not (extra_tags & set(info['tags'])), 'new X tags already used'
backup_dir.mkdir(parents=True, exist_ok=True)
for filename in ('AFR_1936.txt', 'AFR_1936_nsb.txt', 'AFR_1936_naval.txt', 'AFR_1936_naval_mtg.txt'):
    src = M / 'history/units' / filename
    assert src.is_file(), f'missing Kytai unit file {src}'
    shutil.copyfile(src, backup_dir / filename)
for sid, (old, _) in D.ENCLAVES.items():
    assert info['states'][sid]['owner'] == old, f'enclave {sid} no longer belongs to {old}'
for tag, (_, _, ids) in D.KYT.items():
    for sid in ids:
        replace_owner(sid, {'AFR'}, tag)
        if tag != 'AFR':
            p = state_path(sid)
            raw = p.read_bytes(); t = raw.decode('utf-8-sig')
            t = re.sub(r'(?m)^\s*add_core_of\s*=\s*X0[1-9]\s*\r?\n', '', t)
            t = re.sub(r'(?m)^(\s*owner\s*=\s*' + tag + r'[^\r\n]*\r?\n)', r'\1\t\tadd_core_of = ' + tag + '\n', t, count=1)
            p.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'') + t.encode('utf-8'))
for sid, (old, new) in D.ENCLAVES.items():
    replace_owner(sid, {old}, new)

base = (M / 'common/countries' / f"{info['tags']['AFR']}.txt").read_text(encoding='utf-8-sig')
color_entries = []
for i, (tag, (name, leader, ids)) in enumerate(D.KYT.items()):
    if tag == 'AFR':
        continue
    cap = max(ids, key=lambda sid: (sum(v for _, v in info['states'][sid]['vps']), info['states'][sid]['manpower']))
    prov = info['states'][cap]['provs'][0]
    rgb = tuple(round(255*x) for x in colorsys.hsv_to_rgb((0.025 + i*0.095) % 1, 0.48, 0.72))
    color_entries.append(f'{tag} = {{\n\tcolor = rgb {{ {rgb[0]} {rgb[1]} {rgb[2]} }}\n\tcolor_ui = rgb {{ {rgb[0]} {rgb[1]} {rgb[2]} }}\n}}\n')
    text = re.sub(r'color\s*=\s*\{[^}]*\}', 'color = { %d %d %d }' % rgb, base, count=1)
    (M / f'common/countries/{tag}.txt').write_text(text, encoding='utf-8')
    (M / f'common/characters/{tag}.txt').write_text(f'characters = {{\n\t{tag}_leader = {{\n\t\tname = "{leader}"\n\t\tcountry_leader = {{ ideology = oligarchism traits = {{ }} expire = "1965.1.1.1" id = -1 }}\n\t}}\n\t{tag}_casuality_leader = {{\n\t\tname = "Казуал-Предводитель"\n\t\tcountry_leader = {{ ideology = casuality_ideology traits = {{ }} expire = "1965.1.1.1" id = -1 }}\n\t}}\n}}\n', encoding='utf-8-sig')
    (M / f'history/countries/{tag} - {tag}.txt').write_text(f'capital = {cap}\nset_technology = {{ infantry_weapons = 1 }}\nset_politics = {{ ruling_party = neutrality last_election = "1936.1.1" election_frequency = 48 elections_allowed = no }}\nset_popularities = {{ democratic = 10 fascism = 10 communism = 10 neutrality = 70 casuality = 0 theology = 0 }}\nrecruit_character = {tag}_leader\nrecruit_character = {tag}_casuality_leader\nadd_ideas = ktits_edu_2\noob = "{tag}_1936"\n', encoding='utf-8')
    (M / f'history/units/{tag}_1936.txt').write_text(f'division_template = {{ name = "Militia Division" regiments = {{ infantry = {{ x = 0 y = 0 }} infantry = {{ x = 0 y = 1 }} infantry = {{ x = 1 y = 0 }} infantry = {{ x = 1 y = 1 }} }} }}\nunits = {{ division = {{ name = "{tag} 1st Militia" location = {prov} division_template = "Militia Division" start_experience_factor = 0.1 start_equipment_factor = 0.8 }} }}\n', encoding='utf-8')
    for d in ('gfx/flags', 'gfx/flags/medium', 'gfx/flags/small'):
        shutil.copyfile(M / d / 'AFR.tga', M / d / f'{tag}.tga')
    for lang in ('russian', 'english'):
        p = M / f'localisation/{lang}/countries_l_{lang}.yml'
        raw = p.read_bytes(); t = raw.decode('utf-8-sig')
        t = re.sub(r'(?m)^\s*' + tag + r'(?:_\w+)?:\d*[^\r\n]*\r?\n', '', t)
        nm = name if lang == 'russian' else L.translit(name)
        t = t.rstrip() + '\n' + ''.join(f' {tag}_{group}{suffix}:0 "{nm}"\n' for group in ('fascism','communism','neutrality','democratic','casuality','theology') for suffix in ('', '_DEF', '_ADJ'))
        t += f' {tag}:0 "{nm}"\n {tag}_DEF:0 "{nm}"\n {tag}_ADJ:0 "{nm}"\n'
        p.write_bytes(b'\xef\xbb\xbf' + t.encode('utf-8'))

# Keep the original Kytai army/fleet in the territory retained by AFR.
parent_provinces = {p for sid in D.KYT['AFR'][2] for p in info['states'][sid]['provs']}
capital_province, home_port = 3056, 3057
assert capital_province in parent_provinces and home_port in parent_provinces
for filename in ('AFR_1936.txt', 'AFR_1936_nsb.txt'):
    p = M / 'history/units' / filename
    t = p.read_text(encoding='utf-8-sig')
    t = re.sub(r'(\blocation\s*=\s*)(\d+)', lambda m: m.group(1) + (m.group(2) if int(m.group(2)) in parent_provinces else str(capital_province)), t)
    p.write_text(t, encoding='utf-8')
for filename in ('AFR_1936_naval.txt', 'AFR_1936_naval_mtg.txt'):
    p = M / 'history/units' / filename
    t = p.read_text(encoding='utf-8-sig')
    t = re.sub(r'(\b(?:naval_base|location)\s*=\s*)(\d+)', lambda m: m.group(1) + (m.group(2) if int(m.group(2)) in parent_provinces else str(home_port)), t)
    p.write_text(t, encoding='utf-8')

for rel in ('common/names/00_names.txt', 'portraits/998_scientist_portraits.txt'):
    p = M / rel
    if not p.exists():
        continue
    raw = p.read_bytes(); t = raw.decode('utf-8-sig')
    t = re.sub(r'(?ms)^X0[1-9] = \{\n.*?^\}[ \t]*\n?', '', t.replace('\r\n', '\n'))
    m = re.search(r'(?ms)^AFR = \{\n.*?^\}[ \t]*(?:\n|$)', t)
    if m:
        t = t.rstrip() + '\n' + ''.join(re.sub(r'^AFR', tag, m.group(0)) for tag in sorted(extra_tags))
    p.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'') + t.encode('utf-8'))

colors = M / 'common/countries/colors.txt'
raw = colors.read_bytes(); t = raw.decode('utf-8-sig').replace('\r\n', '\n')
t = re.sub(r'(?ms)^X0[1-9] = \{.*?^\}[ \t]*\n?', '', t)
colors.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'') + (t.rstrip() + '\n' + ''.join(color_entries)).encode('utf-8'))

with tags_file.open('a', encoding='utf-8', newline='\n') as f:
    f.write('\n' + ''.join(f'{tag} = "countries/{tag}.txt"\n' for tag in sorted(extra_tags)))
print('Kytai split:', {tag: ids for tag, (_, _, ids) in D.KYT.items()})
print('Irakut transferred:', D.ENCLAVES)
