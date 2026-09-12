"use client"

/** Dashboard landing route for a signed-in user's role. */
export function dashboardPathForRole(role?: string | null): string {
  if (role === "healthcare") return "/dashboard/healthcare"
  if (role === "business") return "/dashboard/business"
  return "/dashboard/user"
}

/**
 * Navigate after a successful sign-in / sign-up.
 *
 * `router.push` called from inside a setTimeout during the welcome animation
 * can fire — the RSC payload is fetched and returns 200 — without the
 * navigation ever committing, stranding the user on /signup holding a valid
 * token. Observed in Next 16 with an AnimatePresence transition in flight.
 * We keep the client-side push for the happy path and fall back to a full
 * load if the location hasn't actually changed.
 */
export function navigateAfterAuth(
  router: { push: (href: string) => void },
  target: string,
  graceMs = 700,
): void {
  try {
    router.push(target)
  } catch {
    /* fall through to the hard navigation below */
  }
  if (typeof window === "undefined") return
  window.setTimeout(() => {
    if (window.location.pathname !== target) window.location.assign(target)
  }, graceMs)
}
