// Dreamtalk - Frontend UI
// Based on shadcn/ui (MIT License)
// Source: shadcn-ui

import * as React from "react"
import { DayPicker } from "react-day-picker"

import { cn } from "@/lib/utils"

function Calendar(props: React.ComponentProps<typeof DayPicker>) {
  return (
    <DayPicker
      className={cn("p-3", props.className)}
      {...props}
    />
  )
}

export { Calendar }
