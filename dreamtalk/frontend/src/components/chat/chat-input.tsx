"use client"

import { useState, useRef, type KeyboardEvent } from "react"
import { Send, Mic, Square } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

interface ChatInputProps {
  onSend: (message: string) => void
  onStop: () => void
  isLoading: boolean
  disabled?: boolean
}

export function ChatInput({ onSend, onStop, isLoading, disabled }: ChatInputProps) {
  const [input, setInput] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed || isLoading) return
    onSend(trimmed)
    setInput("")
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = "auto"
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`
  }

  return (
    <div className="flex items-end gap-2 bg-background/80 backdrop-blur-sm p-4 border-t border-border">
      <div className="relative flex-1">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder="Type your message..."
          rows={1}
          disabled={disabled}
          className={cn(
            "w-full resize-none rounded-2xl bg-muted/50 border border-border px-4 py-3 pr-12 text-sm",
            "placeholder:text-muted-foreground/50",
            "focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/50",
            "transition-all duration-200",
            disabled && "opacity-50 cursor-not-allowed"
          )}
        />
        <Button
          size="icon"
          variant="ghost"
          className="absolute right-1.5 bottom-1.5 h-8 w-8 text-muted-foreground hover:text-foreground"
          onClick={() => {}}
        >
          <Mic className="h-4 w-4" />
        </Button>
      </div>
      {isLoading ? (
        <Button size="icon" variant="destructive" onClick={onStop} className="h-10 w-10 shrink-0 rounded-xl">
          <Square className="h-4 w-4 fill-current" />
        </Button>
      ) : (
        <Button
          size="icon"
          onClick={handleSend}
          disabled={!input.trim() || disabled}
          className="h-10 w-10 shrink-0 rounded-xl"
        >
          <Send className="h-4 w-4" />
        </Button>
      )}
    </div>
  )
}
