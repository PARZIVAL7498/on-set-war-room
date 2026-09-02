import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  GitBranch,
  List,
  Settings,
  Users,
} from 'lucide-react'

type Props = {
  critical?: boolean
  onIncidents: () => void
  onTimeline: () => void
  onSimulate: () => void
}

export function WarRoomSidebar({
  critical,
  onIncidents,
  onTimeline,
  onSimulate,
}: Props) {
  return (
    <aside className="flex w-14 shrink-0 flex-col items-center gap-3 border-r border-border bg-card/40 py-4 md:w-16">
      <button
        type="button"
        onClick={onIncidents}
        aria-label="Active alert — open incidents"
        className={`flex h-10 w-10 cursor-pointer items-center justify-center rounded-xl border transition ${
          critical
            ? 'border-accent/60 bg-accent/15 text-accent shadow-[0_0_20px_rgba(225,29,72,0.35)]'
            : 'border-border bg-muted/50 text-muted-foreground hover:text-foreground'
        }`}
      >
        <AlertTriangle className="h-5 w-5" aria-hidden />
      </button>

      <nav className="mt-2 flex flex-1 flex-col items-center gap-2">
        <IconBtn label="Incidents" onClick={onIncidents}>
          <List className="h-4 w-4" />
        </IconBtn>
        <IconBtn label="Timeline" onClick={onTimeline}>
          <GitBranch className="h-4 w-4" />
        </IconBtn>
        <IconBtn label="Crew" disabled>
          <Users className="h-4 w-4" />
        </IconBtn>
        <IconBtn label="Simulate / settings" onClick={onSimulate}>
          <Settings className="h-4 w-4" />
        </IconBtn>
      </nav>

      <Link
        to="/"
        className="font-display text-[9px] uppercase tracking-[0.14em] text-muted-foreground transition hover:text-foreground"
        title="Landing"
      >
        Home
      </Link>
    </aside>
  )
}

function IconBtn({
  label,
  onClick,
  disabled,
  children,
}: {
  label: string
  onClick?: () => void
  disabled?: boolean
  children: ReactNode
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
      className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-lg text-muted-foreground transition hover:bg-muted hover:text-foreground disabled:cursor-not-allowed disabled:opacity-35"
    >
      {children}
    </button>
  )
}
