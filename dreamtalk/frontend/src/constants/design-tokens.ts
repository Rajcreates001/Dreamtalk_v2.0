/**
 * DreamTalk Design System — Centralized Tokens
 *
 * All colors, spacing, glass, typography, and animation values
 * consumed by every component. Nothing hardcoded or duplicated.
 */

/* ─── SPACING SCALE ─── */
export const space = {
  4: "4px",
  8: "8px",
  12: "12px",
  16: "16px",
  20: "20px",
  24: "24px",
  32: "32px",
  40: "40px",
  48: "48px",
  64: "64px",
  80: "80px",
  96: "96px",
  128: "128px",
  160: "160px",
} as const

export const spacingClass = {
  4: "p-1", 8: "p-2", 12: "p-3", 16: "p-4", 20: "p-5", 24: "p-6",
  32: "p-8", 48: "p-12", 64: "p-16", 96: "p-24", 128: "p-32",
} as const

/* ─── SECTION COLOR THEMES ─── */
export interface SectionTheme {
  name: string
  color: {
    primary: string
    secondary: string
    accent: string
    glow: string
  }
  background: {
    base: string
    gradient: string
    blob1: string
    blob2: string
    blob3: string
  }
  glass: {
    bg: string
    border: string
    blur: string
  }
}

export const sectionThemes: Record<string, SectionTheme> = {
  hero: {
    name: "Hero",
    color: { primary: "#7C5CFF", secondary: "#00E5FF", accent: "#42FFC6", glow: "rgba(124,92,255,0.4)" },
    background: { base: "#070B14", gradient: "from-[#070B14] via-[#0A0F1F] to-[#070B14]", blob1: "rgba(124,92,255,0.12)", blob2: "rgba(0,229,255,0.07)", blob3: "rgba(66,255,198,0.05)" },
    glass: { bg: "rgba(15,23,42,0.72)", border: "rgba(255,255,255,0.06)", blur: "blur(28px)" },
  },
  problem: {
    name: "Problem",
    color: { primary: "#FF5F73", secondary: "#FF8A65", accent: "#FFB74D", glow: "rgba(255,95,115,0.3)" },
    background: { base: "#070B14", gradient: "from-[#070B14] via-[#0F0B0B] to-[#070B14]", blob1: "rgba(255,95,115,0.08)", blob2: "rgba(255,138,101,0.04)", blob3: "rgba(255,183,77,0.03)" },
    glass: { bg: "rgba(15,10,10,0.72)", border: "rgba(255,95,115,0.06)", blur: "blur(28px)" },
  },
  solution: {
    name: "Solution",
    color: { primary: "#7C5CFF", secondary: "#42FFC6", accent: "#00E5FF", glow: "rgba(124,92,255,0.35)" },
    background: { base: "#070B14", gradient: "from-[#070B14] via-[#0A0F1A] to-[#070B14]", blob1: "rgba(124,92,255,0.1)", blob2: "rgba(66,255,198,0.05)", blob3: "rgba(0,229,255,0.04)" },
    glass: { bg: "rgba(15,23,42,0.72)", border: "rgba(124,92,255,0.08)", blur: "blur(28px)" },
  },
  avatar: {
    name: "Avatar Studio",
    color: { primary: "#EC4899", secondary: "#7C5CFF", accent: "#F472B6", glow: "rgba(236,72,153,0.3)" },
    background: { base: "#070B14", gradient: "from-[#070B14] via-[#100B15] to-[#070B14]", blob1: "rgba(236,72,153,0.08)", blob2: "rgba(124,92,255,0.05)", blob3: "rgba(244,114,182,0.03)" },
    glass: { bg: "rgba(20,10,20,0.72)", border: "rgba(236,72,153,0.06)", blur: "blur(28px)" },
  },
  knowledge: {
    name: "Knowledge",
    color: { primary: "#22D3EE", secondary: "#7C5CFF", accent: "#34D399", glow: "rgba(34,211,238,0.3)" },
    background: { base: "#070B14", gradient: "from-[#070B14] via-[#0A0F1A] to-[#070B14]", blob1: "rgba(34,211,238,0.08)", blob2: "rgba(124,92,255,0.04)", blob3: "rgba(52,211,153,0.03)" },
    glass: { bg: "rgba(10,20,30,0.72)", border: "rgba(34,211,238,0.06)", blur: "blur(28px)" },
  },
  memory: {
    name: "Memory",
    color: { primary: "#7C5CFF", secondary: "#8B5CF6", accent: "#A78BFA", glow: "rgba(124,92,255,0.35)" },
    background: { base: "#070B14", gradient: "from-[#070B14] via-[#0B0918] to-[#070B14]", blob1: "rgba(124,92,255,0.1)", blob2: "rgba(139,92,246,0.05)", blob3: "rgba(167,139,250,0.03)" },
    glass: { bg: "rgba(15,10,25,0.72)", border: "rgba(124,92,255,0.06)", blur: "blur(28px)" },
  },
  humanization: {
    name: "Humanization",
    color: { primary: "#FF6B9D", secondary: "#7C5CFF", accent: "#FFB347", glow: "rgba(255,107,157,0.3)" },
    background: { base: "#070B14", gradient: "from-[#070B14] via-[#100910] to-[#070B14]", blob1: "rgba(255,107,157,0.08)", blob2: "rgba(124,92,255,0.04)", blob3: "rgba(255,179,71,0.03)" },
    glass: { bg: "rgba(20,10,15,0.72)", border: "rgba(255,107,157,0.06)", blur: "blur(28px)" },
  },
  reasoning: {
    name: "Reasoning",
    color: { primary: "#FBBF24", secondary: "#7C5CFF", accent: "#F59E0B", glow: "rgba(251,191,36,0.3)" },
    background: { base: "#070B14", gradient: "from-[#070B14] via-[#0F0E08] to-[#070B14]", blob1: "rgba(251,191,36,0.08)", blob2: "rgba(124,92,255,0.04)", blob3: "rgba(245,158,11,0.03)" },
    glass: { bg: "rgba(20,15,8,0.72)", border: "rgba(251,191,36,0.06)", blur: "blur(28px)" },
  },
  voice: {
    name: "Voice",
    color: { primary: "#00E5FF", secondary: "#7C5CFF", accent: "#22D3EE", glow: "rgba(0,229,255,0.3)" },
    background: { base: "#070B14", gradient: "from-[#070B14] via-[#0A0D18] to-[#070B14]", blob1: "rgba(0,229,255,0.08)", blob2: "rgba(124,92,255,0.04)", blob3: "rgba(34,211,238,0.03)" },
    glass: { bg: "rgba(10,15,25,0.72)", border: "rgba(0,229,255,0.06)", blur: "blur(28px)" },
  },
  deploy: {
    name: "Deployment",
    color: { primary: "#0EA5E9", secondary: "#7C5CFF", accent: "#38BDF8", glow: "rgba(14,165,233,0.3)" },
    background: { base: "#070B14", gradient: "from-[#070B14] via-[#080F18] to-[#070B14]", blob1: "rgba(14,165,233,0.08)", blob2: "rgba(124,92,255,0.04)", blob3: "rgba(56,189,248,0.03)" },
    glass: { bg: "rgba(10,15,22,0.72)", border: "rgba(14,165,233,0.06)", blur: "blur(28px)" },
  },
  industry: {
    name: "Industries",
    color: { primary: "#10B981", secondary: "#7C5CFF", accent: "#34D399", glow: "rgba(16,185,129,0.3)" },
    background: { base: "#070B14", gradient: "from-[#070B14] via-[#080F12] to-[#070B14]", blob1: "rgba(16,185,129,0.08)", blob2: "rgba(124,92,255,0.04)", blob3: "rgba(52,211,153,0.03)" },
    glass: { bg: "rgba(10,18,15,0.72)", border: "rgba(16,185,129,0.06)", blur: "blur(28px)" },
  },
  security: {
    name: "Security",
    color: { primary: "#38BDF8", secondary: "#7C5CFF", accent: "#60A5FA", glow: "rgba(56,189,248,0.3)" },
    background: { base: "#070B14", gradient: "from-[#070B14] via-[#080D16] to-[#070B14]", blob1: "rgba(56,189,248,0.08)", blob2: "rgba(124,92,255,0.04)", blob3: "rgba(96,165,250,0.03)" },
    glass: { bg: "rgba(10,14,22,0.72)", border: "rgba(56,189,248,0.06)", blur: "blur(28px)" },
  },
  cta: {
    name: "CTA",
    color: { primary: "#7C5CFF", secondary: "#00E5FF", accent: "#42FFC6", glow: "rgba(124,92,255,0.5)" },
    background: { base: "#070B14", gradient: "from-[#070B14] via-[#0A0F1F] to-[#070B14]", blob1: "rgba(124,92,255,0.15)", blob2: "rgba(0,229,255,0.08)", blob3: "rgba(66,255,198,0.06)" },
    glass: { bg: "rgba(15,23,42,0.85)", border: "rgba(124,92,255,0.12)", blur: "blur(28px)" },
  },
  footer: {
    name: "Footer",
    color: { primary: "#475569", secondary: "#64748B", accent: "#94A3B8", glow: "rgba(71,85,105,0.2)" },
    background: { base: "#050812", gradient: "from-[#050812] via-[#070B14] to-[#050812]", blob1: "rgba(71,85,105,0.04)", blob2: "rgba(100,116,139,0.02)", blob3: "rgba(148,163,184,0.01)" },
    glass: { bg: "rgba(10,14,22,0.85)", border: "rgba(255,255,255,0.04)", blur: "blur(28px)" },
  },
}

