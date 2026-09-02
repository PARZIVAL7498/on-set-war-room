import type { IncidentSummary, RiskLevel } from '../../api'

export type IncidentGroup = {
  key: string
  resourceId: string
  resourceStatus: string
  riskLevel: RiskLevel
  affectedScenes: number[]
  count: number
  latest: IncidentSummary
  incidentIds: string[]
}

function scenesKey(scenes: number[]): string {
  return [...scenes].sort((a, b) => a - b).join(',')
}

export function groupIncidents(incidents: IncidentSummary[]): IncidentGroup[] {
  const map = new Map<string, IncidentGroup>()

  for (const inc of incidents) {
    const resourceId = (inc.resource_id || 'UNKNOWN').toUpperCase()
    const resourceStatus = (inc.resource_status || 'ISSUE').toUpperCase()
    const key = `${resourceId}|${resourceStatus}|${scenesKey(inc.affected_scenes ?? [])}`
    const existing = map.get(key)
    if (!existing) {
      map.set(key, {
        key,
        resourceId,
        resourceStatus,
        riskLevel: inc.risk_level,
        affectedScenes: [...(inc.affected_scenes ?? [])],
        count: 1,
        latest: inc,
        incidentIds: [inc.incident_id],
      })
      continue
    }
    existing.count += 1
    existing.incidentIds.push(inc.incident_id)
    const prev = new Date(existing.latest.created_at).getTime()
    const next = new Date(inc.created_at).getTime()
    if (next >= prev) {
      existing.latest = inc
      existing.riskLevel = inc.risk_level
    }
  }

  return [...map.values()].sort(
    (a, b) =>
      new Date(b.latest.created_at).getTime() - new Date(a.latest.created_at).getTime(),
  )
}

export function formatShortTime(value?: string | null): string {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return value
  }
}

export function formatDuration(from?: string | null, now = Date.now()): string {
  if (!from) return '—'
  const start = new Date(from).getTime()
  if (Number.isNaN(start)) return '—'
  const sec = Math.max(0, Math.floor((now - start) / 1000))
  if (sec < 60) return `${sec}s`
  const min = Math.floor(sec / 60)
  const rem = sec % 60
  if (min < 60) return `${min}m ${rem.toString().padStart(2, '0')}s`
  const hr = Math.floor(min / 60)
  return `${hr}h ${min % 60}m`
}

export const RISK_BADGE: Record<RiskLevel, string> = {
  LOW: 'text-primary border-primary/40 bg-primary/10',
  MEDIUM: 'text-amber border-amber/40 bg-amber/10',
  HIGH: 'text-accent border-accent/40 bg-accent/10',
  CRITICAL: 'text-accent border-accent/50 bg-accent/15',
}

export const RISK_DOT: Record<RiskLevel, string> = {
  LOW: 'bg-primary',
  MEDIUM: 'bg-amber',
  HIGH: 'bg-accent',
  CRITICAL: 'bg-accent shadow-[0_0_8px_rgba(225,29,72,0.7)]',
}

export const RISK_GLOW: Record<RiskLevel, string> = {
  LOW: 'border-primary/50 bg-primary/5 shadow-[0_0_20px_rgba(34,197,94,0.12)]',
  MEDIUM: 'border-amber/50 bg-amber/5 shadow-[0_0_20px_rgba(245,158,11,0.12)]',
  HIGH: 'border-accent/50 bg-accent/5 shadow-[0_0_24px_rgba(225,29,72,0.18)]',
  CRITICAL: 'border-accent/60 bg-accent/[0.07] shadow-[0_0_28px_rgba(225,29,72,0.22)]',
}
