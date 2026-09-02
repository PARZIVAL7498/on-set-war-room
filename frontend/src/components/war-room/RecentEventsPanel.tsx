import type { ProductionHealth } from '../../api'
import { formatShortTime } from './groupIncidents'

type Props = {
  events: ProductionHealth['recent_events']
}

export function RecentEventsPanel({ events }: Props) {
  const rows = (events ?? []).slice(0, 5)

  return (
    <section className="panel flex h-full flex-col p-4 md:p-5">
      <h3 className="mb-3 font-display text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
        Recent events
      </h3>
      <ul className="space-y-2">
        {rows.map((ev) => (
          <li
            key={ev.event_id}
            className="flex items-start justify-between gap-2 border-b border-border/60 pb-2 last:border-0 last:pb-0"
          >
            <div className="min-w-0">
              <p className="font-display text-xs font-medium">
                {ev.resource_id}{' '}
                <span
                  className={
                    ev.status === 'DOWN' ? 'text-accent' : 'text-primary'
                  }
                >
                  {ev.status}
                </span>
              </p>
              <p className="mt-0.5 line-clamp-1 text-[10px] text-muted-foreground">
                {ev.notes || ev.resource_type}
              </p>
            </div>
            <span className="shrink-0 font-display text-[10px] text-muted-foreground">
              {formatShortTime(ev.event_time)}
            </span>
          </li>
        ))}
        {!rows.length && (
          <li className="text-sm text-muted-foreground">No recent events.</li>
        )}
      </ul>
    </section>
  )
}
