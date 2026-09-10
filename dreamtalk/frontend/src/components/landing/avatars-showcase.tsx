"use client"

import { useState } from "react"
import { motion } from "motion/react"
import { Sparkles, Star, ArrowRight } from "lucide-react"
import { BlurFade } from "@/components/magic/blur-fade"
import { BorderBeam } from "@/components/magic/border-beam"
import { cn } from "@/lib/utils"
import Link from "next/link"

interface AvatarPersonality {
  name: string
  role: string
  description: string
  emoji: string
  accent: string
  category: string
  popularity: number
  tags: string[]
}

const AVATARS: AvatarPersonality[] = [
  {
    name: "Dr. Priya Sharma",
    role: "Cardiologist",
    description: "Board-certified cardiologist for heart health consultations, diet plans, and post-op care.",
    emoji: "👩‍⚕️",
    accent: "#10b981",
    category: "healthcare",
    popularity: 98,
    tags: ["Heart Health", "Consultations", "24/7"],
  },
  {
    name: "Sachin Tendulkar",
    role: "Cricket Legend & Mentor",
    description: "Get inspired by the Master Blaster. Discuss cricket strategy, mental toughness, and life lessons.",
    emoji: "🏏",
    accent: "#3b82f6",
    category: "sports",
    popularity: 100,
    tags: ["Sports", "Motivation", "Mentorship"],
  },
  {
    name: "Dr. Ananya Patel",
    role: "Clinical Psychologist",
    description: "Licensed therapist for anxiety, depression, stress management, and emotional well-being.",
    emoji: "🧠",
    accent: "#8b5cf6",
    category: "healthcare",
    popularity: 95,
    tags: ["Mental Health", "Therapy", "Wellness"],
  },
  {
    name: "Ravi Kapoor",
    role: "Business Strategist",
    description: "Seasoned entrepreneur and startup advisor. Get guidance on scaling, fundraising, and leadership.",
    emoji: "👨‍💼",
    accent: "#f59e0b",
    category: "business",
    popularity: 92,
    tags: ["Startups", "Strategy", "Leadership"],
  },
  {
    name: "Dr. Maria Santos",
    role: "Nutritionist & Dietitian",
    description: "Personalized nutrition plans, weight management, and holistic wellness coaching.",
    emoji: "🥗",
    accent: "#10b981",
    category: "healthcare",
    popularity: 90,
    tags: ["Nutrition", "Diet", "Wellness"],
  },
  {
    name: "Neha Gupta",
    role: "Yoga & Meditation Coach",
    description: "Certified yoga instructor and mindfulness practitioner for stress relief and inner peace.",
    emoji: "🧘",
    accent: "#a855f7",
    category: "personal",
    popularity: 88,
    tags: ["Yoga", "Meditation", "Mindfulness"],
  },
  {
    name: "Prof. James Carter",
    role: "Physics Professor",
    description: "MIT-trained physicist for tutoring, research discussions, and science communication.",
    emoji: "🔬",
    accent: "#06b6d4",
    category: "education",
    popularity: 86,
    tags: ["Physics", "Tutoring", "Research"],
  },
  {
    name: "Aisha Mehra",
    role: "Creative Director",
    description: "Award-winning designer for creative brainstorming, design feedback, and artistic collaboration.",
    emoji: "🎨",
    accent: "#ec4899",
    category: "creative",
    popularity: 84,
    tags: ["Design", "Creativity", "Art"],
  },
  {
    name: "Coach Vikram Singh",
    role: "Fitness & Life Coach",
    description: "Transformed 10,000+ lives with HIIT, strength training, and accountability coaching.",
    emoji: "💪",
    accent: "#f97316",
    category: "personal",
    popularity: 87,
    tags: ["Fitness", "Coaching", "Motivation"],
  },
  {
    name: "Dr. Wei Chen",
    role: "AI Research Scientist",
    description: "Deep learning researcher for tech discussions, career advice, and exploring future technologies.",
    emoji: "🤖",
    accent: "#3b82f6",
    category: "tech",
    popularity: 89,
    tags: ["AI", "Tech", "Research"],
  },
]

