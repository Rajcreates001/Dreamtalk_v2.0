"use client"

import { motion } from "motion/react"
import { Sparkles, Heart, Activity } from "lucide-react"
import { TypingAnimation } from "@/components/magic/typing-animation"

export function WelcomeScreen() {
  return (
    <div className="flex flex-col items-center justify-center h-full px-6 text-center">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="space-y-6 max-w-md"
      >
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-emerald-400/20 to-blue-400/20 ring-1 ring-border">
          <Heart className="h-8 w-8 text-emerald-500" />
        </div>

        <div className="space-y-2">
          <h2 className="text-2xl font-semibold tracking-tight">
            <TypingAnimation words={["Hello, I'm Dr. Aria"]} duration={50} />
          </h2>
          <p className="text-muted-foreground text-sm leading-relaxed">
            Your AI health companion. I can help with medical questions, health advice,
            and wellness guidance. How can I assist you today?
          </p>
        </div>

        <div className="grid grid-cols-1 gap-2 text-left">
          {[
            { icon: Activity, text: "What are the symptoms of dehydration?" },
            { icon: Heart, text: "How can I improve my sleep quality?" },
            { icon: Sparkles, text: "Tell me about your capabilities" },
          ].map((suggestion, i) => (
            <motion.button
              key={i}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4, delay: 0.3 + i * 0.1 }}
              className="flex items-center gap-3 px-4 py-3 rounded-xl bg-muted/30 border border-border/50 hover:bg-muted/50 hover:border-border transition-all text-sm text-left group"
            >
              <suggestion.icon className="h-4 w-4 text-muted-foreground shrink-0" />
              <span className="text-muted-foreground group-hover:text-foreground transition-colors">
                {suggestion.text}
              </span>
            </motion.button>
          ))}
        </div>
      </motion.div>
    </div>
  )
}
