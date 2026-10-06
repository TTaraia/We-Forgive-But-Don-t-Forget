"""Synthesises 15 s of calm classical-style piano (Pachelbel's Canon progression, public domain composition).
Put your own music.mp3 in the repo to override this."""
import math, wave, array

SR = 22050
CHORDS = [  # (bass midi, [chord tones midi])
    (50, [62, 66, 69, 74]), (45, [61, 64, 69, 73]), (47, [62, 66, 71, 74]), (42, [61, 66, 69, 73]),
    (43, [62, 67, 71, 74]), (50, [62, 66, 69, 74]), (43, [62, 67, 71, 74]), (45, [61, 64, 69, 73])]
PATTERN = [0, 1, 2, 3, 2, 1, 2, 1]

def f(m): return 440.0 * 2 ** ((m - 69) / 12)

def add(buf, start, freq, dur, amp, tau):
    n0 = int(start * SR)
    for i in range(int(dur * SR)):
        j = n0 + i
        if j >= len(buf): break
        t = i / SR
        env = min(1.0, t / 0.005) * math.exp(-t / tau)
        w = math.sin(2*math.pi*freq*t) + 0.45*math.sin(4*math.pi*freq*t) + 0.2*math.sin(6*math.pi*freq*t)
        buf[j] += amp * env * w

def make_music(path, seconds=15.0):
    buf = [0.0] * int(seconds * SR)
    step = seconds / (len(CHORDS) * 8)
    for c, (bass, tones) in enumerate(CHORDS):
        for k, idx in enumerate(PATTERN):
            t0 = (c * 8 + k) * step
            add(buf, t0, f(tones[idx]), 1.4, 0.16, 0.45)
            if k in (0, 4): add(buf, t0, f(bass), 2.0, 0.22, 0.9)
    n = len(buf)
    fi, fo = int(0.6 * SR), int(2.5 * SR)
    out = array.array("h")
    for i, v in enumerate(buf):
        g = min(1.0, i / fi) * min(1.0, (n - i) / fo)
        out.append(int(max(-1, min(1, v * g * 0.8)) * 32767))
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(out.tobytes())


def make_eritrean_bed(path, seconds=150, seed=11):
    """Original synthesised instrumental in a pentatonic mode (tizita-minor: 1 2 b3 5 b6) with a 6/8 pulse,
    plucked-lyre style notes, a soft drone and a gentle hand-drum thump. It is NOT a traditional recording.
    Short (default 2.5 min): the video builder loops it under the whole video."""
    import numpy as np
    sr = 22050
    rng = np.random.default_rng(seed)
    n = int(seconds * sr)
    out = np.zeros(n + sr * 4, dtype=np.float32)
    root = 146.83                                        # D3
    scale = [0, 2, 3, 7, 8]                              # semitones of the pentatonic mode
    degrees = [s + 12 * o for o in (0, 1) for s in scale]   # two octaves
    freq = lambda semis: root * 2 ** (semis / 12)
    eighth = 60 / 66 / 3                                 # 6/8, dotted-quarter = 66 bpm

    def add(t0, y):
        i = int(t0 * sr)
        if i < len(out): out[i:i + len(y)] += y[:len(out) - i]

    def pluck(f, dur=1.8, amp=0.16):
        t = np.arange(int(dur * sr)) / sr
        env = np.exp(-t / 0.6) * (1 - np.exp(-t / 0.004))
        y = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(4 * np.pi * f * t) * np.exp(-t / 0.35) \
            + 0.25 * np.sin(6 * np.pi * f * t) * np.exp(-t / 0.2) + 0.12 * np.sin(2 * np.pi * f * 1.004 * t)
        return (amp * env * y).astype(np.float32)

    def thump(amp=0.10):
        t = np.arange(int(0.25 * sr)) / sr
        return (amp * np.sin(2 * np.pi * (70 + 60 * np.exp(-t / 0.03)) * t) * np.exp(-t / 0.07)).astype(np.float32)

    # soft drone: root and fifth, slowly breathing
    t = np.arange(n) / sr
    drone = 0.05 * (np.sin(2 * np.pi * root * t) + 0.6 * np.sin(2 * np.pi * root * 1.5 * t)) * (0.7 + 0.3 * np.sin(2 * np.pi * t / 9))
    out[:n] += drone.astype(np.float32)

    pos, bar, step = 2, 0, 0.0
    probs = [1.0, 0.55, 0.7, 1.0, 0.55, 0.7]
    while step < seconds - 3:
        for k in range(6):
            t0 = step + k * eighth
            if k in (0, 3):
                add(t0, thump(0.10 if k == 0 else 0.06))
                add(t0, pluck(freq(degrees[0] - 12), 2.2, 0.13))
            if rng.random() < probs[k]:
                move = rng.choice([-2, -1, -1, 0, 1, 1, 2])
                pos = int(np.clip(pos + move, 0, len(degrees) - 1))
                if bar % 4 == 3 and k == 3: pos = 0 if rng.random() < 0.6 else 4    # phrase cadence on root or fifth
                add(t0, pluck(freq(degrees[pos])))
        step += 6 * eighth; bar += 1
    out = out[:n]
    fi, fo = int(0.3 * sr), int(2.5 * sr)
    out[:fi] *= np.linspace(0, 1, fi); out[-fo:] *= np.linspace(1, 0, fo)
    out = out / max(1e-9, float(np.abs(out).max())) * 0.85
    import wave
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((out * 32767).astype(np.int16).tobytes())
