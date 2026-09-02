import { useMemo, useState } from 'react'
import { Filter, LoaderCircle } from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'
import type { IncidentSummary } from '../../api'
import {
  RISK_BADGE,
  RISK_DOT,
  RISK_GLOW,
  formatShortTime,
  groupIncidents,
  type IncidentGroup,
} from './groupIncidents'

const VISIBLE = 6

type Props = {
  incidents: IncidentSummary[]
  activeId?: string
  loading?: boolean
  reduced?: boolean
  onSelect: (incidentId: string) => void
}

export function IncidentRail({
  incidents,
  activeId,
  loading,
  reduced,
  onSelect,
}: Props) {
  const [expanded, setExpanded] = useState(false)
  const groups = useMemo(() => groupIncidents(incidents), [incidents])
  const visible = expanded ? groups : groups.slice(0, VISIBLE)
  const hidden = Math.max(0, groups.length - VISIBLE)

  return (
    <aside className="panel flex h-full min-h-[320px] flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
          Incidents{' '}
          <span className="text-foreground/70">{groups.length}</span>
        </h2>
        <Filter className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto p-3">
        {loading && !incidents.length ? (
          <p className="flex items-center gap-2 px-1 py-6 text-sm text-muted-foreground">
            <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden />
            Loading…
          </p>
        ) : !groups.length ? (
          <p className="px-1 py-6 text-sm text-muted-foreground">
            No incidents yet. Run a simulation to start.
          </p>
        ) : (
          <AnimatePresence initial={false}>
            {visible.map((group) => (
              <IncidentRow
                key={group.key}
                group={group}
                selected={group.incidentIds.includes(activeId ?? '')}
                reduced={reduced}
                onSelect={() => onSelect(group.latest.incident_id)}
              />
            ))}
          </AnimatePresence>
        )}
      </div>

      {hidden > 0 && !expanded ? (
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="cursor-pointer border-t border-border px-4 py-2.5 text-left font-display text-xs text-muted-foreground transition hover:text-foreground"
        >
          + {hidden} more incidents
        </button>
      ) : null}
      {expanded && groups.length > VISIBLE ? (
        <button
          type="button"
          onClick={() => setExpanded(false)}
          className="cursor-pointer border-t border-border px-4 py-2.5 text-left font-display text-xs text-muted-foreground transition hover:text-foreground"
        >
          Show less
        </button>
      ) : null}
    </aside>
  )
}

function IncidentRow({
  group,
  selected,
  reduced,
  onSelect,
}: {
  group: IncidentGroup
  selected: boolean
  reduced?: boolean
  onSelect: () => void
}) {
  return (
    <motion.button
      type="button"
      layout={!reduced}
      initial={reduced ? false : { opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={reduced ? undefined : { opacity: 0, height: 0 }}
      transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
      onClick={onSelect}
      className={`w-full cursor-pointer rounded-xl border px-3 py-2.5 text-left transition duration-200 hover:-translate-y-px ${
        selected
          ? RISK_GLOW[group.riskLevel]
          : 'border-border bg-background/30 hover:border-white/20'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <span
            className={`mt-1 h-2 w-2 shrink-0 rounded-full ${RISK_DOT[group.riskLevel]}`}
            aria-hidden
          />
          <div className="min-w-0">
            <p className="truncate font-display text-sm font-semibold tracking-tight">
              {group.resourceId}
              {group.count > 1 ? (
                <span className="ml-1.5 text-[10px] font-medium text-muted-foreground">
                  ×{group.count}
                </span>
              ) : null}
            </p>
            <p className="mt-0.5 text-[11px] text-muted-foreground">
              <span
                className={
                  group.resourceStatus === 'DOWN' ? 'text-accent' : 'text-foreground/80'
                }
              >
                {group.resourceStatus}
              </span>
              {group.affectedScenes.length
                ? ` · Scene ${group.affectedScenes.join(', ')}`
                : ''}
            </p>
          </div>
        </div>
        <span className="shrink-0 font-display text-[10px] text-muted-foreground">
          {formatShortTime(group.latest.created_at)}
        </span>
      </div>
      <div className="mt-2 flex justify-end">
        <span
          className={`rounded border px-1.5 py-0.5 font-display text-[9px] font-semibold uppercase tracking-wider ${RISK_BADGE[group.riskLevel]}`}
        >
          {group.riskLevel}
        </span>
      </div>
    </motion.button>
  )
}
