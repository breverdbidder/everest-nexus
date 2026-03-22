'use client'
import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip } from 'recharts'
import { Activity, CheckSquare, GitBranch, Layers, Database, Key, Globe, AlertCircle, TrendingUp } from 'lucide-react'

type Stats = {
  tasks: { total: number, p0: number, p1: number, p2: number, p3: number, blocked: number }
  workflows: { total: number, dead: number, failing: number }
  repos: { total: number, healthy: number, stale: number }
  tables: { total: number, orphans: number }
  secrets: { total: number, expiring: number }
  domains: { total: number, expiringSoon: number }
}

const LAYER_COLORS = {
  tasks: '#EF4444',
  workflows: '#8B5CF6',
  repos: '#1E3A5F',
  data: '#10B981',
  secrets: '#F59E0B',
  domains: '#06B6D4',
}

export default function OverviewPage() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [recentTasks, setRecentTasks] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchStats()
    const channel = supabase
      .channel('nexus_overview')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'nexus_tasks' }, () => fetchStats())
      .subscribe()
    return () => { supabase.removeChannel(channel) }
  }, [])

  async function fetchStats() {
    try {
      const [tasksR, workflowsR, reposR, tablesR, secretsR, domainsR, recentR] = await Promise.all([
        supabase.from('nexus_tasks').select('priority, status'),
        supabase.from('nexus_workflows').select('is_dead, last_run_status, success_rate_30d'),
        supabase.from('nexus_repos').select('health_score, stale_days, tier'),
        supabase.from('nexus_tables').select('is_orphan'),
        supabase.from('nexus_secrets').select('known_expiry, status'),
        supabase.from('nexus_domains').select('ssl_expiry, is_active'),
        supabase.from('nexus_tasks').select('*').order('created_at', { ascending: false }).limit(10),
      ])

      const tasks = tasksR.data || []
      const workflows = workflowsR.data || []
      const repos = reposR.data || []
      const tables = tablesR.data || []
      const secrets = secretsR.data || []
      const domains = domainsR.data || []

      const now = Date.now()
      const in30days = now + 30 * 86400000

      setStats({
        tasks: {
          total: tasks.length,
          p0: tasks.filter(t => t.priority === 'P0').length,
          p1: tasks.filter(t => t.priority === 'P1').length,
          p2: tasks.filter(t => t.priority === 'P2').length,
          p3: tasks.filter(t => t.priority === 'P3').length,
          blocked: tasks.filter(t => t.status === 'blocked').length,
        },
        workflows: {
          total: workflows.length,
          dead: workflows.filter(w => w.is_dead).length,
          failing: workflows.filter(w => w.last_run_status === 'failure').length,
        },
        repos: {
          total: repos.length,
          healthy: repos.filter(r => r.health_score >= 80).length,
          stale: repos.filter(r => r.stale_days > 30).length,
        },
        tables: {
          total: tables.length,
          orphans: tables.filter(t => t.is_orphan).length,
        },
        secrets: {
          total: secrets.length,
          expiring: secrets.filter(s => s.known_expiry && new Date(s.known_expiry).getTime() < in30days).length,
        },
        domains: {
          total: domains.filter(d => d.is_active).length,
          expiringSoon: domains.filter(d => d.ssl_expiry && new Date(d.ssl_expiry).getTime() < in30days).length,
        },
      })
      setRecentTasks(recentR.data || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const radarData = stats ? [
    { layer: 'Tasks', score: Math.max(0, 100 - (stats.tasks.p0 * 20 + stats.tasks.blocked * 10)), color: LAYER_COLORS.tasks },
    { layer: 'Workflows', score: Math.max(0, 100 - (stats.workflows.dead * 5 + stats.workflows.failing * 10)), color: LAYER_COLORS.workflows },
    { layer: 'Repos', score: stats.repos.total > 0 ? Math.round((stats.repos.healthy / stats.repos.total) * 100) : 100, color: LAYER_COLORS.repos },
    { layer: 'Data', score: stats.tables.total > 0 ? Math.max(0, 100 - (stats.tables.orphans / stats.tables.total) * 100) : 100, color: LAYER_COLORS.data },
    { layer: 'Secrets', score: Math.max(0, 100 - stats.secrets.expiring * 20), color: LAYER_COLORS.secrets },
    { layer: 'Domains', score: Math.max(0, 100 - stats.domains.expiringSoon * 30), color: LAYER_COLORS.domains },
  ] : []

  const overallScore = radarData.length > 0 ? Math.round(radarData.reduce((a, b) => a + b.score, 0) / 6) : 0

  if (loading) return (
    <div className="flex items-center justify-center h-screen">
      <div className="text-accent text-lg font-semibold animate-pulse">Loading Nexus...</div>
    </div>
  )

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Ecosystem Brain</h1>
          <p className="text-gray-500 text-sm mt-1">BidDeed / ZoneWise / Everest — 6 Intelligence Layers</p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 rounded-lg glass">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
          <span className="text-xs text-gray-400">Live</span>
        </div>
      </div>

      {/* Priority Strip */}
      {stats && (
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: 'P0 Critical', count: stats.tasks.p0, color: '#EF4444', bg: 'rgba(239,68,68,0.1)', border: 'rgba(239,68,68,0.3)' },
            { label: 'P1 High', count: stats.tasks.p1, color: '#F59E0B', bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.3)' },
            { label: 'P2 Normal', count: stats.tasks.p2, color: '#EAB308', bg: 'rgba(234,179,8,0.1)', border: 'rgba(234,179,8,0.3)' },
            { label: 'P3 Low', count: stats.tasks.p3, color: '#6B7280', bg: 'rgba(107,114,128,0.1)', border: 'rgba(107,114,128,0.3)' },
          ].map(p => (
            <div key={p.label} className="rounded-xl p-4 flex items-center gap-3"
              style={{ background: p.bg, border: `1px solid ${p.border}` }}>
              <div className="text-3xl font-bold" style={{ color: p.color }}>{p.count}</div>
              <div className="text-xs text-gray-400">{p.label}</div>
              {p.label === 'P0 Critical' && p.count > 0 && (
                <AlertCircle size={14} className="ml-auto animate-pulse-red" style={{ color: p.color }} />
              )}
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-3 gap-6">
        {/* Health Ring */}
        <div className="col-span-1 rounded-2xl p-5 glass">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white text-sm">Ecosystem Health</h2>
            <div className="text-2xl font-bold" style={{ color: overallScore >= 80 ? '#10B981' : overallScore >= 60 ? '#F59E0B' : '#EF4444' }}>
              {overallScore}
            </div>
          </div>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid stroke="rgba(30,58,95,0.4)" />
                <PolarAngleAxis dataKey="layer" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <Radar name="Health" dataKey="score" stroke="#F59E0B" fill="#F59E0B" fillOpacity={0.15} strokeWidth={2} />
                <Tooltip
                  contentStyle={{ background: '#0f172a', border: '1px solid #1E3A5F', borderRadius: 8, fontSize: 12 }}
                  formatter={(v: any) => [`${v}/100`, 'Score']}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="col-span-2 grid grid-cols-3 gap-3 content-start">
          {stats && [
            { label: 'Repos', icon: Layers, total: stats.repos.total, sub: `${stats.repos.healthy} healthy`, color: '#1E3A5F', href: '/repos' },
            { label: 'Workflows', icon: GitBranch, total: stats.workflows.total, sub: `${stats.workflows.dead} dead`, color: '#8B5CF6', href: '/workflows' },
            { label: 'Tables', icon: Database, total: stats.tables.total, sub: `${stats.tables.orphans} orphans`, color: '#10B981', href: '/data' },
            { label: 'Secrets', icon: Key, total: stats.secrets.total, sub: `${stats.secrets.expiring} expiring`, color: '#F59E0B', href: '/secrets' },
            { label: 'Domains', icon: Globe, total: stats.domains.total, sub: `${stats.domains.expiringSoon} at risk`, color: '#06B6D4', href: '/domains' },
            { label: 'Tasks', icon: CheckSquare, total: stats.tasks.total, sub: `${stats.tasks.blocked} blocked`, color: '#EF4444', href: '/tasks' },
          ].map(({ label, icon: Icon, total, sub, color, href }) => (
            <a key={label} href={href} className="rounded-xl p-4 hover:scale-105 transition-transform cursor-pointer"
              style={{ background: 'rgba(30,58,95,0.15)', border: '1px solid rgba(30,58,95,0.4)' }}>
              <div className="flex items-center gap-2 mb-2">
                <Icon size={14} style={{ color }} />
                <span className="text-xs text-gray-400">{label}</span>
              </div>
              <div className="text-2xl font-bold text-white">{total}</div>
              <div className="text-xs text-gray-500 mt-1">{sub}</div>
            </a>
          ))}
        </div>
      </div>

      {/* Recent Tasks */}
      <div className="rounded-2xl glass p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-white text-sm flex items-center gap-2">
            <Activity size={14} className="text-accent" /> Recent Activity
          </h2>
          <a href="/tasks" className="text-xs text-accent hover:underline">View all →</a>
        </div>
        <div className="space-y-2">
          {recentTasks.length === 0 ? (
            <div className="text-gray-500 text-sm text-center py-4">No tasks yet. Data populates as scanners run.</div>
          ) : recentTasks.map(task => (
            <div key={task.id} className="flex items-center gap-3 py-2 border-b border-navy/20 last:border-0">
              <span className={`text-xs font-bold px-2 py-0.5 rounded border ${
                task.priority === 'P0' ? 'text-red-400 border-red-400/30 bg-red-400/10' :
                task.priority === 'P1' ? 'text-amber-400 border-amber-400/30 bg-amber-400/10' :
                task.priority === 'P2' ? 'text-yellow-400 border-yellow-400/30 bg-yellow-400/10' :
                'text-gray-400 border-gray-400/30 bg-gray-400/10'
              }`}>{task.priority}</span>
              <span className="text-sm text-gray-300 flex-1 truncate">{task.description}</span>
              <span className={`text-xs px-2 py-0.5 rounded ${
                task.status === 'success' ? 'text-emerald-400 bg-emerald-400/10' :
                task.status === 'blocked' ? 'text-red-400 bg-red-400/10' :
                task.status === 'running' ? 'text-blue-400 bg-blue-400/10' :
                'text-gray-400 bg-gray-400/10'
              }`}>{task.status}</span>
              <span className="text-xs text-gray-600 w-20 text-right">{task.project || '—'}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
