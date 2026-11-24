import pytest
from fastapi.testclient import TestClient

from app.errors import LLMUnavailableError, MemoryStoreError
from app.main import app
from app.services import security


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(security, "API_KEY", "test-only-key")
    return TestClient(app)


@pytest.fixture(autouse=True)
def block_external_services(monkeypatch):
    async def embed_blocked(*args, **kwargs):
        raise RuntimeError("embed blocked in tests")

    async def chat_blocked(*args, **kwargs):
        raise RuntimeError("ollama blocked in tests")

    def gmail_blocked(*args, **kwargs):
        raise RuntimeError("gmail blocked in tests")

    async def connect_blocked(*args, **kwargs):
        raise RuntimeError("database blocked in tests")

    monkeypatch.setattr("app.services.memory.get_embedding", embed_blocked)
    monkeypatch.setattr("app.services.memory.client.embed", embed_blocked)
    monkeypatch.setattr("app.services.llm.client.chat", chat_blocked)
    monkeypatch.setattr("app.services.gmail.get_gmail_service", gmail_blocked)
    monkeypatch.setattr("psycopg.AsyncConnection.connect", connect_blocked)


HEADERS = {"X-API-Key": "test-only-key"}


def test_health_and_chat_require_api_key(client, monkeypatch):
    assert client.get("/health").status_code == 401
    assert client.post("/chat", json={"message": "ping"}).status_code == 401

    health = client.get("/health", headers=HEADERS)
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    async def fake_reply(message, **kwargs):
        return "merhaba"

    async def no_history(limit=10, session_id=None):
        return []

    monkeypatch.setattr("app.main.get_chat_history", no_history)
    monkeypatch.setattr("app.main.run_agent", fake_reply)
    chat = client.post("/chat", headers=HEADERS, json={"message": "ping"})
    assert chat.status_code == 200
    assert chat.json() == {"reply": "merhaba", "language": None}

    empty = client.post("/chat", headers=HEADERS, json={"message": ""})
    assert empty.status_code == 422


def test_chat_errors_do_not_leak_exception_text(client, monkeypatch):
    async def no_history(limit=10, session_id=None):
        return []

    monkeypatch.setattr("app.main.get_chat_history", no_history)

    async def unavailable(message, **kwargs):
        raise LLMUnavailableError("local-model-detail")

    monkeypatch.setattr("app.main.run_agent", unavailable)
    response = client.post("/chat", headers=HEADERS, json={"message": "ping"})
    assert response.status_code == 503
    assert response.json()["detail"] == "Yerel yapay zeka servisine erişilemedi."
    assert "local-model-detail" not in response.text

    async def memory_down(message, **kwargs):
        raise MemoryStoreError("database-detail")

    monkeypatch.setattr("app.main.run_agent", memory_down)
    response = client.post("/chat", headers=HEADERS, json={"message": "ping"})
    assert response.status_code == 503
    assert response.json()["detail"] == "Hafıza servisine erişilemedi."
    assert "database-detail" not in response.text

    async def unexpected(message, **kwargs):
        raise RuntimeError("secret-trace")

    monkeypatch.setattr("app.main.run_agent", unexpected)
    response = client.post("/chat", headers=HEADERS, json={"message": "ping"})
    assert response.status_code == 500
    assert response.json()["detail"] == "İstek tamamlanamadı."
    assert "secret-trace" not in response.text


def test_gmail_routes_use_mock_and_hide_failures(client, monkeypatch):
    fake = [{
        "id": "m1",
        "sender": "a@example.com",
        "subject": "Deneme",
        "date": "Mon",
        "snippet": "ornek",
    }]

    def fake_search(query, limit):
        assert query == "in:inbox"
        assert limit == 10
        return fake

    monkeypatch.setattr("app.gmail_api.search_emails", fake_search)
    response = client.get("/gmail/inbox", headers=HEADERS)
    body = response.json()
    if response.status_code != 200 or body.get("emails") != fake:
        count = len(body.get("emails", [])) if isinstance(body, dict) else -1
        raise AssertionError(f"gmail inbox mismatch status={response.status_code} count={count}")

    missing = client.get("/gmail/search", headers=HEADERS)
    assert missing.status_code == 422

    too_long = client.get("/gmail/search", headers=HEADERS, params={"q": "x" * 501})
    assert too_long.status_code == 422

    def explode(query, limit):
        raise RuntimeError("token super-secret")

    monkeypatch.setattr("app.gmail_api.search_emails", explode)
    failed = client.get("/gmail/unread", headers=HEADERS)
    assert failed.status_code == 503
    assert failed.json()["detail"] == "Gmail servisine erişilemedi."
    assert "super-secret" not in failed.text


def test_memory_routes_do_not_touch_live_store(client, monkeypatch):
    blank = client.post(
        "/memory/save",
        headers=HEADERS,
        json={"content": "   ", "category": "general"},
    )
    assert blank.status_code == 422

    async def save(content, category="general", **kwargs):
        assert content == "ornek kayit"
        assert category == "general"
        assert kwargs.get("consent") is True

    monkeypatch.setattr("app.memory_api.save_memory", save)
    saved = client.post(
        "/memory/save",
        headers=HEADERS,
        json={"content": " ornek kayit ", "category": "general"},
    )
    assert saved.status_code == 200
    assert saved.json() == {"status": "saved"}

    async def search(query, limit=5):
        assert query == "ornek"
        assert limit == 2
        return ["ornek kayit"]

    monkeypatch.setattr("app.memory_api.search_memories", search)
    found = client.post(
        "/memory/search",
        headers=HEADERS,
        json={"query": "ornek", "limit": 2},
    )
    assert found.status_code == 200
    assert found.json() == {"memories": ["ornek kayit"]}

    async def list_rows(limit=100):
        return [{
            "id": 1,
            "content": "ornek",
            "category": "general",
            "created_at": None,
        }]

    monkeypatch.setattr("app.memory_api.list_memories", list_rows)
    listed = client.get("/memory/list", headers=HEADERS)
    body = listed.json()
    expected = {"memories": [{
        "id": 1,
        "content": "ornek",
        "category": "general",
        "created_at": None,
    }]}
    if listed.status_code != 200 or body != expected:
        count = len(body.get("memories", [])) if isinstance(body, dict) else -1
        raise AssertionError(f"memory list mismatch status={listed.status_code} count={count}")

    missing = client.delete("/memory/abc", headers=HEADERS)
    assert missing.status_code == 422

    async def not_deleted(memory_id):
        assert memory_id == 2147483647
        return False

    monkeypatch.setattr("app.memory_api.delete_memory", not_deleted)
    deleted = client.delete("/memory/2147483647", headers=HEADERS)
    assert deleted.status_code == 404
    assert deleted.json()["detail"] == "Hafıza kaydı bulunamadı."