export function AvatarsShowcase() {
  const [selected, setSelected] = useState<string | null>(null)

  return (
    <section id="avatars" className="relative w-full py-12 px-6 lg:px-16 xl:px-24 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-background/0 via-primary/[0.02] via-accent/[0.02] to-background/0 pointer-events-none" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-px bg-gradient-to-r from-transparent via-accent/30 to-transparent" />

      <div className="relative max-w-7xl mx-auto">
        <BlurFade inView offset={10} blur="4px">
          <div className="text-center space-y-4 mb-12">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent/10 border border-accent/20 text-xs text-accent font-medium">
              10 Digital Personalities
            </span>
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight">
              Meet Your{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent to-secondary">
                Digital Humans
              </span>
            </h2>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
              Real personalities with deep expertise. Each digital human has unique knowledge, voice, and emotional intelligence.
            </p>
          </div>
        </BlurFade>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
          {AVATARS.map((avatar, i) => (
            <BlurFade key={avatar.name} inView offset={10} blur="4px" delay={0.05 * i}>
              <motion.div
                layout
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                whileHover={{ y: -6 }}
                onClick={() => setSelected(selected === avatar.name ? null : avatar.name)}
                data-glow="primary"
                className={cn(
                  "group relative rounded-2xl border p-4 cursor-pointer transition-all",
                  "bg-gradient-to-br from-card via-card/90 to-card/80 animate-gradient-shift",
                  selected === avatar.name
                    ? "border-foreground/30 shadow-xl shadow-foreground/5"
                    : "border-border/50 hover:border-foreground/20"
                )}
              >
                {avatar.popularity >= 98 && (
                  <div className="absolute top-2 right-2 z-10">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/15 border border-amber-500/30 text-[9px] font-medium text-amber-400">
                      <Star className="h-2.5 w-2.5 fill-amber-400" />
                      Top Rated
                    </span>
                  </div>
                )}

                <BorderBeam size={80} duration={8} colorFrom={avatar.accent} colorTo={avatar.accent} borderWidth={0.5} />

                <div className="relative z-10 flex flex-col items-center gap-3 text-center">
                  <div
                    className="w-16 h-16 rounded-2xl flex items-center justify-center text-2xl ring-1"
                    style={{
                      background: `linear-gradient(135deg, ${avatar.accent}20, ${avatar.accent}08)`,
                      borderColor: `${avatar.accent}30`,
                    }}
                  >
                    {avatar.emoji}
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold">{avatar.name}</h3>
                    <p className="text-[10px] text-muted-foreground">{avatar.role}</p>
                  </div>

                  {selected === avatar.name && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      className="space-y-2 w-full"
                    >
                      <p className="text-[11px] text-muted-foreground leading-relaxed">{avatar.description}</p>
                      <div className="flex flex-wrap justify-center gap-1.5">
                        {avatar.tags.map((tag) => (
                          <span
                            key={tag}
                            className="px-2 py-0.5 rounded-full bg-muted/30 border border-border/30 text-[9px] text-muted-foreground"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                      <Link
                        href="/signup"
                        className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:text-accent mt-1"
                      >
                        Interact Now <ArrowRight className="h-3 w-3" />
                      </Link>
                    </motion.div>
                  )}

                  {selected !== avatar.name && (
                    <div className="flex items-center gap-2 text-[9px] text-muted-foreground">
                      <Sparkles className="h-3 w-3" style={{ color: avatar.accent }} />
                      Click to meet
                    </div>
                  )}
                </div>
              </motion.div>
            </BlurFade>
          ))}
        </div>

        <div className="text-center mt-10">
          <Link
            href="/signup"
            className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            View all digital humans <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>
    </section>
  )
}
