import asyncio
import json

import pytest

from app.agents.agent import run_agent
from app.errors import LLMUnavailableError


def _run(coro):
    return asyncio.run(coro)


def test_legacy_remember_delegates_without_tool_router():
    calls = {"router": 0, "save": 0, "reply": 0}

    async def router(message, observations):
        calls["router"] += 1
        return '{"tool":"chat","arguments":{}}'

    async def reply(message):
        calls["reply"] += 1
        return "delegated"

    async def save(content, category="general"):
        calls["save"] += 1

    result = _run(run_agent(
        "Bunu Hatırla: mavi defter",
        router=router,
        reply_fn=reply,
        memory_save=save,
    ))

    assert result == "delegated"
    assert calls == {"router": 0, "save": 0, "reply": 1}


def test_explicit_save_uses_user_text_not_model_text():
    saved = []

    async def router(message, observations):
        raise AssertionError("router should not run")

    async def save(content, category="general", *args, **kwargs):
        saved.append((content, category))

    result = _run(run_agent(
        "hafızaya kaydet: kırmızı kalem",
        router=router,
        memory_save=save,
        reply_fn=router,
    ))

    assert result == "Tamam, bunu kalıcı hafızama kaydettim."
    assert saved == [("kırmızı kalem", "user_note")]

    result = _run(run_agent(
        "hafızaya kaydet:",
        router=router,
        memory_save=save,
        reply_fn=router,
    ))
    assert result == "Neyi hatırlamamı istediğini yaz."
    assert saved == [("kırmızı kalem", "user_note")]


def test_model_cannot_save_memory_without_explicit_request():
    calls = {"router": 0, "save": 0}

    async def router(message, observations):
        calls["router"] += 1
        return json.dumps({
            "tool": "memory_save",
            "arguments": {"content": "model-uydurmasi", "category": "secret"},
        })

    async def save(content, category="general"):
        calls["save"] += 1

    async def reply(message):
        return "sohbet"

    result = _run(run_agent(
        "merhaba",
        router=router,
        reply_fn=reply,
        memory_save=save,
    ))

    assert result == "sohbet"
    assert calls == {"router": 3, "save": 0}


def test_gmail_query_builder_ignores_raw_model_query():
    seen = []

    async def router(message, observations):
        if observations:
            return '{"tool":"chat","arguments":{}}'
        return json.dumps({
            "tool": "gmail_search",
            "arguments": {
                "query": "in:anywhere filename:pdf",
                "location": "inbox",
            },
        })

    def gmail(query, limit):
        seen.append((query, limit))
        return [{"sender": "a@example.com", "subject": "S", "date": "Mon", "snippet": "ornek"}]

    async def synthesize(message, observations):
        assert observations[0]["query"] == "in:sent newer_than:1d"
        assert "filename:pdf" not in json.dumps(observations)
        return "ozet"

    async def reply(message):
        raise AssertionError("chat fallback should not replace email summary")

    result = _run(run_agent(
        "bugün gönderilmiş mailler",
        router=router,
        reply_fn=reply,
        gmail_search=gmail,
        synthesize=synthesize,
    ))

    assert result == "ozet"
    assert seen == [("in:sent newer_than:1d", 30)]


def test_gmail_errors_and_empty_results_stop_cleanly():
    async def router(message, observations):
        return '{"tool":"gmail_search","arguments":{}}'

    def fail(query, limit):
        raise RuntimeError("token should stay inside the exception")

    failed = _run(run_agent("mailler", router=router, gmail_search=fail, reply_fn=router))
    assert failed == "Gmail bağlantısında bir hata oluştu."

    def empty(query, limit):
        return []

    nothing = _run(run_agent("mailler", router=router, gmail_search=empty, reply_fn=router))
    assert nothing == "Aramana uygun mail bulamadım."


def test_tool_loop_is_bounded_to_three_steps():
    calls = {"router": 0, "gmail": 0, "synth": 0}

    async def router(message, observations):
        calls["router"] += 1
        return '{"tool":"gmail_search","arguments":{"limit":5}}'

    def gmail(query, limit):
        calls["gmail"] += 1
        assert limit == 5
        assert query == "in:inbox"
        return [{"sender": "a", "subject": "s", "date": "d", "snippet": "n"}]

    async def synthesize(message, observations):
        calls["synth"] += 1
        assert len(observations) == 3
        return "ozet"

    async def reply(message):
        raise AssertionError("reply should not run after productive tools")

    result = _run(run_agent(
        "maillerimi özetle",
        router=router,
        gmail_search=gmail,
        synthesize=synthesize,
        reply_fn=reply,
    ))

    assert result == "ozet"
    assert calls == {"router": 3, "gmail": 3, "synth": 1}


def test_invalid_router_output_falls_back_to_chat():
    async def router(message, observations):
        return "bu json degil"

    async def reply(message):
        return "sohbet"

    result = _run(run_agent("selam", router=router, reply_fn=reply))
    assert result == "sohbet"


def test_router_transport_error_is_explicit():
    async def router(message, observations):
        raise LLMUnavailableError

    async def reply(message):
        raise AssertionError("chat should not hide a model outage")

    with pytest.raises(LLMUnavailableError):
        _run(run_agent("selam", router=router, reply_fn=reply))