/* ─── GLASS TOKENS ─── */
export const glass = {
  subtle: "backdrop-blur-xl bg-white/[0.03] border border-white/[0.06]",
  standard: "backdrop-blur-2xl bg-[#0F172A]/80 border border-white/[0.06]",
  strong: "backdrop-blur-3xl bg-[#0F172A]/92 border border-white/[0.08]",
  premium: "backdrop-blur-2xl bg-gradient-to-b from-white/[0.05] to-white/[0.01] border border-white/[0.08]",
  glow: "backdrop-blur-2xl bg-gradient-to-b from-[#7C5CFF]/[0.08] to-transparent border border-[#7C5CFF]/15",
} as const

/* ─── ANIMATION TOKENS ─── */
export const animation = {
  spring: { type: "spring" as const, stiffness: 300, damping: 20 },
  springSnappy: { type: "spring" as const, stiffness: 400, damping: 25 },
  springGentle: { type: "spring" as const, stiffness: 200, damping: 15 },
  easeOut: { ease: [0.16, 1, 0.3, 1] as [number, number, number, number] },
  easeStandard: { ease: [0.25, 0.1, 0.25, 1] as [number, number, number, number] },
  duration: { fast: 0.2, normal: 0.4, slow: 0.6, cinematic: 0.9 },
  stagger: { fast: 0.03, normal: 0.06, slow: 0.1 },
} as const

