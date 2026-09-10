"use client"

import { Check, ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"

interface ModelOption {
  id: string
  name: string
  provider: string
}

interface ModelSelectorProps {
  label: string
  description: string
  options: readonly ModelOption[]
  value: string
  onChange: (value: string) => void
  icon?: React.ReactNode
}

export function ModelSelector({ label, description, options, value, onChange, icon }: ModelSelectorProps) {
  const selected = options.find((o) => o.id === value)

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        {icon && <span className="text-muted-foreground">{icon}</span>}
        <div>
          <h3 className="text-sm font-medium">{label}</h3>
          <p className="text-xs text-muted-foreground">{description}</p>
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {options.map((option) => (
          <button
            key={option.id}
            type="button"
            onClick={() => onChange(option.id)}
            className={cn(
              "flex items-center justify-between px-4 py-3 rounded-xl border text-left transition-all",
              value === option.id
                ? "border-emerald-500/50 bg-emerald-500/10 ring-1 ring-emerald-500/20"
                : "border-border/50 bg-muted/20 hover:bg-muted/40 hover:border-border"
            )}
          >
            <div className="flex flex-col gap-0.5">
              <span className="text-sm font-medium">{option.name}</span>
              <span className="text-[11px] text-muted-foreground">{option.provider}</span>
            </div>
            {value === option.id && (
              <Check className="h-4 w-4 text-emerald-500 shrink-0" />
            )}
          </button>
        ))}
      </div>
    </div>
  )
}
