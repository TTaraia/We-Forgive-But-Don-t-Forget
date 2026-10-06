"""Wikimedia Commons helper: looks up a file's licence/author, REFUSES anything that is not freely reusable, and downloads it.
Allowed: public domain, CC0, CC BY, CC BY-SA.  Refused: NonCommercial, NoDerivatives, fair use, unknown.
Needs internet (works on GitHub Actions)."""
import html, json, os, re, urllib.parse, urllib.request

API = "https://commons.wikimedia.org/w/api.php"
UA = "EritreaWarYearsVideo/1.0 (educational documentary project; contact via GitHub repository)"
CACHE = os.path.join("photos", "cache")

def api(params):
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json"})
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40) as r:
        return json.load(r)

def strip(s): return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()

def license_ok(lic):
    l = (lic or "").lower().strip()
    if not l or any(b in l for b in ("-nc", "nc-", " nc", "-nd", " nd", "fair use", "all rights", "non-free", "copyrighted")): return False
    return l.startswith(("cc by", "cc-by", "cc0", "public domain", "pd"))

def parse_page(page):
    """Turns one 'page' from the Commons API into a dict, or None if it has no image info."""
    ii = (page.get("imageinfo") or [None])[0]
    if not ii: return None
    em = ii.get("extmetadata", {}); val = lambda k: strip(em.get(k, {}).get("value", ""))
    lic = val("LicenseShortName")
    return {"title": page.get("title", ""), "license": lic, "allowed": license_ok(lic), "author": val("Artist") or val("Credit") or "unknown",
            "url": ii.get("thumburl") or ii.get("url"), "thumb": ii.get("thumburl"), "page": ii.get("descriptionurl", ""),
            "description": val("ImageDescription")[:200], "width": ii.get("thumbwidth") or ii.get("width"), "mime": ii.get("mime", "")}

def lookup(title, width=1400):
    if not title.lower().startswith("file:"): title = "File:" + title
    data = api({"action": "query", "titles": title, "redirects": 1, "prop": "imageinfo", "iiprop": "url|extmetadata|mime|size", "iiurlwidth": width})
    pages = data.get("query", {}).get("pages", {})
    return next((p for p in (parse_page(x) for x in pages.values()) if p), None)

def search(query, limit=12, width=400):
    data = api({"action": "query", "generator": "search", "gsrsearch": query + " filetype:bitmap", "gsrnamespace": 6, "gsrlimit": limit,
                "prop": "imageinfo", "iiprop": "url|extmetadata|mime|size", "iiurlwidth": width})
    pages = data.get("query", {}).get("pages", {})
    return [p for p in (parse_page(x) for x in pages.values()) if p]

def download(url, name):
    os.makedirs(CACHE, exist_ok=True)
    dest = os.path.join(CACHE, re.sub(r"[^A-Za-z0-9._-]", "_", name)[:120])
    if not os.path.exists(dest):
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r, open(dest, "wb") as o: o.write(r.read())
    return dest
