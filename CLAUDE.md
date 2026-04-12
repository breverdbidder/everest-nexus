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


## SEARCH-FIRST MANDATE (PERMANENT — Apr 1 2026)

BEFORE any architecture, design, or component work:
1. Search GitHub for mature, tested repositories solving the same problem
2. Run REPOEVAL: security + value + stability + integration + cost  
3. ADOPT (score>=80) -> install and compose, build only the delta
4. EVAL (60-79) -> test 1 week before committing
5. REJECT (<40) -> build custom

NEVER build from scratch what already exists tested and verified.
Applies: UI (shadcn/ui), frameworks, pipelines, auth, payments, charts, maps.


<!-- KARPATHY_DISCIPLINE_BEGIN v1.0 -->
## Behavioral Discipline (Karpathy Guidelines)

> Adapted from [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills) · MIT License · ~14k★ · Karpathy-starred.
> Adopted by Everest Capital 2026-04-12. This section is **complementary** to the existing HONESTY PROTOCOL, PAIRING RULE, COST DISCIPLINE, and CLI-ANYTHING mandates above — it does not replace them.

**Tradeoff posture:** These guidelines bias toward caution over speed. For trivial tasks (typo fix, one-line config), use judgment and skip the ceremony.

### K1. Think Before Coding *(reinforces HONESTY PROTOCOL)*

Don't assume. Don't hide confusion. Surface tradeoffs.

- State assumptions explicitly. If uncertain, label as `INFERRED` per HONESTY PROTOCOL.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

**Everest delta:** when an assumption is surfaced, it must carry a `VERIFIED / UNTESTED / INFERRED` tag. Wrong `VERIFIED` = 3× penalty to honesty_violations table.

### K2. Simplicity First *(complements XGBoost efficiency cap)*

Minimum code that solves the problem. Nothing speculative.

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and 50 would do, rewrite.

Ask: "Would a senior engineer call this overcomplicated?" If yes, simplify.

**Everest delta:** this is per-diff. XGBoost efficiency (90 min/chat, max 3 chats/task) is per-session. Both apply.

### K3. Surgical Changes *(NEW — closes AUTOLOOP evolver bloat gap)*

Touch only what you must. Clean up only your own mess.

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, **mention it — don't delete it.**

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless explicitly asked.

**The test:** every changed line must trace directly to the user's request.

**Everest delta — AUTOLOOP V2 evolver constraint:** prompt/rule updates produced by the evolver must be **minimal and surgical**. Diffs that exceed 20% line growth or touch sections unrelated to the failing case must be rejected by the evolver's self-check and re-attempted with a narrower edit. This closes the bloat failure mode flagged by Dylan Cleppe's extraction-funnel analysis (2026-04-12) and by Karpathy directly.

### K4. Goal-Driven Execution *(complements EG14 gate)*

Define success criteria. Loop until verified.

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

**Everest delta:** for SUMMIT dispatches touching production (zonewise-web, dify-zonewise, nexus), the EG14 14-point enterprise gate is the canonical success criteria. Goal-driven execution at the sub-task level must compose up to an EG14 verdict, not replace it.

### Working indicators

These guidelines are working if:
- Fewer unnecessary changes appear in diffs.
- Fewer rewrites happen due to overcomplication.
- Clarifying questions arrive *before* implementation, not after mistakes.
- AUTOLOOP evolver prompt diffs stay small and targeted.

### Attribution

Source: https://github.com/forrestchang/andrej-karpathy-skills (MIT)
Upstream quote from Karpathy: *"LLMs are exceptionally good at looping until they meet specific goals. Don't tell it what to do, give it success criteria and watch it go."*
<!-- KARPATHY_DISCIPLINE_END v1.0 -->
