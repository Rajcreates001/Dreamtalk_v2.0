"use client"

import { forwardRef } from "react"
import { cn } from "@/lib/utils"

/* ──────────────────────────────────────────────────────────────
   Neumorphic controls.

   Soft UI has one well-known failure mode: it encodes state purely as the
   direction of a shadow, which is invisible to anyone with low vision, and it
   tends to eat the focus ring. Every control here therefore carries a
   non-shadow signal as well — a real border, a colour shift, an aria state —
   and an explicit `:focus-visible` outline from depth.css.

   These are for TACTILE controls (press, toggle, pick). Text and data
   surfaces stay on elevation/glass.
   ────────────────────────────────────────────────────────────── */

export interface NeoButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** `accent` tints the face with the brand colour for primary actions. */
  variant?: "plain" | "accent"
  size?: "sm" | "md" | "lg"
}

export const NeoButton = forwardRef<HTMLButtonElement, NeoButtonProps>(
  function NeoButton({ variant = "plain", size = "md", className, children, ...rest }, ref) {
    return (
      <button
        ref={ref}
        className={cn(
          "neo-pressable inline-flex select-none items-center justify-center gap-2 font-medium",
          "text-foreground disabled:pointer-events-none disabled:opacity-50",
          size === "sm" && "min-h-9 px-3.5 text-sm",
          // 44px is the minimum comfortable touch target.
          size === "md" && "min-h-11 px-5 text-sm",
          size === "lg" && "min-h-13 px-7 text-base",
          variant === "accent" &&
            "bg-primary text-primary-foreground [--neo-dark:rgba(120,20,50,0.45)] [--neo-light:rgba(255,255,255,0.28)]",
          className,
        )}
        {...rest}
      >
        {children}
      </button>
    )
  },
)

export interface NeoToggleProps {
  checked: boolean
  onCheckedChange: (next: boolean) => void
  label: string
  /** Render the label visibly beside the switch rather than only for AT. */
  showLabel?: boolean
  disabled?: boolean
  className?: string
}

/**
 * A switch whose track is carved into the surface and whose thumb sits proud
 * of it. State is carried by the thumb position AND by colour AND by
 * `role="switch" aria-checked` — never by the shadow alone.
 */
export function NeoToggle({
  checked,
  onCheckedChange,
  label,
  showLabel = false,
  disabled = false,
  className,
}: NeoToggleProps) {
  return (
    <label className={cn("inline-flex items-center gap-3", className)}>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={showLabel ? undefined : label}
        disabled={disabled}
        onClick={() => onCheckedChange(!checked)}
        className={cn(
          "neo-inset relative h-7 w-12 shrink-0 rounded-full p-1 transition-colors duration-200",
          "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--ring)]",
          checked && "bg-primary/85",
          disabled && "pointer-events-none opacity-50",
        )}
      >
        <span
          aria-hidden
          className={cn(
            "block size-5 rounded-full bg-[var(--surface-elevated)] shadow-elev-2",
            "transition-transform duration-200 ease-[cubic-bezier(0.16,1,0.3,1)]",
            "motion-reduce:transition-none",
            checked ? "translate-x-5" : "translate-x-0",
          )}
        />
      </button>
      {showLabel && <span className="text-sm text-foreground">{label}</span>}
    </label>
  )
}

export interface NeoSegmentedProps<T extends string> {
  options: ReadonlyArray<{ value: T; label: string; icon?: React.ReactNode }>
  value: T
  onValueChange: (next: T) => void
  /** Names the group for assistive tech, e.g. "Avatar mode". */
  label: string
  className?: string
}

/**
 * Segmented picker: the track is carved in, the active segment is raised out.
 * Implemented as a radiogroup so arrow keys work and the selection is
 * announced, which a row of buttons would not give us.
 */
export function NeoSegmented<T extends string>({
  options,
  value,
  onValueChange,
  label,
  className,
}: NeoSegmentedProps<T>) {
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className={cn("neo-inset inline-flex gap-1 rounded-full p-1", className)}
    >
      {options.map((opt) => {
        const active = opt.value === value
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={active}
            tabIndex={active ? 0 : -1}
            onClick={() => onValueChange(opt.value)}
            onKeyDown={(e) => {
              if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return
              e.preventDefault()
              const i = options.findIndex((o) => o.value === value)
              const next =
                e.key === "ArrowRight"
                  ? options[(i + 1) % options.length]
                  : options[(i - 1 + options.length) % options.length]
              onValueChange(next.value)
            }}
            className={cn(
              "inline-flex min-h-9 items-center gap-1.5 rounded-full px-4 text-sm font-medium",
              "transition-all duration-200 motion-reduce:transition-none",
              "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--ring)]",
              active
                ? "neo text-foreground"
                : "text-foreground-muted hover:text-foreground",
            )}
          >
            {opt.icon}
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}

export default NeoButton
