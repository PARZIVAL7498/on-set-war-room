import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  AlertTriangle,
  Camera,
  ChevronDown,
  CloudRain,
  LoaderCircle,
  Radio,
  RefreshCw,
  UserRound,
  Zap,
} from 'lucide-react'
import { BrandLogo } from '../components/BrandLogo'
import { ActiveIncidentHero } from '../components/war-room/ActiveIncidentHero'
import { AffectedScenesPanel } from '../components/war-room/AffectedScenesPanel'
import { AiOpsBar } from '../components/war-room/AiOpsBar'
import { IncidentDrawer } from '../components/war-room/IncidentDrawer'
import { InvestigationTimeline } from '../components/war-room/InvestigationTimeline'
import { KpiStrip } from '../components/war-room/KpiStrip'
import { RecentEventsPanel } from '../components/war-room/RecentEventsPanel'
import { RecommendedPivotCard } from '../components/war-room/RecommendedPivotCard'
import { WarRoomSidebar } from '../components/war-room/WarRoomSidebar'
import { usePrefersReducedMotion } from '../motion/usePrefersReducedMotion'
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
  type ScenarioInfo,
} from '../api'

const SCENARIO_ICONS: Record<string, typeof Camera> = {
  camera_failure: Camera,
  actor_delay: UserRound,
  weather_issue: CloudRain,
  equipment_alias: Zap,
}

