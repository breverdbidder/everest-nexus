'use client'
import { useEffect, useState } from 'react'
import { supabase, NexusTable } from '@/lib/supabase'
import { formatBytes } from '@/lib/utils'
import { Database, AlertTriangle, Shield, ShieldOff, TrendingUp } from 'lucide-react'

export default function DataPage() {
  const [tables, setTables] = useState<NexusTable[]>([])
  const [loading, setLoading] = useState(true)
  const [filterProject, setFilterProject] = useState('All')

  useEffect(() => {
    supabase.from('nexus_tables').select('*').order('size_bytes', { ascending: false })
      .then(({ data }) => { setTables(data || []); setLoading(false) })
  }, [])

  const projects = ['All', ...Array.from(new Set(tables.map(t => t.belongs_to_project).filter(Boolean)))]
  const orphans = tables.filter(t => t.is_orphan)
  const noRls = tables.filter(t => !t.rls_enabled)
  const filtered = filterProject === 'All' ? tables : tables.filter(t => t.belongs_to_project === filterProject)
  const totalSize = tables.reduce((a, t) => a + (t.size_bytes || 0), 0)

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-white">Data Intelligence</h1>
        <p className="text-gray-500 text-sm mt-1">{tables.length} tables mapped · {formatBytes(totalSize)} total</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'Tables', value: tables.length, icon: Database, color: '#10B981' },
          { label: 'Orphans', value: orphans.length, icon: AlertTriangle, color: '#EF4444' },
          { label: 'No RLS', value: noRls.length, icon: ShieldOff, color: '#F59E0B' },
          { label: 'Total Size', value: formatBytes(totalSize), icon: TrendingUp, color: '#8B5CF6' },
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

      {/* Orphan Panel */}
      {orphans.length > 0 && (
        <div className="rounded-xl p-4" style={{ background: 'rgba(239,68,68,0.05)', border: '1px solid rgba(239,68,68,0.2)' }}>
          <h2 className="text-sm font-semibold text-red-400 mb-3 flex items-center gap-2">
            <AlertTriangle size={14} /> Orphan Tables — No Inserts in 30+ Days, No FK References
          </h2>
          <div className="space-y-1.5">
            {orphans.map(t => (
              <div key={t.id} className="flex items-center gap-3 text-xs py-1.5 border-b border-red-400/10 last:border-0">
                <span className="text-gray-400 font-mono flex-1">{t.table_name}</span>
                <span className="text-gray-600">{t.row_count.toLocaleString()} rows</span>
                <span className="text-gray-600">{formatBytes(t.size_bytes)}</span>
                <span className="text-gray-500">{t.belongs_to_project}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-red-400/10 text-red-400">ORPHAN</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* RLS Warning */}
      {noRls.length > 0 && (
        <div className="rounded-xl p-4" style={{ background: 'rgba(245,158,11,0.05)', border: '1px solid rgba(245,158,11,0.2)' }}>
          <h2 className="text-sm font-semibold text-amber-400 mb-2 flex items-center gap-2">
            <ShieldOff size={14} /> Tables Without RLS ({noRls.length})
          </h2>
          <div className="flex flex-wrap gap-1.5">
            {noRls.slice(0, 12).map(t => (
              <span key={t.id} className="text-xs font-mono px-2 py-0.5 rounded bg-amber-400/10 text-amber-300">{t.table_name}</span>
            ))}
            {noRls.length > 12 && <span className="text-xs text-gray-500">+{noRls.length - 12} more</span>}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        {projects.map(p => (
          <button key={p} onClick={() => setFilterProject(p)}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-all ${
              filterProject === p ? 'border-accent text-accent' : 'border-navy/40 text-gray-400 hover:text-white'
            }`}>{p}</button>
        ))}
      </div>

      {/* Table Grid */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading tables...</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-gray-500">No table data. Run the data scanner to populate.</div>
      ) : (
        <div className="rounded-2xl glass overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500 border-b border-navy/30">
                <th className="px-4 py-3 text-left">Table</th>
                <th className="px-4 py-3 text-left">Project</th>
                <th className="px-4 py-3 text-right">Rows</th>
                <th className="px-4 py-3 text-right">Size</th>
                <th className="px-4 py-3 text-center">RLS</th>
                <th className="px-4 py-3 text-center">Type</th>
                <th className="px-4 py-3 text-center">Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(t => (
                <tr key={t.id} className="border-b border-navy/10 hover:bg-navy/10 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-gray-300">{t.table_name}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{t.belongs_to_project || '—'}</td>
                  <td className="px-4 py-3 text-xs text-right text-gray-400">{(t.row_count || 0).toLocaleString()}</td>
                  <td className="px-4 py-3 text-xs text-right text-gray-400">{formatBytes(t.size_bytes || 0)}</td>
                  <td className="px-4 py-3 text-center">
                    {t.rls_enabled ? <Shield size={12} className="mx-auto text-emerald-400" /> : <ShieldOff size={12} className="mx-auto text-amber-400" />}
                  </td>
                  <td className="px-4 py-3 text-center text-xs text-gray-500">{t.table_type}</td>
                  <td className="px-4 py-3 text-center">
                    {t.is_orphan ? (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-red-400/10 text-red-400">orphan</span>
                    ) : (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-emerald-400/10 text-emerald-400">active</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
