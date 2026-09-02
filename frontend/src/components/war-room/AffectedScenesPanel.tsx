import { Crosshair } from 'lucide-react'
import type { Incident } from '../../api'
import { formatShortTime } from './groupIncidents'

type Props = {
  incident: Incident | null
}

export function AffectedScenesPanel({ incident }: Props) {
  const scenes = incident?.evidence?.affected_scenes ?? []

  return (
    <section id="wr-affected" className="panel flex h-full flex-col p-4 md:p-5">
      <h3 className="mb-3 flex items-center gap-2 font-display text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
        <Crosshair className="h-3.5 w-3.5 text-accent" aria-hidden />
        Affected scenes
      </h3>
      <ul className="space-y-2">
        {scenes.map((scene) => (
          <li
            key={scene.scene_number}
            className="rounded-lg border border-border bg-background/40 px-3 py-2.5"
          >
            <p className="font-display text-sm font-medium">
              Scene {scene.scene_number} — {scene.title}
            </p>
            <p className="mt-1 text-[11px] text-muted-foreground">
              {scene.location_id}
              {scene.scheduled_start ? ` · ${formatShortTime(scene.scheduled_start)}` : ''}
            </p>
          </li>
        ))}
        {!scenes.length && (
          <li className="text-sm text-muted-foreground">
            {incident?.affected_scenes?.length
              ? `Scenes ${incident.affected_scenes.join(', ')}`
              : 'No affected scenes.'}
          </li>
        )}
      </ul>
    </section>
  )
}
