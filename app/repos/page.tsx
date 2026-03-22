'use client'
import { useEffect, useState } from 'react'
import { supabase, Repo } from '@/lib/supabase'
import { healthColor, formatDaysAgo } from '@/lib/utils'
import { Layers, Archive, AlertTriangle, CheckCircle, GitPullRequest, Star } from 'lucide-react'

const TIERS = ['All', 'core', 'active', 'monitored', 'archived'] as const

export default function ReposPage() {
  const [repos, setRepos] = useState<Repo[]>([])
  const [loading, setLoading] = useState(true)
  const [tier, setTier] = useState<string>('All')
  const [archiving, setArchiving] = useState<string | null>(null)

  useEffect(() => {
    supabase.from('nexus_repos').select('*').order('health_score').order('stale_days', { ascending: false })
      .then(({ data }) => { setRepos(data || []); setLoading(false) })
  }, [])

  async function archiveRepo(repo: Repo) {
    if (!confirm(`Archive ${repo.repo_name}? This will call the GitHub API to mark it archived.`)) return
    setArchiving(repo.id)
    try {
      const res = await fetch('/api/archive-repo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo: repo.full_name }),
      })
      if (res.ok) {
        await supabase.from('nexus_repos').update({ tier: 'archived', updated_at: new Date().toISOString() }).eq('id', repo.id)
        setRepos(prev => prev.map(r => r.id === repo.id ? { ...r, tier: 'archived' as const } : r))
      }
    } finally {
      setArchiving(null)
    }
  }

  const filtered = tier === 'All' ? repos : repos.filter(r => r.tier === tier)

  const consolidationGroups = repos.reduce((acc, r) => {
    if (r.consolidation_group) {
      if (!acc[r.consolidation_group]) acc[r.consolidation_group] = []
      acc[r.consolidation_group].push(r)
    }
    return acc
  }, {} as Record<string, Repo[]>)

  const archiveCandidates = repos.filter(r => r.stale_days > 90 && r.tier !== 'archived')

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Repo Intelligence</h1>
          <p className="text-gray-500 text-sm mt-1">{repos.length} repos monitored</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        {(['core','active','monitored','archived'] as const).map(t => {
          const count = repos.filter(r => r.tier === t).length
          const colors: Record<string, string> = { core: '#EF4444', active: '#10B981', monitored: '#F59E0B', archived: '#6B7280' }
          return (
            <button key={t} onClick={() => setTier(tier === t ? 'All' : t)}
              className={`rounded-xl p-4 text-left transition-all glass ${tier === t ? 'ring-1' : ''}`}
              style={{ '--tw-ring-color': colors[t] } as any}>
              <div className="text-2xl font-bold" style={{ color: colors[t] }}>{count}</div>
              <div className="text-xs text-gray-500 capitalize mt-1">{t}</div>
            </button>
          )
        })}
      </div>

      {/* Archive Candidates */}
      {archiveCandidates.length > 0 && (
        <div className="rounded-xl p-4" style={{ background: 'rgba(107,114,128,0.08)', border: '1px solid rgba(107,114,128,0.2)' }}>
          <h2 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
            <Archive size={14} /> Archive Candidates — Stale 90+ Days
          </h2>
          <div className="space-y-1.5">
            {archiveCandidates.slice(0, 8).map(r => (
              <div key={r.id} className="flex items-center gap-3 text-xs">
                <span className="text-gray-400 flex-1 font-mono">{r.repo_name}</span>
                <span className="text-gray-600">{r.stale_days}d stale</span>
                <span className="text-xs px-1.5 py-0.5 rounded capitalize"
                  style={{ background: `${healthColor(r.health_score)}20`, color: healthColor(r.health_score) }}>
                  {r.health_score}/100
                </span>
                <button onClick={() => archiveRepo(r)} disabled={archiving === r.id}
                  className="px-2.5 py-1 rounded bg-gray-400/10 text-gray-400 hover:bg-gray-400/20 border border-gray-400/20 transition-all">
                  {archiving === r.id ? '...' : 'Archive'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Consolidation Panel */}
      {Object.keys(consolidationGroups).length > 0 && (
        <div className="rounded-xl p-4 glass">
          <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <GitPullRequest size={14} className="text-accent" /> Consolidation Panel
          </h2>
          <div className="grid grid-cols-2 gap-4">
            {Object.entries(consolidationGroups).map(([group, groupRepos]) => (
              <div key={group} className="rounded-lg p-3" style={{ background: 'rgba(30,58,95,0.3)' }}>
                <div className="text-xs font-semibold text-accent mb-2">{group}</div>
                <div className="space-y-1">
                  {groupRepos.map(r => (
                    <div key={r.id} className="text-xs text-gray-400 flex justify-between">
                      <span>{r.repo_name}</span>
                      <span style={{ color: healthColor(r.health_score) }}>{r.health_score}</span>
                    </div>
                  ))}
                </div>
                {groupRepos[0]?.consolidation_recommendation && (
                  <div className="text-xs text-gray-600 mt-2 italic">{groupRepos[0].consolidation_recommendation.slice(0, 80)}...</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tier filter */}
      <div className="flex gap-2">
        {TIERS.map(t => (
          <button key={t} onClick={() => setTier(t)}
            className={`text-xs px-3 py-1.5 rounded-lg border capitalize transition-all ${
              tier === t ? 'border-accent text-accent' : 'border-navy/40 text-gray-400 hover:text-white'
            }`}>{t}</button>
        ))}
      </div>

      {/* Repo Cards */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading repos...</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-gray-500">No repos found. Run the repo scanner to populate.</div>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          {filtered.map(repo => (
            <div key={repo.id} className="rounded-xl p-4 glass hover:bg-navy/20 transition-all">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <div className="text-sm font-medium text-white">{repo.repo_name}</div>
                  {repo.description && <div className="text-xs text-gray-500 mt-0.5 line-clamp-1">{repo.description}</div>}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs capitalize px-2 py-0.5 rounded"
                    style={{
                      background: repo.tier === 'core' ? 'rgba(239,68,68,0.1)' : repo.tier === 'active' ? 'rgba(16,185,129,0.1)' : 'rgba(107,114,128,0.1)',
                      color: repo.tier === 'core' ? '#EF4444' : repo.tier === 'active' ? '#10B981' : '#6B7280'
                    }}>{repo.tier}</span>
                </div>
              </div>
              {/* Health Bar */}
              <div className="mb-2">
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-500">Health</span>
                  <span style={{ color: healthColor(repo.health_score) }}>{repo.health_score}/100</span>
                </div>
                <div className="h-1.5 bg-navy/30 rounded-full overflow-hidden">
                  <div className="h-full health-bar rounded-full" style={{ width: `${repo.health_score}%`, background: healthColor(repo.health_score) }}></div>
                </div>
              </div>
              <div className="flex items-center gap-3 text-xs text-gray-600">
                <span>{formatDaysAgo(repo.last_push_at)}</span>
                {repo.language && <span className="text-gray-500">· {repo.language}</span>}
                {repo.open_prs > 0 && <span className="text-blue-400">· {repo.open_prs} PRs</span>}
                {repo.last_ci_status === 'success' && <CheckCircle size={10} className="text-emerald-400 ml-auto" />}
                {repo.last_ci_status === 'failure' && <AlertTriangle size={10} className="text-red-400 ml-auto" />}
              </div>
              {repo.tier !== 'archived' && repo.stale_days > 90 && (
                <div className="mt-2 flex justify-end">
                  <button onClick={() => archiveRepo(repo)} className="text-xs px-2 py-0.5 rounded border border-gray-400/20 text-gray-400 hover:text-white hover:border-gray-400/40 transition-all">
                    Archive
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
