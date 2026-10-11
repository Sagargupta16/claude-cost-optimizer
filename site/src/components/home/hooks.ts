import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties, type RefObject } from 'react'

interface InViewOptions {
  rootMargin?: string
  threshold?: number
  /** Latch at true after the first sighting (default). False tracks live visibility. */
  once?: boolean
}

/**
 * True once the element has scrolled into view, then stays true. Bars and
 * count-ups key off it so their motion plays where the reader can see it.
 */
export function useInView(
  ref: RefObject<Element | null>,
  { rootMargin = '0px 0px -8% 0px', threshold = 0.12, once = true }: InViewOptions = {},
): boolean {
  const [inView, setInView] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (typeof IntersectionObserver === 'undefined') {
      setInView(true)
      return
    }
    const io = new IntersectionObserver(
      (entries) => {
        const visible = entries.some((e) => e.isIntersecting)
        if (!once) {
          setInView(visible)
        } else if (visible) {
          setInView(true)
          io.disconnect()
        }
      },
      { rootMargin, threshold },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [ref, rootMargin, threshold, once])
  return inView
}

/** Content-box width of the element, kept current with a ResizeObserver. */
export function useMeasuredWidth(ref: RefObject<HTMLElement | null>): number {
  const [width, setWidth] = useState(0)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const ro = new ResizeObserver((entries) => {
      setWidth(entries[0].contentRect.width)
    })
    ro.observe(el)
    setWidth(el.clientWidth)
    return () => ro.disconnect()
  }, [ref])
  return width
}

/**
 * Ref, measured width and "play the motion now" flag for a chart container.
 * `shown` flips only after the chart has painted once at its start state, so
 * bars visibly grow instead of appearing at full length.
 */
export function useChartFrame(): { ref: RefObject<HTMLDivElement | null>; width: number; shown: boolean } {
  const ref = useRef<HTMLDivElement>(null)
  const width = useMeasuredWidth(ref)
  const inView = useInView(ref)
  return { ref, width, shown: inView && width > 0 }
}

/**
 * Animates from the last shown value to `target` with an ease-out curve. Holds
 * at 0 until `run` is true, so a count-up below the fold waits for the reader.
 */
export function useCountUp(target: number, run: boolean, duration = 900): number {
  const [value, setValue] = useState(0)
  const current = useRef(0)
  useEffect(() => {
    if (!run) return
    const from = current.current
    const start = performance.now()
    let frame = 0
    const tick = (now: number) => {
      const t = Math.min((now - start) / duration, 1)
      const next = from + (target - from) * (1 - (1 - t) ** 3)
      current.current = next
      setValue(next)
      if (t < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [target, run, duration])
  return value
}

/** Inline style that sets the stagger index read by RevealSection's CSS. */
export function staggerStyle(index: number): CSSProperties {
  return { '--i': index } as CSSProperties
}
