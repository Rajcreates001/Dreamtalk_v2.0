"use client"

import { useCallback, useEffect, useState } from "react"
import { avatarRuntime } from "./client"
import type { AvatarProfile, RespondResult } from "./types"

export interface ChatTurn { role: "user" | "assistant"; content: string; emotion?: string }

/**
 * Conversation state bound to the avatar runtime. Loads the user's profiles,
 * sends text to `respond`, and exposes the latest spoken result for the
 * renderer to play.
 */
export function useAvatarChat(options: { renderVideo?: boolean } = {}) {
  const [profiles, setProfiles] = useState<AvatarProfile[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [speech, setSpeech] = useState<RespondResult | null>(null)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loadingProfiles, setLoadingProfiles] = useState(true)

  useEffect(() => {
    let alive = true
    avatarRuntime.listProfiles()
      .then((r) => {
        if (!alive) return
        setProfiles(r.profiles ?? [])
        setActiveId(r.active_profile_id ?? r.profiles?.[0]?.id ?? null)
      })
      .catch(() => { if (alive) setProfiles([]) })
      .finally(() => { if (alive) setLoadingProfiles(false) })
    return () => { alive = false }
  }, [])

  const activeProfile = profiles.find((p) => p.id === activeId) ?? null

  const send = useCallback(async (message: string, language = "auto") => {
    const text = message.trim()
    if (!text || sending) return
    setError(null)
    setSending(true)
    setTurns((prev) => [...prev, { role: "user", content: text }])
    try {
      const history = turns.slice(-8).map((t) => ({ role: t.role, content: t.content }))
      const result = activeId
        ? await avatarRuntime.respond(activeId, { message: text, language, history, render_video: options.renderVideo ?? false })
        : await avatarRuntime.chat({ message: text, language, history, render_video: options.renderVideo ?? false })
      setTurns((prev) => [...prev, { role: "assistant", content: result.text || result.response, emotion: result.emotion }])
      setSpeech(result)
    } catch (e) {
      setError((e as Error)?.message?.includes("HTTP") || (e as Error)?.message?.includes("fetch")
        ? "Couldn't reach the avatar runtime. Is the backend running and are you signed in?"
        : (e as Error)?.message || "Failed to get a response.")
    } finally {
      setSending(false)
    }
  }, [activeId, sending, turns, options.renderVideo])

  return {
    profiles, activeId, setActiveId, activeProfile, loadingProfiles,
    turns, speech, sending, error, send,
  }
}
