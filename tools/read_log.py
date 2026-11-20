"""Read the KTITS debug journal from game.log and write a report (docs/global_mechanics/Debug-Log.md).

Journal lines (tools/make_debug.py):  [hh:mm:ss][1936.01.01.12]: KTITS:<SEC>:<TAG>:<EVENT> key=value ...
Output: no_commit/temp/ktits_report.md (+ PNG charts next to it when matplotlib is installed).
Usage: python tools/read_log.py [--log PATH] [--mod PATH] [--out PATH] [--stuck N] [--errlog PATH] [--top N]
"""
import argparse, collections, datetime as dt, re, sys
from pathlib import Path

DOCS = Path.home() / "CatshrediasDocs/Paradox Interactive/Hearts of Iron IV"
REPO = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--log", default=str(DOCS / "logs/game.log"))
ap.add_argument("--errlog", default=str(DOCS / "logs/error.log"))
ap.add_argument("--mod", default=str(DOCS / "mod/Ktits"))
ap.add_argument("--out", default=str(REPO / "no_commit/temp/ktits_report.md"))
ap.add_argument("--stuck", type=int, default=6, help="months of scale 100 in a row that count as stuck")
ap.add_argument("--top", type=int, default=10, help="countries in the scale table")
a = ap.parse_args()

LINE = re.compile(r"\[(\d{4})\.(\d{1,2})\.(\d{1,2})[^\]]*\]:?\s*KTITS:([A-Z]+):([^:]*):(\w+)\s*(.*)$")
KV = re.compile(r"(\w+)=(-?[\w.\-]+)")
Ev = collections.namedtuple("Ev", "d sec tag ev kv raw")

def num(v):
    try: return float(v)
    except Exception: return None

events = []
p = Path(a.log)
if not p.exists():
    sys.exit(f"no game.log: {p}")
for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
    if "KTITS" not in raw: continue
    m = LINE.search(raw)
    if not m: continue
    y, mo, d, sec, tag, ev, rest = m.groups()
    events.append(Ev(dt.date(int(y), int(mo), int(d)), sec, tag, ev, dict(KV.findall(rest)), rest))
if not events:
    sys.exit("no KTITS lines in game.log (is the flag set? console: run ktits_debug.txt)")

by = collections.defaultdict(list)
for e in events: by[e.sec].append(e)
ym = lambda d: f"{d.year}-{d.month:02d}"
out = []
W = out.append
def table(head, rows):
    W("| " + " | ".join(head) + " |"); W("|" + "---|" * len(head))
    for r in rows: W("| " + " | ".join(str(x) for x in r) + " |")
    W("")
def chron(evs, skip=("MONTH",), limit=400):
    n = 0
    for e in evs:
        if e.ev in skip: continue
        W(f"- {e.d} `{e.tag}` {e.ev} {e.raw}"); n += 1
        if n >= limit: W(f"- ... (more than {limit})"); break
    if n == 0: W("- (nothing)")
    W("")

susp = []
d0, d1 = events[0].d, events[-1].d
W("# KTITS journal report")
W(f"\nLog `{a.log}`: {len(events)} lines, game dates {d0} .. {d1}.\n")
table(["Section", "Lines"], [(k, len(v)) for k, v in sorted(by.items())])

# ---------- KAZ ----------
W("## Kazualia (KAZ)\n")
kaz = by.get("KAZ", [])
mon = [e for e in kaz if e.ev == "MONTH"]
if mon:
    W("Monthly values:\n")
    rows = []
    for e in mon:
        k = e.kv
        path = ",".join(n for n in ("ref", "ind", "com", "great", "neutral") if k.get("path_" + n) in ("1", "1.0")) or "-"
        rows.append((ym(e.d), k.get("faith"), k.get("faith_gain"), k.get("inner"), k.get("outer"), k.get("reform"), k.get("britt"), path))
    table(["Month", "Faith", "Gain", "Inner", "Outer", "Reforms", "Britt", "Path"], rows)
    fa = [num(e.kv.get("faith")) for e in mon]
    run = 0
    for i in range(1, len(fa)):
        run = run + 1 if fa[i] is not None and fa[i - 1] is not None and fa[i] <= fa[i - 1] else 0
        if run == 3: susp.append(f"KAZ: Faith does not grow for 3+ months in a row (month {ym(mon[i].d)}, value {fa[i]}). Gain column shows why.")
    if all(num(e.kv.get("faith_gain")) in (0.0, None) for e in mon): susp.append("KAZ: the Faith gain is 0 in every monthly line")
else:
    W("(no monthly lines: Kazualia is not played / the flag was set late)\n")
W("Chronology (starts, decisions, focuses, events, rebellions):\n")
chron([e for e in events if e.sec in ("KAZ", "OUT", "FOC") or (e.tag == "SCU" and e.sec in ("DEC", "EVT"))])

# ---------- CAS ----------
W("## Casuality of other countries (CAS)\n")
cas = by.get("CAS", [])
scale = collections.defaultdict(dict)   # tag -> month -> scale
for e in cas:
    if e.ev == "MONTH" and num(e.kv.get("scale")) is not None: scale[e.tag][ym(e.d)] = num(e.kv["scale"])
