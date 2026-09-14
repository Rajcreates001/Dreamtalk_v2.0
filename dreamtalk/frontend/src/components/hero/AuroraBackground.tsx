"use client"

/**
 * AuroraBackdrop — Simplified CSS-only animated background.
 *
 * Two slow-moving radial gradient blobs with a deep vignette.
 * Zero JavaScript cost. All animations are GPU-composited via CSS.
 */
export function AuroraBackdrop() {
  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
      <div className="absolute inset-0 bg-background" />
      <div className="absolute inset-0 bg-gradient-to-b from-background via-background-secondary to-background" />

      {/* Animated radial gradient blob — primary */}
      <div
        className="absolute w-[700px] h-[700px] rounded-full animate-aurora-drift"
        style={{
          background: "radial-gradient(circle, rgba(200,90,58,0.08), transparent 70%)",
          left: "35%",
          top: "25%",
          transform: "translate(-50%, -50%)",
        }}
      />

      {/* Animated radial gradient blob — secondary */}
      <div
        className="absolute w-[500px] h-[500px] rounded-full animate-aurora-drift"
        style={{
          background: "radial-gradient(circle, rgba(60,150,138,0.05), transparent 70%)",
          animationDelay: "5s",
          left: "60%",
          top: "60%",
          transform: "translate(-50%, -50%)",
        }}
      />

      {/* Deep vignette — fades to the theme background (invisible in light) */}
      <div
        className="absolute inset-0"
        style={{ background: "radial-gradient(ellipse at center, transparent 0%, var(--background) 78%)" }}
      />
    </div>
  )
}
