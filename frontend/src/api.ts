export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export interface IncidentSummary {
  incident_id: string
  production_id: string
  event_id: string
  status: string
  risk_level: RiskLevel
  risk_score: number
  affected_scenes: number[]
  recommended_scene: number | null
  created_at: string
  title?: string
  resource_id?: string | null
  resource_status?: string | null
}

export interface TimelineStep {
  step: string
  agent: string
  status: string
  summary: string
  tool?: string | null
  latency_ms?: number | null
  row_count?: number | null
  timestamp?: string | null
}

export interface PivotRecommendation {
  scene_number: number
  title: string
  location_id: string
  scheduled_start?: string | null
  reasons: string[]
  rank_score: number
}

export interface SceneSummary {
  scene_number: number
  title: string
  location_id: string
  scheduled_start: string
  scheduled_end: string
  status: string
  requirements: Array<{
    requirement_type: string
    requirement_id: string
    requirement_name: string
  }>
}

export interface Incident {
  incident_id: string
  production_id: string
  event_id: string
  status: string
  risk_level: RiskLevel
  risk_score: number
  risk_factors: string[]
  affected_scenes: number[]
  evidence?: {
    resource_type: string
    resource_id: string
    status: string
    notes: string
    affected_scenes: SceneSummary[]
  } | null
  recommended_pivot: PivotRecommendation | null
  narrative: string
  timeline: TimelineStep[]
  created_at: string
  gemini_used: boolean
  title?: string
}

/** Display name for list/detail — never show raw incident_id as the headline. */
export function incidentDisplayName(
  inc: Pick<
    IncidentSummary,
    'title' | 'incident_id' | 'affected_scenes' | 'resource_id' | 'resource_status'
  > & {
    evidence?: Incident['evidence']
  },
): string {
  if (inc.title?.trim()) return inc.title.trim()
  const rid = inc.evidence?.resource_id || inc.resource_id
  const status = inc.evidence?.status || inc.resource_status
  if (rid) {
    const verb = (status || 'ISSUE').toLowerCase()
    const scenes = inc.affected_scenes?.length
      ? ` — Scenes ${inc.affected_scenes.join(', ')}`
      : ''
    return `${rid} ${verb}${scenes}`
  }
  return 'Untitled incident'
}

export interface ProductionHealth {
  production: {
    production_id: string
    name: string
    shoot_date: string
  } | null
  scene_status_counts: Record<string, number>
  open_incidents: number
  recent_events: Array<{
    event_id: string
    resource_type: string
    resource_id: string
    status: string
    event_time: string
    notes: string
  }>
}

export interface ScenarioInfo {
  name: string
  description: string
  resource_type?: string
  resource_id?: string
  status?: string
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const base = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, '') ?? ''
  const url = path.startsWith('http') ? path : `${base}${path}`
  const res = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export const fetchIncidents = () =>
  api<IncidentSummary[]>('/api/incidents?production_id=prod-midnight-protocol')

export const fetchIncident = (id: string) => api<Incident>(`/api/incidents/${id}`)

export const fetchProductionHealth = () =>
  api<ProductionHealth>('/api/production/health?production_id=prod-midnight-protocol')

export const fetchScenarios = () => api<ScenarioInfo[]>('/api/simulate/scenarios')

export const runScenario = (name: string) =>
  api<{ scenario: string; event_id: string; incident: Incident | null }>(
    `/api/simulate/${name}`,
    { method: 'POST' },
  )

export const fetchGeminiStatus = () =>
  api<{ available: boolean; live_llm?: boolean; mode?: string }>(
    '/api/agent/adk-status',
  )
