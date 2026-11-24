import json
from pathlib import Path

import pytest

from app.agents.tools import (
    MAX_TOOL_STEPS,
    GmailSearchArguments,
    REGISTRY,
    build_gmail_query,
    parse_tool_call,
    prepare_emails,
    resolve_gmail_search,
    router_instructions,
    router_payload,
)
from app.config import BACKEND_DIR, settings
from app.services.gmail import normalize_search
from app.services.memory import EMBEDDING_DIM, validate_memory, vector_string


def test_registry_is_read_only_catalog():
    assert {
        "chat",
        "gmail_search",
        "memory_search",
        "memory_save",
        "gmail_read",
        "gmail_draft",
        "web_search",
        "web_read",
        "contacts_search",
        "calendar_list",
        "calendar_propose",
    } <= set(REGISTRY)
    assert "gmail_send" not in REGISTRY
    assert "calendar_delete" not in REGISTRY
    instructions = router_instructions()
    for name in REGISTRY:
        assert name in instructions
    assert "gmail_send" not in instructions
    assert MAX_TOOL_STEPS == 3


def test_parse_accepts_fenced_json_and_rejects_unknown_tools():
    parsed = parse_tool_call(
        """```json
        {"tool":"chat","arguments":{}}
        ```"""
    )
    assert parsed is not None
    assert parsed.tool == "chat"
    assert parse_tool_call('{"tool":"gmail_send","arguments":{}}') is None
    assert parse_tool_call("merhaba") is None
    assert parse_tool_call('["chat"]') is None


def test_invalid_gmail_arguments_fall_back_to_safe_defaults():
    parsed = parse_tool_call(json.dumps({
        "tool": "gmail_search",
        "arguments": {"limit": 999, "query": "in:anywhere filename:pdf"},
    }))
    assert parsed is not None
    assert parsed.arguments.limit == 30
    query = build_gmail_query(resolve_gmail_search("mailler", parsed.arguments))
    assert query == "in:inbox"
    assert "filename:pdf" not in query


def test_sent_today_query_is_not_forced_into_inbox():
    arguments = resolve_gmail_search(
        "bugün gönderilmiş fatura mailleri",
        GmailSearchArguments(location="inbox", subject="fatura\nin:anywhere", newer_than_days=30),
    )
    query = build_gmail_query(arguments)
    assert query == 'in:sent newer_than:1d subject:"fatura in:anywhere"'
    assert "filename:" not in query


def test_ambiguous_location_keeps_validated_model_choice():
    arguments = resolve_gmail_search(
        "gönderilmiş gelen mailler",
        GmailSearchArguments(location="unread"),
    )
    assert build_gmail_query(arguments) == "is:unread"


def test_router_payload_and_email_preview_hide_extra_fields():
    payload = router_payload("özetle", [{
        "tool": "gmail_search",
        "ok": True,
        "count": 1,
        "query": "in:inbox",
        "emails": [{"snippet": "GIZLI-ICERIK"}],
    }])
    encoded = json.dumps(payload, ensure_ascii=False)
    if "GIZLI-ICERIK" in encoded or "in:inbox" in encoded:
        raise AssertionError("router payload includes email data")

    prepared = prepare_emails([{
        "id": "abc",
        "sender": "a@example.com",
        "subject": "Konu",
        "date": "Mon",
        "snippet": "x" * 500,
        "secret": "no",
    }])
    assert list(prepared[0]) == ["sender", "subject", "date", "snippet"]
    assert len(prepared[0]["snippet"]) == 300


def test_normalize_search_rejects_blank_and_overlong_input():
    assert normalize_search("  in:inbox \n is:unread ", 10) == ("in:inbox is:unread", 10)
    with pytest.raises(ValueError):
        normalize_search("   \n ", 10)
    with pytest.raises(ValueError):
        normalize_search("x" * 501, 10)
    with pytest.raises(ValueError):
        normalize_search("in:inbox", 51)
    with pytest.raises(ValueError):
        normalize_search("in:inbox", True)


def test_vector_string_accepts_only_finite_floats():
    literal = vector_string([0.25] * EMBEDDING_DIM)
    assert literal.startswith("[0.25,")
    assert "drop" not in literal
    with pytest.raises(ValueError):
        vector_string([0.1, 0.2])
    with pytest.raises(ValueError):
        vector_string(["1); select 1;--", *([0.0] * (EMBEDDING_DIM - 1))])
    with pytest.raises(ValueError):
        vector_string([float("nan"), *([0.0] * (EMBEDDING_DIM - 1))])


def test_memory_text_is_validated_before_storage():
    content, category = validate_memory("  not  ", "user_note")
    assert content == "not"
    assert category == "user_note"
    with pytest.raises(ValueError):
        validate_memory("   ", "general")
    with pytest.raises(ValueError):
        validate_memory("not", "k" * 101)


def test_settings_repr_is_redacted():
    text = repr(settings)
    leaked = text != "Settings(redacted)"
    if settings.database_url is not None and settings.database_url.get_secret_value() in text:
        leaked = True
    if settings.nova_api_key is not None and settings.nova_api_key.get_secret_value() in text:
        leaked = True
    if leaked:
        raise AssertionError("settings repr is not redacted")
    assert BACKEND_DIR.name == "backend"


def test_schema_and_env_example_are_safe_templates():
    schema = (Path(__file__).resolve().parents[1] / "app" / "db" / "schema.sql").read_text(encoding="utf-8")
    lowered = schema.lower()
    for forbidden in ("drop ", "truncate", "delete ", "alter "):
        assert forbidden not in lowered
    assert "create extension if not exists vector" in lowered
    assert "vector(768)" in lowered
    assert "create table if not exists memories" in lowered
    assert "create table if not exists conversations" in lowered

    example = (BACKEND_DIR / ".env.example").read_text(encoding="utf-8")
    for key in ("OLLAMA_MODEL", "OLLAMA_BASE_URL", "OLLAMA_EMBED_MODEL", "DATABASE_URL", "NOVA_API_KEY"):
        assert key in example
    assert "PASSWORD" in example
    assert "sk-" not in example
    assert "OPENAI_API_KEY" not in example
