"""Usage: python make_history.py (project: Remembering the Eritrean War Years) en|am|ti
Builds history_<lang>.mp4 (intro music, narrated scenes with a map for each, outro music) and history_<lang>.<sub>.srt files.
Tigrinya has no free voice: put your own recordings in audio_ti/01.mp3 ... (scene numbers); scenes without a recording
become silent captioned scenes over quiet music."""
import asyncio, glob, json, math, os, re, subprocess, sys, textwrap
from PIL import Image, ImageDraw, ImageFilter
import lang, mapkit, histmap, music, scenes, commons_tools

V = sys.argv[1] if len(sys.argv) > 1 else "en"
W, H = 1280, 720
PANEL, INK, ACC, WARN = (200, 226, 250, 170), (12, 32, 64), (20, 85, 160), (200, 100, 10)
INTRO_SECONDS = 10
MIN_SCENE = 10.0      # YouTube chapters need at least 10 s each
PAUSE = float(os.environ.get("SENTENCE_PAUSE", "0.7")) if V == "am" else 0.0
T = lang.draw_text

def run(cmd): subprocess.run(cmd, check=True)

def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True, check=True).stdout.strip())

def split_sentences(text): return [p for p in re.split(r"(?<=[።፧!?.])\s+", text.strip()) if p.strip()]

def speak(text, voice, out):
    if os.environ.get("FAKE_TTS"):
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", str(max(1, len(text) / 14)), out]); return
    import edge_tts
    for attempt in range(4):
        try: asyncio.run(edge_tts.Communicate(text, voice).save(out)); return
        except Exception as e: print("tts retry:", e); asyncio.run(asyncio.sleep(2 * (attempt + 1)))
    raise RuntimeError("speech failed: " + text[:50])

def tts(text, mp3, voice):
    """Returns [(sentence, start, end)] when sentences are spoken separately (Amharic), else None."""
    if PAUSE <= 0: speak(text, voice, mp3); return None
    sil = f"{V}_sil.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", str(PAUSE), sil])
    base = mp3.rsplit(".", 1)[0]; lst, timing, t = [], [], 0.0
    for j, sent in enumerate(split_sentences(text)):
        m, w = f"{base}_{j}.mp3", f"{base}_{j}.wav"
        speak(sent, voice, m); run(["ffmpeg", "-y", "-loglevel", "error", "-i", m, "-ar", "44100", "-ac", "2", w])
        d = dur(w); timing.append((sent, t, t + d)); t += d + PAUSE; lst += [w, sil]
    open(f"{base}_list.txt", "w").write("".join(f"file '{os.path.abspath(p)}'\n" for p in lst[:-1]))
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{base}_list.txt", "-c:a", "libmp3lame", "-q:a", "4", mp3])
    return timing

_bed = []
def bed_file():
    """Background music for the WHOLE video: your music.mp3 if present, else an original Eritrean-style instrumental.
    Env BED=eritrean (default) | pachelbel | none."""
    if _bed: return _bed[0]
    mode = os.environ.get("BED", "eritrean")
    own = [f for f in ("music.mp3", "music.m4a", "music.wav", "music.aac", "music.ogg") if os.path.exists(f)]
    if own: p = own[0]
    elif mode == "none": p = None
    elif mode == "pachelbel":
        p = "bed_pachelbel.wav"
        if not os.path.exists(p): music.make_music(p, 60)
    else:
        p = "bed_eritrean.wav"
        if not os.path.exists(p): music.make_eritrean_bed(p, 150)
    _bed.append(p); return p

def silence(out, seconds):
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{seconds:.2f}", out])

def music_clip(out, seconds=INTRO_SECONDS):      # intro/outro: with a full-length bed these stay silent (the bed plays)
    if bed_file(): silence(out, seconds); return
    if not os.path.exists("music_auto.wav"): music.make_music("music_auto.wav", 15)
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", "music_auto.wav", "-t", str(seconds), "-af",
         f"afade=t=in:d=1,afade=t=out:st={seconds - 2.5}:d=2.5,apad=whole_dur={seconds}", "-ar", "44100", "-ac", "2", out])

def silent_scene(out, seconds):   # captioned scene without a voice
    silence(out, seconds)

