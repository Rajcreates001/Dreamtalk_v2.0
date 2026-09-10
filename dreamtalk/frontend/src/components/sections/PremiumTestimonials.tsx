"use client"

import { motion } from "motion/react"
import { Quote, Star } from "lucide-react"
import { SectionWrapper, SectionHeading, StaggerGrid, staggerItem, GlassCard } from "./SectionWrapper"

const testimonials = [
  {
    name: "Dr. Priya Sharma",
    role: "CMO, Apollo Hospitals",
    text: "DreamTalk's healthcare avatars have transformed our patient triage system. The emotional intelligence is remarkable.",
  },
  {
    name: "Rajesh Mehta",
    role: "CTO, TechCorp India",
    text: "We deployed DreamTalk for customer support. 40% reduction in response time and 95% customer satisfaction.",
  },
  {
    name: "Ananya Patel",
    role: "Product Lead, HealthFirst",
    text: "Uploaded 500+ medical documents and our avatar was ready in hours. The knowledge integration is incredible.",
  },
  {
    name: "Vikram Joshi",
    role: "CEO, EduTech Solutions",
    text: "Multi-language support and emotion detection make it perfect for educational applications worldwide.",
  },
  {
    name: "Neha Gupta",
    role: "Director, CareGroup",
    text: "Mental health avatars that actually understand and remember. This is the future of digital therapy.",
  },
  {
    name: "Arun Kumar",
    role: "VP Engineering, FinServe",
    text: "Enterprise-grade security, persistent memory, and API-first design. Exactly what we needed for compliance.",
  },
]

export function PremiumTestimonials() {
  return (
    <SectionWrapper id="testimonials" bg="alt" label="Chapter 14" reveal="scale">
      <SectionHeading
        label="Testimonials"
        title="Trusted by innovators"
        description="See what early adopters and partners are saying about DreamTalk."
      />
      <StaggerGrid className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {testimonials.map((t) => (
          <GlassCard key={t.name}>
            <Quote className="h-5 w-5 text-[#CC3A63]/40 mb-3" />
            <p className="text-sm text-foreground leading-relaxed mb-4 italic">&ldquo;{t.text}&rdquo;</p>
            <div className="flex items-center gap-2 mb-3">
              {[...Array(5)].map((_, i) => (
                <Star key={i} className="h-3 w-3 fill-[#D6A44C] text-[#D6A44C]" />
              ))}
            </div>
            <div>
              <div className="text-sm font-semibold text-foreground">{t.name}</div>
              <div className="text-xs text-foreground-muted">{t.role}</div>
            </div>
          </GlassCard>
        ))}
      </StaggerGrid>
    </SectionWrapper>
  )
}
