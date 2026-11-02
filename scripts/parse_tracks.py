"""Read every Strava ride (GPX / FIT / FIT.GZ) into one compact pickle of tracks.

Usage: python -I parse_tracks.py <export_dir> <out.pkl>
"""
import csv, gzip, io, pickle, sys, os, datetime
import xml.etree.ElementTree as ET
import fitdecode

export, out = sys.argv[1], sys.argv[2]
rows = list(csv.reader(open(os.path.join(export, "activities.csv"), encoding="utf-8")))
head = rows[0]
col = {}
for i, c in enumerate(head):
    col.setdefault(c, i)  # first occurrence

def read_gpx(raw):
    root = ET.fromstring(raw)
    pts = []
    for el in root.iter():
        if el.tag.endswith("trkpt"):
            t = None
            for ch in el:
                if ch.tag.endswith("time"):
                    t = ch.text
            pts.append((float(el.get("lat")), float(el.get("lon")), t))
    return pts

SEMI = 180.0 / 2 ** 31
def read_fit(raw):
    pts = []
    with fitdecode.FitReader(io.BytesIO(raw), check_crc=fitdecode.CrcCheck.DISABLED) as fr:
        for frame in fr:
            if isinstance(frame, fitdecode.FitDataMessage) and frame.name == "record":
                if frame.has_field("position_lat") and frame.has_field("position_long"):
                    la, lo = frame.get_value("position_lat"), frame.get_value("position_long")
                    if la is None or lo is None:
                        continue
                    ts = frame.get_value("timestamp") if frame.has_field("timestamp") else None
                    pts.append((la * SEMI, lo * SEMI, ts.isoformat() if ts else None))
    return pts

acts = []
bad = 0
for r in rows[1:]:
    typ = r[col["Tipo attività"]]
    fn = r[col["Nome del file"]]
    if typ != "Ciclismo" or not fn:
        continue
    path = os.path.join(export, fn)
    try:
        raw = open(path, "rb").read()
        if fn.endswith(".gz"):
            raw = gzip.decompress(raw)
        pts = read_gpx(raw) if ".gpx" in fn else read_fit(raw)
    except Exception as e:
        bad += 1
        print("skip", fn, e, file=sys.stderr)
        continue
    if len(pts) < 10:
        continue
    acts.append(dict(id=r[col["ID attività"]], date=r[col["Data dell’attività"]], name=r[col["Nome attività"]],
                     km=float(r[col["Distanza"]].replace(".", "").replace(",", ".") or 0), pts=pts))
print(len(acts), "rides with GPS;", bad, "unreadable", file=sys.stderr)
pickle.dump(acts, open(out, "wb"))
