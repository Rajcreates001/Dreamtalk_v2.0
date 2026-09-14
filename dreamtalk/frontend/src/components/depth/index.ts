/**
 * The DreamTalk depth system.
 *
 * Pick by JOB, not by looks:
 *   GlassPanel      chrome floating above content (nav, modal, toolbar)
 *   Neo*            tactile controls carved from the page (toggle, picker)
 *   TiltCard        a card with real 3D response to the cursor
 *   Spotlight       cursor-tracked light over a surface
 *   MagneticButton  one or two focal CTAs per screen
 *   ScrollReveal    entrance on scroll (GSAP ScrollTrigger)
 *   Parallax        decorative background drift — never text
 *   AuroraField     the colour field glass refracts over
 *
 * For ordinary cards use the `shadow-elev-1..4` Tailwind utilities from
 * depth.css — not glass, which needs something behind it to be worth anything.
 */
export { GlassPanel, type GlassPanelProps } from "./GlassPanel"
export { TiltCard, type TiltCardProps } from "./TiltCard"
export { Spotlight, type SpotlightProps } from "./Spotlight"
export {
  NeoButton,
  NeoToggle,
  NeoSegmented,
  type NeoButtonProps,
  type NeoToggleProps,
  type NeoSegmentedProps,
} from "./NeoControls"
export { ScrollReveal, Parallax, type ScrollRevealProps, type ParallaxProps } from "./ScrollReveal"
export { MagneticButton, type MagneticButtonProps } from "./MagneticButton"
export { AuroraField, type AuroraFieldProps } from "./AuroraField"
export { PerfGovernor } from "./PerfGovernor"
