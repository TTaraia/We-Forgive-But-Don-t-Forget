"""Draws the sliding East Africa map and the per-story inset maps (Natural Earth data, public domain)."""
import json, os, re, math, urllib.request
import lang
from PIL import Image, ImageDraw, ImageFont

B = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
DATA = "mapdata"
LANG = "en"
def set_lang(code):
    global LANG; LANG = code

OCEAN, LAND, BORDER = (30, 66, 104), (70, 98, 126), (160, 184, 206)
FLAG_R, FLAG_G, FLAG_B = (234, 4, 55), (18, 173, 43), (65, 137, 221)   # Eritrea flag colours
ETH_RED, ETH_RED_STRONG, GOLD = (255, 140, 140), (225, 70, 70), (255, 205, 90)
LON0, LON1, LAT0, LAT1, PPD = 16.0, 60.0, 0.0, 22.0, 40   # panorama extent, pixels per degree (1x)
SHOW = {"Egypt", "Sudan", "S. Sudan", "Eritrea", "Ethiopia", "Djibouti", "Somalia", "Somaliland",
        "Kenya", "Uganda", "Yemen", "Saudi Arabia", "Chad", "Libya", "Oman"}
DISPLAY = {"S. Sudan": "South Sudan"}
PLACES = [  # (regex, kind, admin/country, name, label)
    (r"\bafar\b", "r", "Ethiopia", "Afar", "Afar"), (r"\btigray\b", "r", "Ethiopia", "Tigray", "Tigray"),
    (r"\bamhara\b", "r", "Ethiopia", "Amhara", "Amhara"), (r"\boromi?[ay]\b", "r", "Ethiopia", "Oromiya", "Oromia"),
    (r"\bbenishangul|\bbenshangul", "r", "Ethiopia", "Benshangul-Gumaz", "Benishangul-Gumuz"),
    (r"\bassab\b", "r", "Eritrea", "Debubawi Keyih Bahri", "Assab"),
    (r"\bethiopia", "c", "Ethiopia", "Ethiopia", "Ethiopia"), (r"\beritrea", "c", "Eritrea", "Eritrea", "Eritrea"),
    (r"\bsouth sudan", "c", "S. Sudan", "S. Sudan", "South Sudan"), (r"\bsudan", "c", "Sudan", "Sudan", "Sudan"),
    (r"\bdjibouti", "c", "Djibouti", "Djibouti", "Djibouti"), (r"\bsomali(a|land)\b", "c", "Somalia", "Somalia", "Somalia"),
    (r"\begypt", "c", "Egypt", "Egypt", "Egypt"), (r"\bkenya", "c", "Kenya", "Kenya", "Kenya"),
    (r"\buganda", "c", "Uganda", "Uganda", "Uganda"), (r"\byemen", "c", "Yemen", "Yemen", "Yemen")]

def font(sz):
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    return ImageFont.truetype(p, sz) if os.path.exists(p) else ImageFont.load_default()

def _get(name):
    os.makedirs(DATA, exist_ok=True); p = os.path.join(DATA, name)
    if not os.path.exists(p):
        req = urllib.request.Request(B + name, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=180) as r, open(p, "wb") as o: o.write(r.read())
    return p

def merge_somalia(features):
    """Somaliland is shown as part of Somalia (one country)."""
    sel = [f for f in features if f["properties"]["NAME"] in ("Somalia", "Somaliland")]
    try:
        from shapely.geometry import shape, mapping
        from shapely.ops import unary_union
        u = unary_union([shape(f["geometry"]).buffer(0.03) for f in sel]).buffer(-0.03)
        rest = [f for f in features if f not in sel]
        return rest + [{"type": "Feature", "properties": {"NAME": "Somalia"}, "geometry": mapping(u)}]
    except Exception as e:
        print("Somalia merge fallback:", e)
        for f in sel: f["properties"]["NAME"] = "Somalia"
        return features

