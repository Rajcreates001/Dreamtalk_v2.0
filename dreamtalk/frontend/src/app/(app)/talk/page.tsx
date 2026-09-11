import type { Metadata } from "next"
import { AvatarConversation } from "@/features/studio/AvatarConversation"

export const metadata: Metadata = {
  title: "Studio — DreamTalk",
  description: "Talk to your digital human — it speaks your replies in your cloned voice.",
}

export default function TalkStudioPage() {
  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-6">
        <span className="label-mono">Studio</span>
        <h1 className="mt-1 font-display text-3xl font-bold">Talk to your digital human</h1>
        <p className="mt-1 text-foreground-muted">Type a message — your twin responds in its cloned voice, with real lip-sync.</p>
      </div>
      <AvatarConversation />
    </div>
  )
}
