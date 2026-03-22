-- ============================================================
-- EVEREST NEXUS — pg_cron Jobs
-- Schedule: 9 jobs covering all 6 intelligence layers
-- Requires: pg_cron extension (enabled in Supabase)
-- ============================================================

-- Enable pg_cron (idempotent on Supabase)
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- ============================================================
-- Remove old jobs if re-running (idempotent)
-- ============================================================
SELECT cron.unschedule('nexus_staleness')      WHERE EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'nexus_staleness');
SELECT cron.unschedule('nexus_p0_escalation')  WHERE EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'nexus_p0_escalation');
SELECT cron.unschedule('nexus_morning_digest') WHERE EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'nexus_morning_digest');
SELECT cron.unschedule('nexus_evening_digest') WHERE EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'nexus_evening_digest');
SELECT cron.unschedule('nexus_workflow_scan')  WHERE EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'nexus_workflow_scan');
SELECT cron.unschedule('nexus_repo_scan')      WHERE EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'nexus_repo_scan');
SELECT cron.unschedule('nexus_data_scan')      WHERE EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'nexus_data_scan');
SELECT cron.unschedule('nexus_secret_scan')    WHERE EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'nexus_secret_scan');
SELECT cron.unschedule('nexus_domain_scan')    WHERE EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'nexus_domain_scan');

-- ============================================================
-- JOB 1: Staleness check — every 5 minutes
-- Updates stale_days on nexus_repos + flags overdue tasks
-- ============================================================
SELECT cron.schedule(
  'nexus_staleness',
  '*/5 * * * *',
  $$
  UPDATE nexus_repos
  SET stale_days = EXTRACT(
    DAY FROM (NOW() - last_push_at)
  )::INT
  WHERE last_push_at IS NOT NULL;
  $$
);

-- ============================================================
-- JOB 2: P0 escalation — every 2 hours
-- Flags P0 tasks for escalation (Python scanner picks these up)
-- ============================================================
SELECT cron.schedule(
  'nexus_p0_escalation',
  '0 */2 * * *',
  $$
  INSERT INTO nexus_notifications (type, priority, title, body, channel, sent, related_task_id, metadata)
  SELECT
    'p0_escalation',
    'P0',
    'P0 Escalation: ' || description,
    'Task ' || task_id || ' has been open for ' ||
      EXTRACT(EPOCH FROM (NOW() - created_at))/3600 || ' hours',
    'telegram',
    false,
    task_id,
    jsonb_build_object(
      'escalation_count', escalation_count + 1,
      'elapsed_hours', EXTRACT(EPOCH FROM (NOW() - created_at))/3600
    )
  FROM nexus_tasks
  WHERE
    priority = 'P0'
    AND status NOT IN ('success','failed','cancelled','skipped','timeout')
    AND (last_escalated_at IS NULL OR last_escalated_at < NOW() - INTERVAL '2 hours');

  -- Update escalation metadata
  UPDATE nexus_tasks
  SET
    escalation_count  = escalation_count + 1,
    last_escalated_at = NOW()
  WHERE
    priority = 'P0'
    AND status NOT IN ('success','failed','cancelled','skipped','timeout')
    AND (last_escalated_at IS NULL OR last_escalated_at < NOW() - INTERVAL '2 hours');
  $$
);

-- ============================================================
-- JOB 3: Morning digest trigger — 9AM EST = 14:00 UTC
-- ============================================================
SELECT cron.schedule(
  'nexus_morning_digest',
  '0 14 * * *',
  $$
  INSERT INTO nexus_notifications (type, priority, title, body, channel, sent)
  VALUES ('digest', 'P2', 'Morning Digest', '9AM EST digest trigger', 'telegram', false);
  $$
);

-- ============================================================
-- JOB 4: Evening digest trigger — 5PM EST = 22:00 UTC
-- ============================================================
SELECT cron.schedule(
  'nexus_evening_digest',
  '0 22 * * *',
  $$
  INSERT INTO nexus_notifications (type, priority, title, body, channel, sent)
  VALUES ('digest', 'P2', 'Evening Digest', '5PM EST digest trigger', 'telegram', false);
  $$
);

-- ============================================================
-- JOB 5: Workflow scan trigger — every 6 hours
-- (GHA workflow runner picks up and calls workflow_scanner.py)
-- ============================================================
SELECT cron.schedule(
  'nexus_workflow_scan',
  '0 */6 * * *',
  $$
  INSERT INTO nexus_notifications (type, priority, title, body, channel, sent)
  VALUES ('scan_trigger', 'P3', 'Workflow Scan', 'Trigger: workflow_scanner.py scan_all_repos', 'internal', false);
  $$
);

-- ============================================================
-- JOB 6: Repo scan trigger — every 6 hours
-- ============================================================
SELECT cron.schedule(
  'nexus_repo_scan',
  '0 */6 * * *',
  $$
  INSERT INTO nexus_notifications (type, priority, title, body, channel, sent)
  VALUES ('scan_trigger', 'P3', 'Repo Scan', 'Trigger: repo_scanner.py scan_all_repos', 'internal', false);
  $$
);

-- ============================================================
-- JOB 7: Data/table scan — every 12 hours
-- ============================================================
SELECT cron.schedule(
  'nexus_data_scan',
  '0 */12 * * *',
  $$
  -- Refresh nexus_tables metadata from information_schema
  INSERT INTO nexus_notifications (type, priority, title, body, channel, sent)
  VALUES ('scan_trigger', 'P3', 'Data Scan', 'Trigger: data_scanner.py scan_all_tables', 'internal', false);
  $$
);

-- ============================================================
-- JOB 8: Secret scan — daily at 6AM UTC
-- ============================================================
SELECT cron.schedule(
  'nexus_secret_scan',
  '0 6 * * *',
  $$
  INSERT INTO nexus_notifications (type, priority, title, body, channel, sent)
  VALUES ('scan_trigger', 'P3', 'Secret Scan', 'Trigger: secret_scanner.py scan_all_secrets', 'internal', false);
  $$
);

-- ============================================================
-- JOB 9: Domain scan — daily at 7AM UTC
-- ============================================================
SELECT cron.schedule(
  'nexus_domain_scan',
  '0 7 * * *',
  $$
  INSERT INTO nexus_notifications (type, priority, title, body, channel, sent)
  VALUES ('scan_trigger', 'P3', 'Domain Scan', 'Trigger: domain_scanner.py scan_all_domains', 'internal', false);
  $$
);

-- ============================================================
-- VERIFY: List scheduled jobs
-- ============================================================
SELECT jobname, schedule, command FROM cron.job WHERE jobname LIKE 'nexus_%' ORDER BY jobname;
