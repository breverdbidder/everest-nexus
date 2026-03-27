-- ============================================================
-- DAILY CHECKPOINT SYSTEM
-- Two reports: 11:59 PM checkpoint + 6:00 AM action plan
-- ============================================================

CREATE TABLE IF NOT EXISTS daily_checkpoints (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    date DATE NOT NULL,
    domain TEXT NOT NULL CHECK (domain IN ('BIDDEED','ZONEWISE','GTM','MICHAEL','PROPERTY','PERSONAL','ECOSYSTEM')),
    task TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('completed','in_progress','blocked','pending','deferred')),
    chat_url TEXT,
    detail TEXT,
    priority TEXT DEFAULT 'P2' CHECK (priority IN ('P0','P1','P2','P3')),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_minutes INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS daily_action_plans (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    date DATE NOT NULL,
    rank INT NOT NULL,
    task TEXT NOT NULL,
    domain TEXT NOT NULL,
    source TEXT,
    reason TEXT,
    estimated_minutes INT,
    actual_minutes INT,
    outcome TEXT CHECK (outcome IN ('completed','partial','skipped','blocked','deferred')),
    lesson TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS daily_scores (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    total_items INT DEFAULT 0,
    completed INT DEFAULT 0,
    in_progress INT DEFAULT 0,
    blocked INT DEFAULT 0,
    completion_rate NUMERIC(5,2) DEFAULT 0,
    top_domain TEXT,
    worst_domain TEXT,
    streak_days INT DEFAULT 0,
    pattern_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_date ON daily_checkpoints(date DESC);
CREATE INDEX IF NOT EXISTS idx_checkpoints_status ON daily_checkpoints(status);
CREATE INDEX IF NOT EXISTS idx_action_plans_date ON daily_action_plans(date DESC);
CREATE INDEX IF NOT EXISTS idx_scores_date ON daily_scores(date DESC);

ALTER TABLE daily_checkpoints ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_action_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_scores ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS checkpoints_service ON daily_checkpoints FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY IF NOT EXISTS action_plans_service ON daily_action_plans FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY IF NOT EXISTS scores_service ON daily_scores FOR ALL TO service_role USING (true) WITH CHECK (true);

-- View: weekly trends
CREATE OR REPLACE VIEW weekly_trends AS
SELECT
    date,
    total_items,
    completed,
    blocked,
    completion_rate,
    top_domain,
    worst_domain,
    streak_days,
    AVG(completion_rate) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as rolling_7day_avg
FROM daily_scores
ORDER BY date DESC;
