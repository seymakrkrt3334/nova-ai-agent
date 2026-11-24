import io
import wave
from pathlib import Path

import pytest

from app.services.audio_convert import AudioConvertError, convert_to_wav, ffmpeg_binary


def test_unexpected_suffix_is_rejected():
    with pytest.raises(ValueError):
        convert_to_wav(b"abc", ".exe")


def test_ffmpeg_command_stays_local(monkeypatch, tmp_path):
    seen = {}
    binary = tmp_path / "ffmpeg.exe"
    binary.write_bytes(b"")

    def fake_run(args, shell, capture_output, timeout, check):
        seen["args"] = args
        seen["shell"] = shell
        Path(args[-1]).write_bytes(b"RIFF")

        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr("app.services.audio_convert.ffmpeg_binary", lambda: binary)
    monkeypatch.setattr("app.services.audio_convert.subprocess.run", fake_run)
    assert convert_to_wav(b"audio", ".m4a") == b"RIFF"
    assert seen["shell"] is False
    assert seen["args"][0] == str(binary)
    assert seen["args"][1:8] == ["-y", "-i", seen["args"][3], "-ar", "16000", "-ac", "1"]
    assert "pcm_s16le" in seen["args"]


def test_missing_ffmpeg_is_reported_without_a_path(monkeypatch):
    monkeypatch.setattr("app.services.audio_convert.ffmpeg_binary", lambda: None)
    with pytest.raises(AudioConvertError) as caught:
        convert_to_wav(b"audio", ".m4a")
    assert str(caught.value) == "ffmpeg-missing"


def test_installed_ffmpeg_converts_audio_to_wav():
    if ffmpeg_binary() is None:
        pytest.skip("local ffmpeg is not present")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x00" * 1600)
    converted = convert_to_wav(buffer.getvalue(), ".wav")
    assert converted.startswith(b"RIFF")
