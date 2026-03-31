#!/bin/bash
# TGmonitor Phase 3 Deployment Script
# Run on VPS: cd /var/app/tgmonitor && bash deploy_phase3.sh
#
# Phase 3 adds: Gemini AI analysis, alerts, daily journals

set -e
cd /var/app/tgmonitor

echo "=== TGmonitor Phase 3 Deployment ==="
echo ""

# Step 1: Pull latest code
echo "[1/4] Pulling latest code..."
git pull origin main || git pull

# Step 2: Run database migrations
echo "[2/4] Running database migrations..."
docker compose exec -T postgres psql -U tgmonitor -d tgmonitor << 'SQL'
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

-- New indexes
CREATE INDEX IF NOT EXISTS idx_alerts_employee_created ON alerts(employee_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON alerts(acknowledged);
CREATE INDEX IF NOT EXISTS idx_daily_journals_employee_date ON daily_journals(employee_id, journal_date DESC);
SQL
echo "  Schema migration complete."

# Step 3: Build and restart backend
echo "[3/4] Rebuilding backend with AI analysis..."
docker compose build backend
echo "  Build complete."

# Step 4: Restart services
echo "[4/4] Restarting services..."
docker compose up -d backend
sleep 5

# Verify
echo ""
echo "=== Verification ==="
curl -sf http://localhost:8000/api/v1/health && echo "Backend: OK" || echo "Backend: FAILED"
curl -sf http://localhost:8000/api/v1/ready && echo "Database: OK" || echo "Database: FAILED"

echo ""
echo "=== Phase 3 Deployment Complete ==="
echo ""
echo "New endpoints:"
echo "  GET  /api/v1/alerts           - List alerts"
echo "  POST /api/v1/alerts/{id}/acknowledge"
echo "  POST /api/v1/alerts/acknowledge-all"
echo "  GET  /api/v1/journals         - List journals"
echo "  GET  /api/v1/journals/latest/{employee_id}"
echo ""
echo "Background workers started:"
echo "  - Analysis worker: polls pending screenshots every 30s"
echo "  - Daily journal cron: runs at 23:59 UTC each day"
echo ""
echo "IMPORTANT: Set GEMINI_API_KEY env var if not already set:"
echo "  echo 'GEMINI_API_KEY=your_key_here' >> .env"
echo "  docker compose up -d backend"
