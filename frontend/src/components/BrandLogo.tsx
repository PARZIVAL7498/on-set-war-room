import { Link } from 'react-router-dom'

type Props = {
  /** Pass `null` to render without a link */
  to?: string | null
  className?: string
  /** Mark decorative when adjacent text already names the product */
  decorative?: boolean
  size?: 'sm' | 'md' | 'lg' | 'hero'
  showWordmark?: boolean
}

const SIZES = {
  sm: 'h-8 w-8',
  md: 'h-11 w-11',
  lg: 'h-14 w-14',
  hero: 'h-[4.5rem] w-[4.5rem] md:h-24 md:w-24',
} as const

const WORDMARK = {
  sm: 'font-display text-sm font-semibold tracking-[0.14em] text-foreground',
  md: 'font-display text-base font-semibold tracking-[0.12em] text-foreground',
  lg: 'font-display text-xl font-semibold tracking-tight text-foreground',
  hero:
    'font-display text-[clamp(2rem,5.5vw,3.75rem)] font-semibold leading-[0.95] tracking-[-0.03em] text-foreground',
} as const

export function BrandLogo({
  to = '/',
  className = '',
  decorative = false,
  size = 'sm',
  showWordmark = true,
}: Props) {
  const img = (
    <img
      src="/brand/logo.png"
      alt={decorative || showWordmark ? '' : 'On-Set War Room'}
      aria-hidden={decorative || showWordmark ? true : undefined}
      className={`${SIZES[size]} shrink-0 object-contain`}
      decoding="async"
    />
  )

  const wordmark = showWordmark ? (
    <span className={WORDMARK[size]}>
      {size === 'hero' ? (
        <>
          On-Set
          <br />
          War Room
        </>
      ) : (
        'ON-SET WAR ROOM'
      )}
    </span>
  ) : null

  const inner = (
    <span className={`inline-flex items-center gap-3 md:gap-4 ${className}`}>
      {img}
      {wordmark}
    </span>
  )

  if (to == null || to === '') return inner

  return (
    <Link
      to={to}
      className="cursor-pointer transition hover:opacity-90"
      aria-label="On-Set War Room home"
    >
      {inner}
    </Link>
  )
}
