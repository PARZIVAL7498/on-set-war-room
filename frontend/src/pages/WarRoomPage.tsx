import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  Camera,
  Clapperboard,
  CloudRain,
  Crosshair,
  LoaderCircle,
  Radio,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  UserRound,
  Zap,
} from 'lucide-react'
import { BrandLogo } from '../components/BrandLogo'
import {
  fetchGeminiStatus,
  fetchIncident,
  fetchIncidents,
  fetchProductionHealth,
  fetchScenarios,
  runScenario,
  type Incident,
  type IncidentSummary,
  type ProductionHealth,
  type RiskLevel,
  type ScenarioInfo,
} from '../api'

const RISK_STYLES: Record<RiskLevel, string> = {
  LOW: 'text-primary border-primary/40 bg-primary/10',
  MEDIUM: 'text-amber border-amber/40 bg-amber/10',
  HIGH: 'text-accent border-accent/40 bg-accent/10',
  CRITICAL: 'text-accent border-accent bg-accent/20',
}

const SCENARIO_ICONS: Record<string, typeof Camera> = {
  camera_failure: Camera,
  actor_delay: UserRound,
  weather_issue: CloudRain,
  equipment_alias: Zap,
}

function formatTime(value?: string | null) {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return value
  }
}

export default function WarRoomPage() {
  const [health, setHealth] = useState<ProductionHealth | null>(null)
  const [incidents, setIncidents] = useState<IncidentSummary[]>([])
  const [active, setActive] = useState<Incident | null>(null)
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([])
  const [geminiOn, setGeminiOn] = useState(false)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null)
  const activeIdRef = useRef<string | undefined>(undefined)

  const load = useCallback(async (preferredId?: string) => {
    setError(null)
    try {
      const [h, list, sc, gem] = await Promise.all([
        fetchProductionHealth(),
        fetchIncidents(),
        fetchScenarios(),
        fetchGeminiStatus().catch(() => ({ available: false })),
      ])
      setHealth(h)
      setIncidents(list)
      setScenarios(sc)
      setGeminiOn(gem.available)
      setUpdatedAt(new Date())

      const targetId =
        preferredId ?? activeIdRef.current ?? list[0]?.incident_id
      if (targetId) {
        activeIdRef.current = targetId
        const detail = await fetchIncident(targetId)
        setActive(detail)
      } else {
        activeIdRef.current = undefined
        setActive(null)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
    const id = window.setInterval(() => void load(), 8000)
    return () => window.clearInterval(id)
  }, [load])

  async function triggerScenario(name: string) {
    setBusy(name)
    setError(null)
    try {
      const result = await runScenario(name)
      await load(result.incident?.incident_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(null)
    }
  }

  const productionName = health?.production?.name ?? 'On-Set War Room'
  const openCount = health?.open_incidents ?? incidents.filter((i) => i.status === 'open').length

  return (
    <div className="mx-auto max-w-[1200px] px-4 py-6 md:px-6 md:py-8">
      <header className="fade-in mb-8 flex flex-col gap-4 border-b border-border pb-6 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="mb-2 flex items-center gap-2 font-display text-xs uppercase tracking-[0.2em] text-muted-foreground">
            <Link
              to="/"
              className="inline-flex cursor-pointer items-center gap-1.5 transition duration-200 hover:text-secondary"
            >
              <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
              Landing
            </Link>
            <span aria-hidden>·</span>
            <Radio className="live-dot h-3.5 w-3.5 text-primary" aria-hidden />
            Live ops · Agentic cinema
          </p>
          <div className="mb-1 flex items-center gap-3">
            <BrandLogo to="/" size="md" showWordmark={false} decorative />
            <h1 className="font-display text-3xl font-semibold tracking-tight text-foreground md:text-4xl">
              On-Set War Room
            </h1>
          </div>
          <p className="mt-2 max-w-xl text-sm text-muted-foreground md:text-base">
            {productionName} — incident command when kit, cast, or locations go dark.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span
            className={`inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 font-display text-xs ${
              geminiOn
                ? 'border-primary/40 bg-primary/10 text-secondary'
                : 'border-border bg-muted text-muted-foreground'
            }`}
          >
            <Sparkles className="h-3.5 w-3.5" aria-hidden />
            {geminiOn ? 'Gemini narration on' : 'Deterministic narrative'}
          </span>
          <button
            type="button"
            onClick={() => void load(active?.incident_id)}
            className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-primary px-3 py-2 font-display text-sm font-semibold text-primary transition duration-200 hover:bg-primary/10"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} aria-hidden />
            Refresh
          </button>
        </div>
      </header>

      {error && (
        <div
          role="alert"
          className="fade-in mb-6 flex items-start gap-3 rounded-lg border border-accent/50 bg-accent/10 px-4 py-3 text-sm text-foreground"
        >
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-accent" aria-hidden />
          <span>{error}</span>
        </div>
      )}

      <section className="fade-in stagger-1 mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label="Production"
          value={productionName}
          hint={health?.production?.shoot_date ?? '—'}
          icon={Clapperboard}
        />
        <Stat
          label="Open incidents"
          value={String(openCount)}
          hint="Active investigations"
          icon={ShieldAlert}
          accent={openCount > 0}
        />
        <Stat
          label="Scheduled scenes"
          value={String(health?.scene_status_counts?.scheduled ?? '—')}
          hint={`Completed ${health?.scene_status_counts?.completed ?? 0}`}
          icon={Activity}
        />
        <Stat
          label="Last refresh"
          value={updatedAt ? updatedAt.toLocaleTimeString() : '—'}
          hint="Auto every 8s"
          icon={Radio}
        />
      </section>

      <section className="fade-in stagger-2 mb-6 panel p-4 md:p-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="font-display text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            Trigger simulator
          </h2>
        </div>
        <div className="flex flex-wrap gap-3">
          {scenarios.map((s) => {
            const Icon = SCENARIO_ICONS[s.name] ?? Zap
            const running = busy === s.name
            return (
              <button
                key={s.name}
                type="button"
                disabled={!!busy}
                onClick={() => void triggerScenario(s.name)}
                className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-accent px-4 py-2.5 font-display text-sm font-semibold text-white transition duration-200 hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
                title={s.description}
              >
                {running ? (
                  <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden />
                ) : (
                  <Icon className="h-4 w-4" aria-hidden />
                )}
                {s.name.replace(/_/g, ' ')}
              </button>
            )
          })}
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[1fr_1.4fr]">
        <aside className="fade-in stagger-3 space-y-4">
          <div className="panel p-4 md:p-5">
            <h2 className="mb-3 font-display text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              Incidents
            </h2>
            {loading && !incidents.length ? (
              <p className="text-sm text-muted-foreground">Loading…</p>
            ) : !incidents.length ? (
              <p className="text-sm text-muted-foreground">
                No incidents yet. Trigger a camera failure to start the demo.
              </p>
            ) : (
              <ul className="space-y-2">
                {incidents.map((inc) => (
                  <li key={inc.incident_id}>
                    <button
                      type="button"
                      onClick={() => {
                        activeIdRef.current = inc.incident_id
                        void fetchIncident(inc.incident_id).then(setActive)
                      }}
                      className={`w-full cursor-pointer rounded-lg border px-3 py-3 text-left transition duration-200 hover:border-primary/50 ${
                        active?.incident_id === inc.incident_id
                          ? 'border-primary/60 bg-muted'
                          : 'border-border bg-background/40'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-display text-sm font-medium">{inc.incident_id}</span>
                        <span
                          className={`rounded border px-2 py-0.5 font-display text-[10px] font-semibold uppercase ${RISK_STYLES[inc.risk_level]}`}
                        >
                          {inc.risk_level}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Scenes {inc.affected_scenes.join(', ') || '—'} · pivot{' '}
                        {inc.recommended_scene ?? '—'}
                      </p>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="panel p-4 md:p-5">
            <h2 className="mb-3 font-display text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              Recent events
            </h2>
            <ul className="space-y-2">
              {(health?.recent_events ?? []).slice(0, 5).map((ev) => (
                <li
                  key={ev.event_id}
                  className="rounded-lg border border-border bg-background/40 px-3 py-2 text-xs"
                >
                  <div className="flex justify-between gap-2 font-display">
                    <span>
                      {ev.resource_id}{' '}
                      <span
                        className={
                          ev.status === 'DOWN' ? 'text-accent' : 'text-secondary'
                        }
                      >
                        {ev.status}
                      </span>
                    </span>
                    <span className="text-muted-foreground">{formatTime(ev.event_time)}</span>
                  </div>
                  <p className="mt-1 text-muted-foreground line-clamp-2">{ev.notes}</p>
                </li>
              ))}
              {!health?.recent_events?.length && (
                <li className="text-sm text-muted-foreground">No events yet.</li>
              )}
            </ul>
          </div>
        </aside>

        <main className="fade-in stagger-4 space-y-4">
          {!active ? (
            <div className="panel flex min-h-[320px] items-center justify-center p-8 text-center text-muted-foreground">
              Select or trigger an incident to inspect the investigation.
            </div>
          ) : (
            <>
              <div className="panel p-4 md:p-6">
                <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-display text-xs uppercase tracking-wider text-muted-foreground">
                      Active incident
                    </p>
                    <h2 className="mt-1 font-display text-xl font-semibold">{active.incident_id}</h2>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Event {active.event_id} · {formatTime(active.created_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`rounded border px-3 py-1 font-display text-sm font-semibold uppercase ${RISK_STYLES[active.risk_level]}`}
                    >
                      {active.risk_level} · {active.risk_score}
                    </span>
                  </div>
                </div>

                <p className="text-sm leading-relaxed text-foreground/90">{active.narrative}</p>

                {active.risk_factors.length > 0 && (
                  <ul className="mt-4 flex flex-wrap gap-2">
                    {active.risk_factors.map((f) => (
                      <li
                        key={f}
                        className="rounded border border-border bg-muted px-2 py-1 text-xs text-muted-foreground"
                      >
                        {f}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="panel p-4 md:p-5">
                  <h3 className="mb-3 flex items-center gap-2 font-display text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                    <Crosshair className="h-4 w-4 text-accent" aria-hidden />
                    Affected scenes
                  </h3>
                  <ul className="space-y-2">
                    {(active.evidence?.affected_scenes ?? []).map((scene) => (
                      <li
                        key={scene.scene_number}
                        className="rounded-lg border border-accent/30 bg-accent/5 px-3 py-2"
                      >
                        <p className="font-display text-sm font-medium">
                          Scene {scene.scene_number} — {scene.title}
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {scene.location_id} · {formatTime(scene.scheduled_start)}
                        </p>
                      </li>
                    ))}
                    {!active.evidence?.affected_scenes?.length && (
                      <li className="text-sm text-muted-foreground">
                        Scenes {active.affected_scenes.join(', ')}
                      </li>
                    )}
                  </ul>
                </div>

                <div className="panel p-4 md:p-5">
                  <h3 className="mb-3 flex items-center gap-2 font-display text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                    <Zap className="h-4 w-4 text-primary" aria-hidden />
                    Recommended pivot
                  </h3>
                  {active.recommended_pivot ? (
                    <div className="rounded-lg border border-primary/40 bg-primary/10 px-3 py-3">
                      <p className="font-display text-lg font-semibold text-secondary">
                        Scene {active.recommended_pivot.scene_number}
                      </p>
                      <p className="mt-1 text-sm">{active.recommended_pivot.title}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {active.recommended_pivot.location_id}
                      </p>
                      <ul className="mt-3 space-y-1 text-xs text-muted-foreground">
                        {active.recommended_pivot.reasons.map((r) => (
                          <li key={r}>· {r}</li>
                        ))}
                      </ul>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">No valid pivot found.</p>
                  )}
                </div>
              </div>

              <div className="panel p-4 md:p-5">
                <h3 className="mb-4 font-display text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                  Investigation timeline
                </h3>
                <ol className="relative space-y-0 border-l border-border pl-5">
                  {active.timeline.map((step, idx) => (
                    <li key={`${step.step}-${idx}`} className="relative pb-5 last:pb-0">
                      <span className="absolute -left-[1.4rem] top-1 h-2.5 w-2.5 rounded-full bg-primary" />
                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <p className="font-display text-sm font-medium">
                          {step.agent} · {step.step}
                        </p>
                        {step.latency_ms != null && (
                          <span className="font-display text-[10px] text-muted-foreground">
                            {step.latency_ms} ms
                            {step.row_count != null ? ` · ${step.row_count} rows` : ''}
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">{step.summary}</p>
                      {step.tool && (
                        <p className="mt-1 font-display text-[10px] text-primary/80">{step.tool}</p>
                      )}
                    </li>
                  ))}
                </ol>
              </div>
            </>
          )}
        </main>
      </div>

      <footer className="mt-10 border-t border-border pt-4 text-center font-display text-[11px] text-muted-foreground">
        On-Set War Room · hybrid deterministic + optional Gemini narration · ClickHouse Cloud
      </footer>
    </div>
  )
}

function Stat({
  label,
  value,
  hint,
  icon: Icon,
  accent,
}: {
  label: string
  value: string
  hint: string
  icon: typeof Activity
  accent?: boolean
}) {
  return (
    <div className="panel p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-display text-[10px] uppercase tracking-wider text-muted-foreground">
          {label}
        </span>
        <Icon
          className={`h-4 w-4 ${accent ? 'text-accent' : 'text-primary'}`}
          aria-hidden
        />
      </div>
      <p className="font-display text-lg font-semibold leading-tight">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
    </div>
  )
}
