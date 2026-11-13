"""Shared lore data and helpers for make_state_names.py, make_city_names.py and make_countries.py.

Lore (names of capitals/cities, population) comes from docs/lore/Contries-Description.md. Cultural styles for generated names are NOT lore.
"""
import glob, re
from pathlib import Path
import numpy as np
from PIL import Image
import invented_lore as INV

REPO = Path(__file__).resolve().parent.parent
DEFAULT_MOD = "C:/Users/catsh/CatshrediasDocs/Paradox Interactive/Hearts of Iron IV/mod/Ktits"

# ---- lore: capitals and named cities (docs/lore/Contries-Description.md, docs/map/build/Map-Build-Plan.md section 6) ----
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
    "TMR": ("Барбинсберг", ["Кёльнбург", "Дрезденвальд", "Мюнхенштадт", "Гамбургсхафен"]),
    "SOY": ("Поридж-Сити", ["Нью-Бостон", "Спрингфилд", "Вашингтаун", "Чикагтаун", "Сиэттлвилл"]),
    "BRT": ("Большой Джон", ["Йорквик", "Ливерпорт", "Мэнчестон", "Кентбридж", "Бристау"]),
    "KZZ": ("Станица Дарьевская", []),
    "CSL": ("Ставка Казуала", []),
}

# ---- cultural styles for generated names (invented; chosen from the naming hints in docs/lore/Contries-Description.md) ----
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
STYLES.update(INV.INVENTED_STYLES)
for _t, _c in INV.INVENTED_COUNTRIES.items():          # Z01..Z05: invented names (docs/lore/Invented-Lore.md), lore cities of docs/lore/Contries-Description.md untouched
    COUNTRY_STYLE[_t] = _c["style"]; LORE[_t] = (_c["capital"], _c["cities"])
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



def gen(style, rnd):
    stems, sufs = STYLES[style]
    st, sf = rnd.choice(stems), rnd.choice(sufs)
    if st[-1] in "аеёиоуыэюя" and sf[0] in "аеёиоуыэюя":
        st = st[:-1]                                     # no vowel clashes
    n = st + sf
    return n[0].upper() + n[1:]


def load_mod(M):
    """tag->lore country by color, states (owner, manpower, provinces, victory points), capital states"""
    M = Path(M)
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
        sid = int(re.search(r"id\s*=\s*(\d+)", t).group(1))
        ow = re.search(r"owner\s*=\s*(\w+)", t)
        mp = re.search(r"manpower\s*=\s*(\d+)", t)
        pr = re.search(r"provinces\s*=\s*\{([^}]*)\}", t)
        vps = [(int(x), int(y)) for x, y in re.findall(r"victory_points\s*=\s*\{\s*(\d+)\s+(\d+)\s*\}", t)]
        states[sid] = {"owner": ow.group(1) if ow else None, "manpower": int(mp.group(1)) if mp else 0,
                       "provs": [int(x) for x in pr.group(1).split()] if pr else [], "vps": vps, "file": f}
    prov_state = {p: sid for sid, s in states.items() for p in s["provs"]}
    d = {}
    for l in open(M / "map/definition.csv", encoding="latin1"):
        p = l.strip().split(";")
        if len(p) > 4 and p[0].isdigit():
            d[(int(p[1]), int(p[2]), int(p[3]))] = int(p[0])
    pv = np.array(Image.open(M / "map/provinces.bmp").convert("RGB"))
    country_ru, capital_state = {}, {}
    for l in open(REPO / "tools/rp_input/stage_04/capitals.txt", encoding="utf-8"):
        p = l.strip().split(";")
        if len(p) >= 2 and len(p[0]) == 3:
            country_ru[p[0]] = re.sub(r"\s*\(.*\)", "", p[1])
        if len(p) >= 5 and p[3].isdigit():
            pid = d.get(tuple(int(v) for v in pv[int(p[4]), int(p[3])]))
            sid = prov_state.get(pid)
            if sid and tag2lore.get(states[sid]["owner"]) == p[0]:
                capital_state[p[0]] = sid
    country_ru.update({t: c["name"] for t, c in INV.INVENTED_COUNTRIES.items()})
    return {"tag2lore": tag2lore, "states": states, "country_ru": country_ru, "capital_state": capital_state, "tags": tags}


