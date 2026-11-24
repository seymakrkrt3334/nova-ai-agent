import logging
import shlex
import subprocess
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from app.config import settings
from app.services.audio_convert import AudioConvertError, convert_to_wav, ffmpeg_binary

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["Voice"])

MAX_AUDIO_BYTES = 5_000_000
WAV_TYPES = {"audio/wav", "audio/x-wav", "audio/wave"}
CONVERTIBLE = {
    "audio/m4a": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/mp4": ".m4a",
    "audio/aac": ".aac",
    "audio/mpeg": ".mp3",
    "audio/ogg": ".ogg",
    "audio/flac": ".flac",
}


def voice_ready() -> bool:
    provider = (settings.voice_stt_provider or "disabled").strip().lower()
    return provider == "whisper" and bool(settings.voice_stt_command.strip())


def transcribe_locally(payload: bytes, command: str) -> str:
    tokens = shlex.split(command, posix=False)
    if not tokens:
        raise ValueError("Invalid command.")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
        handle.write(payload)
        path = handle.name
    try:
        completed = subprocess.run(
            [*tokens, path],
            shell=False,
            capture_output=True,
            timeout=60,
            check=False,
        )
    finally:
        Path(path).unlink(missing_ok=True)
    if completed.returncode != 0:
        raise RuntimeError("whisper failed")
    return completed.stdout.decode("utf-8", errors="replace").strip()[:4000]


@router.get("/status")
def voice_status():
    provider = (settings.voice_stt_provider or "disabled").strip().lower()
    return {
        "stt_provider": provider if provider in {"disabled", "whisper"} else "disabled",
        "push_to_talk": True,
        "continuous_listening": False,
        "ready": voice_ready(),
        "ffmpeg": ffmpeg_binary() is not None,
    }


@router.post("/transcribe")
async def transcribe(request: Request):
    provider = (settings.voice_stt_provider or "disabled").strip().lower()
    command = settings.voice_stt_command.strip()
    if provider != "whisper" or not command:
        raise HTTPException(
            status_code=409,
            detail="Local speech recognition is off. Set VOICE_STT_PROVIDER=whisper and VOICE_STT_COMMAND for push-to-talk.",
        )
    media = request.headers.get("content-type", "audio/wav").split(";", 1)[0].strip().lower()
    if media not in WAV_TYPES and media not in CONVERTIBLE:
        raise HTTPException(status_code=415, detail="Local recognition accepts WAV, or M4A, MP3, OGG, AAC, and FLAC converted with FFmpeg.")
    payload = await request.body()
    if not payload:
        raise HTTPException(status_code=422, detail="An audio recording is required.")
    if len(payload) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="The audio recording is too large.")
    if media in CONVERTIBLE:
        try:
            payload = convert_to_wav(payload, CONVERTIBLE[media])
        except AudioConvertError as exc:
            logger.error("Audio conversion failed: %s", exc.__class__.__name__)
            detail = "Local FFmpeg was not found." if str(exc) == "ffmpeg-missing" else "The audio recording could not be converted."
            raise HTTPException(status_code=503, detail=detail) from None
    try:
        text = transcribe_locally(payload, command)
    except Exception as exc:
        logger.error("Local speech recognition failed: %s", exc.__class__.__name__)
        raise HTTPException(status_code=503, detail="Local speech recognition could not be completed.") from None
    if not text:
        raise HTTPException(status_code=422, detail="Speech could not be transcribed.")
    from app.services.language import response_language

    return {"text": text, "language": response_language(text)}
