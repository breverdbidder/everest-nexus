export function cn(...classes: (string | undefined | null | false)[]) {
  return classes.filter(Boolean).join(' ')
}

export function priorityColor(priority: string) {
  switch (priority) {
    case 'P0': return 'text-red-400 bg-red-400/10 border-red-400/30'
    case 'P1': return 'text-amber-400 bg-amber-400/10 border-amber-400/30'
    case 'P2': return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30'
    case 'P3': return 'text-gray-400 bg-gray-400/10 border-gray-400/30'
    default: return 'text-gray-400 bg-gray-400/10 border-gray-400/30'
  }
}

export function statusColor(status: string) {
  switch (status) {
    case 'success': return 'text-emerald-400 bg-emerald-400/10'
    case 'running': return 'text-blue-400 bg-blue-400/10'
    case 'blocked': return 'text-red-400 bg-red-400/10'
    case 'failed': return 'text-red-400 bg-red-400/10'
    case 'queued': return 'text-gray-400 bg-gray-400/10'
    case 'dispatched': return 'text-purple-400 bg-purple-400/10'
    default: return 'text-gray-400 bg-gray-400/10'
  }
}

export function healthColor(score: number) {
  if (score >= 80) return '#10B981'
  if (score >= 60) return '#F59E0B'
  if (score >= 40) return '#EF4444'
  return '#7F1D1D'
}

export function sslDaysColor(days: number) {
  if (days > 30) return 'text-emerald-400'
  if (days > 14) return 'text-amber-400'
  return 'text-red-400'
}

export function formatDaysAgo(dateStr: string | null) {
  if (!dateStr) return 'never'
  const days = Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000)
  if (days === 0) return 'today'
  if (days === 1) return '1d ago'
  return `${days}d ago`
}

export function formatCountdown(deadlineStr: string | null) {
  if (!deadlineStr) return null
  const ms = new Date(deadlineStr).getTime() - Date.now()
  if (ms <= 0) return 'EXPIRED'
  const h = Math.floor(ms / 3600000)
  const m = Math.floor((ms % 3600000) / 60000)
  if (h > 24) return `${Math.floor(h / 24)}d ${h % 24}h`
  return `${h}h ${m}m`
}

export function daysUntil(dateStr: string | null) {
  if (!dateStr) return null
  return Math.ceil((new Date(dateStr).getTime() - Date.now()) / 86400000)
}

export function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`
}
