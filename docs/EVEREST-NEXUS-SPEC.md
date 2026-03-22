# Everest Nexus — nexus.zonewise.ai
## Ecosystem Intelligence Platform — Design Specification v1.0

**Author:** Claude AI Architect
**Date:** Mar 22, 2026
**Status:** APPROVED — 10 decisions locked
**Domain:** nexus.zonewise.ai
**Repo:** breverdbidder/everest-nexus (NEW)
**Infra:** Vercel Pro (separate project), Supabase (existing instance)

---

## What Is This

A self-updating second-brain system that maps, monitors, and optimizes the entire BidDeed/ZoneWise/Everest ecosystem. Six intelligence layers scan repos, tables, workflows, secrets, domains, and tasks — writing findings to Supabase and rendering them on a single dashboard. Telegram alerts fire on anomalies. Consolidation recommendations surface automatically.

---

## Decisions Log

```yaml
D1_domain: nexus.zonewise.ai
D2_ingestion: Hybrid (instant P0/blockers, session summary for rest)
D3_notifications: Event-driven Telegram via @BidDeedAI_bot (740118343)
D4_repos: All 50+ repos under breverdbidder org
D5_escalation: P0 repeats every 2hr, ACCOUNTABILITY at 4hr
D6_digest: Twice daily 9AM + 5PM EST
D7_priority: Auto-assign with Telegram override (/bump /demote)
D8_scope: Full 6-layer ecosystem intelligence
D9_deploy: All layers in mega-sprint (4-5 Claude Code sessions)
D10_infra: New repo breverdbidder/everest-nexus + separate Vercel project
build_order: [Task, Workflow, Repo, Data, Secret, Domain]
```

---

## Architecture

```mermaid
graph TB
    subgraph Scanners[Scheduled Scanners]
        TS[Task Scanner<br/>pg_cron 5min]
        WS[Workflow Scanner<br/>pg_cron 6hr]
        RS[Repo Scanner<br/>pg_cron 6hr]
        DS[Data Scanner<br/>pg_cron 12hr]
        SS[Secret Scanner<br/>pg_cron daily]
        DNS[Domain Scanner<br/>pg_cron daily]
    end

    subgraph Ingestion
        CA[Claude AI Chat] -->|instant P0| API[Supabase REST]
        CA -->|session summary| API
        CC[Claude Code] -->|watch hooks| API
        GH[GitHub Webhooks] -->|push/PR/CI| EF[Edge Func]
        EF --> API
    end

    subgraph Storage[Supabase — nexus_ prefix]
        API --> BT[nexus_tasks]
        API --> BW[nexus_workflows]
        API --> BR[nexus_repos]
        API --> BD[nexus_tables]
        API --> BS[nexus_secrets]
        API --> BDN[nexus_domains]
        API --> BN[nexus_notifications]
        API --> BC[nexus_chat_sessions]
        API --> BI[nexus_insights]
    end

    TS & WS & RS & DS & SS & DNS --> Storage

    subgraph Dashboard[nexus.zonewise.ai]
        Storage -->|Realtime| UI[Next.js 14 App]
        UI --> P1[/tasks]
        UI --> P2[/workflows]
        UI --> P3[/repos]
        UI --> P4[/data]
        UI --> P5[/secrets]
        UI --> P6[/domains]
        UI --> P7[/ overview]
    end

    subgraph Alerts[Telegram @BidDeedAI_bot]
        Storage -->|P0/blocked| TG[Event Alerts]
        Storage -->|9AM+5PM| DG[Digest]
        Storage -->|2hr loop| ESC[P0 Escalation]
        TG & DG & ESC --> BOT[Bot 8763706981]
        BOT -->|/bump /done /tasks| Storage
    end
```

---

## Layer 1: Task Intelligence (Priority: #1)

### Purpose
Track every open item across Claude AI chats, Claude Code sessions, and Telegram commands. Priority-based SLA enforcement with ADHD-optimized escalation.

### Table: nexus_tasks

