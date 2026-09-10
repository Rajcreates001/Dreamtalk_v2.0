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
      <div className="absolute inset-0 bg-[#201D1D]" />
      <div className="absolute inset-0 bg-gradient-to-b from-[#201D1D] via-[#232020] to-[#201D1D]" />

      {/* Animated radial gradient blob — primary */}
      <div
        className="absolute w-[700px] h-[700px] rounded-full animate-aurora-drift"
        style={{
          background: "radial-gradient(circle, rgba(204,58,99,0.08), transparent 70%)",
          left: "35%",
          top: "25%",
          transform: "translate(-50%, -50%)",
        }}
      />

      {/* Animated radial gradient blob — secondary */}
      <div
        className="absolute w-[500px] h-[500px] rounded-full animate-aurora-drift"
        style={{
          background: "radial-gradient(circle, rgba(162,171,115,0.05), transparent 70%)",
          animationDelay: "5s",
          left: "60%",
          top: "60%",
          transform: "translate(-50%, -50%)",
        }}
      />

      {/* Deep vignette */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_transparent_0%,_#201D1D_70%)]" />
    </div>
  )
}
