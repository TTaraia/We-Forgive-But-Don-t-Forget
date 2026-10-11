"""
Tigrinya speech generation with Meta MMS-TTS.

MMS-TTS expects romanized text. This script calls the `uroman` command to
romanize Ethiopic-script Tigrinya before synthesis.
Check the model/data license before using generated speech commercially.
"""
from pathlib import Path
import subprocess
import tempfile
import sys

MODEL_NAME = "facebook/mms-tts-tir"
_PIPELINE = None


def _romanize(text: str) -> str:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "uroman"], input=text, text=True, capture_output=True, check=True
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "The `uroman` command was not found. Install/configure Uroman first."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Uroman failed: {exc.stderr.strip()}") from exc
    romanized = result.stdout.strip()
    if not romanized:
        raise RuntimeError("Uroman returned empty text.")
    return romanized


def _get_pipeline():
    global _PIPELINE
    if _PIPELINE is None:
        try:
            from transformers import pipeline
        except ImportError as exc:
            raise RuntimeError(
                "Install the dependencies: torch, transformers, and soundfile."
            ) from exc
        _PIPELINE = pipeline("text-to-speech", model=MODEL_NAME)
    return _PIPELINE


def synthesize_tigrinya(text: str, out_mp3: str) -> str:
    """Generate Tigrinya speech from text and save it as an MP3."""
    text = text.strip()
    if not text:
        raise ValueError("Tigrinya text is empty.")

    romanized = _romanize(text)
    result = _get_pipeline()(romanized)
    audio = result["audio"]
    sample_rate = int(result["sampling_rate"])

    try:
        import numpy as np
        import soundfile as sf
    except ImportError as exc:
        raise RuntimeError("Install numpy and soundfile.") from exc

    destination = Path(out_mp3)
    destination.parent.mkdir(parents=True, exist_ok=True)
    audio = np.asarray(audio).squeeze()

    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path = str(Path(tmpdir) / "speech.wav")
        sf.write(wav_path, audio, sample_rate)
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-i", wav_path,
                 "-codec:a", "libmp3lame", "-q:a", "3", str(destination)],
                check=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "ffmpeg was not found. Install it and ensure it is on PATH."
            ) from exc
    return str(destination)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate Tigrinya speech with MMS-TTS.")
    parser.add_argument("input_txt", help="UTF-8 file containing Tigrinya text")
    parser.add_argument("output_mp3", help="Output MP3 path")
    args = parser.parse_args()
    text = Path(args.input_txt).read_text(encoding="utf-8")
    print(synthesize_tigrinya(text, args.output_mp3))
