import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Magnetic } from '../motion/Magnetic'
import { BrandLogo } from './BrandLogo'

const LINKS = [
  { href: '#story', label: 'Story' },
  { href: '#pipeline', label: 'Pipeline' },
  { href: '#pivot', label: 'Pivot' },
]

export function SiteNav() {
  const [scrolled, setScrolled] = useState(false)
  const [open, setOpen] = useState(false)
  const { pathname } = useLocation()
  const onLanding = pathname === '/'

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <motion.header
      initial={{ y: -24, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
      className={`fixed inset-x-0 top-0 z-50 transition-colors duration-300 ${
        scrolled || !onLanding
          ? 'border-b border-white/10 bg-[#05070c]/75 backdrop-blur-xl'
          : 'bg-transparent'
      }`}
    >
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 md:px-8">
        <BrandLogo size="sm" showWordmark />

        {onLanding && (
          <nav className="hidden items-center gap-8 md:flex">
            {LINKS.map((l) => (
              <a
                key={l.href}
                href={l.href}
                className="cursor-pointer font-display text-[11px] uppercase tracking-[0.22em] text-muted-foreground transition hover:text-foreground"
              >
                {l.label}
              </a>
            ))}
          </nav>
        )}

        <div className="flex items-center gap-3">
          <Magnetic strength={0.4}>
            <Link
              to="/war-room"
              className="group relative inline-flex cursor-pointer overflow-hidden rounded-full border border-white/15 bg-white/5 px-4 py-2 font-display text-[11px] font-semibold uppercase tracking-[0.18em] text-foreground backdrop-blur-md transition hover:border-signal/50 hover:shadow-[0_0_24px_rgba(225,29,72,0.25)]"
            >
              <span className="relative z-10">Enter console</span>
              <span className="absolute inset-0 -translate-x-full bg-gradient-to-r from-signal/0 via-signal/30 to-signal/0 transition duration-500 group-hover:translate-x-full" />
            </Link>
          </Magnetic>

          {onLanding && (
            <button
              type="button"
              className="cursor-pointer md:hidden"
              aria-expanded={open}
              aria-label="Menu"
              onClick={() => setOpen((v) => !v)}
            >
              <span className="flex h-9 w-9 flex-col items-center justify-center gap-1.5 rounded-full border border-white/15 bg-white/5">
                <span className={`h-px w-4 bg-foreground transition ${open ? 'translate-y-[3.5px] rotate-45' : ''}`} />
                <span className={`h-px w-4 bg-foreground transition ${open ? 'opacity-0' : ''}`} />
                <span className={`h-px w-4 bg-foreground transition ${open ? '-translate-y-[3.5px] -rotate-45' : ''}`} />
              </span>
            </button>
          )}
        </div>
      </div>

      {open && onLanding && (
        <div className="border-t border-white/10 bg-[#05070c]/95 px-5 py-4 backdrop-blur-xl md:hidden">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              className="block cursor-pointer py-3 font-display text-xs uppercase tracking-[0.2em] text-muted-foreground"
            >
              {l.label}
            </a>
          ))}
        </div>
      )}
    </motion.header>
  )
}
