import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LOCAL_FFMPEG = ROOT / "voice" / "ffmpeg" / "ffmpeg.exe"
ALLOWED_SUFFIXES = {".m4a", ".mp3", ".ogg", ".aac", ".wav", ".flac"}


class AudioConvertError(RuntimeError):
    pass


def ffmpeg_binary() -> Path | None:
    if LOCAL_FFMPEG.is_file():
        return LOCAL_FFMPEG
    found = shutil.which("ffmpeg")
    return Path(found) if found else None


def convert_to_wav(payload: bytes, suffix: str) -> bytes:
    if suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError("Unsupported audio extension.")
    binary = ffmpeg_binary()
    if binary is None:
        raise AudioConvertError("ffmpeg-missing")
    with tempfile.TemporaryDirectory(prefix="nova-audio-") as directory:
        source = Path(directory) / f"input{suffix.lower()}"
        target = Path(directory) / "speech.wav"
        source.write_bytes(payload)
        completed = subprocess.run(
            [str(binary), "-y", "-i", str(source), "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(target)],
            shell=False,
            capture_output=True,
            timeout=30,
            check=False,
        )
        if completed.returncode != 0 or not target.is_file():
            raise AudioConvertError("ffmpeg-failed")
        return target.read_bytes()