```yaml
columns:
  id: UUID DEFAULT gen_random_uuid() PK
  task_id: TEXT UNIQUE NOT NULL
  description: TEXT NOT NULL
  priority: TEXT DEFAULT 'P2' CHECK (P0, P1, P2, P3)
  status: TEXT DEFAULT 'queued' CHECK (queued, dispatched, running, blocked, success, failed, timeout, cancelled, skipped)
  project: TEXT  # designwise, utcc, zonewise, youtube, infra, michael, personal, nexus
  owner: TEXT DEFAULT 'Claude Code'
  task_type: TEXT  # gha_executor, claude_code, transcript, manual, decision
  platform: TEXT  # biddeed, zonewise, shared, personal
  triggered_by: TEXT  # claude_ai, claude_code, telegram, gha, cron
  source_chat_id: TEXT
  sla_deadline: TIMESTAMPTZ
  escalation_count: INT DEFAULT 0
  last_escalated_at: TIMESTAMPTZ
  auto_priority: BOOLEAN DEFAULT true
  gha_run_id: BIGINT
  gha_run_url: TEXT
  result_summary: TEXT
  error_message: TEXT
  tokens_used: INT DEFAULT 0
  cost_usd: NUMERIC(8,4) DEFAULT 0
  batch_id: UUID
  batch_index: INT
  created_at: TIMESTAMPTZ DEFAULT NOW()
  dispatched_at: TIMESTAMPTZ
  started_at: TIMESTAMPTZ
  completed_at: TIMESTAMPTZ
  updated_at: TIMESTAMPTZ DEFAULT NOW()
indexes: [priority, status, project, owner, sla_deadline, created_at DESC]
```

### Priority Auto-Assignment Rules

```yaml
auto_rules:
  P0:
    - status == blocked
    - contains(description, 'blocker|critical|down|broken|production')
    - CI failed on Tier CORE repo
    - Sentinel alert
  P1:
    - owner == Ariel
    - Summit dispatched
    - spec or plan created
    - CI failed on Tier ACTIVE repo
    - contains(description, 'deploy|launch|release')
  P2:
    - Claude Code routine task
    - feature implementation
    - repo staleness 7-30 days (core/active)
  P3:
    - documentation
    - repo staleness (monitored tier)
    - deferred items
    - nice-to-have
```

### Escalation Engine

```yaml
escalation:
  P0:
    2hr: "🔴 P0 REMINDER: {description} — {elapsed} elapsed. Owner: {owner}"
    4hr: "⚠️ ACCOUNTABILITY: {description} started {elapsed} ago. Status? Be honest."
    repeat: every 2hr until resolved
  P1:
    24hr: "🟠 P1 stale: {description} — past 24hr SLA"
    repeat: daily in digest
  P2:
    72hr: included in digest as stale
  P3:
    30d: auto-archive suggestion
  blocked:
    any_priority: instant Telegram alert on status change to blocked
  completed:
    P0: instant "✅ RESOLVED: {description}"
    P1: instant "✅ Done: {description}"
    P2_P3: silent (dashboard only)
```

### Telegram Bot Commands

```yaml
commands:
  /tasks: List active by priority (P0 first)
  /p0: P0 items only
  /p1: P1 items only
  /stale: Past SLA deadline
  /bump <id>: Priority up (P2→P1→P0)
  /demote <id>: Priority down
  /done <id>: Mark success
  /skip <id>: Mark skipped
  /block <id>: Mark blocked (triggers instant alert)
  /digest: Force immediate digest
  /nexus: Dashboard link + quick stats
```

### Digest Format (9AM + 5PM EST)

```yaml
format: |
  🧠 BRAIN DIGEST — {date} {time}

  🔴 P0 CRITICAL ({count})
  {list or "None — all clear ✅"}

  📊 Since last digest:
  • {completed_count} completed
  • {created_count} new
  • {blocked_count} blocked

  🟠 P1 needing attention ({count})
  {top 5 items}

  📦 Ecosystem health:
  • Repos: {healthy}/{total} healthy
  • Workflows: {passing}/{total} passing
  • Stale items: {stale_count}

  🔗 nexus.zonewise.ai
max_chars: 4096
```

---

## Layer 2: Workflow Intelligence (Priority: #2)

### Purpose
Map ALL GitHub Actions workflows across ALL repos. Track run history, detect dead workflows, measure costs, identify failures.

### Table: nexus_workflows

```yaml
columns:
  id: UUID PK
  repo_name: TEXT NOT NULL
  workflow_name: TEXT NOT NULL
  workflow_path: TEXT NOT NULL
  workflow_id: BIGINT
  state: TEXT  # active, disabled_manually, disabled_inactivity
  trigger_types: JSONB  # [push, workflow_dispatch, schedule, repository_dispatch]
  last_run_at: TIMESTAMPTZ
  last_run_status: TEXT  # success, failure, cancelled
  last_run_url: TEXT
  total_runs_30d: INT DEFAULT 0
  success_rate_30d: NUMERIC(5,2)
  avg_duration_seconds: INT
  is_scheduled: BOOLEAN DEFAULT false
  schedule_expression: TEXT
  is_dead: BOOLEAN DEFAULT false  # no runs in 30 days + active state
  estimated_cost_30d: NUMERIC(8,4) DEFAULT 0  # minutes * $0.008
  updated_at: TIMESTAMPTZ DEFAULT NOW()
  UNIQUE(repo_name, workflow_path)
indexes: [repo_name, is_dead, last_run_at, state]
```

