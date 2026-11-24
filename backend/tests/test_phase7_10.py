from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import security
from app.services.automations import advance_due_jobs
from app.voice_api import transcribe_locally

HEADERS = {"X-API-Key": "test-only-key"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(security, "API_KEY", "test-only-key")
    return TestClient(app)


def test_local_vite_origin_is_allowed(client):
    allowed = client.options(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-api-key",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"

    denied = client.get("/health", headers={"Origin": "https://evil.example", **HEADERS})
    assert denied.status_code == 200
    assert denied.headers.get("access-control-allow-origin") is None


def test_sessions_endpoint_uses_memory_service(client, monkeypatch):
    async def fake_sessions(limit=20):
        return [{"session_id": "desk1", "messages": 2, "updated_at": None, "preview": "merhaba"}]

    monkeypatch.setattr("app.memory_api.list_sessions", fake_sessions)
    response = client.get("/memory/sessions", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["sessions"][0]["session_id"] == "desk1"


def test_voice_disabled_does_not_start_a_process(client, monkeypatch):
    called = []

    def blocked(*args, **kwargs):
        called.append(True)
        raise AssertionError("process")

    monkeypatch.setattr("app.voice_api.subprocess.run", blocked)
    monkeypatch.setattr("app.voice_api.settings.voice_stt_provider", "disabled")
    monkeypatch.setattr("app.voice_api.settings.voice_stt_command", "")
    status = client.get("/voice/status", headers=HEADERS)
    assert status.status_code == 200
    body = status.json()
    assert body["ready"] is False
    assert body["push_to_talk"] is True
    assert body["continuous_listening"] is False

    response = client.post(
        "/voice/transcribe",
        headers={**HEADERS, "Content-Type": "audio/wav"},
        content=b"abc",
    )
    assert response.status_code == 409
    assert called == []


def test_voice_rejects_unsupported_audio(client, monkeypatch):
    monkeypatch.setattr("app.voice_api.settings.voice_stt_provider", "whisper")
    monkeypatch.setattr("app.voice_api.settings.voice_stt_command", "python transcribe_wav.py")
    response = client.post(
        "/voice/transcribe",
        headers={**HEADERS, "Content-Type": "audio/webm"},
        content=b"abc",
    )
    assert response.status_code == 415


def test_m4a_is_converted_locally_before_whisper(client, monkeypatch):
    seen = {}

    def fake_convert(payload, suffix):
        seen["suffix"] = suffix
        seen["payload"] = payload
        return b"converted-wav"

    def fake_run(args, shell, capture_output, timeout, check):
        seen["shell"] = shell
        seen["args"] = args

        class Result:
            returncode = 0
            stdout = "merhaba".encode()

        return Result()

    monkeypatch.setattr("app.voice_api.settings.voice_stt_provider", "whisper")
    monkeypatch.setattr("app.voice_api.settings.voice_stt_command", "python transcribe_wav.py")
    monkeypatch.setattr("app.voice_api.convert_to_wav", fake_convert)
    monkeypatch.setattr("app.voice_api.subprocess.run", fake_run)
    response = client.post(
        "/voice/transcribe",
        headers={**HEADERS, "Content-Type": "audio/m4a"},
        content=b"m4a-bytes",
    )
    assert response.status_code == 200
    assert response.json()["text"] == "merhaba"
    assert seen["suffix"] == ".m4a"
    assert seen["payload"] == b"m4a-bytes"
    assert seen["shell"] is False


def test_transcribe_locally_uses_argument_list(monkeypatch):
    seen = {}

    def fake_run(args, shell, capture_output, timeout, check):
        seen["args"] = args
        seen["shell"] = shell

        class Result:
            returncode = 0
            stdout = "selam".encode()

        return Result()

    monkeypatch.setattr("app.voice_api.subprocess.run", fake_run)
    assert transcribe_locally(b"data", "whisper.exe --model tiny") == "selam"
    assert seen["shell"] is False
    assert seen["args"][0] == "whisper.exe"
    assert seen["args"][-1].endswith(".wav")


def test_due_automation_waits_for_a_person():
    now = datetime(2026, 11, 18, tzinfo=timezone.utc)
    jobs = [{
        "id": 7,
        "name": "Sabah",
        "status": "active",
        "next_run_at": now,
        "prompt": "gelen kutusu",
    }]
    waiting = advance_due_jobs(jobs, now)
    assert waiting == [{"id": 7, "name": "Sabah"}]
    assert "prompt" not in waiting[0]
    assert jobs[0]["status"] == "awaiting_confirmation"


def test_automation_tick_does_not_return_prompt(client, monkeypatch):
    called = []

    async def fake_tick():
        called.append("tick")
        return [{"id": 7, "name": "Sabah"}]

    async def agent_blocked(*args, **kwargs):
        called.append("agent")
        raise AssertionError("agent")

    monkeypatch.setattr("app.automation_api.tick_automations", fake_tick)
    monkeypatch.setattr("app.main.run_agent", agent_blocked)
    response = client.post("/automations/tick", headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == {"notifications": [{"id": 7, "name": "Sabah"}]}
    assert "prompt" not in response.text
    assert called == ["tick"]


def test_automation_approval_requires_explicit_confirm(client, monkeypatch):
    async def fake_approve(automation_id):
        raise AssertionError("approved")

    monkeypatch.setattr("app.automation_api.approve_automation", fake_approve)
    response = client.post("/automations/3/approve", headers=HEADERS, json={"confirm": False})
    assert response.status_code == 422
    assert "onay" in response.json()["detail"].lower()
