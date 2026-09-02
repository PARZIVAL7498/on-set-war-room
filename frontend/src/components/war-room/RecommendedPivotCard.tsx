import { CheckCircle2 } from 'lucide-react'
import type { PivotRecommendation } from '../../api'

type Props = {
  pivot: PivotRecommendation | null | undefined
}

export function RecommendedPivotCard({ pivot }: Props) {
  return (
    <section id="wr-pivot" className="flex h-full flex-col border border-border bg-card">
      <div className="border-b border-border px-4 py-3 md:px-5">
        <h3 className="font-display text-sm font-bold uppercase tracking-wide">
          Recommended pivot
        </h3>
        <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">
          Best schedule preservation move
        </p>
      </div>
      {pivot ? (
        <div className="flex flex-1 flex-col gap-4 p-4 md:p-5">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="font-mono text-[10px] uppercase text-muted-foreground">
                Move now
              </p>
              <p className="mt-1 font-display text-3xl font-extrabold leading-none text-primary md:text-4xl">
                Scene {pivot.scene_number}
              </p>
              <p className="mt-2 text-sm text-foreground">{pivot.title}</p>
              <p className="mt-1 font-mono text-[11px] text-muted-foreground">
                {pivot.location_id}
              </p>
            </div>
            <CheckCircle2 className="h-5 w-5 shrink-0 text-primary" aria-hidden />
          </div>
          <ul className="space-y-2 border-t border-border pt-3 text-sm leading-snug text-zinc-400">
            {pivot.reasons.slice(0, 3).map((r) => (
              <li key={r} className="flex gap-2">
                <span className="text-primary" aria-hidden>
                  ·
                </span>
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="p-4 text-sm text-muted-foreground md:p-5">No valid pivot found.</p>
      )}
    </section>
  )
}
