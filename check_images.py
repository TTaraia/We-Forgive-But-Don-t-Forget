"""Checks images.json against scenes_en.txt and the picture files, and says exactly what is wrong.
Run:  python check_images.py            (also runs automatically at the start of every build; it never stops the build)"""
import difflib, glob, json, os, sys
import scenes

EXTS = (".png", ".jpg", ".jpeg", ".webp")

def find_file(name):
    """Finds a picture even if the extension or folder is a little different (photos/ folder, .png vs .jpg, upper/lower case)."""
    stem, ext = os.path.splitext(name)
    for folder in ("", "photos/"):
        for e in ([ext] if ext else []) + list(EXTS):
            for cand in (folder + stem + e,):
                if os.path.exists(cand): return cand
    low = {os.path.basename(p).lower(): p for p in glob.glob("*") + glob.glob("photos/*")}
    for e in ([ext] if ext else []) + list(EXTS):
        if (os.path.basename(stem) + e).lower() in low: return low[(os.path.basename(stem) + e).lower()]
    return None

def as_list(v):
    return v if isinstance(v, list) else ([v] if isinstance(v, dict) else [])

def scene_key(cfg_scenes, title, idx):
    """Finds this scene's entry: exact title, same title ignoring case, or scene number."""
    for k in cfg_scenes:
        if k.strip().lower() == title.strip().lower(): return k
    return str(idx + 1) if str(idx + 1) in cfg_scenes else None

def check(path="images.json", scenes_path="scenes_en.txt", quiet=False):
    say = (lambda *a: None) if quiet else print
    if not os.path.exists(path): say("no images.json: the video is built without photos"); return 0
    try: cfg = json.load(open(path, encoding="utf-8"))
    except json.JSONDecodeError as e:
        say(f"images.json is not valid JSON: {e}. (A comma is missing or extra, or a quote/bracket is missing near line {e.lineno}.)"); return 1
    titles = [s["title"] for s in scenes.parse(scenes_path)]; problems = 0
    default = cfg.get("default_credit", "")
    if "REPLACE" in default: say("WARNING default_credit still says REPLACE: photos without their own credit are skipped until you write who made the pictures"); problems += 1
    for key, val in cfg.get("scenes", {}).items():
        real = key.strip().lower() in [t.lower() for t in titles] or (key.isdigit() and 1 <= int(key) <= len(titles))
        if not real:
            hint = difflib.get_close_matches(key, titles, 1, 0.5)
            say(f"WARNING scene '{key}' does not exist" + (f" - did you mean '{hint[0]}'?" if hint else "")); problems += 1; continue
        if key.isdigit(): say(f"NOTE '{key}' is a scene NUMBER: it means '{titles[int(key) - 1]}'. Titles are safer if you add or remove scenes.")
        if isinstance(val, dict): say(f"NOTE '{key}': one picture should still be inside square brackets [ ... ] (the build accepts it anyway)")
        for e in as_list(val):
            label = e.get("file") or e.get("image") or e.get("commons") or "?"
            if e.get("commons"): continue
            f = e.get("file") or e.get("image")
            if not f: say(f"WARNING '{key}': an entry has no \"file\""); problems += 1; continue
            if "image" in e and "file" not in e: say(f"NOTE '{key}': use \"file\" instead of \"image\" (accepted anyway)")
            real_path = find_file(f)
            if not real_path: say(f"WARNING '{key}': picture '{f}' not found (checked top folder and photos/, .png/.jpg/.jpeg/.webp)"); problems += 1
            elif real_path != f: say(f"NOTE '{key}': '{f}' -> using '{real_path}'")
            cred = e.get("credit") or default
            if not cred or "REPLACE" in cred: say(f"WARNING '{key}': '{label}' has no credit, so it will be skipped"); problems += 1
            if any(c in os.path.basename(f) for c in ':,;"?*<>|'): say(f"WARNING '{label}': characters like : , ; ? in a file name cause trouble. Rename it, e.g. massawa_damage.png"); problems += 1
    say(f"images.json check finished: {problems} problem(s)"); return problems

if __name__ == "__main__":
    sys.exit(1 if check() else 0)
