'use client'
import { useEffect, useState } from 'react'
import { supabase, Workflow } from '@/lib/supabase'
import { formatDaysAgo } from '@/lib/utils'
import { GitBranch, AlertTriangle, XCircle, CheckCircle, Clock, DollarSign, Skull } from 'lucide-react'

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [loading, setLoading] = useState(true)
  const [showDead, setShowDead] = useState(false)
  const [groupByRepo, setGroupByRepo] = useState(true)

  useEffect(() => {
    supabase.from('nexus_workflows').select('*').order('repo_name').order('last_run_at', { ascending: false })
      .then(({ data }) => { setWorkflows(data || []); setLoading(false) })
  }, [])

  const dead = workflows.filter(w => w.is_dead)
  const failing = workflows.filter(w => w.last_run_status === 'failure')
  const totalCost = workflows.reduce((a, w) => a + (w.estimated_cost_30d || 0), 0)

  const byRepo = workflows.reduce((acc, w) => {
    if (!acc[w.repo_name]) acc[w.repo_name] = []
    acc[w.repo_name].push(w)
    return acc
  }, {} as Record<string, Workflow[]>)

  const displayed = showDead ? dead : workflows

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Workflow Intelligence</h1>
          <p className="text-gray-500 text-sm mt-1">{workflows.length} workflows across all repos</p>
        </div>
      </div>

      {/* Stats Strip */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'Total Workflows', value: workflows.length, icon: GitBranch, color: '#8B5CF6' },
          { label: 'Dead (0 runs/30d)', value: dead.length, icon: Skull, color: '#EF4444' },
          { label: 'Failing', value: failing.length, icon: XCircle, color: '#F59E0B' },
          { label: 'Est. Monthly Cost', value: `$${totalCost.toFixed(2)}`, icon: DollarSign, color: '#10B981' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="rounded-xl p-4 glass">
            <div className="flex items-center gap-2 mb-2">
              <Icon size={14} style={{ color }} />
              <span className="text-xs text-gray-500">{label}</span>
            </div>
            <div className="text-2xl font-bold" style={{ color }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Dead Workflow Panel */}
      {dead.length > 0 && (
        <div className="rounded-xl p-5" style={{ background: 'rgba(239,68,68,0.05)', border: '1px solid rgba(239,68,68,0.2)' }}>
          <h2 className="text-sm font-semibold text-red-400 mb-3 flex items-center gap-2">
            <Skull size={14} /> Dead Workflows — No Runs in 30+ Days
          </h2>
          <div className="space-y-2">
            {dead.map(w => (
              <div key={w.id} className="flex items-center gap-3 text-xs py-1.5 border-b border-red-400/10 last:border-0">
                <span className="text-gray-400 font-mono">{w.repo_name}</span>
                <span className="text-red-300 flex-1">{w.workflow_name}</span>
                <span className="text-gray-600">last: {formatDaysAgo(w.last_run_at)}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-red-400/10 text-red-400">DEAD</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Controls */}
      <div className="flex gap-3 items-center">
        <button onClick={() => setGroupByRepo(!groupByRepo)}
          className={`text-xs px-3 py-1.5 rounded-lg border transition-all ${groupByRepo ? 'border-accent text-accent' : 'border-navy/40 text-gray-400'}`}>
          Group by Repo
        </button>
        <button onClick={() => setShowDead(!showDead)}
          className={`text-xs px-3 py-1.5 rounded-lg border transition-all ${showDead ? 'border-red-400 text-red-400' : 'border-navy/40 text-gray-400'}`}>
          {showDead ? 'Show All' : 'Dead Only'}
        </button>
      </div>

      {/* Workflow Grid */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading workflows...</div>
      ) : Object.keys(byRepo).length === 0 ? (
        <div className="text-center py-12 text-gray-500">No workflow data yet. Run the workflow scanner to populate.</div>
      ) : groupByRepo ? (
        <div className="space-y-4">
          {Object.entries(byRepo).map(([repo, wfs]) => {
            const repoWfs = showDead ? wfs.filter(w => w.is_dead) : wfs
            if (repoWfs.length === 0) return null
            return (
              <div key={repo} className="rounded-xl glass overflow-hidden">
                <div className="px-4 py-2.5 border-b border-navy/30 flex items-center justify-between">
                  <span className="text-sm font-medium text-white">{repo}</span>
                  <span className="text-xs text-gray-500">{repoWfs.length} workflows</span>
                </div>
                <div className="divide-y divide-navy/10">
                  {repoWfs.map(w => <WorkflowRow key={w.id} w={w} />)}
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="rounded-2xl glass overflow-hidden">
          <div className="divide-y divide-navy/10">
            {displayed.map(w => <WorkflowRow key={w.id} w={w} />)}
          </div>
        </div>
      )}
    </div>
  )
}

function WorkflowRow({ w }: { w: Workflow }) {
  return (
    <div className="px-4 py-3 flex items-center gap-3 hover:bg-navy/10 transition-colors">
      <div className="flex-1">
        <div className="text-sm text-gray-200">{w.workflow_name}</div>
        <div className="text-xs text-gray-600 font-mono">{w.workflow_path}</div>
      </div>
      <div className="text-xs text-gray-500 w-20 text-right">{formatDaysAgo(w.last_run_at)}</div>
      <div className="text-xs w-12 text-right text-gray-400">{w.total_runs_30d} runs</div>
      <div className="text-xs w-16 text-right">
        {w.success_rate_30d != null ? (
          <span style={{ color: w.success_rate_30d >= 80 ? '#10B981' : w.success_rate_30d >= 50 ? '#F59E0B' : '#EF4444' }}>
            {w.success_rate_30d.toFixed(0)}%
          </span>
        ) : '—'}
      </div>
      <div>
        {w.is_dead ? (
          <span className="text-xs px-2 py-0.5 rounded bg-red-400/10 text-red-400 border border-red-400/20">dead</span>
        ) : w.last_run_status === 'success' ? (
          <CheckCircle size={13} className="text-emerald-400" />
        ) : w.last_run_status === 'failure' ? (
          <XCircle size={13} className="text-red-400" />
        ) : (
          <Clock size={13} className="text-gray-500" />
        )}
      </div>
    </div>
  )
}
