"""Name every state of the exported mod after the lore country that owns it.

How: RandomParadox gives the mod its own tags (CHE, MAK, ...), but the country colors are exactly the lore colors from
tools/rp_input/stage_04/countryMappings.txt, so owner tag -> color -> lore country.
 * the state that contains a lore capital gets the capital's name (capitals.txt pixel -> province -> state);
 * the other lore cities (docs/01) go to the next biggest states of that country (by manpower);
 * every remaining state gets a generated name in the country's cultural style (syllable lists below).
Generated names and city placement are NOT lore; the report lists them.

Writes localisation/russian/state_names_l_russian.yml and localisation/english/state_names_l_english.yml
(Latin transliteration) in the mod, and no_commit/temp/state_names_report.csv.
Usage: python tools/make_state_names.py [--seed N] [--mod PATH]
"""
import argparse, csv, glob, random, re
from pathlib import Path
import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--mod", default="C:/Users/catsh/CatshrediasDocs/Paradox Interactive/Hearts of Iron IV/mod/Ktits")
ap.add_argument("--seed", type=int, default=2026)
ap.add_argument("--mode", choices=["lore", "style"], default="lore", help="lore: only names from docs/01, other states get '<country> N'; style: also generate names in the country's style (invented, NOT lore)")
a = ap.parse_args()
M = Path(a.mod)
rnd = random.Random(a.seed)

# ---- lore: capitals and named cities (docs/01, docs/04 section 6) ----
LORE = {
    "SVS": ("Ваньград-на-Окре", ["Ваньград-на-Димитрове", "Ваньград-на-Желтой-Реке", "Ваньград-на-Устое", "Идель-Кала", "Ак-Тау", "Ладожь", "Велеград", "Радогощь"]),
    "IRK": ("Лахарабад", ["Мултанпур", "Пешаркот"]),
    "IRR": ("Дехлагарх", ["Варанагар", "Ганджапур", "Каликата", "Мумбадеви", "Мадраспур"]),
    "MUS": ("Мандалаят", ["Рангавади", "Аюттара", "Ангкорат", "Сингапара"]),
    "TRV": ("Травопорт", ["Бонгкок", "Пыхалово", "Раскурайя", "Чиллтаун", "Умиротворенск"]),
    "ZLD": ("Мирный", ["Центр"]),
    "ADL": ("Бернхорн", []),
    "SVA": ("Ослорвик", ["Скъёльдборг", "Эльвесунд", "Фьордвик", "Ульфхейм", "Бьорнстад", "Хельмстад"]),
    "FDP": ("Депутатск", []),
    "DMK": ("Ордабад", ["Ширкент", "Кзыл-Шахр"]),
    "CLB": ("Челябинск", ["Угольдар", "Тяжпромск", "Нью-Челябинск"]),
    "MGN": ("Улан-Батыр", []),
    "KTY": ("Бэйчжао", []),
    "BLK": ("Токомэ", ["Саппорока", "Нагоясу", "Осакара", "Фукусава"]),
    "SRK": ("Кумыс-Орда", ["Ак-Сарай", "Тамгабад", "Караван-Кала"]),
    "TMR": ("Барбинсберг", []),
    "SOY": ("Поридж-Сити", []),
    "BRT": ("Большой Джон", []),
    "KZZ": ("Станица Дарьевская", []),
    "CSL": ("Ставка Казуала", []),
}

