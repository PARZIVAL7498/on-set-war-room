import { useMemo } from 'react'
import type { TimelineStep } from '../../api'

type AgentSlot = {
  id: string
  label: string
  match: string[]
  idle: string
  active: string
  dot: string
  pill: string
}

const SLOTS: AgentSlot[] = [
  {
    id: 'monitor',
    label: 'monitor_agent',
    match: ['monitor'],
    idle: 'Watching',
    active: 'Watching',
    dot: 'bg-primary',
    pill: 'border-primary/40 bg-primary/10 text-primary',
  },
  {
    id: 'investigator',
    label: 'investigator_agent',
    match: ['investigator'],
    idle: 'Ready',
    active: 'Investigating',
    dot: 'bg-sky-400',
    pill: 'border-sky-400/40 bg-sky-400/10 text-sky-400',
  },
  {
    id: 'impact',
    label: 'impact_agent',
    match: ['impact'],
    idle: 'Ready',
    active: 'Calculating',
    dot: 'bg-amber',
    pill: 'border-amber/40 bg-amber/10 text-amber',
  },
  {
    id: 'recommender',
    label: 'recommender_agent',
    match: ['narrator', 'pivot', 'recommend'],
    idle: 'Ready',
    active: 'Evaluating',
    dot: 'bg-emerald',
    pill: 'border-emerald/40 bg-emerald/10 text-emerald',
  },
]

function statusFor(
  slot: AgentSlot,
  timeline: TimelineStep[],
): { label: string; hot: boolean } {
  const hits = timeline.filter((t) =>
    slot.match.some(
      (m) => t.agent.toLowerCase().includes(m) || t.step.toLowerCase().includes(m),
    ),
  )
  if (!hits.length) return { label: slot.idle, hot: false }
  const last = hits[hits.length - 1]
  const done =
    /complete|done|scored|pivot|narrat/i.test(last.summary) ||
    /complete|done/i.test(last.status)
  if (slot.id === 'recommender') {
    const hasPivot = timeline.some(
      (t) =>
        /pivot|recommend|narrator/i.test(t.agent) || /pivot|recommend/i.test(t.step),
    )
    return hasPivot
      ? { label: done ? 'Done' : 'Evaluating', hot: !done }
      : { label: slot.idle, hot: false }
  }
  if (done) return { label: 'Done', hot: false }
  return { label: slot.active, hot: true }
}

type Props = {
  timeline: TimelineStep[]
}

export function AiOpsBar({ timeline }: Props) {
  const states = useMemo(
    () => SLOTS.map((slot) => ({ slot, ...statusFor(slot, timeline) })),
    [timeline],
  )

  return (
    <section className="panel flex h-full flex-col p-4 md:p-5">
      <h3 className="mb-3 font-display text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
        AI operations
      </h3>
      <ul className="space-y-2">
        {states.map(({ slot, label, hot }) => (
          <li
            key={slot.id}
            className="flex items-center justify-between gap-2 rounded-lg border border-border/70 bg-background/30 px-3 py-2"
          >
            <div className="flex min-w-0 items-center gap-2.5">
              <span
                className={`h-2 w-2 shrink-0 rounded-full ${slot.dot} ${hot ? 'live-dot' : ''}`}
                aria-hidden
              />
              <span className="truncate font-display text-xs text-foreground">
                {slot.label}
              </span>
            </div>
            <span
              className={`shrink-0 rounded-full border px-2 py-0.5 font-display text-[10px] font-medium ${slot.pill}`}
            >
              {label}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
