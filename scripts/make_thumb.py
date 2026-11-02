"""Render a small heatmap of the (already privacy-trimmed) tracks for the homepage.

Usage, from the repository root:  python scripts/make_thumb.py
Reads data/cycling-data.json, writes assets/rides-thumb.png. Needs numpy, opencv-python, pillow.
"""
import json, math, os
import numpy as np, cv2
from PIL import Image

ROOT = os.path.join(os.path.dirname(__file__), "..")
D = json.load(open(os.path.join(ROOT, "data", "cycling-data.json")))
W, H, SS = 1200, 760, 2          # output size, supersampling
LAT0, LAT1, LON0, LON1 = 44.95, 46.85, 10.75, 13.15   # Veneto & Dolomites

def merc(lat, lon):
    return math.radians(lon), math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
x0, y0 = merc(LAT0, LON0); x1, y1 = merc(LAT1, LON1)
# keep the aspect ratio of the box, centred
sx = (W * SS) / (x1 - x0); sy = (H * SS) / (y1 - y0); s = min(sx, sy)
cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

def decode(st):
    i = lat = lon = 0; pts = []
    while i < len(st):
        for k in range(2):
            shift = res = 0
            while True:
                b = ord(st[i]) - 63; i += 1; res |= (b & 0x1f) << shift; shift += 5
                if b < 0x20: break
            v = ~(res >> 1) if res & 1 else res >> 1
            if k == 0: lat += v
            else: lon += v
        x, y = merc(lat / 1e5, lon / 1e5)
        pts.append((W * SS / 2 + (x - cx) * s, H * SS / 2 - (y - cy) * s))
    return np.array(pts, dtype=np.int32)

layers = {}
for name in ("other", "commute", "conference"):
    acc = np.zeros((H * SS, W * SS), np.float32)
    for st in D["tracks"][name]:
        p = decode(st["p"] if isinstance(st, dict) else st)
        layer = np.zeros_like(acc)
        cv2.polylines(layer, [p.reshape(-1, 1, 2)], False, 1.0, thickness=2 * SS if name != "other" else SS + 1, lineType=cv2.LINE_AA)
        acc += layer
    layers[name] = cv2.resize(acc, (W, H), interpolation=cv2.INTER_AREA)

bg = np.array([7, 12, 23], np.float32)
img = np.tile(bg, (H, W, 1))
def add(layer, rgb, gain, cap=1.0):
    a = np.clip(np.log1p(layer * gain) / np.log1p(gain * 6), 0, cap)[..., None]
    return a, np.array(rgb, np.float32)
for name, rgb, gain in (("other", (138, 164, 255), 8.0), ("commute", (255, 181, 71), 4.0), ("conference", (52, 211, 153), 4.0)):
    a, c = add(layers[name], rgb, gain)
    img = img * (1 - a) + c * a
Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(os.path.join(ROOT, "assets", "rides-thumb.png"), optimize=True)
print("wrote assets/rides-thumb.png")
