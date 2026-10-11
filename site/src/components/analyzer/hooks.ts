import { type RefObject, useEffect, useLayoutEffect, useRef, useState } from 'react'

function easeOutCubic(t: number): number {
  return 1 - (1 - t) ** 3
}

/** Tweens from the last shown value to `target` on requestAnimationFrame. */
export function useCountUp(target: number, durationMs = 1200): number {
  const [value, setValue] = useState(0)
  const shown = useRef(0)

  useEffect(() => {
    const from = shown.current
    const start = performance.now()
    let frame = requestAnimationFrame(function tick(now: number) {
      const t = Math.min((now - start) / durationMs, 1)
      shown.current = from + (target - from) * easeOutCubic(t)
      setValue(shown.current)
      if (t < 1) frame = requestAnimationFrame(tick)
    })
    return () => cancelAnimationFrame(frame)
  }, [target, durationMs])

  return value
}

/** Width of an element, kept current with a ResizeObserver, so SVG charts render at real pixels. */
export function useContainerWidth<T extends HTMLElement>(): [RefObject<T | null>, number] {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(0)

  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const observer = new ResizeObserver((entries) => {
      setWidth(entries[0].contentRect.width)
    })
    observer.observe(el)
    setWidth(el.clientWidth)
    return () => observer.disconnect()
  }, [])

  return [ref, width]
}
