'use client'
import { useEffect, useState, useCallback } from 'react'
import { supabase, Task } from '@/lib/supabase'
import { priorityColor, statusColor, formatCountdown, formatDaysAgo } from '@/lib/utils'
import { Clock, CheckCircle, SkipForward, TrendingUp, AlertCircle, RefreshCw, Filter } from 'lucide-react'

const PRIORITIES = ['All', 'P0', 'P1', 'P2', 'P3']
const STATUSES = ['All', 'queued', 'running', 'blocked', 'success', 'failed']

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [filterPriority, setFilterPriority] = useState('All')
  const [filterStatus, setFilterStatus] = useState('All')
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const fetchTasks = useCallback(async () => {
    let q = supabase.from('nexus_tasks').select('*').order('priority').order('created_at', { ascending: false })
    if (filterPriority !== 'All') q = q.eq('priority', filterPriority)
    if (filterStatus !== 'All') q = q.eq('status', filterStatus)
    const { data } = await q.limit(100)
    setTasks(data || [])
    setLoading(false)
  }, [filterPriority, filterStatus])

  useEffect(() => {
    fetchTasks()
    const channel = supabase.channel('nexus_tasks_rt')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'nexus_tasks' }, fetchTasks)
      .subscribe()
    return () => { supabase.removeChannel(channel) }
  }, [fetchTasks])

  async function doAction(taskId: string, action: 'done' | 'skip' | 'bump' | 'block') {
    setActionLoading(taskId + action)
    const updates: Partial<Task> = {}
    if (action === 'done') updates.status = 'success'
    else if (action === 'skip') updates.status = 'skipped' as any
    else if (action === 'block') updates.status = 'blocked'
    else if (action === 'bump') {
      const task = tasks.find(t => t.id === taskId)
      if (task) {
        const pMap: Record<string, string> = { P3: 'P2', P2: 'P1', P1: 'P0', P0: 'P0' }
        updates.priority = (pMap[task.priority] || 'P2') as Task['priority']
      }
    }
    await supabase.from('nexus_tasks').update({ ...updates, updated_at: new Date().toISOString() }).eq('id', taskId)
    setActionLoading(null)
    fetchTasks()
  }

  const p0 = tasks.filter(t => t.priority === 'P0')
  const blocked = tasks.filter(t => t.status === 'blocked')

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Task Intelligence</h1>
          <p className="text-gray-500 text-sm mt-1">{tasks.length} tasks · realtime</p>
        </div>
        <div className="flex gap-2">
          {p0.length > 0 && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-red-400 bg-red-400/10 border border-red-400/30 animate-pulse">
              <AlertCircle size={12} /> {p0.length} P0 CRITICAL
            </div>
          )}
          {blocked.length > 0 && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-orange-400 bg-orange-400/10 border border-orange-400/30">
              <AlertCircle size={12} /> {blocked.length} BLOCKED
            </div>
          )}
        </div>
      </div>

      {/* SLA Timers for P0/P1 */}
      {tasks.filter(t => (t.priority === 'P0' || t.priority === 'P1') && t.sla_deadline && t.status !== 'success').length > 0 && (
        <div className="rounded-xl p-4 space-y-2" style={{ background: 'rgba(239,68,68,0.05)', border: '1px solid rgba(239,68,68,0.2)' }}>
          <div className="text-xs font-semibold text-red-400 mb-2 flex items-center gap-1.5"><Clock size={12} /> SLA TIMERS</div>
          {tasks.filter(t => (t.priority === 'P0' || t.priority === 'P1') && t.sla_deadline && t.status !== 'success').slice(0, 3).map(task => (
            <div key={task.id} className="flex items-center gap-3 text-xs">
              <span className={`font-bold px-2 py-0.5 rounded border ${priorityColor(task.priority)}`}>{task.priority}</span>
              <span className="text-gray-300 flex-1 truncate">{task.description}</span>
              <span className={`font-mono font-bold ${
                formatCountdown(task.sla_deadline) === 'EXPIRED' ? 'text-red-400' : 'text-amber-400'
              }`}>{formatCountdown(task.sla_deadline) || '—'}</span>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <div className="flex items-center gap-1.5">
          <Filter size={12} className="text-gray-500" />
          <span className="text-xs text-gray-500">Priority:</span>
          {PRIORITIES.map(p => (
            <button key={p} onClick={() => setFilterPriority(p)}
              className={`text-xs px-2.5 py-1 rounded-md transition-all ${
                filterPriority === p ? 'bg-accent text-black font-bold' : 'text-gray-400 bg-navy/20 hover:text-white'
              }`}>{p}</button>
          ))}
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-gray-500">Status:</span>
          {STATUSES.map(s => (
            <button key={s} onClick={() => setFilterStatus(s)}
              className={`text-xs px-2.5 py-1 rounded-md transition-all capitalize ${
                filterStatus === s ? 'bg-accent text-black font-bold' : 'text-gray-400 bg-navy/20 hover:text-white'
              }`}>{s}</button>
          ))}
        </div>
        <button onClick={fetchTasks} className="ml-auto text-xs text-gray-500 hover:text-white flex items-center gap-1">
          <RefreshCw size={11} /> Refresh
        </button>
      </div>

      {/* Task Table */}
      <div className="rounded-2xl overflow-hidden glass">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-gray-500 border-b border-navy/30">
              <th className="px-4 py-3 text-left">Priority</th>
              <th className="px-4 py-3 text-left">Description</th>
              <th className="px-4 py-3 text-left">Project</th>
              <th className="px-4 py-3 text-left">Owner</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Created</th>
              <th className="px-4 py-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-500">Loading...</td></tr>
            ) : tasks.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-500">No tasks found. Scanners populate data automatically.</td></tr>
            ) : tasks.map(task => (
              <tr key={task.id} className="border-b border-navy/10 hover:bg-navy/10 transition-colors">
                <td className="px-4 py-3">
                  <span className={`text-xs font-bold px-2 py-0.5 rounded border ${priorityColor(task.priority)}`}>
                    {task.priority}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="text-gray-200 max-w-xs truncate" title={task.description}>{task.description}</div>
                  {task.escalation_count > 0 && (
                    <div className="text-xs text-red-400 mt-0.5">⚠ escalated {task.escalation_count}×</div>
                  )}
                </td>
                <td className="px-4 py-3 text-gray-400 text-xs">{task.project || '—'}</td>
                <td className="px-4 py-3 text-gray-400 text-xs">{task.owner || '—'}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded capitalize ${statusColor(task.status)}`}>{task.status}</span>
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs">{formatDaysAgo(task.created_at)}</td>
                <td className="px-4 py-3">
                  <div className="flex gap-1">
                    {['success','skipped'].includes(task.status) ? null : (<>
                      <button onClick={() => doAction(task.id, 'done')} disabled={actionLoading === task.id + 'done'}
                        className="p-1 rounded hover:bg-emerald-400/20 text-emerald-400 transition-colors" title="Done">
                        <CheckCircle size={13} />
                      </button>
                      <button onClick={() => doAction(task.id, 'skip')} disabled={actionLoading === task.id + 'skip'}
                        className="p-1 rounded hover:bg-gray-400/20 text-gray-400 transition-colors" title="Skip">
                        <SkipForward size={13} />
                      </button>
                      <button onClick={() => doAction(task.id, 'bump')} disabled={actionLoading === task.id + 'bump'}
                        className="p-1 rounded hover:bg-amber-400/20 text-amber-400 transition-colors" title="Bump priority">
                        <TrendingUp size={13} />
                      </button>
                      <button onClick={() => doAction(task.id, 'block')} disabled={actionLoading === task.id + 'block'}
                        className="p-1 rounded hover:bg-red-400/20 text-red-400 transition-colors" title="Mark blocked">
                        <AlertCircle size={13} />
                      </button>
                    </>)}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
