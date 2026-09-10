# DreamTalk Astra — Design System

The visual language communicates **human identity + AI + digital presence**:
warm and organic in light, deep and intelligent in dark. All color, type, and
motion flow from centralized tokens in `src/app/globals.css`.

## Color tokens

Colors are defined once as CSS variables on `:root` (light) and `.dark`, then
exposed to Tailwind via `@theme inline`. **Never hardcode hex in components** —
use the semantic classes (`bg-background`, `text-foreground`, `bg-primary`,
`border-border`, …).

| Token | Light | Dark | Use |
| --- | --- | --- | --- |
| `--background` | `#FFF7EB` | `#262322` | page ground |
| `--background-secondary` | `#F9F0E0` | `#2E2A2A` | alternating sections |
| `--surface` / `--card` | `#F9F0E0` / `#FFFDF8` | `#322E2E` | panels, cards |
| `--surface-elevated` | `#FFFDF8` | `#3A3535` | raised surfaces |
| `--foreground` | `#2B2622` | `#F3F4F4` | primary text |
| `--foreground-muted` | `#7A7167` | `#B7ADA3` | secondary text |
| `--primary` | `#CC3A63` | `#CC3A63` | identity / primary action (pink) |
| `--secondary` / `--accent` | `#A2AB73` | `#A2AB73` | organic green |
| `--burgundy` | `#853953` | `#853953` | dark atmosphere |
| `--plum` | `#612D53` | `#612D53` | dark atmosphere |
| `--success` | `#7E8F52` | `#94A363` | success |
| `--warning` | `#C88A2E` | `#D6A44C` | warning |
| `--destructive` / `--error` | `#C0364F` | `#D84C63` | error |
| `--border` | `#E6D9C4` | `rgba(243,244,244,.10)` | lines |

**Philosophy:** pink `#CC3A63` = human identity & primary actions; green
`#A2AB73` = organic / natural / success; burgundy + plum give the dark theme its
atmosphere. Accents are used sparingly against warm neutral surfaces.

## Typography

- Display / headings — **Plus Jakarta Sans** (`--font-display`, applied to `h1–h5`)
- Body / UI — **Manrope** (`--font-sans`)
- Technical labels — mono, uppercase, tracked (`.label-mono`)
- Mono — Geist Mono (`--font-mono`)

Fonts are loaded in `src/app/layout.tsx` via `next/font/google` and wired to the
CSS variables above.

## Theme system

`next-themes` toggles the `.dark` class. Palette changes are animated (not
instant) via a global transition on `background-color`, `border-color`, and
`color` (`--theme-ease`, `420ms`). The transition is disabled under
`prefers-reduced-motion: reduce`.

## Motion

Keyframes and `@utility animate-*` helpers live in `globals.css`
(`aurora-flow`, `float`, `fade-blur-in`, `breathe`, …). Prefer ease-out /
spring-like curves and subtle scale/opacity/blur. All heavy animation collapses
under `prefers-reduced-motion`.

## Effects

`glass`, `glass-strong`, `aurora-card`, `gradient-text`, `gradient-border`,
`number-glow` — all driven by tokens, retuned to the Astra palette (no legacy
purple/cyan neon).

## Conventions

- Radius base: `--radius: 1rem`.
- Add new colors as tokens in **both** `:root` and `.dark`, then map under
  `@theme inline` — do not introduce ad-hoc hex.
