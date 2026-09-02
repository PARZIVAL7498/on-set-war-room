import { X } from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'
import type { IncidentSummary } from '../../api'
import { IncidentRail } from './IncidentRail'

type Props = {
  open: boolean
  incidents: IncidentSummary[]
  activeId?: string
  loading?: boolean
  reduced?: boolean
  onClose: () => void
  onSelect: (incidentId: string) => void
}

export function IncidentDrawer({
  open,
  incidents,
  activeId,
  loading,
  reduced,
  onClose,
  onSelect,
}: Props) {
  return (
    <AnimatePresence>
      {open ? (
        <>
          <motion.button
            type="button"
            aria-label="Close incidents"
            initial={reduced ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 cursor-pointer bg-black/50"
            onClick={onClose}
          />
          <motion.aside
            initial={reduced ? false : { x: -320 }}
            animate={{ x: 0 }}
            exit={reduced ? undefined : { x: -320 }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
            className="fixed bottom-0 left-14 top-0 z-50 flex w-[min(100vw-3.5rem,320px)] flex-col border-r border-border bg-void shadow-2xl md:left-16"
          >
            <div className="flex items-center justify-between border-b border-border px-3 py-2">
              <p className="font-display text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                Incident drawer
              </p>
              <button
                type="button"
                onClick={onClose}
                className="cursor-pointer rounded-lg p-1.5 text-muted-foreground transition hover:bg-muted hover:text-foreground"
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-hidden p-2">
              <IncidentRail
                incidents={incidents}
                activeId={activeId}
                loading={loading}
                reduced={reduced}
                onSelect={(id) => {
                  onSelect(id)
                  onClose()
                }}
              />
            </div>
          </motion.aside>
        </>
      ) : null}
    </AnimatePresence>
  )
}
