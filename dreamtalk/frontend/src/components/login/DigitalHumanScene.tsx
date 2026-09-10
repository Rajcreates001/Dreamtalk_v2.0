"use client"

import { Sparkles } from "lucide-react"

interface DigitalHumanSceneProps {
  roleColor?: string
  roleId?: string | null
}

const RING_CONFIGS = [
  { radius: 90 },
  { radius: 60 },
  { radius: 30 },
]

export function DigitalHumanScene({ roleColor = "#7C5CFF", roleId }: DigitalHumanSceneProps) {
  const accentColor = roleId === "healthcare" ? "#00E5FF" : roleId === "business" ? "#42FFC6" : "#7C5CFF"

  return (
    <div className="relative w-full h-full flex items-center justify-center">
      <div className="relative w-[400px] h-[400px] lg:w-[480px] lg:h-[480px]">
        {/* Outer glow */}
        <div
          className="absolute inset-[10%] rounded-full blur-[80px]"
          style={{
            background: `radial-gradient(circle, ${accentColor}12, transparent 70%)`,
            animation: "chamber-glow 4s ease-in-out infinite",
          }}
        />

        {/* Orbiting Rings — CSS animated (3 rings) */}
        {RING_CONFIGS.map((ring, i) => (
          <div
            key={i}
            className="absolute inset-0 flex items-center justify-center pointer-events-none"
            style={{
              animation: `login-orbit ${14 + i * 3}s linear infinite`,
              animationDirection: i % 2 === 0 ? "normal" : "reverse",
            }}
          >
            <div
              className="absolute rounded-full border"
              style={{
                width: ring.radius * 2,
                height: ring.radius * 2,
                borderColor: `${accentColor}10`,
                borderWidth: "1px",
              }}
            />
            <div
              className="absolute w-1.5 h-1.5 rounded-full"
              style={{
                background: accentColor,
                left: `calc(50% + ${ring.radius - 1}px)`,
                top: "50%",
                marginTop: -3,
                boxShadow: `0 0 6px ${accentColor}40`,
              }}
            />
          </div>
        ))}

        {/* Digital Human */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="relative w-28 h-28">
            <div
              className="absolute inset-[15%] rounded-full blur-[25px]"
              style={{
                background: `radial-gradient(circle, ${accentColor}20, transparent 70%)`,
                animation: "body-glow 4s ease-in-out infinite",
              }}
            />

            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-16 h-16">
              {/* Head */}
              <div
                className="w-full h-full rounded-[40%_40%_45%_45%]"
                style={{
                  background: `linear-gradient(to bottom, ${accentColor}, ${roleColor})`,
                  padding: "2px",
                  animation: "breathe 4s ease-in-out infinite",
                }}
              >
                <div className="w-full h-full rounded-[40%_40%_45%_45%] bg-[#070B14] flex items-center justify-center flex-col gap-1.5">
                  <div className="flex gap-4">
                    <div
                      className="w-[3px] h-[3px] rounded-full"
                      style={{
                        background: accentColor,
                        boxShadow: `0 0 4px ${accentColor}`,
                        animation: "blink 4s ease-in-out infinite",
                      }}
                    />
                    <div
                      className="w-[3px] h-[3px] rounded-full"
                      style={{
                        background: accentColor,
                        boxShadow: `0 0 4px ${accentColor}`,
                        animation: "blink 4s ease-in-out infinite 0.1s",
                      }}
                    />
                  </div>
                  <div
                    className="w-3 h-[2px] rounded-full"
                    style={{
                      background: `${accentColor}40`,
                      opacity: 0.5,
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Single role label */}
        <div className="absolute bottom-[5%] left-1/2 -translate-x-1/2 z-10">
          <div
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg"
            style={{
              background: "rgba(15,23,42,0.6)",
              backdropFilter: "blur(16px)",
              border: "1px solid rgba(255,255,255,0.06)",
            }}
          >
            <Sparkles className="h-2.5 w-2.5" style={{ color: accentColor }} />
            <span className="text-[9px] font-mono tracking-wider" style={{ color: `${accentColor}CC` }}>
              {roleId === "healthcare" ? "DIGITAL DOCTOR" : roleId === "business" ? "DIGITAL EMPLOYEE" : "DIGITAL COMPANION"}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
