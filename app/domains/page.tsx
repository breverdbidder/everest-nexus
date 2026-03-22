'use client'
import { useEffect, useState } from 'react'
import { supabase, Domain } from '@/lib/supabase'
import { daysUntil, sslDaysColor } from '@/lib/utils'
import { Globe, Shield, AlertTriangle, DollarSign, Clock, CheckCircle, XCircle } from 'lucide-react'

export default function DomainsPage() {
  const [domains, setDomains] = useState<Domain[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase.from('nexus_domains').select('*').order('ssl_expiry')
      .then(({ data }) => { setDomains(data || []); setLoading(false) })
  }, [])

  const active = domains.filter(d => d.is_active)
  const at_risk = domains.filter(d => d.ssl_expiry && daysUntil(d.ssl_expiry)! < 14)
  const expiring_30 = domains.filter(d => d.ssl_expiry && daysUntil(d.ssl_expiry)! < 30)
  const total_cost = domains.reduce((a, d) => a + (d.monthly_cost || 0), 0)

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-white">Domain Intelligence</h1>
        <p className="text-gray-500 text-sm mt-1">{active.length} active domains tracked</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'Active Domains', value: active.length, icon: Globe, color: '#06B6D4' },
          { label: 'SSL at Risk', value: at_risk.length, icon: AlertTriangle, color: '#EF4444' },
          { label: 'Expiring <30d', value: expiring_30.length, icon: Clock, color: '#F59E0B' },
          { label: 'Monthly Cost', value: `$${total_cost.toFixed(2)}`, icon: DollarSign, color: '#10B981' },
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

      {/* SSL Countdown */}
      <div className="grid grid-cols-1 gap-3">
        {domains.length === 0 && !loading && (
          <div className="rounded-xl p-8 glass text-center text-gray-500">
            No domain data. Run the domain scanner to populate.
          </div>
        )}
        {domains.map(domain => {
          const sslDays = daysUntil(domain.ssl_expiry)
          return (
            <div key={domain.id} className="rounded-xl p-5 glass hover:bg-navy/20 transition-all">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  {domain.is_active ? (
                    <CheckCircle size={14} className="text-emerald-400" />
                  ) : (
                    <XCircle size={14} className="text-gray-500" />
                  )}
                  <div>
                    <div className="text-white font-semibold">{domain.domain}</div>
                    <div className="text-xs text-gray-500 mt-0.5">{domain.purpose} · {domain.hosting_provider}</div>
                  </div>
                </div>
                <div className="text-right">
                  {sslDays !== null ? (
                    <div>
                      <div className={`text-2xl font-bold ${sslDaysColor(sslDays)}`}>
                        {sslDays < 0 ? 'EXPIRED' : sslDays}
                        {sslDays >= 0 && <span className="text-sm font-normal text-gray-500">d</span>}
                      </div>
                      <div className="text-xs text-gray-600">SSL remaining</div>
                    </div>
                  ) : (
                    <div className="text-gray-600 text-sm">SSL unknown</div>
                  )}
                </div>
              </div>

              {/* SSL Progress Bar */}
              {sslDays !== null && sslDays > 0 && (
                <div className="mb-3">
                  <div className="h-1.5 bg-navy/30 rounded-full overflow-hidden">
                    <div className="h-full health-bar rounded-full transition-all"
                      style={{
                        width: `${Math.min(100, (sslDays / 90) * 100)}%`,
                        background: sslDays > 30 ? '#10B981' : sslDays > 14 ? '#F59E0B' : '#EF4444'
                      }}></div>
                  </div>
                </div>
              )}

              <div className="flex items-center gap-4 text-xs text-gray-600">
                <span className="flex items-center gap-1"><Shield size={10} /> {domain.ssl_issuer || 'unknown issuer'}</span>
                <span>{domain.dns_provider}</span>
                <span>{domain.registrar}</span>
                {domain.monthly_cost > 0 && (
                  <span className="ml-auto text-gray-500">${domain.monthly_cost}/mo</span>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
