"""Removes the singing/voice from a song and keeps the instrumental, using a UVR "MDX-Net" model (ONNX) - no PyTorch needed.

  python remove_vocals.py song.m4a                       -> music_instrumental.mp3   (+ music_vocals_only.mp3 for checking)
  python remove_vocals.py song.m4a --model Kim_Vocal_2   -> uses the vocal model and subtracts (try if the default sounds odd)

Models (about 65 MB) are downloaded from github.com/TRvlvr/model_repo the first time.
Only use recordings you own or have permission to edit.
"""
import argparse, os, subprocess, sys, urllib.request
import numpy as np
from scipy.signal import get_window

BASE = "https://github.com/TRvlvr/model_repo/releases/download/all_public_uvr_models/"
# name: (file, n_fft, dim_f, dim_t, compensate, what the model outputs)
MODELS = {"Inst_HQ_3": ("UVR-MDX-NET-Inst_HQ_3.onnx", 7680, 3072, 256, 1.0, "instrumental"),
          "Kim_Vocal_2": ("Kim_Vocal_2.onnx", 7680, 3072, 256, 1.0, "vocals")}
HOP = 1024

def stft(x, n_fft):                               # x: [ch, n] -> [ch, F, T] complex (same as torch.stft, center=True, hann)
    win = get_window("hann", n_fft, fftbins=True).astype(np.float32); pad = n_fft // 2
    xp = np.pad(x, ((0, 0), (pad, pad)), mode="reflect")
    fr = np.lib.stride_tricks.sliding_window_view(xp, n_fft, axis=1)[:, ::HOP]
    return np.fft.rfft(fr * win, axis=-1).transpose(0, 2, 1)

def istft(spec, n_fft, length):                   # [ch, F, T] complex -> [ch, length]
    win = get_window("hann", n_fft, fftbins=True).astype(np.float32); pad = n_fft // 2
    fr = np.fft.irfft(spec.transpose(0, 2, 1), n=n_fft, axis=-1).astype(np.float32) * win
    ch, T, _ = fr.shape; n = HOP * (T - 1) + n_fft
    out, norm = np.zeros((ch, n), np.float32), np.zeros(n, np.float32)
    for t in range(T):
        out[:, t * HOP:t * HOP + n_fft] += fr[:, t]; norm[t * HOP:t * HOP + n_fft] += win ** 2
    return (out / np.maximum(norm, 1e-8))[:, pad:pad + length]

def run_model(mix, model_key, models_dir="models"):
    import onnxruntime as ort
    fname, n_fft, dim_f, dim_t, comp, _ = MODELS[model_key]
    path = os.path.join(models_dir, fname); os.makedirs(models_dir, exist_ok=True)
    if not os.path.exists(path):
        print("downloading", fname, "..."); urllib.request.urlretrieve(BASE + fname, path)
    sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"]); inp = sess.get_inputs()[0].name
    chunk = HOP * (dim_t - 1); trim = n_fft // 2; gen = chunk - 2 * trim; n = mix.shape[1]
    padn = gen - (n % gen)
    mp = np.concatenate([np.zeros((2, trim), np.float32), mix, np.zeros((2, padn + trim), np.float32)], axis=1)
    out = []
    for i in range(0, n + padn, gen):
        seg = mp[:, i:i + chunk]
        if seg.shape[1] < chunk: seg = np.pad(seg, ((0, 0), (0, chunk - seg.shape[1])))
        S = stft(seg, n_fft)[:, :dim_f]                                        # [2, dim_f, T]
        x = np.stack([S.real, S.imag], axis=1).reshape(1, 4, dim_f, S.shape[-1]).astype(np.float32)   # L_re L_im R_re R_im
        y = sess.run(None, {inp: x})[0].reshape(2, 2, dim_f, -1)
        full = np.zeros((2, n_fft // 2 + 1, y.shape[-1]), np.complex64)
        full[:, :dim_f] = y[:, 0] + 1j * y[:, 1]
        out.append(istft(full, n_fft, chunk)[:, trim:-trim] * comp)
        print(f"  {model_key}: {min(100, int(100 * (i + gen) / (n + padn)))}%", flush=True)
    return np.concatenate(out, axis=1)[:, :n]

def read(path):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-ac", "2", "-ar", "44100", "-f", "f32le", "_in.raw"], check=True)
    return np.fromfile("_in.raw", np.float32).reshape(-1, 2).T.copy()

def write(path, x):
    x = np.clip(x, -1, 1).T.astype(np.float32); x.tofile("_out.raw")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", "44100", "-ac", "2", "-i", "_out.raw", "-codec:a", "libmp3lame", "-b:a", "192k", path], check=True)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("song"); ap.add_argument("--model", default="Inst_HQ_3", choices=list(MODELS))
    ap.add_argument("--out", default="music_instrumental.mp3"); a = ap.parse_args()
    mix = read(a.song); res = run_model(mix, a.model)
    inst, voc = (res, mix - res) if MODELS[a.model][5] == "instrumental" else (mix - res, res)
    np.save("_inst.npy", inst); np.save("_voc.npy", voc)
    write(a.out, inst); write("music_vocals_only.mp3", voc); print("wrote", a.out)
