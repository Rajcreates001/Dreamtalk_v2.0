"use client"

import { useCallback, useSyncExternalStore } from "react"

/**
 * Subscribe to a media query.
 *
 * `useSyncExternalStore` is the right primitive here rather than
 * useState + useEffect: a media query IS an external store, and reading it
 * through this hook avoids the cascading re-render that a setState-in-effect
 * would cause on every mount. It also gives us a proper server snapshot.
 */
function useMediaQuery(query: string, serverFallback: boolean): boolean {
  const subscribe = useCallback(
    (onChange: () => void) => {
      const mq = window.matchMedia(query)
      mq.addEventListener("change", onChange)
      return () => mq.removeEventListener("change", onChange)
    },
    [query],
  )

  return useSyncExternalStore(
    subscribe,
    () => window.matchMedia(query).matches,
    () => serverFallback,
  )
}

/**
 * Tracks `prefers-reduced-motion`, and keeps tracking it — the OS setting can
 * change while the tab is open, so a one-shot read at mount would strand the
 * page in the wrong mode.
 *
 * The server snapshot is `false` so markup matches the common case; if the
 * visitor does prefer reduced motion, the first client read corrects it before
 * any animation has had time to run.
 */
export function useReducedMotion(): boolean {
  return useMediaQuery("(prefers-reduced-motion: reduce)", false)
}

/**
 * True for a hovering, precise pointer (a mouse).
 *
 * Tilt, magnetic and spotlight effects are driven by a cursor that simply does
 * not exist on touch — running them there wastes frames and, worse, can leave
 * an element stranded mid-transform after a tap. The server snapshot is
 * `false`, so those effects stay off until the client confirms a real mouse.
 */
export function useFinePointer(): boolean {
  return useMediaQuery("(hover: hover) and (pointer: fine)", false)
}

/**
 * False during SSR and the first client render, true afterwards.
 *
 * For the narrow case of "this value cannot exist on the server" — the
 * resolved colour theme being the usual one. Branching on such a value before
 * hydration makes the markup disagree with the server's and React throws the
 * tree away.
 */
export function useIsHydrated(): boolean {
  return useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  )
}
