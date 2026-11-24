-- Additive columns for an existing local NOVA database.
-- These statements keep current rows in place.
ALTER TABLE memories ADD COLUMN IF NOT EXISTS durability varchar(20) DEFAULT 'long_term';
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS session_id varchar(64);

CREATE TABLE IF NOT EXISTS automations (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    prompt TEXT NOT NULL,
    interval_minutes INTEGER NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    next_run_at TIMESTAMPTZ,
    last_status VARCHAR(40),
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE automations ADD COLUMN IF NOT EXISTS scope varchar(40) DEFAULT 'manual';
ALTER TABLE automations ADD COLUMN IF NOT EXISTS access_grant varchar(40) DEFAULT 'none';
ALTER TABLE automations ADD COLUMN IF NOT EXISTS auto_execute boolean DEFAULT false;
ALTER TABLE automations ADD COLUMN IF NOT EXISTS authorized boolean DEFAULT false;
ALTER TABLE automations ADD COLUMN IF NOT EXISTS last_run_at timestamptz;

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