def assign_state_names(info, mode, rnd):
    """returns names {state id: name}, kind {state id: source}, used (set of all names so far)"""
    states, tag2lore, capital_state, country_ru = info["states"], info["tag2lore"], info["capital_state"], info["country_ru"]
    names, kind, used = {}, {}, set()
    by_country = {}
    for sid, s in states.items():
        by_country.setdefault(tag2lore.get(s["owner"]), []).append(sid)
    for lt, sids in sorted(by_country.items(), key=lambda kv: str(kv[0])):
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
        style = COUNTRY_STYLE.get(lt, STYLE_DEFAULT) if mode == "style" else "numbered"
        num = 0
        for sid in sids:
            if sid in names: continue
            if style == "numbered":
                num += 1
                nm = f"{country_ru.get(lt, LORE_RU.get(lt, str(lt)))} {num}"
                names[sid] = nm; kind[sid] = "numbered (no lore data)"; used.add(nm)
                continue
            for _ in range(200):
                nm = gen(style, rnd)
                if nm not in used: break
            else:
                nm = gen(style, rnd) + f"-{sid}"
            names[sid] = nm; kind[sid] = f"generated ({style})"; used.add(nm)
    return names, kind, used


def write_yml(path, lang, entries):
    lines = [f"l_{lang}:"] + [f' {k}:0 "{v}"' for k, v in entries]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(chr(10).join(lines) + chr(10), encoding="utf-8-sig")


def province_adjacency(M):
    """set of (a, b) province id pairs that touch (4-neighbourhood in provinces.bmp)"""
    M = Path(M)
    d = {}
    for l in open(M / "map/definition.csv", encoding="latin1"):
        p = l.strip().split(";")
        if len(p) > 4 and p[0].isdigit():
            d[(int(p[1]) << 16) | (int(p[2]) << 8) | int(p[3])] = int(p[0])
    pv = np.array(Image.open(M / "map/provinces.bmp").convert("RGB")).astype(np.int64)
    key = (pv[..., 0] << 16) | (pv[..., 1] << 8) | pv[..., 2]
    keys = np.array(sorted(d)); ids = np.array([d[k] for k in sorted(d)])
    idx = ids[np.searchsorted(keys, key)]
    pairs = set()
    for a_, b_ in ((idx[:, :-1], idx[:, 1:]), (idx[:-1], idx[1:])):
        m = a_ != b_
        x = np.stack([np.minimum(a_[m], b_[m]), np.maximum(a_[m], b_[m])], 1)
        pairs |= set(map(tuple, np.unique(x, axis=0).tolist()))
    return pairs


# docs/lore/Contries-Description.md, "Население ..." lines, millions (lore is the source; other countries are TODO in the lore)
LORE_POP = {"CSL": 30, "SVS": 120, "KZZ": 10, "BRT": 70, "IRK": 125, "IRR": 350, "MUS": 70, "TRV": 100,
            "TMR": 100, "SOY": 80, "BLK": 100, "SRK": 40}


def province_centroids(M):
    """{province id: (x, y)} centroid in pixels of provinces.bmp"""
    M = Path(M)
    d = {}
    for l in open(M / "map/definition.csv", encoding="latin1"):
        p = l.strip().split(";")
        if len(p) > 4 and p[0].isdigit():
            d[(int(p[1]) << 16) | (int(p[2]) << 8) | int(p[3])] = int(p[0])
    pv = np.array(Image.open(M / "map/provinces.bmp").convert("RGB")).astype(np.int64)
    key = (pv[..., 0] << 16) | (pv[..., 1] << 8) | pv[..., 2]
    keys = np.array(sorted(d)); ids = np.array([d[k] for k in sorted(d)])
    idx = ids[np.searchsorted(keys, key)]
    n = int(idx.max()) + 1
    H, W = idx.shape
    cnt = np.maximum(np.bincount(idx.ravel(), minlength=n), 1)
    ys, xs = np.mgrid[0:H, 0:W]
    cx = np.bincount(idx.ravel(), weights=xs.ravel(), minlength=n) / cnt
    cy = np.bincount(idx.ravel(), weights=ys.ravel(), minlength=n) / cnt
    return {i: (float(cx[i]), float(cy[i])) for i in range(n)}, idx
