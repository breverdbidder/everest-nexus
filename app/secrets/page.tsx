'use client'
import { useEffect, useState } from 'react'
import { supabase, Secret } from '@/lib/supabase'
import { formatDaysAgo, daysUntil } from '@/lib/utils'
import { Key, AlertTriangle, Share2, RotateCcw, Calendar } from 'lucide-react'

export default function SecretsPage() {
  const [secrets, setSecrets] = useState<Secret[]>([])
  const [loading, setLoading] = useState(true)
  const [filterRepo, setFilterRepo] = useState('All')

  useEffect(() => {
    supabase.from('nexus_secrets').select('*').order('repo_name').order('secret_name')
      .then(({ data }) => { setSecrets(data || []); setLoading(false) })
  }, [])

  const repos = ['All', ...Array.from(new Set(secrets.map(s => s.repo_name)))]
  const expiring = secrets.filter(s => s.known_expiry && daysUntil(s.known_expiry)! < 30)
  const stale = secrets.filter(s => {
    if (!s.updated_at_gh) return false
    return (Date.now() - new Date(s.updated_at_gh).getTime()) > 365 * 86400000
  })
  const shared = secrets.filter(s => s.is_shared_across_repos)

  const filtered = filterRepo === 'All' ? secrets : secrets.filter(s => s.repo_name === filterRepo)

  // Build secret-name → repos matrix
  const secretNames = Array.from(new Set(secrets.map(s => s.secret_name))).sort()
  const repoNames = Array.from(new Set(secrets.map(s => s.repo_name))).sort()
  const matrix: Record<string, Set<string>> = {}
  secrets.forEach(s => {
    if (!matrix[s.secret_name]) matrix[s.secret_name] = new Set()
    matrix[s.secret_name].add(s.repo_name)
  })
  const sharedSecretNames = secretNames.filter(n => matrix[n]?.size > 1)

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-white">Secret Intelligence</h1>
        <p className="text-gray-500 text-sm mt-1">{secrets.length} secrets across {repoNames.length} repos</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'Total Secrets', value: secrets.length, icon: Key, color: '#F59E0B' },
          { label: 'Expiring <30d', value: expiring.length, icon: Calendar, color: '#EF4444' },
          { label: 'Stale (1yr+)', value: stale.length, icon: RotateCcw, color: '#F59E0B' },
          { label: 'Shared', value: shared.length, icon: Share2, color: '#8B5CF6' },
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

      {/* Expiry Timeline */}
      {expiring.length > 0 && (
        <div className="rounded-xl p-4" style={{ background: 'rgba(239,68,68,0.05)', border: '1px solid rgba(239,68,68,0.2)' }}>
          <h2 className="text-sm font-semibold text-red-400 mb-3 flex items-center gap-2">
            <AlertTriangle size={14} /> Expiring Within 30 Days
          </h2>
          <div className="space-y-1.5">
            {expiring.map(s => {
              const days = daysUntil(s.known_expiry)
              return (
                <div key={s.id} className="flex items-center gap-3 text-xs py-1 border-b border-red-400/10 last:border-0">
                  <span className="text-gray-400 font-mono flex-1">{s.secret_name}</span>
                  <span className="text-gray-500">{s.repo_name}</span>
                  <span className={`font-bold ${days! <= 7 ? 'text-red-400' : 'text-amber-400'}`}>
                    {days === 0 ? 'TODAY' : days! < 0 ? 'EXPIRED' : `${days}d`}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Shared Secret Map */}
      {sharedSecretNames.length > 0 && (
        <div className="rounded-xl p-4 glass">
          <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <Share2 size={14} className="text-purple-400" /> Shared Secrets Matrix
          </h2>
          <div className="space-y-1.5">
            {sharedSecretNames.map(name => (
              <div key={name} className="flex items-start gap-3 text-xs py-1.5 border-b border-navy/20 last:border-0">
                <span className="text-purple-300 font-mono w-48 shrink-0">{name}</span>
                <div className="flex flex-wrap gap-1">
                  {Array.from(matrix[name]).map(repo => (
                    <span key={repo} className="px-1.5 py-0.5 rounded bg-navy/40 text-gray-400">{repo}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filter + Table */}
      <div className="flex gap-2 flex-wrap">
        {repos.slice(0, 12).map(r => (
          <button key={r} onClick={() => setFilterRepo(r)}
            className={`text-xs px-2.5 py-1 rounded-lg border transition-all ${
              filterRepo === r ? 'border-accent text-accent' : 'border-navy/40 text-gray-400 hover:text-white'
            }`}>{r}</button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading secrets...</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-gray-500">No secrets data. Run the secret scanner to populate.</div>
      ) : (
        <div className="rounded-2xl glass overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500 border-b border-navy/30">
                <th className="px-4 py-3 text-left">Secret Name</th>
                <th className="px-4 py-3 text-left">Repo</th>
                <th className="px-4 py-3 text-left">Type</th>
                <th className="px-4 py-3 text-left">Last Updated</th>
                <th className="px-4 py-3 text-left">Expiry</th>
                <th className="px-4 py-3 text-center">Shared</th>
                <th className="px-4 py-3 text-center">Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(s => {
                const days = daysUntil(s.known_expiry)
                return (
                  <tr key={s.id} className="border-b border-navy/10 hover:bg-navy/10 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-gray-300">{s.secret_name}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{s.repo_name}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{s.known_type || '—'}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{formatDaysAgo(s.updated_at_gh)}</td>
                    <td className="px-4 py-3 text-xs">
                      {days !== null ? (
                        <span className={days <= 7 ? 'text-red-400' : days <= 30 ? 'text-amber-400' : 'text-gray-400'}>
                          {days < 0 ? 'EXPIRED' : `${days}d`}
                        </span>
                      ) : <span className="text-gray-600">—</span>}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {s.is_shared_across_repos ? <Share2 size={12} className="mx-auto text-purple-400" /> : <span className="text-gray-600">—</span>}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`text-xs px-1.5 py-0.5 rounded ${
                        s.status === 'active' ? 'bg-emerald-400/10 text-emerald-400' :
                        s.status === 'expired' ? 'bg-red-400/10 text-red-400' :
                        'bg-gray-400/10 text-gray-400'
                      }`}>{s.status}</span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
