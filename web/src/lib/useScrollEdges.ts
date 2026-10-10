import { useCallback, useEffect, useRef, useState } from 'react'

export interface ScrollEdges {
  /** Hidden content BEFORE the viewport (top for 'y', start/right-in-RTL for 'x'). */
  before: boolean
  /** Hidden content AFTER the viewport (bottom for 'y', end/left-in-RTL for 'x'). */
  after: boolean
}

/**
 * T-35 — tracks whether a scroll container still has content hidden before or
 * after the viewport on one axis, so a caller can show a fade/arrow when there
 * is more to scroll and hide it at the edge. Recomputes on scroll, resize, and
 * content changes. `scrollLeft` is taken as an absolute value so it works under
 * RTL (where modern browsers report it as ≤ 0).
 */
export function useScrollEdges<T extends HTMLElement>(axis: 'x' | 'y' = 'y') {
  const ref = useRef<T | null>(null)
  const [edges, setEdges] = useState<ScrollEdges>({ before: false, after: false })

  const measure = useCallback(() => {
    const el = ref.current
    if (!el) return
    const pos = axis === 'y' ? el.scrollTop : Math.abs(el.scrollLeft)
    const size = axis === 'y' ? el.clientHeight : el.clientWidth
    const total = axis === 'y' ? el.scrollHeight : el.scrollWidth
    const before = pos > 1
    const after = pos + size < total - 1
    setEdges((prev) => (prev.before === before && prev.after === after ? prev : { before, after }))
  }, [axis])

  useEffect(() => {
    const el = ref.current
    if (!el) return
    measure()
    el.addEventListener('scroll', measure, { passive: true })
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    const mo = new MutationObserver(measure)
    mo.observe(el, { childList: true, subtree: true })
    window.addEventListener('resize', measure)
    return () => {
      el.removeEventListener('scroll', measure)
      ro.disconnect()
      mo.disconnect()
      window.removeEventListener('resize', measure)
    }
  }, [measure])

  return { ref, ...edges, measure }
}
