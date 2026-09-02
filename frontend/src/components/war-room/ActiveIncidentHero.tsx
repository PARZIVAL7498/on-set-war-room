import { Crosshair, Zap } from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'
import type { Incident } from '../../api'
import { RISK_BADGE, formatDuration, formatShortTime } from './groupIncidents'

type Props = {
  incident: Incident | null
  reduced?: boolean
  onInvestigate: () => void
  onPivot: () => void
}

function headline(inc: Incident): string {
  const rid = (inc.evidence?.resource_id || inc.title || 'INCIDENT').toUpperCase()
  const status = (inc.evidence?.status || 'ISSUE').toUpperCase()
  if (inc.evidence?.resource_id) return `${rid} ${status}`
  if (inc.title?.trim()) return inc.title.trim()
  return `${rid} ${status}`
}

function cleanNarrative(raw: string, fallback?: string | null): string {
  const text = (raw || fallback || 'Investigation in progress.').trim()
  return text.replace(/^\[Live ADK LLM unavailable:[^\]]*\]\s*/i, '').trim() || text
}

/** Active incident panel — OpenDesign ops console pattern (no glow / schematic) */
export function ActiveIncidentHero({
  incident,
  reduced,
  onInvestigate,
  onPivot,
}: Props) {
  return (
    <AnimatePresence mode="wait">
      {!incident ? (
        <motion.div
          key="empty"
          initial={reduced ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="flex min-h-[220px] items-center justify-center border border-border bg-card p-8 text-center text-muted-foreground"
        >
          Open incidents from the sidebar to inspect an investigation.
        </motion.div>
      ) : (
        <motion.section
          key={incident.incident_id}
          initial={reduced ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={reduced ? undefined : { opacity: 0 }}
          transition={{ duration: 0.28 }}
          className="border border-border bg-card"
        >
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3 md:px-5">
            <div>
              <h2 className="font-display text-sm font-bold uppercase tracking-wide">
                Active incident
              </h2>
              <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">
                {formatShortTime(incident.created_at)} · {formatDuration(incident.created_at)}
              </p>
            </div>
            <span
              className={`border px-2.5 py-1 font-mono text-[10px] font-semibold uppercase tracking-wider ${RISK_BADGE[incident.risk_level]}`}
            >
              {incident.risk_level}
              {typeof incident.risk_score === 'number' ? ` · ${incident.risk_score}` : ''}
            </span>
          </div>

          <div className="grid gap-5 p-4 md:grid-cols-[1fr_auto] md:p-5">
            <div className="min-w-0">
              <p className="font-mono text-[11px] uppercase text-signal">
                {incident.incident_id}
              </p>
              <h3 className="mt-2 font-display text-[clamp(1.75rem,3vw,2.75rem)] font-extrabold leading-[0.98] tracking-tight uppercase">
                {headline(incident)}
              </h3>
              <p className="mt-2 font-mono text-[11px] text-muted-foreground">
                Scenes{' '}
                {incident.affected_scenes.length
                  ? incident.affected_scenes.join(' · ')
                  : '—'}
              </p>
              <p className="mt-4 max-w-prose text-sm leading-relaxed text-zinc-400">
                {cleanNarrative(incident.narrative, incident.evidence?.notes)}
              </p>
              <div className="mt-5 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={onInvestigate}
                  className="inline-flex min-h-11 cursor-pointer items-center gap-2 bg-signal px-4 py-2.5 font-display text-sm font-bold text-white transition hover:bg-[#be123c]"
                >
                  <Crosshair className="h-4 w-4" aria-hidden />
                  Investigate
                </button>
                <button
                  type="button"
                  onClick={onPivot}
                  className="inline-flex min-h-11 cursor-pointer items-center gap-2 border border-border bg-transparent px-4 py-2.5 font-display text-sm font-bold transition hover:border-primary/50 hover:text-primary"
                >
                  <Zap className="h-4 w-4" aria-hidden />
                  Pivot options
                </button>
              </div>
            </div>

            {typeof incident.risk_score === 'number' ? (
              <aside className="w-full border border-signal/50 bg-signal/10 p-4 md:w-40">
                <p className="font-mono text-[10px] uppercase text-muted-foreground">
                  Risk score
                </p>
                <p className="mt-2 font-display text-4xl font-extrabold leading-none text-signal">
                  {incident.risk_score}
                </p>
                <div className="mt-3 h-1.5 overflow-hidden border border-signal/30 bg-void">
                  <div
                    className="h-full bg-signal"
                    style={{ width: `${Math.min(100, Math.max(0, incident.risk_score))}%` }}
                  />
                </div>
              </aside>
            ) : null}
          </div>
        </motion.section>
      )}
    </AnimatePresence>
  )
}