# ---- cultural styles for generated names (invented; chosen from the naming hints in docs/01) ----
STYLES = {
    "slav": (["Бело", "Черно", "Красно", "Зелено", "Гор", "Луго", "Звено", "Волко", "Медведе", "Сосно", "Дубо", "Камено", "Ржано", "Сухо", "Крива", "Ново", "Старо", "Верхо", "Ниже", "Рыбо", "Солнце", "Лесо", "Болото"],
             ["град", "гор", "ск", "ово", "ино", "ица", "поль", "зерск", "борск", "полье", "вод", "горск"]),
    "english": (["Вест", "Ист", "Норт", "Саут", "Грин", "Блэк", "Рэд", "Грей", "Стоун", "Оук", "Эш", "Бригг", "Крос", "Хай", "Лоу", "Милл", "Корн", "Лайм"],
                ["форд", "тон", "хэм", "шир", "вуд", "бридж", "мут", "порт", "филд", "бери", "ленд", "вик"]),
    "indic": (["Рама", "Кришна", "Шива", "Лакшми", "Джай", "Сури", "Нанда", "Харти", "Бхима", "Ганга", "Индра", "Каве", "Мара", "Пата", "Дева"],
              ["гарх", "нагар", "пур", "абад", "кот", "вади", "паттан", "кунд", "гарт", "ганд"]),
    "islamic": (["Мултан", "Кара", "Сарк", "Дара", "Хуш", "Заф", "Нур", "Бахр", "Касим", "Рашид", "Тахир", "Ширин", "Алам"],
                ["абад", "пур", "кот", "шахр", "кент", "кала", "дар", "ган"]),
    "seasia": (["Ава", "Мон", "Тан", "Лао", "Кхмер", "Сиам", "Пхра", "Нака", "Чианг", "Бан", "Тхай", "Сам", "Крунг"],
               ["ават", "корат", "бури", "пура", "нам", "ара", "ратана", "конг", "май", "яй"]),
    "stoner": (["Трав", "Пых", "Раскур", "Чилл", "Косяк", "Умирот", "Расслаб", "Бонг", "Дым", "Шиш", "Хмур", "Зелен", "Кайф"],
               ["порт", "ово", "айя", "таун", "град", "ск", "ино", "кок"]),
    "german": (["Берн", "Фрейн", "Грау", "Шварц", "Альт", "Нойен", "Кёнигс", "Эйзен", "Штайн", "Вальд", "Ной", "Гольд", "Рот"],
               ["берг", "бург", "штадт", "хайм", "дорф", "брюк", "хорн", "тал", "фельд", "ау"]),
    "norse": (["Ульв", "Бьёрн", "Хельм", "Фьорд", "Скъёльд", "Эльв", "Торг", "Рагн", "Гранд", "Вест", "Ост", "Нур", "Сигт"],
              ["борг", "сунд", "вик", "хельм", "стад", "хейм", "нес", "фьорд", "ленд", "вин"]),
    "steppe": (["Ак", "Кара", "Кзыл", "Ала", "Сары", "Тамга", "Караван", "Кумыс", "Бай", "Ордун", "Темир", "Тюрк", "Алтын"],
               ["орда", "сарай", "кала", "кум", "тау", "кент", "булак", "узяк"]),
    "mongol": (["Улан", "Хара", "Цаган", "Дали", "Зун", "Баруун", "Дорно", "Ундур", "Тэмэр", "Алтан", "Бор", "Хэнтий"],
               ["батыр", "хото", "орда", "нуур", "гол", "хийд", "уул"]),
    "chinese": (["Бэй", "Нань", "Дун", "Си", "Чжао", "Лун", "Хэ", "Шань", "Цзян", "Ань", "Тянь", "Фэн", "Юй"],
                ["чжао", "цзин", "фу", "чэн", "тай", "лин", "хуа", "бао", "ян", "хай"]),
    "japanese": (["Току", "Сапо", "Нагоя", "Осака", "Фуку", "Кага", "Мацу", "Хиро", "Сэнда", "Нара", "Кита", "Мина"],
                 ["мэ", "ока", "саки", "яма", "сава", "ясу", "рока", "гава", "мура", "сима"]),
    "cossack": (["Дарьев", "Станич", "Атаман", "Казач", "Хутор", "Дон", "Кубан", "Терск", "Запорож", "Верхне", "Нижне"],
                ["ская", "ская Станица", "ский Хутор", "ка", "овка", "ская Слобода"]),
    "ice": (["Лед", "Мороз", "Снеж", "Вьюж", "Иней", "Стыл", "Хлад", "Метел"],
            ["ышка", "ск", "ово", "град", "ица", "ино"]),
    "neutral": (["Северо", "Южно", "Западно", "Восточно", "Центро", "Приморо", "Горо", "Речно", "Озёрно", "Равнино"],
                ["ский Округ", "ск", "град", "зем", "вия", "мор"]),
}
COUNTRY_STYLE = {"SVS": "slav", "CLB": "slav", "FDP": "slav", "ZLD": "slav", "CSL": "slav", "KZZ": "cossack",
                 "BRT": "english", "SOY": "english", "IRK": "islamic", "IRR": "indic", "CEY": "indic", "MUS": "seasia",
                 "TRV": "stoner", "TMR": "german", "ADL": "german", "SVA": "norse", "DMK": "steppe", "SRK": "steppe",
                 "MGN": "mongol", "KTY": "chinese", "BLK": "japanese", "LED": "ice"}