### Scanner Logic

```yaml
scan_schedule: every 6 hours
scan_actions:
  - GitHub API: list workflows for each repo
  - For each workflow: fetch last 5 runs
  - Compute: success_rate_30d, avg_duration, total_runs_30d
  - Flag dead: active state + 0 runs in 30 days
  - Flag failing: success_rate < 50%
  - Estimate cost: total_minutes * $0.008/min (ubuntu-latest)
recommendations:
  - "DELETE: {workflow} in {repo} — dead for {days} days, never succeeded"
  - "DISABLE: {workflow} — 0% success rate in 30 days"
  - "OPTIMIZE: {workflow} — avg {duration}s, runs {frequency}, costing ${cost}/mo"
alerts:
  - CI failure on core repo → P0 task auto-created
  - Scheduled workflow missed → P1 task
  - Workflow disabled by GitHub inactivity → P2 notification
```

---

## Layer 3: Repo Intelligence (Priority: #3)

### Purpose
Map all 50+ repos. Tier, health-score, detect redundancy, recommend consolidation and archival.

### Table: nexus_repos

```yaml
columns:
  id: UUID PK
  repo_name: TEXT UNIQUE NOT NULL
  full_name: TEXT  # breverdbidder/repo-name
  tier: TEXT CHECK (core, active, monitored, archived) NOT NULL
  description: TEXT
  language: TEXT
  topics: JSONB DEFAULT '[]'
  default_branch: TEXT DEFAULT 'main'
  is_private: BOOLEAN DEFAULT false
  created_at_gh: TIMESTAMPTZ
  last_push_at: TIMESTAMPTZ
  last_push_by: TEXT
  last_ci_status: TEXT CHECK (success, failure, pending, none)
  last_ci_url: TEXT
  last_ci_at: TIMESTAMPTZ
  open_prs: INT DEFAULT 0
  open_issues: INT DEFAULT 0
  total_commits: INT DEFAULT 0
  contributors: JSONB DEFAULT '[]'
  size_kb: INT DEFAULT 0
  stale_days: INT DEFAULT 0
  health_score: INT DEFAULT 100
  consolidation_group: TEXT  # e.g. "zonewise-family", "biddeed-family"
  consolidation_recommendation: TEXT  # "merge into zonewise-web", "archive"
  dependencies: JSONB DEFAULT '[]'  # repos this depends on
  updated_at: TIMESTAMPTZ DEFAULT NOW()
indexes: [tier, stale_days DESC, health_score, consolidation_group]
```

### Health Score Formula

```yaml
health_score:  # 0-100
  base: 100
  deductions:
    - stale_days > 7 AND tier=core: -20
    - stale_days > 14 AND tier=active: -15
    - stale_days > 30 AND tier=monitored: -10
    - stale_days > 90: -30 (any tier)
    - last_ci_status == failure: -25
    - last_ci_status == none: -5
    - open_issues > 10: -10
    - no_description: -5
    - no_topics: -5
  bonuses:
    - ci_passing + recent_push: +0 (already at 100)
```

### Consolidation Engine

```yaml
consolidation_groups:
  zonewise-family:
    repos: [zonewise, zonewise-web, zonewise-desktop, zonewise-landing, zonewise-agents, zonewise-agent-teams, zonewise-gtm, zonewise-loans, zonewise-scraper-v4]
    recommendation: "Merge zonewise-agents + zonewise-agent-teams into cli-anything-biddeed. Archive zonewise-desktop + zonewise-gtm + zonewise-loans (inactive). Keep zonewise-web + zonewise + zonewise-landing."
  biddeed-family:
    repos: [biddeed-ai, biddeed-ai-ui, biddeed-landing, biddeed-conversational-ai, brevard-bidder-landing]
    recommendation: "Merge biddeed-ai + biddeed-ai-ui into monorepo. Archive biddeed-conversational-ai (superseded). Merge landing pages into one."
  infra-family:
    repos: [claude-code-telegram-control, claude-code-telegram-control-1, cliproxy-gateway, agents-command-center]
    recommendation: "Archive telegram-control-1 (duplicate). Merge agents-command-center into cli-anything."
  archive-candidates:
    criteria: "No push in 90+ days AND not a dependency of any active repo"
    action: "Surface in dashboard with one-click archive button"
```

