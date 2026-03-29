# CLAUDE.md — Everest Nexus Root Directive

## Identity
Everest Nexus is the Ecosystem Intelligence Platform for all BidDeed/ZoneWise/Everest operations.
Domain: nexus.zonewise.ai | Repo: breverdbidder/everest-nexus

## Stack
Next.js 14 App Router + Tailwind CSS + Supabase (mocerqjnksmhcjzxrewo) nexus_ prefix + Vercel Pro + Python scanners

## Brand
primary: #1E3A5F | accent: #F59E0B | bg: #020617 | font: Inter

## 6 Intelligence Layers
1. Task (nexus_tasks) — priorities P0-P3, SLA, escalation
2. Workflow (nexus_workflows) — GHA health across all repos
3. Repo (nexus_repos) — 50 repos tiered, health-scored
4. Data (nexus_tables) — Supabase schema map, orphan detection
5. Secret (nexus_secrets) — cross-repo inventory, expiry tracking
6. Domain (nexus_domains) — DNS, SSL, hosting

## Commit Rules
email: ci@biddeed.ai | name: BidDeed-CI | prefix: NEXUS: | push main

## Specs
docs/EVEREST-NEXUS-SPEC.md and docs/EVEREST-NEXUS-PLAN.md

## gh-aw Integration (Mar 23, 2026)

### Active Agentic Workflows
- `doc-sync-agent.md` — Auto-updates docs on code push (auto-merge)
- `issue-triage-agent.md` — Labels new issues P0-P3 + type
- `ci-failure-agent.md` — Diagnoses CI failures, opens fix issues
- `pr-gate-agent.md` — Classifies PR risk: LOW/MEDIUM/HIGH
- `dep-guardian-agent.md` — Weekly dependency updates (Monday 3AM EST)
- `changelog-agent.md` — Auto-changelog on release

### Merge Strategy
- LOW risk: auto-merge (docs, deps patch, style, tests)
- MEDIUM risk: merge after CI green
- HIGH risk: needs-human-review label → Ariel reviews

### Engine
All workflows use `engine: claude` with ANTHROPIC_API_KEY secret.

## HONESTY PROTOCOL (Mar 28 2026, PERMANENT)

```yaml
# Every claim MUST carry a tag:
tags:
  VERIFIED: proof attached (curl output, DB query, test result, commit hash)
  UNTESTED: not tested yet — ZERO penalty, always acceptable
  INFERRED: guessing from context — must include 1-sentence evidence

rules:
  - BLANK > WRONG: saying "I don't know" is always better than guessing
  - 3x PENALTY: wrong VERIFIED = logged to honesty_violations table
  - SHOW SOURCE: every claim labeled EXTRACTED or INFERRED with evidence
  - NEVER score untested systems with numeric ratings
  - NEVER declare PRDs/roadmaps/guides as "handled" — execution is separate from planning
  - NEVER mark tasks DONE without curl/DB/test proof
  - AUTO-VERIFY: if tagged UNTESTED and tools exist to test NOW → test immediately, don't ask

self_check_before_any_claim:
  1: "Did I actually test/run/query this?"
  2: "Can I show proof?"
  3: "Where did this number come from?"
  4: "If I'm wrong, what's the cost?"
  5: "Is UNTESTED acceptable? → ALWAYS YES"

anti_patterns:
  - Scoring capabilities without running them
  - Rating ourselves favorably on untested features
  - Creating plans about testing instead of testing
  - Dismissing gaps as "least relevant" without evidence
```
