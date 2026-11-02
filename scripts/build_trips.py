"""Daily stages, names and elevation profiles of the rides to conferences.

Usage, from the repository root:
  python scripts/build_trips.py /path/to/strava_export private/cities1000.json data/cycling-data.json
Run after build_cycling.py and before add_food.py. cities1000.json is GeoNames (population >= 1000), see README.

A recording is split into stages wherever the clock stops for more than 3 hours (an overnight stop),
so a 2-day ride saved as one activity still shows 2 stages.
"""
import csv, gzip, io, json, math, os, sys, datetime
import xml.etree.ElementTree as ET
import fitdecode

export, cities_path, data_path = sys.argv[1:4]
D = json.load(open(data_path))
CITIES = json.load(open(cities_path))   # [name, lat, lon, population, featureCode, country]

DATES = {t["id"]: None for t in D["trips"]}
CONF_DATES = {
    "netsci2023": ["2023-07-06", "2023-07-07"],
    "cs2ita2025": ["2025-01-15", "2025-01-18"],
    "netsci2025": ["2025-05-28", "2025-05-29", "2025-05-30", "2025-05-31", "2025-06-01"],
    "c72h2026": ["2026-06-15", "2026-06-16", "2026-06-17", "2026-06-18", "2026-06-19", "2026-06-20", "2026-06-21"],
}
# names that the nearest-town rule cannot know (edit freely): (trip, stage number from 1) -> name
OVERRIDES = {("c72h2026", 6): "Dieppe (ferry to Newhaven)"}
GAP_H = 3.0
MON = {'gen': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'mag': 5, 'giu': 6, 'lug': 7, 'ago': 8, 'set': 9, 'ott': 10, 'nov': 11, 'dic': 12}

def hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))

def read_gpx(raw):
    pts = []
    for el in ET.fromstring(raw).iter():
        if el.tag.endswith("trkpt"):
            t = e = None
            for ch in el:
                if ch.tag.endswith("time"): t = datetime.datetime.fromisoformat(ch.text.replace("Z", "+00:00"))
                if ch.tag.endswith("ele"): e = float(ch.text)
            pts.append((float(el.get("lat")), float(el.get("lon")), t, e))
    return pts

SEMI = 180.0 / 2 ** 31
def read_fit(raw):
    pts = []
    with fitdecode.FitReader(io.BytesIO(raw), check_crc=fitdecode.CrcCheck.DISABLED) as fr:
        for f in fr:
            if isinstance(f, fitdecode.FitDataMessage) and f.name == "record" and f.has_field("position_lat"):
                la, lo = f.get_value("position_lat"), f.get_value("position_long")
                if la is None or lo is None: continue
                e = None
                for k in ("enhanced_altitude", "altitude"):
                    if f.has_field(k) and f.get_value(k) is not None: e = float(f.get_value(k)); break
                pts.append((la * SEMI, lo * SEMI, f.get_value("timestamp") if f.has_field("timestamp") else None, e))
    return pts

rows = list(csv.reader(open(os.path.join(export, "activities.csv"), encoding="utf-8")))
col = {}
for i, c in enumerate(rows[0]): col.setdefault(c, i)
legs = {k: [] for k in CONF_DATES}
for r in rows[1:]:
    d, m, y = r[col["Data dell’attività"]].split(",")[0].split()
    date = datetime.date(int(y), MON[m], int(d)).isoformat()
    name = r[col["Nome attività"]]
    for k, ds in CONF_DATES.items():
        if date in ds and "biking" in name.lower() and r[col["Tipo attività"]] == "Ciclismo":
            fn = r[col["Nome del file"]]
            raw = open(os.path.join(export, fn), "rb").read()
            if fn.endswith(".gz"): raw = gzip.decompress(raw)
            pts = read_gpx(raw) if ".gpx" in fn else read_fit(raw)
            legs[k].append(pts)

def nearest_name(p):
    near = [(hav(p, (c[1], c[2])), c) for c in CITIES if abs(c[1] - p[0]) < 0.3 and abs(c[2] - p[1]) < 0.4]
    if not near: return "?"
    # the main town within 8 km (Strasbourg rather than its suburb), else the closest village
    close = [c for d, c in near if d <= 8]
    if close: return max(close, key=lambda c: c[3])[0]
    big = max((c for d, c in near if d <= 20), key=lambda c: c[3], default=min(near)[1])
    return "near " + big[0]

def smooth(vals, k=5):
    out = []
    for i in range(len(vals)):
        w = [v for v in vals[max(0, i - k):i + k + 1] if v is not None]
        out.append(sum(w) / len(w) if w else None)
    return out

for t in D["trips"]:
    L = sorted(legs[t["id"]], key=lambda p: p[0][2])
    stages, cur = [], []
    for pts in L:
        cur = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            if a[2] and b[2] and (b[2] - a[2]).total_seconds() > GAP_H * 3600:
                stages.append(cur); cur = []
            cur.append(b)
        stages.append(cur)
    prof_d, prof_e, cuts, out, dist = [], [], [], [], 0.0
    for i, st in enumerate(stages):
        km = sum(hav(a, b) for a, b in zip(st, st[1:]))
        ele = smooth([p[3] for p in st])
        if sum(1 for p in st if p[3] is None) > 0.3 * len(st):   # the device lost the barometer: no profile for this stage
            ele = [None] * len(st)
        asc, last = 0.0, None
        for e in ele:
            if e is None: continue
            if last is not None and e - last > 0: asc += e - last
            last = e
        # profile samples about every 2 km
        acc = 0.0; nxt = 0.0
        for j, p in enumerate(st):
            if j: acc += hav(st[j - 1], p)
            if acc >= nxt and ele[j] is not None:
                prof_d.append(round(dist + acc, 1)); prof_e.append(int(round(ele[j]))); nxt += 2.0
        dist += km
        cuts.append(round(dist, 1))
        end = st[-1]
        out.append(dict(date=(st[0][2] or datetime.datetime.fromisoformat(t["start"])).date().isoformat(),
                        km=round(km), ascent=int(round(asc, -1)) if any(e is not None for e in ele) else None,
                        to=OVERRIDES.get((t["id"], i + 1)) or nearest_name(end),
                        at=[round(end[0], 2), round(end[1], 2)]))
    # GPS noise makes point-to-point sums a few % longer than Strava's distance: rescale to Strava's total
    k = t["km"] / dist if dist else 1
    for st_ in out: st_["km"] = round(st_["km"] * k)
    prof_d = [round(x * k, 1) for x in prof_d]; cuts = [round(x * k, 1) for x in cuts]
    t["stages"] = out
    t["days"] = len({s["date"] for s in out})
    t["ascent"] = sum(s["ascent"] or 0 for s in out)
    t["profile"] = dict(d=prof_d, e=prof_e, cuts=cuts[:-1])
    t["start"], t["end"] = out[0]["date"], out[-1]["date"]
    print(t["id"], t["days"], "days", t["ascent"], "m", [(s["date"][5:], s["km"], s["ascent"], s["to"]) for s in out])
json.dump(D, open(data_path, "w"), separators=(",", ":"))
