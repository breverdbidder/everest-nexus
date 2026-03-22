-- ============================================================
-- EVEREST NEXUS — Foundation Migration
-- 9 tables: nexus_tasks, nexus_workflows, nexus_repos,
--           nexus_tables, nexus_secrets, nexus_domains,
--           nexus_notifications, nexus_chat_sessions, nexus_insights
-- RLS: anon SELECT, service_role ALL
-- Realtime: nexus_tasks, nexus_notifications
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- TABLE: nexus_tasks (Layer 1 — Task Intelligence)
-- ============================================================
CREATE TABLE IF NOT EXISTS nexus_tasks (
    id              UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    task_id         TEXT        UNIQUE NOT NULL,
    description     TEXT        NOT NULL,
    priority        TEXT        DEFAULT 'P2' CHECK (priority IN ('P0','P1','P2','P3')),
    status          TEXT        DEFAULT 'queued' CHECK (status IN ('queued','dispatched','running','blocked','success','failed','timeout','cancelled','skipped')),
    project         TEXT,
    owner           TEXT        DEFAULT 'Claude Code',
    task_type       TEXT,
    platform        TEXT,
    triggered_by    TEXT,
    source_chat_id  TEXT,
    sla_deadline    TIMESTAMPTZ,
    escalation_count INT        DEFAULT 0,
    last_escalated_at TIMESTAMPTZ,
    auto_priority   BOOLEAN     DEFAULT true,
    gha_run_id      BIGINT,
    gha_run_url     TEXT,
    result_summary  TEXT,
    error_message   TEXT,
    tokens_used     INT         DEFAULT 0,
    cost_usd        NUMERIC(8,4) DEFAULT 0,
    batch_id        UUID,
    batch_index     INT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    dispatched_at   TIMESTAMPTZ,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nexus_tasks_priority      ON nexus_tasks (priority);
CREATE INDEX IF NOT EXISTS idx_nexus_tasks_status        ON nexus_tasks (status);
CREATE INDEX IF NOT EXISTS idx_nexus_tasks_project       ON nexus_tasks (project);
CREATE INDEX IF NOT EXISTS idx_nexus_tasks_owner         ON nexus_tasks (owner);
CREATE INDEX IF NOT EXISTS idx_nexus_tasks_sla_deadline  ON nexus_tasks (sla_deadline);
CREATE INDEX IF NOT EXISTS idx_nexus_tasks_created_at    ON nexus_tasks (created_at DESC);

ALTER TABLE nexus_tasks ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS nexus_tasks_anon_select   ON nexus_tasks;
DROP POLICY IF EXISTS nexus_tasks_service_all   ON nexus_tasks;
CREATE POLICY nexus_tasks_anon_select   ON nexus_tasks FOR SELECT TO anon USING (true);
CREATE POLICY nexus_tasks_service_all   ON nexus_tasks FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION nexus_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS nexus_tasks_updated_at ON nexus_tasks;
CREATE TRIGGER nexus_tasks_updated_at
    BEFORE UPDATE ON nexus_tasks
    FOR EACH ROW EXECUTE FUNCTION nexus_set_updated_at();

-- ============================================================
-- TABLE: nexus_workflows (Layer 2 — Workflow Intelligence)
-- ============================================================
CREATE TABLE IF NOT EXISTS nexus_workflows (
    id                      UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    repo_name               TEXT        NOT NULL,
    workflow_name           TEXT        NOT NULL,
    workflow_path           TEXT        NOT NULL,
    workflow_id             BIGINT,
    state                   TEXT,
    trigger_types           JSONB       DEFAULT '[]',
    last_run_at             TIMESTAMPTZ,
    last_run_status         TEXT,
    last_run_url            TEXT,
    total_runs_30d          INT         DEFAULT 0,
    success_rate_30d        NUMERIC(5,2),
    avg_duration_seconds    INT,
    is_scheduled            BOOLEAN     DEFAULT false,
    schedule_expression     TEXT,
    is_dead                 BOOLEAN     DEFAULT false,
    estimated_cost_30d      NUMERIC(8,4) DEFAULT 0,
    updated_at              TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(repo_name, workflow_path)
);

CREATE INDEX IF NOT EXISTS idx_nexus_workflows_repo_name   ON nexus_workflows (repo_name);
CREATE INDEX IF NOT EXISTS idx_nexus_workflows_is_dead     ON nexus_workflows (is_dead);
CREATE INDEX IF NOT EXISTS idx_nexus_workflows_last_run_at ON nexus_workflows (last_run_at);
CREATE INDEX IF NOT EXISTS idx_nexus_workflows_state       ON nexus_workflows (state);

ALTER TABLE nexus_workflows ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS nexus_workflows_anon_select ON nexus_workflows;
DROP POLICY IF EXISTS nexus_workflows_service_all ON nexus_workflows;
CREATE POLICY nexus_workflows_anon_select ON nexus_workflows FOR SELECT TO anon USING (true);
CREATE POLICY nexus_workflows_service_all ON nexus_workflows FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP TRIGGER IF EXISTS nexus_workflows_updated_at ON nexus_workflows;
CREATE TRIGGER nexus_workflows_updated_at
    BEFORE UPDATE ON nexus_workflows
    FOR EACH ROW EXECUTE FUNCTION nexus_set_updated_at();

-- ============================================================
-- TABLE: nexus_repos (Layer 3 — Repo Intelligence)
-- ============================================================
CREATE TABLE IF NOT EXISTS nexus_repos (
    id                          UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    repo_name                   TEXT        UNIQUE NOT NULL,
    full_name                   TEXT,
    tier                        TEXT        NOT NULL CHECK (tier IN ('core','active','monitored','archived')),
    description                 TEXT,
    language                    TEXT,
    topics                      JSONB       DEFAULT '[]',
    default_branch              TEXT        DEFAULT 'main',
    is_private                  BOOLEAN     DEFAULT false,
    created_at_gh               TIMESTAMPTZ,
    last_push_at                TIMESTAMPTZ,
    last_push_by                TEXT,
    last_ci_status              TEXT        CHECK (last_ci_status IN ('success','failure','pending','none')),
    last_ci_url                 TEXT,
    last_ci_at                  TIMESTAMPTZ,
    open_prs                    INT         DEFAULT 0,
    open_issues                 INT         DEFAULT 0,
    total_commits               INT         DEFAULT 0,
    contributors                JSONB       DEFAULT '[]',
    size_kb                     INT         DEFAULT 0,
    stale_days                  INT         DEFAULT 0,
    health_score                INT         DEFAULT 100,
    consolidation_group         TEXT,
    consolidation_recommendation TEXT,
    dependencies                JSONB       DEFAULT '[]',
    updated_at                  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nexus_repos_tier               ON nexus_repos (tier);
CREATE INDEX IF NOT EXISTS idx_nexus_repos_stale_days         ON nexus_repos (stale_days DESC);
CREATE INDEX IF NOT EXISTS idx_nexus_repos_health_score       ON nexus_repos (health_score);
CREATE INDEX IF NOT EXISTS idx_nexus_repos_consolidation_group ON nexus_repos (consolidation_group);

ALTER TABLE nexus_repos ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS nexus_repos_anon_select ON nexus_repos;
DROP POLICY IF EXISTS nexus_repos_service_all ON nexus_repos;
CREATE POLICY nexus_repos_anon_select ON nexus_repos FOR SELECT TO anon USING (true);
CREATE POLICY nexus_repos_service_all ON nexus_repos FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP TRIGGER IF EXISTS nexus_repos_updated_at ON nexus_repos;
CREATE TRIGGER nexus_repos_updated_at
    BEFORE UPDATE ON nexus_repos
    FOR EACH ROW EXECUTE FUNCTION nexus_set_updated_at();

-- ============================================================
-- TABLE: nexus_tables (Layer 4 — Data Intelligence)
-- ============================================================
CREATE TABLE IF NOT EXISTS nexus_tables (
    id                  UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    table_name          TEXT        UNIQUE NOT NULL,
    schema_name         TEXT        DEFAULT 'public',
    table_type          TEXT,
    row_count           BIGINT      DEFAULT 0,
    size_bytes          BIGINT      DEFAULT 0,
    columns             JSONB,
    indexes             JSONB,
    rls_enabled         BOOLEAN     DEFAULT false,
    rls_policies        JSONB       DEFAULT '[]',
    belongs_to_project  TEXT,
    last_insert_at      TIMESTAMPTZ,
    last_query_at       TIMESTAMPTZ,
    is_orphan           BOOLEAN     DEFAULT false,
    growth_rate_daily   NUMERIC,
    dependencies        JSONB       DEFAULT '[]',
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nexus_tables_project   ON nexus_tables (belongs_to_project);
CREATE INDEX IF NOT EXISTS idx_nexus_tables_is_orphan ON nexus_tables (is_orphan);
CREATE INDEX IF NOT EXISTS idx_nexus_tables_row_count ON nexus_tables (row_count DESC);

ALTER TABLE nexus_tables ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS nexus_tables_anon_select ON nexus_tables;
DROP POLICY IF EXISTS nexus_tables_service_all ON nexus_tables;
CREATE POLICY nexus_tables_anon_select ON nexus_tables FOR SELECT TO anon USING (true);
CREATE POLICY nexus_tables_service_all ON nexus_tables FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP TRIGGER IF EXISTS nexus_tables_updated_at ON nexus_tables;
CREATE TRIGGER nexus_tables_updated_at
    BEFORE UPDATE ON nexus_tables
    FOR EACH ROW EXECUTE FUNCTION nexus_set_updated_at();

-- ============================================================
-- TABLE: nexus_secrets (Layer 5 — Secret Intelligence)
-- ============================================================
CREATE TABLE IF NOT EXISTS nexus_secrets (
    id                      UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    repo_name               TEXT        NOT NULL,
    secret_name             TEXT        NOT NULL,
    created_at_gh           TIMESTAMPTZ,
    updated_at_gh           TIMESTAMPTZ,
    is_org_secret           BOOLEAN     DEFAULT false,
    known_expiry            TIMESTAMPTZ,
    known_type              TEXT,
    is_shared_across_repos  BOOLEAN     DEFAULT false,
    shared_with             JSONB       DEFAULT '[]',
    status                  TEXT        DEFAULT 'active' CHECK (status IN ('active','expired','rotating','unknown')),
    notes                   TEXT,
    updated_at              TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(repo_name, secret_name)
);

CREATE INDEX IF NOT EXISTS idx_nexus_secrets_status      ON nexus_secrets (status);
CREATE INDEX IF NOT EXISTS idx_nexus_secrets_known_expiry ON nexus_secrets (known_expiry);
CREATE INDEX IF NOT EXISTS idx_nexus_secrets_repo_name   ON nexus_secrets (repo_name);

ALTER TABLE nexus_secrets ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS nexus_secrets_anon_select ON nexus_secrets;
DROP POLICY IF EXISTS nexus_secrets_service_all ON nexus_secrets;
CREATE POLICY nexus_secrets_anon_select ON nexus_secrets FOR SELECT TO anon USING (true);
CREATE POLICY nexus_secrets_service_all ON nexus_secrets FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP TRIGGER IF EXISTS nexus_secrets_updated_at ON nexus_secrets;
CREATE TRIGGER nexus_secrets_updated_at
    BEFORE UPDATE ON nexus_secrets
    FOR EACH ROW EXECUTE FUNCTION nexus_set_updated_at();

-- ============================================================
-- TABLE: nexus_domains (Layer 6 — Domain Intelligence)
-- ============================================================
CREATE TABLE IF NOT EXISTS nexus_domains (
    id                  UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    domain              TEXT        UNIQUE NOT NULL,
    registrar           TEXT,
    dns_provider        TEXT,
    hosting_provider    TEXT,
    vercel_project_id   TEXT,
    ssl_expiry          TIMESTAMPTZ,
    ssl_issuer          TEXT,
    dns_records         JSONB,
    is_active           BOOLEAN     DEFAULT true,
    monthly_cost        NUMERIC(8,2) DEFAULT 0,
    purpose             TEXT,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nexus_domains_is_active        ON nexus_domains (is_active);
CREATE INDEX IF NOT EXISTS idx_nexus_domains_ssl_expiry       ON nexus_domains (ssl_expiry);
CREATE INDEX IF NOT EXISTS idx_nexus_domains_hosting_provider ON nexus_domains (hosting_provider);

ALTER TABLE nexus_domains ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS nexus_domains_anon_select ON nexus_domains;
DROP POLICY IF EXISTS nexus_domains_service_all ON nexus_domains;
CREATE POLICY nexus_domains_anon_select ON nexus_domains FOR SELECT TO anon USING (true);
CREATE POLICY nexus_domains_service_all ON nexus_domains FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP TRIGGER IF EXISTS nexus_domains_updated_at ON nexus_domains;
CREATE TRIGGER nexus_domains_updated_at
    BEFORE UPDATE ON nexus_domains
    FOR EACH ROW EXECUTE FUNCTION nexus_set_updated_at();

-- ============================================================
-- TABLE: nexus_notifications
-- ============================================================
CREATE TABLE IF NOT EXISTS nexus_notifications (
    id              UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    type            TEXT        NOT NULL,
    priority        TEXT        DEFAULT 'P2',
    title           TEXT        NOT NULL,
    body            TEXT,
    channel         TEXT        DEFAULT 'telegram',
    sent            BOOLEAN     DEFAULT false,
    sent_at         TIMESTAMPTZ,
    error           TEXT,
    related_task_id TEXT,
    related_repo    TEXT,
    metadata        JSONB       DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nexus_notifications_sent       ON nexus_notifications (sent);
CREATE INDEX IF NOT EXISTS idx_nexus_notifications_priority   ON nexus_notifications (priority);
CREATE INDEX IF NOT EXISTS idx_nexus_notifications_created_at ON nexus_notifications (created_at DESC);

ALTER TABLE nexus_notifications ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS nexus_notifications_anon_select ON nexus_notifications;
DROP POLICY IF EXISTS nexus_notifications_service_all ON nexus_notifications;
CREATE POLICY nexus_notifications_anon_select ON nexus_notifications FOR SELECT TO anon USING (true);
CREATE POLICY nexus_notifications_service_all ON nexus_notifications FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================
-- TABLE: nexus_chat_sessions
-- ============================================================
CREATE TABLE IF NOT EXISTS nexus_chat_sessions (
    id              UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id      TEXT        UNIQUE NOT NULL,
    platform        TEXT        DEFAULT 'claude_ai',
    project         TEXT,
    summary         TEXT,
    tasks_created   INT         DEFAULT 0,
    tasks_completed INT         DEFAULT 0,
    tokens_used     INT         DEFAULT 0,
    cost_usd        NUMERIC(8,4) DEFAULT 0,
    duration_seconds INT,
    metadata        JSONB       DEFAULT '{}',
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nexus_chat_sessions_platform   ON nexus_chat_sessions (platform);
CREATE INDEX IF NOT EXISTS idx_nexus_chat_sessions_project    ON nexus_chat_sessions (project);
CREATE INDEX IF NOT EXISTS idx_nexus_chat_sessions_created_at ON nexus_chat_sessions (created_at DESC);

ALTER TABLE nexus_chat_sessions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS nexus_chat_sessions_anon_select ON nexus_chat_sessions;
DROP POLICY IF EXISTS nexus_chat_sessions_service_all ON nexus_chat_sessions;
CREATE POLICY nexus_chat_sessions_anon_select ON nexus_chat_sessions FOR SELECT TO anon USING (true);
CREATE POLICY nexus_chat_sessions_service_all ON nexus_chat_sessions FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================
-- TABLE: nexus_insights
-- ============================================================
CREATE TABLE IF NOT EXISTS nexus_insights (
    id              UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    layer           TEXT        NOT NULL,
    insight_type    TEXT        NOT NULL,
    severity        TEXT        DEFAULT 'info' CHECK (severity IN ('critical','warning','info','success')),
    title           TEXT        NOT NULL,
    body            TEXT,
    recommendation  TEXT,
    affected_entity TEXT,
    auto_fixable    BOOLEAN     DEFAULT false,
    resolved        BOOLEAN     DEFAULT false,
    resolved_at     TIMESTAMPTZ,
    metadata        JSONB       DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nexus_insights_layer        ON nexus_insights (layer);
CREATE INDEX IF NOT EXISTS idx_nexus_insights_severity     ON nexus_insights (severity);
CREATE INDEX IF NOT EXISTS idx_nexus_insights_resolved     ON nexus_insights (resolved);
CREATE INDEX IF NOT EXISTS idx_nexus_insights_created_at   ON nexus_insights (created_at DESC);

ALTER TABLE nexus_insights ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS nexus_insights_anon_select ON nexus_insights;
DROP POLICY IF EXISTS nexus_insights_service_all ON nexus_insights;
CREATE POLICY nexus_insights_anon_select ON nexus_insights FOR SELECT TO anon USING (true);
CREATE POLICY nexus_insights_service_all ON nexus_insights FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP TRIGGER IF EXISTS nexus_insights_updated_at ON nexus_insights;
CREATE TRIGGER nexus_insights_updated_at
    BEFORE UPDATE ON nexus_insights
    FOR EACH ROW EXECUTE FUNCTION nexus_set_updated_at();

-- ============================================================
-- REALTIME: Enable for nexus_tasks + nexus_notifications
-- ============================================================
ALTER PUBLICATION supabase_realtime ADD TABLE nexus_tasks;
ALTER PUBLICATION supabase_realtime ADD TABLE nexus_notifications;

-- ============================================================
-- SEED: Known domains
-- ============================================================
INSERT INTO nexus_domains (domain, registrar, dns_provider, hosting_provider, is_active, purpose)
VALUES
  ('biddeed.ai',         'cloudflare', 'cloudflare', 'vercel', true, 'production'),
  ('zonewise.ai',        'cloudflare', 'cloudflare', 'vercel', true, 'production'),
  ('nexus.zonewise.ai',  'cloudflare', 'cloudflare', 'vercel', true, 'monitoring'),
  ('watch.biddeed.ai',   'cloudflare', 'cloudflare', 'vercel', true, 'monitoring')
ON CONFLICT (domain) DO NOTHING;
