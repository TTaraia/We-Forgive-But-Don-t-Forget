"""Usage: python make_history.py (project: Remembering the Eritrean War Years) en|am|ti
Builds remembering_<lang>.mp4 (intro music, narrated scenes with a map for each, outro music) and remembering_<lang>.<sub>.srt files.
Tigrinya has no free voice: put your own recordings in audio_ti/01.mp3 ... (scene numbers); scenes without a recording
become silent captioned scenes over quiet music."""
import asyncio, glob, json, os, re, subprocess, sys, textwrap
from PIL import Image, ImageDraw
import lang, mapkit, histmap, music, scenes

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
    if os.path.exists("music.mp3"): p = "music.mp3"
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

def add_bed(video_in, video_out, total):
    """Mixes the bed under the narration: loud in the first/last 10 s, quiet (BED_LEVEL, default 0.16) under the voice."""
    lvl = float(os.environ.get("BED_LEVEL", "0.16"))
    env = f"{lvl}+{0.9 - lvl:.3f}*clip((10-t)/2,0,1)+{0.9 - lvl:.3f}*clip((t-({total:.2f}-12))/2,0,1)"
    fc = (f"[1:a]volume='{env}':eval=frame,afade=t=in:d=1.5,afade=t=out:st={total - 4:.2f}:d=4,atrim=0:{total:.2f}[bed];"
          f"[0:a][bed]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", video_in, "-stream_loop", "-1", "-i", bed_file(), "-filter_complex", fc,
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.2f}", video_out])

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
        T(d, (W//2, 280), h["title"][0], 64, INK, "m"); T(d, (W//2, 365), h["title"][1], 64, INK, "m"); T(d, (W//2, 460), h["intro_sub"], 32, ACC, "m")
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

def check_files():
    """Stops with a clear message if one of the .py files in the repo is an older version than make_history.py."""
    need = {"scenes": ["parse", "validate"], "lang": ["HIST", "draw_text", "wrap", "width"], "music": ["make_music", "make_eritrean_bed"],
            "histmap": ["render"], "mapkit": ["load", "tint", "flag_tint", "set_lang", "label"]}
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
    total = len(scs); parts, starts, cum = [], [], 0.0
    for k, ((kind, role, idx), a, D) in enumerate(zip(items, audio, durs)):
        spec = en[idx]["spec"] if role == "scene" else {"view": "horn", "style": "independent"}
        histmap.render(countries, spec, V).save(f"{V}_m{k}.png")
        overlay(role if role != "scene" else "scene", scs[idx] if idx is not None else None, f"{V}_o{k}.png", (idx or 0) + 1, total, spec)
        xs, xe, ys, ye = (0, 128, 0, 72) if k % 2 == 0 else (128, 0, 72, 0)
        fc = (f"[0:v]crop=2432:1368:x='{xs}+({xe - xs})*t/{D:.3f}':y='{ys}+({ye - ys})*t/{D:.3f}',scale={W}:{H}:flags=bicubic[bg];[bg][1:v]overlay=0:0[v]")
        run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "25", "-t", f"{D:.2f}", "-i", f"{V}_m{k}.png",
             "-loop", "1", "-framerate", "25", "-t", f"{D:.2f}", "-i", f"{V}_o{k}.png", "-i", a, "-filter_complex", fc,
             "-map", "[v]", "-map", "2:a", "-af", f"apad=whole_dur={D:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
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
    open(f"remembering_{V}.description.txt", "w", encoding="utf-8").write(text + "\n")
    base = Image.open(f"{V}_m1.png").convert("RGB").resize((W, H)); ov = Image.open(f"{V}_o1.png"); base.paste(ov, (0, 0), ov)
    base.save(f"remembering_{V}_thumbnail.png")
    print(f"Built remembering_{V}.mp4 ({cum/60:.1f} min) + subtitles: {', '.join(langs)}")
