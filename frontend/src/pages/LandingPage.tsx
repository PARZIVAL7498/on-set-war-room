import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { motion, useScroll, useTransform } from 'framer-motion'
import gsap from 'gsap'
import { useGSAP } from '@gsap/react'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { ArrowDown, ArrowRight, Camera, Crosshair, Sparkles } from 'lucide-react'
import { Magnetic } from '../motion/Magnetic'
import { TiltCard } from '../motion/TiltCard'
import { usePrefersReducedMotion } from '../motion/usePrefersReducedMotion'
import { AmbientCanvas } from '../components/AmbientCanvas'
import { BrandLogo } from '../components/BrandLogo'
import { SiteNav } from '../components/SiteNav'

gsap.registerPlugin(ScrollTrigger)

const HERO_SRC = '/media/hero.mp4'
const POSTER_SRC = '/media/hero-poster.png'

export default function LandingPage() {
  const root = useRef<HTMLDivElement>(null)
  const videoWrap = useRef<HTMLDivElement>(null)
  const reduced = usePrefersReducedMotion()
  const { scrollYProgress } = useScroll()
  const heroY = useTransform(scrollYProgress, [0, 0.25], [0, 120])
  const heroScale = useTransform(scrollYProgress, [0, 0.25], [1, 1.08])
  const heroOpacity = useTransform(scrollYProgress, [0, 0.2], [1, 0.35])

  useGSAP(
    () => {
      if (reduced || !root.current) return

      const mm = gsap.matchMedia()
      mm.add('(prefers-reduced-motion: no-preference)', () => {
        gsap.from('[data-hero-line]', {
          yPercent: 110,
          duration: 1.05,
          stagger: 0.12,
          ease: 'expo.out',
          delay: 0.15,
        })

        gsap.from('[data-hero-fade]', {
          opacity: 0,
          y: 24,
          duration: 0.9,
          stagger: 0.1,
          ease: 'power3.out',
          delay: 0.55,
        })

        gsap.utils.toArray<HTMLElement>('[data-chapter]').forEach((section) => {
          const items = section.querySelectorAll('[data-reveal]')
          gsap.from(items, {
            opacity: 0,
            y: 48,
            duration: 0.85,
            stagger: 0.1,
            ease: 'power3.out',
            scrollTrigger: {
              trigger: section,
              start: 'top 78%',
              toggleActions: 'play none none reverse',
            },
          })
        })

        gsap.to('[data-parallax-slow]', {
          yPercent: -18,
          ease: 'none',
          scrollTrigger: {
            trigger: root.current,
            start: 'top top',
            end: 'bottom top',
            scrub: true,
          },
        })

        const pin = root.current?.querySelector('[data-pipeline-pin]')
        if (pin) {
          gsap.from('[data-pipe-step]', {
            opacity: 0,
            y: 36,
            duration: 0.75,
            stagger: 0.12,
            ease: 'power3.out',
            scrollTrigger: {
              trigger: pin,
              start: 'top 72%',
              toggleActions: 'play none none reverse',
            },
          })
        }
      })

      return () => mm.revert()
    },
    { scope: root, dependencies: [reduced] },
  )

  useEffect(() => {
    document.documentElement.classList.add('cinematic')
    return () => document.documentElement.classList.remove('cinematic')
  }, [])

  return (
    <div ref={root} className="relative min-h-screen overflow-x-hidden bg-void text-foreground">
      <AmbientCanvas />
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 z-[1] bg-[radial-gradient(ellipse_at_20%_0%,rgba(225,29,72,0.14),transparent_45%),radial-gradient(ellipse_at_90%_10%,rgba(34,197,94,0.1),transparent_40%),linear-gradient(180deg,#05070c_0%,#0a0f1a_50%,#05070c_100%)]"
      />
      <div aria-hidden className="noise-overlay pointer-events-none fixed inset-0 z-[2]" />
      <div aria-hidden className="grid-overlay pointer-events-none fixed inset-0 z-[2] opacity-[0.18]" />

      <SiteNav />

      {/* HERO */}
      <section className="relative z-10 flex min-h-[100svh] flex-col justify-end pb-16 pt-28 md:pb-24 md:pt-32">
        <motion.div
          ref={videoWrap}
          style={reduced ? undefined : { y: heroY, scale: heroScale, opacity: heroOpacity }}
          className="absolute inset-0 overflow-hidden"
        >
          <div className="absolute inset-0 origin-center will-change-transform" data-parallax-slow>
            {!reduced ? (
              <video
                className="h-full w-full scale-105 object-cover opacity-55"
                src={HERO_SRC}
                poster={POSTER_SRC}
                autoPlay
                muted
                loop
                playsInline
                preload="metadata"
                aria-hidden
              />
            ) : (
              <img src={POSTER_SRC} alt="" className="h-full w-full object-cover opacity-50" />
            )}
          </div>
          <div className="absolute inset-0 bg-gradient-to-t from-void via-void/70 to-void/30" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_40%,transparent_0%,rgba(5,7,12,0.75)_70%)]" />
        </motion.div>

        <div className="relative z-10 mx-auto w-full max-w-6xl px-5 md:px-8">
          <h1 data-hero-fade className="mb-8">
            <BrandLogo to={null} size="hero" showWordmark className="justify-start" />
          </h1>

          <p className="max-w-4xl font-display text-[clamp(1.35rem,3.5vw,2.25rem)] font-medium leading-snug tracking-[-0.02em] text-foreground/90">
            <span className="block overflow-hidden">
              <span data-hero-line className="inline-block">
                Production risk, commanded in realtime.
              </span>
            </span>
          </p>

          <p
            data-hero-fade
            className="mt-6 max-w-xl text-base leading-relaxed text-muted-foreground md:text-lg"
          >
            When CAMERA-02 dies mid-shoot, On-Set War Room investigates downstream
            impact across scenes and kit — then recommends the pivot before delay
            becomes money.
          </p>

          <div data-hero-fade className="mt-10 flex flex-wrap items-center gap-4">
            <Magnetic strength={0.45}>
              <Link
                to="/war-room"
                className="group relative inline-flex cursor-pointer items-center gap-3 overflow-hidden rounded-full bg-signal px-7 py-3.5 font-display text-sm font-semibold tracking-wide text-white shadow-[0_0_40px_rgba(225,29,72,0.35)] transition hover:shadow-[0_0_56px_rgba(225,29,72,0.5)]"
              >
                <span className="absolute inset-0 origin-left scale-x-0 bg-white/20 transition duration-500 group-hover:scale-x-100" />
                <span className="relative">Enter War Room</span>
                <ArrowRight className="relative h-4 w-4 transition group-hover:translate-x-1" />
              </Link>
            </Magnetic>
            <Magnetic strength={0.3}>
              <a
                href="#story"
                className="inline-flex cursor-pointer items-center gap-2 rounded-full border border-white/15 bg-white/5 px-6 py-3.5 font-display text-sm text-foreground backdrop-blur-md transition hover:border-white/30 hover:bg-white/10"
              >
                Watch the cascade
              </a>
            </Magnetic>
          </div>

          <a
            href="#story"
            data-hero-fade
            className="mt-16 inline-flex cursor-pointer items-center gap-3 font-display text-[10px] uppercase tracking-[0.3em] text-muted-foreground"
          >
            <span className="flex h-10 w-6 items-start justify-center rounded-full border border-white/20 pt-2">
              <ArrowDown className="scroll-cue h-3 w-3" />
            </span>
            Scroll
          </a>
        </div>
      </section>

      {/* STORY */}
      <section id="story" data-chapter className="relative z-10 py-28 md:py-40">
        <div className="mx-auto max-w-6xl px-5 md:px-8">
          <p data-reveal className="font-display text-[11px] uppercase tracking-[0.3em] text-emerald">
            01 — The problem
          </p>
          <h2
            data-reveal
            className="mt-5 max-w-4xl font-display text-4xl font-semibold leading-[1.05] tracking-tight md:text-6xl"
          >
            Shoot days never go to plan.
            <span className="text-muted-foreground"> Humans still stitch the cascade by hand.</span>
          </h2>
          <p data-reveal className="mt-8 max-w-2xl text-lg text-muted-foreground">
            Kit fails. Cast slips. Locations close. The 1st AD needs the next move
            before the schedule fractures — not after the overtime bill lands.
          </p>
        </div>
      </section>

      {/* PIPELINE */}
      <section
        id="pipeline"
        data-chapter
        data-pipeline-pin
        className="relative z-10 border-y border-white/10 bg-white/[0.02] py-28 md:py-40"
      >
        <div className="mx-auto max-w-6xl px-5 md:px-8">
          <p data-reveal className="font-display text-[11px] uppercase tracking-[0.3em] text-signal">
            02 — The cascade
          </p>
          <h2
            data-reveal
            className="mt-5 max-w-3xl font-display text-4xl font-semibold tracking-tight md:text-5xl"
          >
            From failure to evidence to action.
          </h2>

          <div className="mt-16 grid gap-5 md:grid-cols-3">
            {[
              {
                icon: Camera,
                title: 'Detect',
                body: 'CAMERA-02 reports DOWN. Event hits ClickHouse Cloud. Monitor flags production risk.',
              },
              {
                icon: Crosshair,
                title: 'Investigate',
                body: 'Scenes 43 & 48 need that A-cam. Constraints surface from requirements — not a spreadsheet guess.',
              },
              {
                icon: Sparkles,
                title: 'Pivot',
                body: 'Scene 47 stays shootable. Deterministic engines score HIGH. Narration explains the call.',
              },
            ].map((step, i) => (
              <TiltCard key={step.title} className="rounded-2xl">
                <article
                  data-pipe-step
                  data-reveal
                  className="glass group relative h-full overflow-hidden rounded-2xl p-7"
                >
                  <div className="mb-8 flex items-center justify-between">
                    <step.icon className="h-6 w-6 text-signal" aria-hidden />
                    <span className="font-display text-xs text-muted-foreground">
                      0{i + 1}
                    </span>
                  </div>
                  <h3 className="font-display text-2xl font-semibold">{step.title}</h3>
                  <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                    {step.body}
                  </p>
                </article>
              </TiltCard>
            ))}
          </div>
        </div>
      </section>

      {/* PIVOT / CLIMAX */}
      <section id="pivot" data-chapter className="relative z-10 py-28 md:py-44">
        <div className="mx-auto max-w-6xl px-5 md:px-8">
          <div className="grid items-end gap-12 lg:grid-cols-[1.2fr_0.8fr]">
            <div>
              <p data-reveal className="font-display text-[11px] uppercase tracking-[0.3em] text-emerald">
                03 — The wow
              </p>
              <h2
                data-reveal
                className="mt-5 font-display text-4xl font-semibold leading-[1.05] tracking-tight md:text-6xl"
              >
                Recommend Scene 47.
                <span className="block text-muted-foreground">Keep the day moving.</span>
              </h2>
              <p data-reveal className="mt-6 max-w-xl text-muted-foreground">
                Same soundstage energy. No A-cam dependency. Risk scored HIGH with a
                reproducible factor stack — Gemini only narrates what the engines already decided.
              </p>
            </div>

            <TiltCard>
              <div
                data-reveal
                className="glass relative overflow-hidden rounded-2xl p-6 md:p-8"
              >
                <p className="font-display text-[10px] uppercase tracking-[0.25em] text-signal">
                  Active incident
                </p>
                <p className="mt-3 font-display text-3xl font-semibold">CAMERA-02 DOWN</p>
                <div className="mt-6 space-y-3 text-sm">
                  <Row label="Affected" value="Scenes 43 · 48" />
                  <Row label="Risk" value="HIGH · 80" accent />
                  <Row label="Pivot" value="Scene 47" good />
                </div>
                <Magnetic className="mt-8 block" strength={0.35}>
                  <Link
                    to="/war-room"
                    className="inline-flex w-full cursor-pointer items-center justify-center gap-2 rounded-full bg-foreground px-5 py-3 font-display text-sm font-semibold text-void transition hover:bg-white"
                  >
                    Open live console
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Magnetic>
              </div>
            </TiltCard>
          </div>
        </div>
      </section>

      <section className="relative z-10 border-t border-white/10 py-24" data-chapter>
        <div className="mx-auto max-w-3xl px-5 text-center md:px-8">
          <h2
            data-reveal
            className="font-display text-3xl font-semibold tracking-tight md:text-5xl"
          >
            The set stays loud.
            <span className="text-muted-foreground"> The war room stays clear.</span>
          </h2>
          <div data-reveal>
            <Magnetic className="mt-10 inline-flex" strength={0.4}>
              <Link
                to="/war-room"
                className="inline-flex cursor-pointer items-center gap-2 rounded-full bg-signal px-8 py-4 font-display text-sm font-semibold text-white shadow-[0_0_40px_rgba(225,29,72,0.35)]"
              >
                Enter War Room
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Magnetic>
          </div>
        </div>
      </section>

      <footer className="relative z-10 border-t border-white/10 px-5 py-10 text-center font-display text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
        On-Set War Room · deterministic engines · optional Gemini · ClickHouse Cloud
      </footer>
    </div>
  )
}

function Row({
  label,
  value,
  accent,
  good,
}: {
  label: string
  value: string
  accent?: boolean
  good?: boolean
}) {
  return (
    <div className="flex items-center justify-between border-b border-white/10 py-2">
      <span className="text-muted-foreground">{label}</span>
      <span
        className={`font-display font-medium ${
          accent ? 'text-signal' : good ? 'text-emerald' : 'text-foreground'
        }`}
      >
        {value}
      </span>
    </div>
  )
}
