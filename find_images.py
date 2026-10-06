"""Finds freely-licensed photos on Wikimedia Commons and writes image_candidates.html (thumbnails + licence + author) for you to REVIEW.
Usage: python find_images.py "Massawa" "Nakfa ruins" "Keren Eritrea"
Then copy the chosen file titles into images.json."""
import html, sys
import commons_tools as ct

queries = sys.argv[1:] or ["Massawa old town", "Massawa Imperial Palace", "Nakfa Eritrea", "Keren Eritrea", "Afabet Eritrea", "Asmara Eritrea", "Eritrea Martyrs Monument"]
rows = []
for q in queries:
    try: found = ct.search(q)
    except Exception as e: print("search failed:", q, e); continue
    rows.append(f"<h2>{html.escape(q)}</h2><div style='display:flex;flex-wrap:wrap;gap:12px'>")
    for p in found:
        ok = "#1a7f37" if p["allowed"] else "#b3261e"
        rows.append(f"<div style='width:260px;border:2px solid {ok};padding:6px;font:13px sans-serif'><img src='{p['thumb']}' style='width:100%'><br>"
                    f"<b>{html.escape(p['title'])}</b><br>{html.escape(p['license'])} {'(usable)' if p['allowed'] else '(NOT usable)'}<br>"
                    f"by {html.escape(p['author'][:80])}<br><a href='{p['page']}'>page</a></div>")
    rows.append("</div>")
open("image_candidates.html", "w", encoding="utf-8").write("<meta charset='utf-8'><h1>Commons candidates</h1>"
    "<p>Green = licence allows reuse (credit required). Choose calm photos of places: no victims, no graphic scenes.</p>" + "".join(rows))
print("Wrote image_candidates.html with", len(queries), "searches")