STYLE_DEFAULT = "numbered"     # FIG, Z01..Z05 and other lore countries without data: "<country> <n>" (plan variant 1)
LORE_RU = {"FIG": "Фигария", "LED": "Ледышка", "Z01": "Заготовка-1", "Z02": "Заготовка-2", "Z03": "Заготовка-3", "Z04": "Заготовка-4", "Z05": "Заготовка-5", "CEY": "Цейлон"}

TR = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя", ["a", "b", "v", "g", "d", "e", "yo", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p", "r", "s", "t", "u", "f", "kh", "ts", "ch", "sh", "shch", "", "y", "", "e", "yu", "ya"]))
def translit(s):
    out = []
    for ch in s:
        low = ch.lower()
        if low in TR:
            t = TR[low]
            out.append(t.capitalize() if ch.isupper() else t)
        else:
            out.append(ch)
    return "".join(out)

def gen(style):
    stems, sufs = STYLES[style]
    st, sf = rnd.choice(stems), rnd.choice(sufs)
    if st[-1] in "аеёиоуыэюя" and sf[0] in "аеёиоуыэюя":
        st = st[:-1]                                     # no vowel clashes: Лесо + ово -> Лесово
    n = st + sf
    return n[0].upper() + n[1:]

# ---- load the mod ----
lore = {}
for l in open(REPO / "tools/rp_input/stage_04/countryMappings.txt", encoding="utf-8"):
    p = l.strip().split(";")
    if len(p) >= 6 and p[0].isdigit():
        lore[(int(p[0]), int(p[1]), int(p[2]))] = p[3]
tags = dict(re.findall(r'(\w{3})\s*=\s*"countries/(.+?)\.txt"', (M / "common/country_tags/02_countries.txt").read_text(encoding="utf-8", errors="ignore")))
tag2lore = {}
for t, f in tags.items():
    c = re.search(r"color\s*=\s*\{\s*(\d+)\s+(\d+)\s+(\d+)", (M / "common/countries" / (f + ".txt")).read_text(encoding="utf-8", errors="ignore"))
    if c and tuple(map(int, c.groups())) in lore:
        tag2lore[t] = lore[tuple(map(int, c.groups()))]

states = {}
for f in glob.glob(str(M / "history/states/*.txt")):
    t = open(f, encoding="utf-8", errors="ignore").read()
    sid = int(re.search(r"\bid\s*=\s*(\d+)", t).group(1))
    ow = re.search(r"owner\s*=\s*(\w+)", t)
    mp = re.search(r"manpower\s*=\s*(\d+)", t)
    pr = re.search(r"provinces\s*=\s*\{([^}]*)\}", t)
    states[sid] = {"owner": ow.group(1) if ow else None, "manpower": int(mp.group(1)) if mp else 0,
                   "provs": [int(x) for x in pr.group(1).split()] if pr else []}

