import { useEffect, useMemo, useState } from 'react'
import type { TimelineStep } from '../../api'
import { formatShortTime } from './groupIncidents'

const AGENT_ORDER = [
  'monitor_agent',
  'investigator_agent',
  'impact_agent',
  'narrator_agent',
] as const

const SHORT_LABEL: Record<string, string> = {
  monitor: 'Detected',
  investigator: 'Investigating',
  impact: 'Impact',
  narrator: 'Pivot eval',
  war_room: 'Pipeline',
}

type Props = {
  timeline: TimelineStep[]
  reduced?: boolean
  highlightKey?: string | null
}

function isToolSpam(step: TimelineStep): boolean {
  return (
    step.agent.includes('adk_tools') ||
    step.step.startsWith('tool:') ||
    step.step.includes('adk_sequential')
  )
}

function isAgentStep(step: TimelineStep): boolean {
  if (isToolSpam(step)) return false
  const agent = step.agent.toLowerCase()
  return (
    AGENT_ORDER.some((a) => agent.includes(a.replace('_agent', '')) || agent === a) ||
    ['monitor', 'investigator', 'impact', 'narrator', 'war_room'].some((k) =>
      agent.includes(k),
    )
  )
}

function shortVerb(step: TimelineStep): string {
  const agent = step.agent.toLowerCase()
  for (const [key, label] of Object.entries(SHORT_LABEL)) {
    if (agent.includes(key)) return label
  }
  const summary = step.summary?.trim()
  if (summary) {
    const first = summary.split(/[.—]/)[0]?.trim()
    if (first && first.length < 28) return first
  }
  return step.step.replace(/_/g, ' ').slice(0, 22)
}

function pickAgentNodes(timeline: TimelineStep[]): TimelineStep[] {
  const agents = timeline.filter(isAgentStep)
  const preferred: TimelineStep[] = []
  const seen = new Set<string>()

  for (const name of AGENT_ORDER) {
    const hit = [...agents]
      .reverse()
      .find(
        (s) =>
          s.agent.toLowerCase().includes(name.replace('_agent', '')) || s.agent === name,
      )
    if (hit && !seen.has(hit.agent + hit.step + (hit.summary ?? ''))) {
      preferred.push(hit)
      seen.add(hit.agent + hit.step + (hit.summary ?? ''))
    }
  }

  if (preferred.length >= 2) return preferred

  const dedup: TimelineStep[] = []
  for (const step of agents) {
    const key = `${step.agent}|${step.step}|${step.summary}`
    if (seen.has(key)) continue
    seen.add(key)
    dedup.push(step)
  }
  return dedup.slice(0, 6)
}

export function InvestigationTimeline({ timeline, reduced, highlightKey }: Props) {
  const [showTools, setShowTools] = useState(false)
  const [selected, setSelected] = useState<number | null>(null)

  const nodes = useMemo(() => {
    const agentNodes = pickAgentNodes(timeline)
    if (showTools) {
      const tools = timeline.filter(isToolSpam).slice(-6)
      return [...agentNodes, ...tools]
    }
    return agentNodes
  }, [timeline, showTools])

  useEffect(() => {
    setSelected(nodes.length ? nodes.length - 1 : null)
  }, [timeline, nodes.length])

  const toolCount = timeline.filter(isToolSpam).length
  const active = selected != null ? nodes[selected] : null

  return (
    <section id="wr-timeline" className="panel p-4 md:p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h3 className="font-display text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
          Investigation timeline
        </h3>
        {toolCount > 0 ? (
          <button
            type="button"
            onClick={() => setShowTools((v) => !v)}
            className="cursor-pointer font-display text-[10px] uppercase tracking-[0.16em] text-muted-foreground transition hover:text-foreground"
          >
            {showTools ? 'Hide tool trace' : `Show tool trace (${toolCount})`}
          </button>
        ) : null}
      </div>

      {!nodes.length ? (
        <p className="text-sm text-muted-foreground">No investigation steps yet.</p>
      ) : (
        <>
          <div className="relative overflow-x-auto pb-1">
            <div className="relative mx-auto flex min-w-[560px] max-w-5xl items-start justify-between px-3 pt-2">
              <div
                aria-hidden
                className="absolute left-8 right-8 top-[1.35rem] h-px bg-border"
              />
              {nodes.map((step, idx) => {
                const isLatest = idx === nodes.length - 1
                const isSel = selected === idx
                const key = `${step.agent}-${step.step}-${idx}`
                const glow = highlightKey === key || (isLatest && !highlightKey)
                const time =
                  formatShortTime(step.timestamp) !== '—'
                    ? formatShortTime(step.timestamp)
                    : `T+${idx}`
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setSelected(idx)}
                    className="relative z-10 flex w-24 cursor-pointer flex-col items-center gap-1.5 text-center sm:w-28"
                  >
                    <span
                      className={`h-3 w-3 border-2 ${
                        isSel || isLatest || glow
                          ? 'border-signal bg-signal'
                          : 'border-white/30 bg-void'
                      } ${!reduced && (isSel || isLatest) ? 'wr-node-flash' : ''}`}
                    />
                    <span
                      className={`font-display text-[10px] font-medium leading-tight ${
                        isSel || isLatest ? 'text-accent' : 'text-foreground'
                      }`}
                    >
                      {time} {shortVerb(step)}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>

          {active ? (
            <div className="mt-4 rounded-lg border border-border bg-background/40 px-4 py-3">
              <p className="font-display text-sm font-medium">
                {active.agent} · {active.step}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">{active.summary}</p>
            </div>
          ) : null}
        </>
      )}
    </section>
  )
}