### Archive Action (one-click)

```yaml
archive_flow:
  1: User clicks "Archive" on dashboard
  2: Edge function calls GitHub API PATCH /repos/{repo} {"archived": true}
  3: Update nexus_repos tier → "archived"
  4: Telegram notification: "📦 Archived: {repo} — last activity {stale_days} days ago"
  5: Remove from active monitoring
```

---

## Layer 4: Data Intelligence (Priority: #4)

### Purpose
Map ALL Supabase tables, views, functions, and RLS policies. Detect orphans, visualize schema, track growth.

### Table: nexus_tables

```yaml
columns:
  id: UUID PK
  table_name: TEXT UNIQUE NOT NULL
  schema_name: TEXT DEFAULT 'public'
  table_type: TEXT  # table, view, materialized_view, function
  row_count: BIGINT DEFAULT 0
  size_bytes: BIGINT DEFAULT 0
  columns: JSONB  # [{name, type, nullable, default}]
  indexes: JSONB
  rls_enabled: BOOLEAN DEFAULT false
  rls_policies: JSONB DEFAULT '[]'
  belongs_to_project: TEXT  # biddeed, zonewise, nexus, lifeOS, watch, esf
  last_insert_at: TIMESTAMPTZ
  last_query_at: TIMESTAMPTZ
  is_orphan: BOOLEAN DEFAULT false  # no inserts in 30 days + no references
  growth_rate_daily: NUMERIC  # rows per day avg
  dependencies: JSONB DEFAULT '[]'  # tables that reference this via FK
  updated_at: TIMESTAMPTZ DEFAULT NOW()
indexes: [belongs_to_project, is_orphan, row_count DESC]
```

### Scanner Logic

```yaml
scan_schedule: every 12 hours
scan_via: Supabase management API or information_schema queries
actions:
  - SELECT table_name, ... FROM information_schema.tables
  - For each table: SELECT count(*), pg_total_relation_size()
  - Detect FKs: information_schema.table_constraints
  - Check RLS: pg_tables.rowsecurity
  - Estimate project ownership by table prefix/naming convention
recommendations:
  - "ORPHAN: {table} — 0 rows, no inserts in 60 days, no FK references"
  - "MISSING RLS: {table} — contains user data but RLS disabled"
  - "LARGE TABLE: {table} — {size}MB, {rows} rows, growing {rate}/day"
  - "DUPLICATE: {table_a} and {table_b} have 80% column overlap"
```

---

## Layer 5: Secret Intelligence (Priority: #5)

### Purpose
Inventory ALL GitHub Actions secrets across ALL repos. Track which are shared, which are stale, expiry dates where known.

### Table: nexus_secrets

```yaml
columns:
  id: UUID PK
  repo_name: TEXT NOT NULL
  secret_name: TEXT NOT NULL
  created_at_gh: TIMESTAMPTZ
  updated_at_gh: TIMESTAMPTZ
  is_org_secret: BOOLEAN DEFAULT false
  known_expiry: TIMESTAMPTZ  # manually tracked
  known_type: TEXT  # api_key, oauth_token, ssh_key, password, webhook_secret
  is_shared_across_repos: BOOLEAN DEFAULT false
  shared_with: JSONB DEFAULT '[]'
  status: TEXT DEFAULT 'active' CHECK (active, expired, rotating, unknown)
  notes: TEXT
  updated_at: TIMESTAMPTZ DEFAULT NOW()
  UNIQUE(repo_name, secret_name)
indexes: [status, known_expiry, repo_name]
```

### Scanner Logic

```yaml
scan_schedule: daily at 6AM UTC
scan_via: GitHub API /repos/{repo}/actions/secrets (returns names + updated_at, NOT values)
actions:
  - List secrets per repo
  - Cross-reference: find same secret name across repos → mark shared
  - Flag: secrets not updated in 365 days → "rotation recommended"
  - Flag: known expired (PAT1-3 are DEAD per memory)
alerts:
  - Secret approaching known expiry → P1 Telegram
  - Secret shared across 5+ repos but updated inconsistently → P2
```

---

## Layer 6: Domain Intelligence (Priority: #6)

### Purpose
Track all domains, DNS records, SSL certificates, Vercel projects, and Cloudflare zones.

### Table: nexus_domains

