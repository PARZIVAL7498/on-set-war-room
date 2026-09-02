type Props = {
  totalIncidents: number
  criticalCount: number
  affectedScenes: number
  nextPivot: string
  reduced?: boolean
}

/** Compact single-row KPI strip — OpenDesign dashboard pattern */
export function KpiStrip({
  totalIncidents,
  criticalCount,
  affectedScenes,
  nextPivot,
}: Props) {
  const items = [
    {
      key: 'incidents',
      label: 'Incidents',
      value: String(totalIncidents),
      tone: 'text-foreground',
    },
    {
      key: 'critical',
      label: 'Critical',
      value: String(criticalCount),
      tone: 'text-signal',
    },
    {
      key: 'scenes',
      label: 'Affected scenes',
      value: String(affectedScenes),
      tone: 'text-foreground',
    },
    {
      key: 'pivot',
      label: 'Next pivot',
      value: nextPivot,
      tone: 'text-primary',
    },
  ] as const

  return (
    <div className="grid overflow-hidden border border-border bg-card sm:grid-cols-2 lg:grid-cols-4">
      {items.map((item, i) => (
        <div
          key={item.key}
          className={`flex min-w-0 flex-col gap-1.5 px-4 py-3.5 ${
            i < items.length - 1
              ? 'border-b border-border sm:border-b-0 sm:border-r'
              : ''
          } ${i === 1 ? 'sm:border-r-0 lg:border-r' : ''} ${
            i === 2 ? 'border-b sm:border-b-0' : ''
          }`}
        >
          <span className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
            {item.label}
          </span>
          <p
            className={`font-display text-xl font-bold leading-none tracking-tight md:text-2xl ${item.tone}`}
          >
            {item.value}
          </p>
        </div>
      ))}
    </div>
  )
}