months = sorted({m for v in scale.values() for m in v})
if scale:
    tops = sorted(scale, key=lambda t: -max(scale[t].values()))[:a.top]
    W(f"Scale by month, top {len(tops)} countries by the maximum (a country appears only while its scale is above 0):\n")
    table(["Month"] + tops, [(m, *[scale[t].get(m, "") for t in tops]) for m in months])
    W("Countries (max scale, months in the log, last growth, next to Kazualia):\n")
    rows = []
    for t in sorted(scale, key=lambda t: -max(scale[t].values())):
        ms = [e for e in cas if e.ev == "MONTH" and e.tag == t]
        rows.append((t, max(scale[t].values()), len(ms), ms[-1].kv.get("growth"), ms[-1].kv.get("next_to_kaz")))
    table(["Tag", "Max", "Months", "Growth", "Next to Kaz"], rows)
    for t, v in scale.items():
        ms = [v[m] for m in sorted(v)]; r = 0
        for x in ms:
            r = r + 1 if x >= 100 else 0
        if r >= a.stuck: susp.append(f"CAS: {t} scale is stuck at 100 for {r} months in a row")
        grow = [e for e in cas if e.ev == "MONTH" and e.tag == t]
        if len(ms) >= 6 and len(set(ms)) == 1 and ms[0] > 0 and ms[0] < 100:
            susp.append(f"CAS: {t} scale is constant {ms[0]} for {len(ms)} months (growth {grow[-1].kv.get('growth')})")
W("Tier changes:\n")
chron([e for e in cas if e.ev == "TIER"])
W("Other CAS lines (transition, struggle/support decisions and random events are in DEC / EVT below):\n")
chron([e for e in cas if e.ev not in ("MONTH", "TIER")])

# ---------- EDU ----------
W("## Education (EDU)\n")
edu = by.get("EDU", [])
W("Level changes and cooperation agreements:\n")
chron([e for e in edu if e.ev != "MONTH"])
last = {}
for e in edu:
    if e.ev == "MONTH": last[e.tag] = e
if last:
    W(f"Specialists at the last month ({max(e.d for e in last.values())}), thousands:\n")
    table(["Tag", "Level", "Own", "Foreign", "Progress"], [(t, e.kv.get("level"), e.kv.get("own"), e.kv.get("foreign"), e.kv.get("progress")) for t, e in sorted(last.items(), key=lambda x: -(num(x[1].kv.get("own")) or 0))[:25]])

# ---------- ALLY ----------
W("## Alliances (ALLY)\n")
al = by.get("ALLY", [])
chron([e for e in al if e.ev != "MONTH"])
cw = collections.defaultdict(list)
for e in al:
    if e.ev == "MONTH": cw[e.tag].append((ym(e.d), e.kv.get("coop"), e.kv.get("size"), e.kv.get("members")))
if cw:
    W("Cooperation scale of the leaders (monthly):\n")
    for t, rows in cw.items():
        W(f"- `{t}`: " + ", ".join(f"{m}={c}" for m, c, s, n in rows[:60]))
    W("")
    for t, rows in cw.items():
        if len({c for _, c, _, _ in rows}) == 1 and len(rows) >= 12: susp.append(f"ALLY: the cooperation scale of {t} did not change for {len(rows)} months")

# ---------- CONT ----------
W("## Continuous focuses (CONT)\n")
cn = by.get("CONT", [])
chron([e for e in cn if e.ev != "MONTH"])
cnt = collections.Counter((e.tag, e.kv.get("focus")) for e in cn if e.ev == "MONTH")
if cnt: table(["Tag", "Focus", "Active months"], [(t, f, n) for (t, f), n in sorted(cnt.items())])

# ---------- WAR ----------
W("## Wars (WAR)\n")
wars = [e for e in by.get("WAR", []) if e.ev == "DECLARE"]
table(["Date", "Attacker", "Target", "Wargoal"], [(e.d, e.tag, e.kv.get("target"), {"0": "NO", "1": "yes", "2": "yes (war goal used)"}.get(e.kv.get("wargoal_code", "?"), "?")) for e in wars])
nowg = [e for e in wars if e.kv.get("wargoal_code") == "0"]
if nowg:
    susp.append(f"WAR: {len(nowg)} declarations without a war goal (wars for fun): " + ", ".join(f"{e.tag}->{e.kv.get('target')} {e.d}" for e in nowg[:15]))

# ---------- DEC / FOC / EVT usage ----------
W("## Decisions, focuses, events\n")
done = collections.Counter(); fires = collections.Counter(); focs = collections.Counter()
for e in events:
    if e.sec == "DEC" and e.ev == "DONE": done[e.raw.split()[0]] += 1
    if e.sec == "EVT" and e.ev == "FIRE": fires[e.raw.split()[0]] += 1
    if e.sec == "FOC" and e.ev == "DONE": focs[e.raw.split()[0]] += 1
