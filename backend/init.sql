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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_screenshots_employee_captured ON screenshots(employee_id, captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_screenshots_device ON screenshots(device_id);
CREATE INDEX IF NOT EXISTS idx_screenshots_status ON screenshots(analysis_status);
CREATE INDEX IF NOT EXISTS idx_devices_machine_id ON devices(machine_id);