export default function WarRoomPage() {
  const reduced = usePrefersReducedMotion()
  const [health, setHealth] = useState<ProductionHealth | null>(null)
  const [incidents, setIncidents] = useState<IncidentSummary[]>([])
  const [active, setActive] = useState<Incident | null>(null)
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([])
  const [geminiOn, setGeminiOn] = useState(false)
  const [adkMode, setAdkMode] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [simOpen, setSimOpen] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [timelineFlash, setTimelineFlash] = useState<string | null>(null)
  const activeIdRef = useRef<string | undefined>(undefined)
  const prevTimelineLen = useRef(0)
  const simRef = useRef<HTMLDivElement>(null)

  const load = useCallback(async (preferredId?: string) => {
    setError(null)
    try {
      const [h, list, sc, gem] = await Promise.all([
        fetchProductionHealth(),
        fetchIncidents(),
        fetchScenarios(),
        fetchGeminiStatus().catch(() => ({
          available: false as boolean,
          live_llm: false,
          mode: '',
        })),
      ])
      setHealth(h)
      setIncidents(list)
      setScenarios(sc)
      setGeminiOn(gem.available)
      setAdkMode(gem.live_llm ? 'live' : gem.mode || (gem.available ? 'tools' : ''))

      const targetId = preferredId ?? activeIdRef.current ?? list[0]?.incident_id
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

  useEffect(() => {
    const len = active?.timeline?.length ?? 0
    if (len > prevTimelineLen.current && len > 0) {
      const last = active!.timeline[len - 1]
      const key = `${last.agent}-${last.step}-${len - 1}`
      setTimelineFlash(key)
      const t = window.setTimeout(() => setTimelineFlash(null), 1000)
      prevTimelineLen.current = len
      return () => window.clearTimeout(t)
    }
    prevTimelineLen.current = len
  }, [active?.timeline, active?.incident_id])

  useEffect(() => {
    if (!simOpen) return
    const onDoc = (e: MouseEvent) => {
      if (!simRef.current?.contains(e.target as Node)) setSimOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [simOpen])

  async function selectIncident(id: string) {
    activeIdRef.current = id
    setError(null)
    try {
      const detail = await fetchIncident(id)
      setActive(detail)
      prevTimelineLen.current = detail.timeline?.length ?? 0
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  async function triggerScenario(name: string) {
    setBusy(name)
    setSimOpen(false)
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

  const productionName = health?.production?.name ?? 'Midnight Protocol'
  const criticalCount = useMemo(
    () =>
      incidents.filter((i) => i.risk_level === 'CRITICAL' || i.risk_level === 'HIGH')
        .length,
    [incidents],
  )
  const hasCritical = useMemo(
    () =>
      !!active &&
      (active.risk_level === 'CRITICAL' || active.risk_level === 'HIGH'),
    [active],
  )
  const affectedScenes = active?.affected_scenes?.length ?? 0
  const nextPivot = active?.recommended_pivot
    ? `Scene ${active.recommended_pivot.scene_number}`
    : '—'

  function scrollTo(id: string) {
    document
      .getElementById(id)
      ?.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' })
  }

  return (
    <div className="flex min-h-svh bg-void">
      <WarRoomSidebar
        critical={hasCritical}
        onIncidents={() => setDrawerOpen(true)}
        onTimeline={() => scrollTo('wr-timeline')}
        onSimulate={() => setSimOpen(true)}
      />

      <IncidentDrawer
        open={drawerOpen}
        incidents={incidents}
        activeId={active?.incident_id}
        loading={loading}
        reduced={reduced}
        onClose={() => setDrawerOpen(false)}
        onSelect={(id) => void selectIncident(id)}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <div className="mx-auto w-full max-w-[1600px] flex-1 px-4 py-4 md:px-6 md:py-5">
          <header className="mb-4 flex flex-col gap-3 border-b border-border pb-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex min-w-0 items-center gap-3">
              <BrandLogo to="/" size="sm" showWordmark={false} decorative />
              <div>
                <h1 className="font-display text-lg font-bold uppercase tracking-wide text-foreground md:text-xl">
                  On-Set War Room
                </h1>
                <p className="font-mono text-[11px] uppercase text-muted-foreground">
                  {productionName}
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <span
                className="inline-flex items-center gap-2 border border-primary/40 bg-primary/10 px-3 py-1.5 font-mono text-[11px] font-semibold uppercase text-primary"
                title={geminiOn ? `ADK ${adkMode || 'ready'}` : 'ADK unavailable'}
              >
                <span className="live-dot h-2 w-2 bg-primary" aria-hidden />
                Live
              </span>

              <div className="relative" ref={simRef}>
                <button
                  type="button"
                  onClick={() => setSimOpen((v) => !v)}
                  disabled={!!busy}
                  className="inline-flex min-h-10 cursor-pointer items-center gap-1.5 border border-border bg-card px-3 py-2 font-display text-xs font-bold text-foreground transition hover:border-white/25 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {busy ? (
                    <LoaderCircle className="h-3.5 w-3.5 animate-spin" aria-hidden />
                  ) : (
                    <Zap className="h-3.5 w-3.5 text-accent" aria-hidden />
                  )}
                  Simulate
                  <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
                </button>
                {simOpen ? (
                  <div className="absolute right-0 z-40 mt-2 w-56 overflow-hidden border border-border bg-card shadow-xl">
                    {scenarios.length ? (
                      scenarios.map((s) => {
                        const Icon = SCENARIO_ICONS[s.name] ?? Zap
                        return (
                          <button
                            key={s.name}
                            type="button"
                            disabled={!!busy}
                            onClick={() => void triggerScenario(s.name)}
                            className="flex w-full cursor-pointer items-center gap-2 px-3 py-2.5 text-left text-sm transition hover:bg-muted disabled:opacity-50"
                            title={s.description}
                          >
                            <Icon className="h-4 w-4 text-muted-foreground" aria-hidden />
                            <span className="font-display capitalize">
                              {s.name.replace(/_/g, ' ')}
                            </span>
                          </button>
                        )
                      })
                    ) : (
                      <p className="px-3 py-3 text-xs text-muted-foreground">
                        No scenarios available from the API. Redeploy so{' '}
                        <code className="text-foreground">app/data/scenarios</code> ships
                        with the backend.
                      </p>
                    )}
                  </div>
                ) : null}
              </div>

              <button
                type="button"
                onClick={() => void load(active?.incident_id)}
                className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-border bg-muted/60 px-3 py-2 font-display text-xs font-semibold text-foreground transition hover:border-primary/40 hover:text-primary"
              >
                <RefreshCw
                  className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`}
                  aria-hidden
                />
                Refresh
              </button>
            </div>
          </header>

          {error ? (
            <div
              role="alert"
              className="mb-4 flex items-start gap-3 rounded-xl border border-accent/40 bg-accent/10 px-4 py-3 text-sm"
            >
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-accent" aria-hidden />
              <span>{error}</span>
            </div>
          ) : null}

          <div className="mb-4">
            <KpiStrip
              totalIncidents={incidents.length}
              criticalCount={criticalCount}
              affectedScenes={affectedScenes}
              nextPivot={nextPivot}
              reduced={reduced}
            />
          </div>

          <div className="mb-4 grid gap-4 lg:grid-cols-[minmax(0,1.7fr)_minmax(260px,0.9fr)]">
            <ActiveIncidentHero
              incident={active}
              reduced={reduced}
              onInvestigate={() => scrollTo('wr-timeline')}
              onPivot={() => scrollTo('wr-pivot')}
            />
            <RecommendedPivotCard pivot={active?.recommended_pivot} />
          </div>

          <div className="mb-4">
            <InvestigationTimeline
              timeline={active?.timeline ?? []}
              reduced={reduced}
              highlightKey={timelineFlash}
            />
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <AffectedScenesPanel incident={active} />
            <AiOpsBar timeline={active?.timeline ?? []} />
            <RecentEventsPanel events={health?.recent_events ?? []} />
          </div>

          <footer className="mt-6 flex items-center justify-center gap-2 border-t border-border pt-4 font-display text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            <Radio className="h-3 w-3 text-primary" aria-hidden />
            On-Set War Room · collapsed sidebar command layout
          </footer>
        </div>
      </div>
    </div>
  )
}