def long_bed(src, total, xf=4.0):
    """Repeats the music with a smooth crossfade at every repeat, so a 3-minute song can run under a 10+ minute video."""
    L = dur(src)
    if L >= total + 2: return src, False
    if L < 3 * xf: return src, True            # very short clip: plain loop
    n = math.ceil((total - xf) / (L - xf)) + 1
    ins = []; fc, prev = "", "[0:a]"
    for i in range(n): ins += ["-i", src]
    for i in range(1, n):
        fc += f"{prev}[{i}:a]acrossfade=d={xf}:c1=tri:c2=tri[x{i}];"; prev = f"[x{i}]"
    out = "bed_long.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", fc.rstrip(";"), "-map", prev, "-t", f"{total + 2:.1f}", out])
    return out, False

def add_bed(video_in, video_out, total):
    """Music under the narration. Two modes:
    - song.mp3 present: your song (with vocals) plays alone for the first and last ~14 s; a vocal-free bed plays quietly in between.
    - otherwise: the bed (music.mp3 or the built-in instrumental) is loud for the first/last 10 s and quiet (BED_LEVEL) under the voice."""
    lvl = float(os.environ.get("BED_LEVEL", "0.05"))
    src, plain_loop = long_bed(bed_file(), total)
    loop = ["-stream_loop", "-1"] if plain_loop else []
    song = next((f for f in ("song.mp3", "song.m4a", "song.wav") if os.path.exists(f)), None)
    if song:
        L = dur(song); n_in = min(14.0, L); n_out = min(14.0, L); ms = int((total - n_out) * 1000)
        fc = (f"[1:a]volume={lvl},afade=t=in:d=1.5,afade=t=out:st={total - 4:.2f}:d=4,atrim=0:{total:.2f}[bed];"
              f"[2:a]asplit=2[sa][sb];"
              f"[sa]atrim=0:{n_in:.1f},asetpts=PTS-STARTPTS,afade=t=out:st={n_in - 4:.1f}:d=4,volume=0.9[s1];"
              f"[sb]atrim=start={L - n_out:.1f}:end={L:.1f},asetpts=PTS-STARTPTS,afade=t=in:d=2,afade=t=out:st={n_out - 3:.1f}:d=3,volume=0.9,adelay={ms}|{ms}[s2];"
              f"[0:a][bed][s1][s2]amix=inputs=4:duration=first:dropout_transition=0:normalize=0[a]")
        ins = ["-i", video_in, *loop, "-i", src, "-i", song]
    else:
        env = f"{lvl}+{0.9 - lvl:.3f}*clip((10-t)/2,0,1)+{0.9 - lvl:.3f}*clip((t-({total:.2f}-12))/2,0,1)"
        fc = (f"[1:a]volume='{env}':eval=frame,afade=t=in:d=1.5,afade=t=out:st={total - 4:.2f}:d=4,atrim=0:{total:.2f}[bed];"
              f"[0:a][bed]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]")
        ins = ["-i", video_in, *loop, "-i", src]
    run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", fc, "-map", "0:v", "-map", "[a]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.2f}", video_out])

def own_recording(n):
    f = glob.glob(f"audio_{V}/{n:02d}.*"); return f[0] if f else None

def estimate_seconds(text): return max(5.0, len(text.split()) * 0.45 + len(split_sentences(text)) * 0.7)

def stamp(t):
    ms = int(round(t * 1000)); return f"{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}"

def write_srt(path, spans):
    cues, n = [], 1
    for a, b, text in spans:
        parts = []
        for sent in re.split(r"(?<=[.!?።፧])\s+", text.strip()): parts += textwrap.wrap(sent, 84) or []
        tot = sum(len(p) for p in parts) or 1; t = a
        for p in parts:
            e = t + (b - a) * len(p) / tot; cues.append(f"{n}\n{stamp(t)} --> {stamp(e)}\n{textwrap.fill(p, 42)}\n"); n += 1; t = e
    open(path, "w", encoding="utf-8").write("\n".join(cues))