prov_state = {p: sid for sid, s in states.items() for p in s["provs"]}
d = {}
for l in open(M / "map/definition.csv", encoding="latin1"):
    p = l.strip().split(";")
    if len(p) > 4 and p[0].isdigit():
        d[(int(p[1]), int(p[2]), int(p[3]))] = int(p[0])
pv = np.array(Image.open(M / "map/provinces.bmp").convert("RGB"))

capital_state = {}
for l in open(REPO / "tools/rp_input/stage_04/capitals.txt", encoding="utf-8"):
    p = l.strip().split(";")
    if len(p) >= 5 and p[3].isdigit():
        pid = d.get(tuple(int(v) for v in pv[int(p[4]), int(p[3])]))
        sid = prov_state.get(pid)
        if sid and tag2lore.get(states[sid]["owner"]) == p[0]:
            capital_state[p[0]] = sid

COUNTRY_RU = {}
for l in open(REPO / "tools/rp_input/stage_04/capitals.txt", encoding="utf-8"):
    p = l.strip().split(";")
    if len(p) >= 2 and len(p[0]) == 3: COUNTRY_RU[p[0]] = re.sub(r"\s*\(.*\)", "", p[1])
# ---- assign names ----
names, kind = {}, {}
used = set()
by_country = {}
for sid, s in states.items():
    by_country.setdefault(tag2lore.get(s["owner"], "?"), []).append(sid)
for lt, sids in sorted(by_country.items()):
    sids.sort(key=lambda i: -states[i]["manpower"])
    cap, cities = LORE.get(lt, (None, []))
    pool = list(cities)
    if cap:
        cs = capital_state.get(lt) or sids[0]
        names[cs] = cap; kind[cs] = "lore capital" + ("" if cs in capital_state.values() else " (placed in biggest state)")
        used.add(cap)
    for sid in sids:
        if sid in names: continue
        if pool:
            nm = pool.pop(0); names[sid] = nm; kind[sid] = "lore city, placed by size"; used.add(nm)
    style = COUNTRY_STYLE.get(lt, STYLE_DEFAULT) if a.mode == "style" else "numbered"
    num = 0
    for sid in sids:
        if sid in names: continue
        if style == "numbered":
            num += 1
            nm = f"{COUNTRY_RU.get(lt, LORE_RU.get(lt, lt))} {num}"
            names[sid] = nm; kind[sid] = "numbered (no lore data)"; used.add(nm)
            continue
        for _ in range(200):
            nm = gen(style)
            if nm not in used: break
        else:
            nm = gen(style) + f"-{sid}"
        names[sid] = nm; kind[sid] = f"generated ({style})"; used.add(nm)

def write(path, lang, conv):
    lines = [f"l_{lang}:"] + [f' STATE_{sid}:0 "{conv(names[sid])}"' for sid in sorted(names)]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
write(M / "localisation/russian/state_names_l_russian.yml", "russian", lambda s: s)
write(M / "localisation/english/state_names_l_english.yml", "english", translit)

rep = REPO / "no_commit/temp/state_names_report.csv"
rep.parent.mkdir(parents=True, exist_ok=True)
with open(rep, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["state", "mod_tag", "lore_country", "name", "source"])
    for sid in sorted(names):
        w.writerow([sid, states[sid]["owner"], tag2lore.get(states[sid]["owner"], "?"), names[sid], kind[sid]])
print(f"states {len(names)}, countries {len(by_country)}, capitals matched by pixel {len(capital_state)}/{len(LORE)}, "
      f"lore names used {sum(1 for k in kind.values() if k.startswith('lore'))}, generated {sum(1 for k in kind.values() if k.startswith('generated'))}, numbered {sum(1 for k in kind.values() if k.startswith('numbered'))}")
print("unmapped owners:", sorted({s['owner'] for s in states.values() if s['owner'] not in tag2lore}))
print("report:", rep)
