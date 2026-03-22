'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Brain, CheckSquare, GitBranch, Database,
  Key, Globe, Activity, Layers
} from 'lucide-react'

const nav = [
  { href: '/', label: 'Overview', icon: Brain, color: '#F59E0B' },
  { href: '/tasks', label: 'Tasks', icon: CheckSquare, color: '#EF4444' },
  { href: '/workflows', label: 'Workflows', icon: GitBranch, color: '#8B5CF6' },
  { href: '/repos', label: 'Repos', icon: Layers, color: '#1E3A5F' },
  { href: '/data', label: 'Data', icon: Database, color: '#10B981' },
  { href: '/secrets', label: 'Secrets', icon: Key, color: '#F59E0B' },
  { href: '/domains', label: 'Domains', icon: Globe, color: '#06B6D4' },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="fixed left-0 top-0 h-full w-56 flex flex-col z-50"
      style={{ background: 'rgba(2, 6, 23, 0.95)', borderRight: '1px solid rgba(30, 58, 95, 0.5)' }}>
      {/* Logo */}
      <div className="p-5 border-b border-navy/30">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #1E3A5F, #F59E0B)' }}>
            <Activity size={16} className="text-white" />
          </div>
          <div>
            <div className="font-bold text-sm text-white">Everest Nexus</div>
            <div className="text-xs text-gray-500">nexus.zonewise.ai</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {nav.map(({ href, label, icon: Icon, color }) => {
          const active = pathname === href
          return (
            <Link key={href} href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                active
                  ? 'text-white'
                  : 'text-gray-400 hover:text-white hover:bg-navy/20'
              }`}
              style={active ? {
                background: `linear-gradient(135deg, rgba(30, 58, 95, 0.6), rgba(30, 58, 95, 0.2))`,
                borderLeft: `2px solid ${color}`,
                paddingLeft: '10px'
              } : {}}
            >
              <Icon size={16} style={{ color: active ? color : undefined }} />
              {label}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-navy/30">
        <div className="text-xs text-gray-600">6 Intelligence Layers</div>
        <div className="text-xs text-gray-500 mt-1">BidDeed / ZoneWise</div>
      </div>
    </aside>
  )
}
