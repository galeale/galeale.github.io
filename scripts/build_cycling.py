"""Strava export -> privacy-trimmed, simplified tracks + trip classification for the cycling page.

Usage: python -I build_cycling.py tracks.pkl out.json
Categories: commute (home <-> Dept. of Mathematics, Padova), conference (bike trips to conferences), other.
Privacy: every track loses its first and last 2-3 km (random per track), and any point within
2.5 km of the home location is dropped, so home cannot be read off the map.
"""
import pickle, json, math, sys, random, datetime, statistics

A = pickle.load(open(sys.argv[1], "rb"))
random.seed(20261102)

def hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))

MON = {'gen': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'mag': 5, 'giu': 6, 'lug': 7, 'ago': 8, 'set': 9, 'ott': 10, 'nov': 11, 'dic': 12}
def parse_dt(s):
    d, rest = s.split(",", 1)
    dd, mm, yy = d.split()
    hh, mi, ss = rest.strip().split(":")
    return datetime.datetime(int(yy), MON[mm], int(dd), int(hh), int(mi), int(ss))

for a in A:
    a["dt"] = parse_dt(a["date"])
    a["len"] = sum(hav(p, q) for p, q in zip(a["pts"], a["pts"][1:]))

# --- de-duplicate rides recorded twice (two devices / re-uploads)
A.sort(key=lambda a: a["dt"])
keep = []
for a in A:
    dup = next((b for b in keep[-6:] if abs((a["dt"] - b["dt"]).total_seconds()) < 1800
                and abs(a["len"] - b["len"]) < 0.05 * max(a["len"], b["len"])), None)
    if dup is None:
        keep.append(a)
    elif len(a["pts"]) > len(dup["pts"]):
        keep[keep.index(dup)] = a
dups = len(A) - len(keep)
A = keep

def center(guess, r):
    pts = [p for a in A for p in (a["pts"][0], a["pts"][-1]) if hav(p, guess) < r]
    return (statistics.median(p[0] for p in pts), statistics.median(p[1] for p in pts))
# The approximate home location is private: it lives in private/config.json (git-ignored), e.g.
#   {"home_guess": [lat, lon], "work_guess": [45.411, 11.887]}
import os
CFG = json.load(open(os.path.join(os.path.dirname(__file__), "..", "private", "config.json")))
HOME = center(tuple(CFG["home_guess"]), 0.8)
WORK = center(tuple(CFG["work_guess"]), 0.6)
STRAIGHT_COMMUTE = hav(HOME, WORK)

# --- conference trips (identified by date + name, checked by hand)
CONF = {
    "netsci2023": dict(label="Mestre → Vienna", event="NetSci 2023", dest=(48.208, 16.373), dates=["2023-07-06"]),
    "cs2ita2025": dict(label="Mestre → Trento → Verona", event="CS2Italy 2025", dest=(46.067, 11.121), dates=["2025-01-15", "2025-01-18"], train_only=True),
    "netsci2025": dict(label="Mestre → Maastricht", event="NetSci 2025", dest=(50.851, 5.691), dates=["2025-05-28", "2025-05-29", "2025-05-30", "2025-05-31", "2025-06-01"]),
    "c72h2026": dict(label="Mestre → London", event="Complexity72h 2026", dest=(51.507, -0.128), dates=["2026-06-15", "2026-06-16", "2026-06-17", "2026-06-18", "2026-06-19", "2026-06-20", "2026-06-21"]),
}
def conf_of(a):
    d = a["dt"].date().isoformat()
    for k, c in CONF.items():
        if d in c["dates"] and ("biking" in a["name"].lower()):
            return k
    return None

cat_counts = {"commute": 0, "conference": 0, "other": 0}
commute_legs = []
conf_legs = {k: [] for k in CONF}
for a in A:
    s, e = a["pts"][0], a["pts"][-1]
    a["cat"] = "other"
    k = conf_of(a)
    if k:
        a["cat"] = "conference"; a["conf"] = k; conf_legs[k].append(a)
    elif (hav(s, HOME) < 2 and hav(e, WORK) < 1) or (hav(s, WORK) < 1 and hav(e, HOME) < 2):
        a["cat"] = "commute"
        commute_legs.append(dict(date=a["dt"].date().isoformat(), km=round(a["km"], 1), legs=1))
    elif hav(s, HOME) < 2 and hav(e, HOME) < 2 and a["len"] < 2 * STRAIGHT_COMMUTE * 1.45 \
            and min(hav(p, WORK) for p in a["pts"][::3]) < 0.5:
        a["cat"] = "commute"  # out and back in one recording
        commute_legs.append(dict(date=a["dt"].date().isoformat(), km=round(a["km"], 1), legs=2))
    cat_counts[a["cat"]] += 1

