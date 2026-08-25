import { useRef, useState, type ReactNode, type MouseEvent as ReactMouseEvent } from 'react'
import { motion, useMotionTemplate, useMotionValue, useSpring } from 'framer-motion'
import { usePrefersReducedMotion } from './usePrefersReducedMotion'

/** Glass card with cursor spotlight — glow only while hovering. */
export function TiltCard({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  const reduced = usePrefersReducedMotion()
  const [hover, setHover] = useState(false)

  const mouseX = useMotionValue(0)
  const mouseY = useMotionValue(0)
  const opacity = useSpring(0, { stiffness: 280, damping: 30 })

  const spotlight = useMotionTemplate`
    radial-gradient(
      420px circle at ${mouseX}px ${mouseY}px,
      rgba(255, 255, 255, 0.12),
      transparent 55%
    )
  `

  function onMove(e: ReactMouseEvent) {
    if (reduced || !ref.current) return
    const r = ref.current.getBoundingClientRect()
    mouseX.set(e.clientX - r.left)
    mouseY.set(e.clientY - r.top)
  }

  function onEnter() {
    if (reduced) return
    setHover(true)
    opacity.set(1)
  }

  function onLeave() {
    setHover(false)
    opacity.set(0)
  }

  return (
    <div
      ref={ref}
      className={`relative ${className}`}
      onMouseMove={onMove}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
    >
      <motion.div
        aria-hidden
        className="pointer-events-none absolute inset-0 z-[1] rounded-[inherit] transition-opacity"
        style={{
          background: spotlight,
          opacity: reduced ? 0 : opacity,
        }}
      />
      <div
        className={`relative z-[2] transition duration-300 ${
          hover && !reduced ? 'translate-y-[-2px]' : ''
        }`}
      >
        {children}
      </div>
    </div>
  )
}