/* ─── TYPOGRAPHY TOKENS ─── */
export const typography = {
  heading: {
    hero: "text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-bold leading-[1.05] tracking-tight",
    section: "text-3xl sm:text-4xl lg:text-5xl font-bold leading-[1.1] tracking-tight",
    card: "text-lg sm:text-xl font-semibold leading-snug tracking-tight",
  },
  body: {
    large: "text-base sm:text-lg leading-relaxed text-[#94A3B8]",
    standard: "text-sm leading-relaxed text-[#94A3B8]",
    small: "text-xs leading-relaxed text-[#64748B]",
  },
  mono: {
    label: "text-[10px] font-mono uppercase tracking-[0.25em]",
    status: "text-[10px] font-mono tracking-wider",
    data: "text-[11px] font-mono tracking-wide",
  },
} as const

/* ─── GRADIENT UTILITIES ─── */
export const gradients = {
  brand: "bg-gradient-to-r from-[#7C5CFF] via-[#00E5FF] to-[#42FFC6]",
  brandVertical: "bg-gradient-to-b from-[#7C5CFF] via-[#00E5FF] to-[#42FFC6]",
  text: "bg-gradient-to-r from-[#7C5CFF] via-[#00E5FF] to-[#42FFC6] bg-clip-text text-transparent",
  textAnimated: "bg-gradient-to-r from-[#7C5CFF] via-[#00E5FF] to-[#42FFC6] bg-clip-text text-transparent bg-[length:200%_200%] animate-aurora",
} as const

/* ─── BLUR LEVELS ─── */
export const blur = {
  subtle: "blur-[40px]",
  medium: "blur-[60px]",
  strong: "blur-[80px]",
  extreme: "blur-[120px]",
} as const