# --- privacy trim + simplification
def rdp(pts, eps):
    """Ramer-Douglas-Peucker on (x, y) metres."""
    if len(pts) < 3:
        return pts
    stack, keep = [(0, len(pts) - 1)], {0, len(pts) - 1}
    while stack:
        i, j = stack.pop()
        (x1, y1), (x2, y2) = pts[i][:2], pts[j][:2]
        dx, dy = x2 - x1, y2 - y1
        n = math.hypot(dx, dy) or 1e-9
        best, bi = -1, None
        for k in range(i + 1, j):
            x, y = pts[k][:2]
            d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / n
            if d > best:
                best, bi = d, k
        if best > eps and bi is not None:
            keep.add(bi); stack += [(i, bi), (bi, j)]
    return [pts[k] for k in sorted(keep)]

def merc(lat, lon):
    R = 6378137.0
    return (R * math.radians(lon), R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))

def encode(coords):
    """Google encoded polyline, precision 1e-5."""
    out, plat, plon = [], 0, 0
    for lat, lon in coords:
        ilat, ilon = int(round(lat * 1e5)), int(round(lon * 1e5))
        for v in (ilat - plat, ilon - plon):
            v = ~(v << 1) if v < 0 else (v << 1)
            while v >= 0x20:
                out.append(chr((0x20 | (v & 0x1f)) + 63)); v >>= 5
            out.append(chr(v + 63))
        plat, plon = ilat, ilon
    return "".join(out)

HOME_MASK_KM = 2.5
tracks = {"commute": [], "conference": [], "other": []}
npts = 0
for a in A:
    pts = a["pts"]
    cum = [0.0]
    for p, q in zip(pts, pts[1:]):
        cum.append(cum[-1] + hav(p, q))
    L = cum[-1]
    cut_s, cut_e = random.uniform(2, 3), random.uniform(2, 3)
    if L < cut_s + cut_e + 1:
        continue
    seg = [p for p, c in zip(pts, cum) if cut_s <= c <= L - cut_e]
    # split where points fall inside the home mask
    runs, cur = [], []
    for p in seg:
        if hav(p, HOME) < HOME_MASK_KM:
            if len(cur) > 1: runs.append(cur)
            cur = []
        else:
            cur.append(p)
    if len(cur) > 1: runs.append(cur)
    for run in runs:
        xy = [merc(p[0], p[1]) + (p[0], p[1]) for p in run]
        simp = rdp(xy, 12.0)
        if len(simp) < 2: continue
        npts += len(simp)
        enc = encode([(p[2], p[3]) for p in simp])
        tracks[a["cat"]].append({"trip": a["conf"], "p": enc} if a["cat"] == "conference" else enc)

# --- trip table
# where each day ended (checked by hand against the GPS end points; edit freely)
STAGE_NAMES = {
    "netsci2023": ["Vienna"],
    "cs2ita2025": ["Trento", "Verona"],
    "netsci2025": ["Ponte di Legno", "Davos", "Strasbourg", "Saarlouis", "Maastricht"],
    "c72h2026": ["near Bergamo", "Andermatt", "Basel", "near Chaumont", "Paris", "Dieppe (ferry to Newhaven)", "Brighton", "London"],
}
trips = []
for k, c in CONF.items():
    legs = sorted(conf_legs[k], key=lambda a: a["dt"])
    out_km = sum(a["km"] for a in legs)  # Strava's own distance
    # straight-line distance: origin -> destination; for the Trento trip, out + back legs
    if c.get("train_only"):
        straight = sum(hav(a["pts"][0], a["pts"][-1]) for a in legs)
    else:
        straight = hav(legs[0]["pts"][0], legs[-1]["pts"][-1])
    trips.append(dict(id=k, label=c["label"], event=c["event"], start=legs[0]["dt"].date().isoformat(),
                      end=legs[-1]["dt"].date().isoformat(), days=len({a["dt"].date() for a in legs}),
                      km=round(out_km), train_only=bool(c.get("train_only")),
                      stages=[dict(date=a["dt"].date().isoformat(), km=round(a["km"]), to=STAGE_NAMES[k][i],
                                   at=[round(a["pts"][-1][0], 2), round(a["pts"][-1][1], 2)])
                              for i, a in enumerate(legs)]))

total_km = sum(a["km"] for a in A)
years = sorted({a["dt"].year for a in A})
out = dict(
    generated=datetime.date.today().isoformat(),
    period=[min(a["dt"] for a in A).date().isoformat(), max(a["dt"] for a in A).date().isoformat()],
    rides=len(A), total_km=round(total_km), duplicates_removed=dups, counts=cat_counts,
    commute=dict(legs=sum(c["legs"] for c in commute_legs), recordings=len(commute_legs),
                 km=round(sum(c["km"] for c in commute_legs)),
                 by_year={str(y): sum(c["legs"] for c in commute_legs if c["date"].startswith(str(y))) for y in years}),
    trips=trips, tracks=tracks,
)
json.dump(out, open(sys.argv[2], "w"), separators=(",", ":"))
summary = {k: v for k, v in out.items() if k != "tracks"}
print(json.dumps(summary, indent=1), file=sys.stderr)
print("segments", {k: len(v) for k, v in tracks.items()}, "points", npts, file=sys.stderr)
