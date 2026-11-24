-- Idempotent bootstrap for a new local NOVA database with pgvector.
-- Existing rows stay in place. Do not recreate Docker volumes to apply this file.
-- The application expects embedding dimension 768 (nomic-embed-text).

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS memories (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    category VARCHAR(100) DEFAULT 'general',
    embedding vector(768),
    created_at TIMESTAMPTZ DEFAULT now(),
    source VARCHAR(50) DEFAULT 'manual',
    updated_at TIMESTAMPTZ DEFAULT now(),
    durability VARCHAR(20) DEFAULT 'long_term'
);

CREATE INDEX IF NOT EXISTS idx_memories_category ON memories (category);

CREATE TABLE IF NOT EXISTS automations (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    prompt TEXT NOT NULL,
    interval_minutes INTEGER NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    next_run_at TIMESTAMPTZ,
    last_status VARCHAR(40),
    created_at TIMESTAMPTZ DEFAULT now(),
    scope VARCHAR(40) NOT NULL DEFAULT 'manual',
    access_grant VARCHAR(40) NOT NULL DEFAULT 'none',
    auto_execute BOOLEAN NOT NULL DEFAULT false,
    authorized BOOLEAN NOT NULL DEFAULT false,
    last_run_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS automation_runs (
    id BIGSERIAL PRIMARY KEY,
    automation_id BIGINT NOT NULL,
    window_key VARCHAR(80) NOT NULL UNIQUE,
    status VARCHAR(32) NOT NULL,
    summary TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS social_messages (
    id BIGSERIAL PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,
    external_id VARCHAR(128) NOT NULL,
    chat_id VARCHAR(128) NOT NULL,
    sender VARCHAR(180),
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (platform, external_id)
);

CREATE TABLE IF NOT EXISTS conversations (
    id BIGSERIAL PRIMARY KEY,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    session_id VARCHAR(64)
);
