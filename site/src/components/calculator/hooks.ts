import { type RefObject, useLayoutEffect, useRef, useState } from 'react'

/** Long enough to read as motion, short enough to keep up with typing. */
export const TWEEN_MS = 700

/** Tracks an element's content width so charts draw at real pixels (text stays legible on phones). */
export function useContainerWidth<T extends HTMLElement>(): [RefObject<T | null>, number] {
  const ref = useRef<T>(null)
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
  }, [])
  return [ref, width]
}

const easeOutCubic = (p: number) => 1 - (1 - p) ** 3

/** Interpolates `from` to `to` over `duration`, calling `onFrame` each animation frame. Returns a cancel function. */
function runTween(
  from: readonly number[],
  to: readonly number[],
  duration: number,
  onFrame: (values: number[]) => void,
): () => void {
  const start = performance.now()
  let frame = requestAnimationFrame(function step(now: number) {
    // The first frame's timestamp can predate `start`, so clamp at both ends.
    const eased = easeOutCubic(Math.min(Math.max((now - start) / duration, 0), 1))
    onFrame(to.map((v, i) => from[i] + (v - from[i]) * eased))
    if (now - start < duration) frame = requestAnimationFrame(step)
  })
  return () => cancelAnimationFrame(frame)
}

/** Stretches or squeezes a series to `length` points so a 30-turn line can morph into a 45-turn one. */
function resample(from: readonly number[], length: number): number[] {
  if (from.length === length) return [...from]
  if (from.length === 0) return Array.from({ length }, () => 0)
  const last = from.length - 1
  return Array.from({ length }, (_, i) => from[Math.round((i * last) / Math.max(length - 1, 1))])
}

function reshape(flat: readonly number[], lengths: readonly number[]): number[][] {
  let offset = 0
  return lengths.map((len) => {
    const part = flat.slice(offset, offset + len)
    offset += len
    return part
  })
}

/**
 * Animated copy of several numeric series. On mount the values grow from 0 (or start at the
 * target when `fromZero` is false); on every change they ease from what is on screen to the
 * new target, so bars and lines move instead of jumping.
 */
export function useTweenSeries(
  series: readonly (readonly number[])[],
  fromZero = true,
  duration = TWEEN_MS,
): number[][] {
  const key = JSON.stringify(series)
  const [shown, setShown] = useState<number[][]>(() => series.map((s) => (fromZero ? s.map(() => 0) : [...s])))
  const shownRef = useRef(shown)

  useLayoutEffect(() => {
    const to = JSON.parse(key) as number[][]
    const from = to.map((s, i) => resample(shownRef.current[i] ?? [], s.length))
    const lengths = to.map((s) => s.length)
    const apply = (flat: number[]) => {
      const next = reshape(flat, lengths)
      shownRef.current = next
      setShown(next)
    }
    // A length change (more turns, fewer rows) is applied before paint so nothing indexes past the end.
    if (from.some((s, i) => s.length !== shownRef.current[i]?.length)) apply(from.flat())
    return runTween(from.flat(), to.flat(), duration, apply)
  }, [key, duration])

  return shown
}

/** Single-series form of useTweenSeries; handy for count-up numbers. */
export function useTween(values: readonly number[], fromZero = true, duration = TWEEN_MS): number[] {
  return useTweenSeries([values], fromZero, duration)[0] ?? []
}

/**
 * Animated copy of a keyed record. Rows are matched by id, so a row keeps its own value when
 * others are added or removed; new ids start at 0 (or at their target when `fromZero` is false).
 */
export function useTweenRecord(
  target: Readonly<Record<string, number>>,
  fromZero = true,
  duration = TWEEN_MS,
): Record<string, number> {
  const key = JSON.stringify(target)
  const [shown, setShown] = useState<Record<string, number>>(() =>
    Object.fromEntries(Object.entries(target).map(([id, v]) => [id, fromZero ? 0 : v])),
  )
  const shownRef = useRef(shown)

  useLayoutEffect(() => {
    const entries = Object.entries(JSON.parse(key) as Record<string, number>)
    const from = entries.map(([id, v]) => shownRef.current[id] ?? (fromZero ? 0 : v))
    return runTween(
      from,
      entries.map(([, v]) => v),
      duration,
      (values) => {
        const next = Object.fromEntries(entries.map(([id], i) => [id, values[i]]))
        shownRef.current = next
        setShown(next)
      },
    )
  }, [key, fromZero, duration])

  return shown
}