def mod_ids(globs, pat):
    ids = []
    for g in globs:
        for f in sorted((Path(a.mod)).glob(g)):
            ids += re.findall(pat, f.read_text(encoding="utf-8-sig", errors="ignore"))
    return sorted(set(ids))
all_dec = mod_ids(["common/decisions/ktits_*.txt"], r'KTITS:DEC:\[THIS\.GetTag\]:DONE (\w+)')
all_foc = mod_ids(["common/national_focus/ktits_*.txt"], r'KTITS:FOC:\[THIS\.GetTag\]:DONE (\w+)')
W(f"Decisions taken: {sum(done.values())} ({len(done)} of {len(all_dec)} kinds); focuses completed: {sum(focs.values())} ({len(focs)} of {len(all_foc)}); events fired: {sum(fires.values())} ({len(fires)} kinds).\n")
if done:
    table(["Decision", "Times"], done.most_common())
if all_dec:
    nd = [d for d in all_dec if d not in done]
    W("Decisions that never fired: " + (", ".join(f"`{d}`" for d in nd) or "none") + "\n")
    if nd and done: susp.append(f"DEC: {len(nd)} of {len(all_dec)} decisions never fired (see the list in the DEC section; it is normal if the scenario did not need them)")
if focs and all_foc:
    nf = [f for f in all_foc if f not in focs]
    W("Focuses never completed: " + (", ".join(f"`{f}`" for f in nf) or "none") + "\n")
# late events: scheduled but not arrived
late = [e for e in events if e.ev == "LATE_SCHEDULED"]
fire_list = collections.defaultdict(list)
for e in events:
    if e.sec == "EVT" and e.ev == "FIRE": fire_list[e.raw.split()[0]].append(e.d)
for e in late:
    ev = e.kv.get("event"); lim = (num(re.sub(r"\.\..*", "", e.kv.get("in", "0"))) or 0)
    hi = int(re.sub(r"^.*\.\.", "", e.kv.get("in", "0")) or 0)
    if not any(e.d <= d <= e.d + dt.timedelta(days=hi + 3) for d in fire_list.get(ev, [])):
        if e.d + dt.timedelta(days=hi + 3) <= d1:
            susp.append(f"FOC: the delayed event {ev} scheduled on {e.d} (in {e.kv.get('in')} days, tag {e.tag}) did not arrive")
W(f"Delayed ('late') events scheduled: {len(late)}.\n")
# rebellions without an outcome
starts = [e for e in by.get("OUT", []) if e.ev in ("REBEL_START", "CIVWAR_START")]
ends = [e for e in by.get("OUT", []) if e.ev.startswith("RESULT")]
for s in starts:
    if not any(x.d >= s.d for x in ends) and (d1 - s.d).days > 400:
        susp.append(f"OUT: the rebellion started {s.d} ({s.ev}, {s.tag}) has no result for over a year")

# ---------- suspicious ----------
W("## Suspicious\n")
for s in dict.fromkeys(susp): W(f"- {s}")
if not susp: W("- nothing found by the rules (see the rules in tools/read_log.py)")
W("")

# ---------- error.log ----------
W("## error.log (ktits_ / K3x)\n")
ep = Path(a.errlog)
if ep.exists():
    hits = [l.strip() for l in ep.read_text(encoding="utf-8", errors="replace").splitlines() if re.search(r"ktits_|\bK3\d\b|\bK4\d\b", l)]
    c = collections.Counter(re.sub(r"^\[[^\]]*\]\[[^\]]*\]:?\s*", "", h) for h in hits)
    W(f"{len(hits)} lines, {len(c)} distinct (first 60):\n")
    for l, n in c.most_common(60): W(f"- x{n} `{l[:220]}`")
else:
    W(f"(no file {ep})")
W("")

# ---------- charts ----------
png = []
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    od = Path(a.out).parent
    if scale:
        plt.figure(figsize=(10, 5))
        for t in sorted(scale, key=lambda t: -max(scale[t].values()))[:a.top]:
            plt.plot(range(len(months)), [scale[t].get(m) for m in months], label=t, marker=".")
        plt.xticks(range(0, len(months), max(1, len(months) // 12)), months[::max(1, len(months) // 12)], rotation=45)
        plt.legend(ncol=3, fontsize=7); plt.title("Casuality scale"); plt.tight_layout()
        plt.savefig(od / "ktits_scale.png"); plt.close(); png.append("ktits_scale.png")
    if mon:
        plt.figure(figsize=(10, 4))
        for key in ("inner", "outer", "reform"):
            plt.plot([num(e.kv.get(key)) for e in mon], label=key)
        plt.legend(); plt.title("Kazualia: inner / outer / reforms"); plt.tight_layout()
        plt.savefig(od / "ktits_kaz.png"); plt.close(); png.append("ktits_kaz.png")
except ImportError:
    pass
if png: W("Charts: " + ", ".join(png) + "\n")

Path(a.out).parent.mkdir(parents=True, exist_ok=True)
Path(a.out).write_text("\n".join(out), encoding="utf-8")
print(f"report: {a.out} ({len(events)} journal lines, {len(susp)} suspicious)")