def load():
    small = os.path.join(DATA, "admin1_small.json")
    countries = merge_somalia(json.load(open(_get("ne_50m_admin_0_countries.geojson")))["features"])
    if not os.path.exists(small):
        a1 = json.load(open(_get("ne_10m_admin_1_states_provinces.geojson")))["features"]
        keep = [f for f in a1 if f["properties"]["admin"] in ("Ethiopia", "Eritrea")]
        json.dump(keep, open(small, "w"))
    return countries, json.load(open(small))

def rings(geom):
    if geom["type"] == "Polygon": return [geom["coordinates"][0]]
    return [p[0] for p in geom["coordinates"]]

def bbox(geom):
    pts = [pt for r in rings(geom) for pt in r]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)

def centroid(geom):
    best, ba = None, -1
    for r in rings(geom):
        a = cx = cy = 0.0
        for (x0, y0), (x1, y1) in zip(r, r[1:]):
            c = x0*y1 - x1*y0; a += c; cx += (x0+x1)*c; cy += (y0+y1)*c
        if abs(a) > ba and a: ba, best = abs(a), (cx/(3*a), cy/(3*a))
    return best or ((bbox(geom)[0]+bbox(geom)[2])/2, (bbox(geom)[1]+bbox(geom)[3])/2)

def label(d, xy, text, sz, fill=(240, 244, 250)):
    text = lang.NAMES.get(LANG, {}).get(text, text)
    lang.draw_text(d, xy, text, sz, fill, "m", stroke=max(2, sz // 8), stroke_fill=(15, 30, 50))

def _bounds(geom, pr):
    pts = [pr(*p) for r in rings(geom) for p in r]
    return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)

def tint(img, geom, pr, color, alpha=150):
    m = Image.new("L", img.size, 0); md = ImageDraw.Draw(m)
    for r in rings(geom): md.polygon([pr(*p) for p in r], fill=alpha)
    img.paste(Image.new("RGB", img.size, color), mask=m)

def flag_tint(img, geom, pr, alpha=150):
    """Eritrea in transparent flag colours: red triangle (left), green (top right), blue (bottom right)."""
    x0, y0, x1, y1 = _bounds(geom, pr); ym = (y0 + y1) / 2
    layer = Image.new("RGB", img.size, LAND); ld = ImageDraw.Draw(layer)
    ld.polygon([(x0, y0), (x1, y0), (x1, ym)], fill=FLAG_G)
    ld.polygon([(x0, y1), (x1, y1), (x1, ym)], fill=FLAG_B)
    ld.polygon([(x0, y0), (x0, y1), (x1, ym)], fill=FLAG_R)
    m = Image.new("L", img.size, 0); md = ImageDraw.Draw(m)
    for r in rings(geom): md.polygon([pr(*p) for p in r], fill=alpha)
    img.paste(layer, mask=m)

def panorama(countries, path, S=2):
    w, h = int((LON1-LON0)*PPD*S), int((LAT1-LAT0)*PPD*S)
    img = Image.new("RGB", (w, h), OCEAN); d = ImageDraw.Draw(img)
    pr = lambda lo, la: ((lo-LON0)*PPD*S, (LAT1-la)*PPD*S)
    for f in countries:
        for r in rings(f["geometry"]):
            d.polygon([pr(*p) for p in r], fill=LAND, outline=BORDER, width=2*S)
    for f in countries:
        n = f["properties"]["NAME"]
        if n == "Ethiopia": tint(img, f["geometry"], pr, ETH_RED, 140)
        if n == "Eritrea": flag_tint(img, f["geometry"], pr, 150)
    d = ImageDraw.Draw(img)
    for f in countries:
        if f["properties"]["NAME"] in ("Ethiopia", "Eritrea"):
            for r in rings(f["geometry"]): d.polygon([pr(*p) for p in r], outline=BORDER, width=2*S)
    for f in countries:
        n = f["properties"]["NAME"]
        if n in SHOW and DISPLAY.get(n, n):
            cx, cy = centroid(f["geometry"])
            if LON0+2 < cx < LON1-2 and LAT0+1 < cy < LAT1-1: label(d, pr(cx, cy), DISPLAY.get(n, n), 15*S)
    label(d, pr(38.6, 20.2), "Red Sea", 12*S, (170, 205, 235)); label(d, pr(48, 12.6), "Gulf of Aden", 12*S, (170, 205, 235))
    img.save(path); return w, h

def detect(text):
    t = text.lower(); found = []
    for rx, kind, adm, name, lab in PLACES:
        if re.search(rx, t) and (kind, adm, name) not in [(k, a, n) for k, a, n, _ in found]:
            found.append((kind, adm, name, lab))
            if rx == r"\bsouth sudan": t = t.replace("south sudan", "")
    return found[:6] or [("c", "Eritrea", "Eritrea", "Eritrea"), ("c", "Ethiopia", "Ethiopia", "Ethiopia")]

def inset(countries, admin1, places, size=440):
    hi_c = {n for k, a, n, _ in places if k == "c"}
    hi_r = {(a, n) for k, a, n, _ in places if k == "r"}
    byname = {f["properties"]["NAME"]: f["geometry"] for f in countries}
    hi_geoms = [byname[n] for n in hi_c if n in byname]
    hi_geoms += [f["geometry"] for f in admin1 if (f["properties"]["admin"], f["properties"]["name"]) in hi_r]
    bs = [bbox(g) for g in hi_geoms] or [(30, 5, 45, 18)]
    x0, y0 = min(b[0] for b in bs), min(b[1] for b in bs); x1, y1 = max(b[2] for b in bs), max(b[3] for b in bs)
    half = max(max(x1-x0, y1-y0) * 0.75, 4.0); cx, cy = (x0+x1)/2, (y0+y1)/2
    L, T = cx-half, cy+half; k = size / (2*half)
    img = Image.new("RGB", (size, size), OCEAN); d = ImageDraw.Draw(img)
    pr = lambda lo, la: ((lo-L)*k, (T-la)*k)
    def vis(g):
        gb = bbox(g)
        return not (gb[2] < L or gb[0] > L+2*half or gb[3] < T-2*half or gb[1] > T)
    def outline(g, col, wd):
        if vis(g):
            for r in rings(g): d.polygon([pr(*p) for p in r], outline=col, width=wd)
    for f in countries:
        if vis(f["geometry"]):
            for r in rings(f["geometry"]): d.polygon([pr(*p) for p in r], fill=LAND, outline=BORDER, width=1)
    if "Ethiopia" in byname and vis(byname["Ethiopia"]): tint(img, byname["Ethiopia"], pr, ETH_RED, 150)
    if "Eritrea" in byname and vis(byname["Eritrea"]): flag_tint(img, byname["Eritrea"], pr, 150)
    for n in hi_c - {"Ethiopia", "Eritrea"}:
        if n in byname and vis(byname[n]): tint(img, byname[n], pr, GOLD, 150)
    for f in admin1:
        key = (f["properties"]["admin"], f["properties"]["name"])
        if key in hi_r and key[0] == "Ethiopia" and vis(f["geometry"]): tint(img, f["geometry"], pr, ETH_RED_STRONG, 190)
    d = ImageDraw.Draw(img)
    for f in countries:
        n = f["properties"]["NAME"]
        outline(f["geometry"], (255, 255, 255) if n in hi_c else BORDER, 2 if n in hi_c else 1)
    for f in admin1:
        key = (f["properties"]["admin"], f["properties"]["name"])
        if key in hi_r: outline(f["geometry"], (255, 255, 255), 2)
        elif f["properties"]["admin"] in {a for a, _ in hi_r}: outline(f["geometry"], (130, 160, 188), 1)
    for f in countries:
        n = f["properties"]["NAME"]; c = centroid(f["geometry"])
        if n in hi_c: label(d, pr(*c), DISPLAY.get(n, n), 20)
        elif n in SHOW and L < c[0] < L+2*half and T-2*half < c[1] < T: label(d, pr(*c), DISPLAY.get(n, n), 14, (205, 218, 230))
    for f in admin1:
        key = (f["properties"]["admin"], f["properties"]["name"])
        if key in hi_r: label(d, pr(*centroid(f["geometry"])), [l for k2, a, nm, l in places if (a, nm) == key][0], 18)
    d.rectangle([0, 0, size-1, size-1], outline=(255, 255, 255), width=3)
    return img
