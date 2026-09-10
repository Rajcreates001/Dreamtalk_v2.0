"use client"

import { cn } from "@/lib/utils"
import type { Message } from "@/types/chat"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

interface ChatMessageProps {
  message: Message
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user"
  const audioUrl = (message as any).audioUrl

  return (
    <div className={cn("flex gap-3 w-full animate-in fade-in slide-in-from-bottom-2 duration-300", isUser ? "flex-row-reverse" : "flex-row")}>
      <Avatar className={cn("h-8 w-8 shrink-0", isUser ? "" : "")}>
        {isUser ? (
          <AvatarFallback className="bg-primary/10 text-primary text-xs">U</AvatarFallback>
        ) : (
          <>
            <AvatarImage src="/images/doctor-avatar.png" alt="Doctor" />
            <AvatarFallback className="bg-emerald-500/10 text-emerald-600 text-xs">D</AvatarFallback>
          </>
        )}
      </Avatar>
      <div className={cn("flex flex-col gap-1 max-w-[80%]", isUser ? "items-end" : "items-start")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
            isUser
              ? "bg-primary text-primary-foreground rounded-tr-md"
              : "bg-muted/50 text-foreground rounded-tl-md border border-border/50"
          )}
        >
          {message.content}
        </div>
        {/* TTS Audio Player */}
        {!isUser && audioUrl && (
          <div className="mt-1 w-full max-w-[280px]">
            <audio
              src={audioUrl.startsWith("http") ? audioUrl : `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001"}${audioUrl}`}
              controls
              autoPlay
              className="w-full h-8 rounded-lg"
              preload="auto"
              onError={(e) => console.error("Audio load error:", audioUrl, e)}
            />
          </div>
        )}
        {message.emotion && !isUser && (
          <span className="text-[10px] text-muted-foreground/60 px-1">
            {message.emotion === "happy" ? "😊" : message.emotion === "sad" ? "😢" : message.emotion === "angry" ? "😠" : message.emotion === "fear" ? "😨" : message.emotion === "surprise" ? "😮" : "😐"} {message.emotion}
          </span>
        )}
      </div>
    </div>
  )
}