```yaml
columns:
  id: UUID PK
  domain: TEXT UNIQUE NOT NULL
  registrar: TEXT  # cloudflare, namecheap, etc
  dns_provider: TEXT  # cloudflare
  hosting_provider: TEXT  # vercel, render, hetzner
  vercel_project_id: TEXT
  ssl_expiry: TIMESTAMPTZ
  ssl_issuer: TEXT
  dns_records: JSONB  # [{type, name, content, ttl}]
  is_active: BOOLEAN DEFAULT true
  monthly_cost: NUMERIC(8,2) DEFAULT 0
  purpose: TEXT  # production, staging, monitoring, landing
  updated_at: TIMESTAMPTZ DEFAULT NOW()
indexes: [is_active, ssl_expiry, hosting_provider]
```

### Known Domains

```yaml
domains:
  - biddeed.ai (Cloudflare → Vercel)
  - zonewise.ai (Cloudflare → Vercel)
  - nexus.zonewise.ai (NEW — Cloudflare → Vercel)
  - watch.biddeed.ai (Cloudflare → Vercel, redirect to nexus)
  - lab.zonewise.ai (planned, not yet active)
```

### Scanner Logic

```yaml
scan_schedule: daily
scan_via: Cloudflare API (zone list + DNS records) + SSL check via openssl
alerts:
  - SSL expiry < 14 days → P0
  - DNS record changed unexpectedly → P1
  - Domain not resolving → P0
```

---

## Dashboard Pages

```yaml
pages:
  /:  # Brain Overview
    components:
      - EcosystemHealthRing: 6 layer scores in radial chart
      - PriorityStrip: P0|P1|P2|P3 counts
      - ArielActionBox: owner=Ariel items
      - RecentActivity: last 20 events across all layers
      - QuickStats: repos|tables|workflows|secrets|domains counts

  /tasks:  # Layer 1
    components:
      - TaskTable: sortable by priority/project/owner/status
      - InlineActions: done/skip/bump/block buttons
      - SLATimers: countdown for P0/P1 items
      - SessionHistory: linked chat sessions

  /workflows:  # Layer 2
    components:
      - WorkflowGrid: grouped by repo, color by status
      - DeadWorkflowPanel: one-click disable/delete
      - CostEstimator: monthly GHA minutes cost
      - FailureTimeline: recent failures chronological

  /repos:  # Layer 3
    components:
      - RepoCards: grouped by tier, health bar
      - ConsolidationPanel: family groups with merge/archive recs
      - ArchiveButton: one-click GitHub archive API
      - DependencyGraph: which repos depend on which

  /data:  # Layer 4
    components:
      - TableGrid: grouped by project, size bars
      - OrphanPanel: unused tables with drop recommendation
      - SchemaViewer: columns and FK visualization
      - GrowthChart: largest tables over time

  /secrets:  # Layer 5
    components:
      - SecretMatrix: repos × secrets heatmap
      - ExpiryTimeline: upcoming expirations
      - SharedSecretMap: which secrets span repos
      - RotationReminders: stale secrets

  /domains:  # Layer 6
    components:
      - DomainList: SSL status, DNS provider, hosting
      - SSLExpiryCountdown: days until renewal
      - CostSummary: monthly domain/hosting costs
```

---

## Tech Stack

```yaml
repo: breverdbidder/everest-nexus
framework: Next.js 14 App Router
styling: Tailwind CSS + house brand (Navy #1E3A5F, Orange #F59E0B, bg #020617, Inter)
hosting: Vercel Pro (separate project)
database: Existing Supabase (mocerqjnksmhcjzxrewo) — nexus_ prefix tables
realtime: Supabase Realtime subscriptions
auth: Vercel deployment protection (Ariel only)
telegram: @BidDeedAI_bot (8763706981, chat_id 740118343)
scanners: Python scripts in scanners/ dir, invoked by pg_cron + GHA
```

---

## Brand

```yaml
brand:
  primary: "#1E3A5F"
  accent: "#F59E0B"
  background: "#020617"
  font: Inter
  p0: "#EF4444"
  p1: "#F59E0B"
  p2: "#EAB308"
  p3: "#6B7280"
  success: "#10B981"
  layer_colors:
    tasks: "#EF4444"
    workflows: "#8B5CF6"
    repos: "#1E3A5F"
    data: "#10B981"
    secrets: "#F59E0B"
    domains: "#06B6D4"
```

---

## Cost

```yaml
incremental_cost: $0/month
  vercel: Pro plan already paid
  supabase: existing instance, tables are free
  github_api: free tier (5000 req/hr)
  cloudflare_api: free
  telegram: free
  pg_cron: included in Supabase
```
