import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://mocerqjnksmhcjzxrewo.supabase.co'
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

export type Task = {
  id: string
  task_id: string
  description: string
  priority: 'P0' | 'P1' | 'P2' | 'P3'
  status: string
  project: string
  owner: string
  task_type: string
  platform: string
  sla_deadline: string | null
  escalation_count: number
  created_at: string
  updated_at: string
  tokens_used: number
  cost_usd: number
}

export type Workflow = {
  id: string
  repo_name: string
  workflow_name: string
  workflow_path: string
  state: string
  last_run_at: string | null
  last_run_status: string | null
  last_run_url: string | null
  total_runs_30d: number
  success_rate_30d: number
  avg_duration_seconds: number
  is_dead: boolean
  estimated_cost_30d: number
  updated_at: string
}

export type Repo = {
  id: string
  repo_name: string
  full_name: string
  tier: 'core' | 'active' | 'monitored' | 'archived'
  description: string
  language: string
  last_push_at: string | null
  last_ci_status: string | null
  open_prs: number
  open_issues: number
  stale_days: number
  health_score: number
  consolidation_group: string | null
  consolidation_recommendation: string | null
  size_kb: number
  updated_at: string
}

export type NexusTable = {
  id: string
  table_name: string
  schema_name: string
  table_type: string
  row_count: number
  size_bytes: number
  belongs_to_project: string
  rls_enabled: boolean
  is_orphan: boolean
  growth_rate_daily: number
  updated_at: string
}

export type Secret = {
  id: string
  repo_name: string
  secret_name: string
  created_at_gh: string | null
  updated_at_gh: string | null
  is_org_secret: boolean
  known_expiry: string | null
  known_type: string | null
  is_shared_across_repos: boolean
  status: string
  updated_at: string
}

export type Domain = {
  id: string
  domain: string
  registrar: string
  dns_provider: string
  hosting_provider: string
  ssl_expiry: string | null
  ssl_issuer: string | null
  is_active: boolean
  monthly_cost: number
  purpose: string
  updated_at: string
}
