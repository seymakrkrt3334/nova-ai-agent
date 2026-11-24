import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLI = ROOT / "unpack" / "Release" / "whisper-cli.exe"
MODEL = ROOT / "models" / "ggml-base.bin"
STAMP = re.compile(r"\[[0-9:.]+\s+-->\s+[0-9:.]+\]")


def transcript(audio: str) -> str:
    completed = subprocess.run(
        [str(CLI), "-m", str(MODEL), "-f", audio, "-l", "auto", "-t", "4", "-nt", "-np", "-ng"],
        shell=False,
        capture_output=True,
        timeout=60,
        check=False,
    )
    if completed.returncode != 0:
        return ""
    lines = []
    for raw in completed.stdout.decode("utf-8", errors="replace").splitlines():
        cleaned = " ".join(STAMP.sub(" ", raw).split())
        lowered = cleaned.lower()
        if cleaned and not lowered.startswith("whisper") and "auto-detected language" not in lowered:
            lines.append(cleaned)
    return " ".join(lines)[:4000]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(2)
    text = transcript(sys.argv[1])
    sys.stdout.write(text)
    sys.exit(0 if text else 1)