def overlay(kind, sc, path, n, total, spec):
    h = lang.HIST[V]; img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    if kind == "intro":
        d.rounded_rectangle([140, 180, 1140, 540], 24, fill=PANEL)
        T(d, (W//2, 280), h["title"][0], 42, INK, "m"); T(d, (W//2, 365), h["title"][1], 42, INK, "m"); T(d, (W//2, 460), h["intro_sub"], 32, ACC, "m")
    elif kind == "outro":
        d.rounded_rectangle([140, 200, 1140, 520], 24, fill=PANEL)
        T(d, (W//2, 320), h["outro_title"], 56, INK, "m")
        for i, line in enumerate(lang.wrap(h["outro_sub"], 30, 900, 2)): T(d, (W//2, 410 + i * 42), line, 30, ACC, "m")
    else:
        d.rounded_rectangle([40, 556, 1240, 690], 22, fill=PANEL)
        T(d, (70, 586), sc["date"], 26, ACC)
        size = 46
        while lang.width(sc["title"], size) > 1140 and size > 28: size -= 2
        T(d, (70, 640), sc["title"], size, INK)
        legend = h["styles"].get(spec.get("style", ""), "")
        if legend:
            w = lang.width(legend, 24) + 40; d.rounded_rectangle([40, 30, 40 + w, 80], 12, fill=PANEL); T(d, (60, 56), legend, 24, INK)
        T(d, (1240, 56), f"{n} / {total}", 24, ACC, "r")
        if spec.get("note") == "analysis":
            lab = h["analysis"]; w = lang.width(lab, 26) + 40
            d.rounded_rectangle([40, 96, 40 + w, 142], 12, fill=WARN); T(d, (60, 120), lab, 26, (255, 255, 255))
    img.save(path)

# ---------------- sliding photos ----------------
PHOTO_X, PHOTO_Y, PHOTO_W, PHOTO_H = 760, 98, 440, 290      # the picture area of a card (pixels in the 1280x720 frame)
SLIDE_IN, SLIDE_OUT, MIN_SLOT = 0.9, 0.7, 3.5

def photo_config():
    return json.load(open("images.json", encoding="utf-8")) if os.path.exists("images.json") else {}

def resolve_photos(cfg, title, idx):
    """Returns [{path, caption, credit, page}] for a scene. Commons photos are licence-checked and skipped if not reusable.
    Forgiving: accepts "image" for "file", a single {...} instead of a list, a missing folder/extension, and a top-level default_credit."""
    import check_images as ci
    scn = cfg.get("scenes", {}); key = ci.scene_key(scn, title, idx)
    default = cfg.get("default_credit", ""); out = []
    for e in (ci.as_list(scn[key]) if key else []):
        try:
            if e.get("commons") and not os.path.exists(e["commons"]):
                import commons_tools as ct
                info = ct.lookup(e["commons"])
                if not info: print("photo skipped (not found on Commons):", e["commons"]); continue
                if not info["allowed"]: print(f"photo skipped (licence '{info['license']}' not reusable):", info["title"]); continue
                path = ct.download(info["url"], info["title"]); credit = f"Photo: {info['author']}, {info['license']}"; page = info["page"]
            else:
                name = e.get("file") or e.get("image") or e.get("commons")
                path = ci.find_file(name)
                if not path: print("photo skipped (file not found):", name); continue
                credit, page = e.get("credit") or default, e.get("page", "")
                if not credit or "REPLACE" in credit: print(f"photo skipped (no credit; add \"credit\" or a top-level \"default_credit\"): {name}"); continue
            out.append({"path": path, "caption": e.get("caption", ""), "credit": credit, "page": page})
        except Exception as ex:
            print("photo skipped:", e, "-", ex)
    return out

def make_card(p, out_png):
    """A framed photo card (white border, soft shadow, caption and credit) as a transparent PNG."""
    im = Image.open(p["path"]).convert("RGB"); bw, bh = PHOTO_W, PHOTO_H
    
    s = min(bw / im.width, bh / im.height)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.Resampling.LANCZOS)

    # Center the complete image inside the photo area
    fitted = Image.new("RGB", (bw, bh), (245, 240, 225))
    x = (bw - im.width) // 2
    y = (bh - im.height) // 2
    fitted.paste(im, (x, y))
    im = fitted
    cap = lang.wrap(p["caption"], 20, bw, 2) if p["caption"] else []
    cred = lang.wrap(p["credit"], 14, bw, 2) if p["credit"] else []
    th = 12 + bh + 10 + 26 * len(cap) + 20 * len(cred) + 14; tw = bw + 24
    card = Image.new("RGBA", (tw + 40, th + 40), (0, 0, 0, 0))
    sh = Image.new("RGBA", card.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle([26, 30, 26 + tw, 30 + th], 10, fill=(0, 0, 0, 120))
    card.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(card); d.rounded_rectangle([20, 20, 20 + tw, 20 + th], 10, fill=(250, 250, 248, 255))
    card.paste(im, (32, 32)); y = 32 + bh + 22
    for line in cap: lang.draw_text(d, (32, y), line, 20, INK); y += 26
    for line in cred: lang.draw_text(d, (32, y), line, 14, (90, 100, 115)); y += 20
    card.save(out_png)
    return card.size

def slide_expr(x0, y0, tin, tout, direction):
    pin = f"clip((t-{tin:.2f})/{SLIDE_IN},0,1)"; pout = f"clip((t-({tout:.2f}-{SLIDE_OUT}))/{SLIDE_OUT},0,1)"
    f = f"((1-{pin}*{pin}*(3-2*{pin}))+{pout}*{pout}*(3-2*{pout}))"          # 1 = off screen, 0 = in place (smooth ease)
    return (f"{x0}+(W-{x0})*{f}", str(y0)) if direction == "right" else (str(x0), f"{y0}+(H-{y0})*{f}")

def photo_plan(n, D):
    """Start/end time for each of n photos in a scene of D seconds."""
    start, end = 1.0, D - 0.8
    n = max(1, min(n, int((end - start) // MIN_SLOT)))
    slot = (end - start) / n
    return n, [(start + i * slot, start + (i + 1) * slot - 0.1) for i in range(n)]

def check_files():
    """Stops with a clear message if one of the .py files in the repo is an older version than make_history.py."""
    need = {"scenes": ["parse", "validate"], "lang": ["HIST", "draw_text", "wrap", "width"], "music": ["make_music", "make_eritrean_bed"],
            "histmap": ["render"], "commons_tools": ["lookup", "download", "license_ok"], "mapkit": ["load", "tint", "flag_tint", "set_lang", "label"]}
    old = [f"{mod}.py" for mod, names in need.items() if any(not hasattr(globals()[mod], n) for n in names)]
    keys = ("video_title", "desc", "sources", "disclosure", "chapters", "chapter_intro", "chapter_outro", "intro_spoken", "styles")
    if "lang.py" not in old and any(k not in lang.HIST[c] for c in ("en", "am", "ti") for k in keys): old.append("lang.py")
    if old: sys.exit("Out-of-date file(s) in your repository: " + ", ".join(sorted(set(old))) + ". Re-upload the latest version of every .py file from the project zip.")

if __name__ == "__main__":
    check_files()
    en = scenes.parse("scenes_en.txt")
    scenes.validate(en)
    langs = {"en": en}
    for c in ("am", "ti"):
        if os.path.exists(f"scenes_{c}.txt"):
            s = scenes.parse(f"scenes_{c}.txt")
            if len(s) != len(en): sys.exit(f"scenes_{c}.txt has {len(s)} scenes but scenes_en.txt has {len(en)}.")
            langs[c] = s
    if V not in langs: sys.exit(f"scenes_{V}.txt not found.")
    scs, h = langs[V], lang.HIST[V]
    countries = mapkit.load()[0]
    items = [("music", "intro", None), ("voice", "intro", None)] + [("voice", "scene", i) for i in range(len(scs))] + \
            [("voice", "outro", None), ("music", "outro", None)]
    male, female = lang.VOICES.get(V, (None, None)); audio, timings = [], {}
    for k, (kind, role, idx) in enumerate(items):
        out = f"{V}_a{k}.m4a" if kind == "music" else f"{V}_a{k}.mp3"
        if kind == "music": music_clip(out)
        else:
            text = h["intro_spoken"] if role == "intro" else (h["outro_spoken"] if role == "outro" else scs[idx]["spoken"])
            rec = own_recording(idx + 1) if role == "scene" else None
            if rec: run(["ffmpeg", "-y", "-loglevel", "error", "-i", rec, "-ar", "44100", "-ac", "2", out.replace(".mp3", ".m4a")]); out = out.replace(".mp3", ".m4a")
            elif male is None: silent_scene(out.replace(".mp3", ".m4a"), estimate_seconds(text)); out = out.replace(".mp3", ".m4a")
            else: timings[k] = tts(text, out, female if (role == "scene" and idx % 2 == 0) else male)
        audio.append(out)
    adur = [dur(a) for a in audio]
    durs = [max(ad + (0.8 if it[0] == "voice" else 0), MIN_SCENE if it[1] == "scene" else 0) for ad, it in zip(adur, items)]
    total = len(scs); parts, starts, cum = [], [], 0.0; pcfg = photo_config(); credits = []
    try:
        import check_images; check_images.check(quiet=False)
    except Exception as ex: print("image check skipped:", ex)
    for k, ((kind, role, idx), a, D) in enumerate(zip(items, audio, durs)):
        spec = en[idx]["spec"] if role == "scene" else {"view": "horn", "style": "independent"}
        histmap.render(countries, spec, V).save(f"{V}_m{k}.png")
        overlay(role if role != "scene" else "scene", scs[idx] if idx is not None else None, f"{V}_o{k}.png", (idx or 0) + 1, total, spec)
        xs, xe, ys, ye = (0, 128, 0, 72) if k % 2 == 0 else (128, 0, 72, 0)
        photos = resolve_photos(pcfg, scs[idx]["title"], idx) if role == "scene" else []
        n_ph, slots = photo_plan(len(photos), D) if photos else (0, [])
        fc = f"[0:v]crop=2432:1368:x='{xs}+({xe - xs})*t/{D:.3f}':y='{ys}+({ye - ys})*t/{D:.3f}',scale={W}:{H}:flags=bicubic[bg];[bg][1:v]overlay=0:0[v0]"
        extra, last = [], "v0"
        for j in range(n_ph):
            png = f"{V}_p{k}_{j}.png"; make_card(photos[j], png)
            direction = ("right" if (k + j) % 2 == 0 else "bottom") if pcfg.get("slide", "alternate") == "alternate" else pcfg.get("slide", "right")
            ex, ey = slide_expr(PHOTO_X - 20, PHOTO_Y - 20, slots[j][0], slots[j][1], direction)
            fc += f";[{last}][{3 + j}:v]overlay=x='{ex}':y='{ey}':enable='between(t,{slots[j][0]:.2f},{slots[j][1]:.2f})'[v{j + 1}]"
            last = f"v{j + 1}"; extra += ["-loop", "1", "-framerate", "25", "-t", f"{D:.2f}", "-i", png]
            credits.append(f"{scs[idx]['title']}: {photos[j]['caption']} - {photos[j]['credit']} {photos[j]['page']}".strip())
        run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "25", "-t", f"{D:.2f}", "-i", f"{V}_m{k}.png",
             "-loop", "1", "-framerate", "25", "-t", f"{D:.2f}", "-i", f"{V}_o{k}.png", "-i", a, *extra, "-filter_complex", fc,
             "-map", f"[{last}]", "-map", "2:a", "-af", f"apad=whole_dur={D:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
             "-r", "25", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-t", f"{D:.2f}", f"{V}_s{k}.mp4"])
        parts.append(f"{V}_s{k}.mp4"); starts.append(cum); cum += D
    open(f"{V}_list.txt", "w").write("".join(f"file '{p}'\n" for p in parts))
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{V}_list.txt", "-c", "copy", f"remembering_{V}_nobed.mp4"])
    if bed_file(): add_bed(f"remembering_{V}_nobed.mp4", f"remembering_{V}.mp4", cum)
    else: os.replace(f"remembering_{V}_nobed.mp4", f"remembering_{V}.mp4")
    for c, cs in langs.items():
        spans = []
        for k, (kind, role, idx) in enumerate(items):
            if kind != "voice": continue
            ch = lang.HIST[c]
            if c == V and timings.get(k): spans += [(starts[k] + a_, starts[k] + b_, t_) for t_, a_, b_ in timings[k]]
            else: spans.append((starts[k], starts[k] + adur[k], ch["intro_spoken"] if role == "intro" else (ch["outro_spoken"] if role == "outro" else cs[idx]["spoken"])))
        write_srt(f"remembering_{V}.{c}.srt", spans)
    # ---- YouTube extras: chapters + description + thumbnail ----
    def clock(t): s = int(t); return f"{s//3600}:{s//60%60:02}:{s%60:02}" if s >= 3600 else f"{s//60}:{s%60:02}"
    chap = [(0.0, h["chapter_intro"])]
    for k, (kind, role, idx) in enumerate(items):
        if kind == "voice" and role == "scene": chap.append((starts[k], scs[idx]["title"]))
        if kind == "voice" and role == "outro": chap.append((starts[k], h["chapter_outro"]))
    text = "\n\n".join([h["video_title"], h["desc"], h["chapters"] + ":\n" + "\n".join(f"{clock(t)} {n}" for t, n in chap), h["sources"], h["disclosure"]])
    if credits: text += "\n\nPhoto credits:\n" + "\n".join("- " + c for c in credits)
    open(f"remembering_{V}.description.txt", "w", encoding="utf-8").write(text + "\n")
    base = Image.open(f"{V}_m1.png").convert("RGB").resize((W, H)); ov = Image.open(f"{V}_o1.png"); base.paste(ov, (0, 0), ov)
    base.save(f"remembering_{V}_thumbnail.png")
    print(f"Built remembering_{V}.mp4 ({cum/60:.1f} min) + subtitles: {', '.join(langs)}")
