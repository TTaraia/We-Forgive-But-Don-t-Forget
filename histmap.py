"""Draws a full-frame (2560x1440) map for one scene."""
from PIL import Image, ImageDraw
import mapkit, lang

W2, H2 = 2560, 1440
CITIES = {"Asmara": (38.9251, 15.3229), "Massawa": (39.4742, 15.6097), "Assab": (42.7399, 13.0073),
          "Adwa": (38.8999, 14.1667), "Aksum": (38.7194, 14.1211), "Addis Ababa": (38.74, 9.03),
          "Keren": (38.4509, 15.7778), "Nakfa": (38.467, 16.65), "Afabet": (38.683, 16.183), "Agordat": (37.88, 15.55),
          "Tessenei": (36.65, 15.12), "Om Hajer": (36.655, 14.325), "She'eb": (39.049, 15.852)}
SIDE = {"Keren": "left", "Nakfa": "right", "Afabet": "left", "Agordat": "left", "Tessenei": "right", "Om Hajer": "right", "She'eb": "right", "Aksum": "left", "Adwa": "right", "Asmara": "right", "Massawa": "right", "Assab": "below", "Addis Ababa": "right"}
VIEWS = {"horn": (40.0, 10.0, 26.0), "eritrea": (39.9, 14.5, 9.0)}   # centre lon, centre lat, latitude span
LIGHT_RED, UN_BLUE = (255, 140, 140), (91, 146, 229)

def render(countries, spec, code):
    mapkit.set_lang(code)
    clon, clat, span = VIEWS.get(spec.get("view", "eritrea"), VIEWS["eritrea"])
    k = H2 / span; half = W2 / k / 2; L = clon - half; T = clat + span / 2
    pr = lambda lo, la: ((lo - L) * k, (T - la) * k)
    big = span < 12; fs = 40 if big else 26
    img = Image.new("RGB", (W2, H2), mapkit.OCEAN); d = ImageDraw.Draw(img)
    def vis(g):
        b = mapkit.bbox(g); return not (b[2] < L or b[0] > L + 2 * half or b[3] < T - span or b[1] > T)
    by = {}
    for f in countries:
        by[f["properties"]["NAME"]] = f["geometry"]
        if vis(f["geometry"]):
            for r in mapkit.rings(f["geometry"]): d.polygon([pr(*p) for p in r], fill=mapkit.LAND, outline=mapkit.BORDER, width=3)
    E, ET, style = by.get("Eritrea"), by.get("Ethiopia"), spec.get("style", "independent")
    if style == "ancient": mapkit.tint(img, E, pr, (232, 200, 120), 120); mapkit.tint(img, ET, pr, (232, 200, 120), 120)
    elif style == "memorial": mapkit.tint(img, E, pr, (150, 70, 70), 140)
    elif style == "coast": mapkit.tint(img, E, pr, (130, 160, 90), 80)
    elif style == "italian": mapkit.tint(img, E, pr, (110, 150, 80), 175)
    elif style == "british": mapkit.tint(img, E, pr, (110, 150, 215), 170)
    elif style == "federation": mapkit.tint(img, E, pr, UN_BLUE, 170); mapkit.tint(img, ET, pr, LIGHT_RED, 110)
    elif style == "province": mapkit.tint(img, E, pr, LIGHT_RED, 150); mapkit.tint(img, ET, pr, LIGHT_RED, 150)
    else: mapkit.flag_tint(img, E, pr, 150); mapkit.tint(img, ET, pr, LIGHT_RED, 125)
    d = ImageDraw.Draw(img)
    for r in mapkit.rings(E): d.polygon([pr(*p) for p in r], outline=(255, 255, 255), width=6)
    for f in countries:
        n = f["properties"]["NAME"]
        if n in mapkit.SHOW and mapkit.DISPLAY.get(n, n):
            cx, cy = mapkit.centroid(f["geometry"])
            if big and n == "Eritrea": cx, cy = 38.0, 16.6          # keep the name clear of the Asmara marker
            if L + 1 < cx < L + 2 * half - 1 and T - span + 0.5 < cy < T - 0.5:
                mapkit.label(d, pr(cx, cy), mapkit.DISPLAY.get(n, n), int(fs * (1.25 if n in ("Eritrea", "Ethiopia") else 1)))
    sea = (40.6, 17.1) if big else (38.6, 20.2)
    mapkit.label(d, pr(*sea), "Red Sea", int(fs * 0.8), (170, 205, 235))
    for name in spec.get("mark", []):
        if name not in CITIES: continue
        x, y = pr(*CITIES[name]); r = 14 if big else 9
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255), outline=(20, 30, 50), width=4)
        t = lang.NAMES.get(code, {}).get(name, name); w = lang.width(t, fs); side = SIDE.get(name, "right")
        pos = {"right": (x + r + 10 + w / 2, y), "left": (x - r - 10 - w / 2, y), "below": (x, y + r + fs)}[side]
        mapkit.label(d, pos, name, fs, (255, 245, 200))
    return img
