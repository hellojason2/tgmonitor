-- TGmonitor PostgreSQL Schema
-- Phase 1: devices, employees, screenshots tables

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Employees
CREATE TABLE IF NOT EXISTS employees (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    location    TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Devices (Mac agents — each has one token)
CREATE TABLE IF NOT EXISTS devices (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    machine_id  TEXT UNIQUE NOT NULL,
    token_hash  TEXT NOT NULL,
    employee_id UUID REFERENCES employees(id),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ
);

-- Screenshots
CREATE TABLE IF NOT EXISTS screenshots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id       UUID REFERENCES devices(id) NOT NULL,
    employee_id     UUID REFERENCES employees(id) NOT NULL,
    captured_at     TIMESTAMPTZ NOT NULL,
    received_at     TIMESTAMPTZ DEFAULT NOW(),
    file_path       TEXT NOT NULL,
    thumb_path      TEXT,
    file_size_bytes INTEGER,
    app_name        TEXT,
    window_title    TEXT,
    analysis_status TEXT DEFAULT 'pending'
);

-- AI Analysis Results
CREATE TABLE IF NOT EXISTS analysis_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    screenshot_id   UUID REFERENCES screenshots(id) NOT NULL UNIQUE,
    caption         TEXT NOT NULL,
    risk_score      TEXT NOT NULL CHECK (risk_score IN ('low', 'medium', 'high')),
    model_used      TEXT NOT NULL DEFAULT 'gemini-2.5-flash-lite',
    tokens_used     INTEGER,
    api_cost_usd    NUMERIC(8,6),
    processed_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Risk Alerts
CREATE TABLE IF NOT EXISTS alerts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id     UUID REFERENCES employees(id) NOT NULL,
    screenshot_id   UUID REFERENCES screenshots(id) NOT NULL,
    alert_type      TEXT NOT NULL,
    caption         TEXT NOT NULL,
    risk_score      TEXT NOT NULL CHECK (risk_score IN ('low', 'medium', 'high')),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    acknowledged    BOOLEAN DEFAULT FALSE
);

-- Daily Journals
CREATE TABLE IF NOT EXISTS daily_journals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id     UUID REFERENCES employees(id) NOT NULL,
    journal_date    DATE NOT NULL,
    narrative       TEXT NOT NULL,
    screenshot_count INTEGER NOT NULL DEFAULT 0,
    high_risk_count INTEGER NOT NULL DEFAULT 0,
    generated_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(employee_id, journal_date)
);

-- Add analyzed_at column to screenshots
ALTER TABLE screenshots ADD COLUMN IF NOT EXISTS analyzed_at TIMESTAMPTZ;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_screenshots_employee_captured ON screenshots(employee_id, captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_screenshots_device ON screenshots(device_id);
CREATE INDEX IF NOT EXISTS idx_screenshots_status ON screenshots(analysis_status);
CREATE INDEX IF NOT EXISTS idx_devices_machine_id ON devices(machine_id);
CREATE INDEX IF NOT EXISTS idx_alerts_employee_created ON alerts(employee_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON alerts(acknowledged);
CREATE INDEX IF NOT EXISTS idx_daily_journals_employee_date ON daily_journals(employee_id, journal_date DESC);
