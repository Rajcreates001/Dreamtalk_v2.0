"use client";

import React, { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";

interface AudioPlayerProps {
  src: string;
  autoPlay?: boolean;
  onPlay?: () => void;
  onPause?: () => void;
  onEnded?: () => void;
}

export function AudioPlayer({
  src,
  autoPlay = false,
  onPlay,
  onPause,
  onEnded,
}: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handlers = {
      play: () => {
        setIsPlaying(true);
        onPlay?.();
      },
      pause: () => {
        setIsPlaying(false);
        onPause?.();
      },
      ended: () => {
        setIsPlaying(false);
        onEnded?.();
      },
      timeupdate: () => setCurrentTime(audio.currentTime),
      loadedmetadata: () => setDuration(audio.duration),
      error: () => setError("Failed to load audio"),
    };

    audio.addEventListener("play", handlers.play);
    audio.addEventListener("pause", handlers.pause);
    audio.addEventListener("ended", handlers.ended);
    audio.addEventListener("timeupdate", handlers.timeupdate);
    audio.addEventListener("loadedmetadata", handlers.loadedmetadata);
    audio.addEventListener("error", handlers.error);

    return () => {
      audio.removeEventListener("play", handlers.play);
      audio.removeEventListener("pause", handlers.pause);
      audio.removeEventListener("ended", handlers.ended);
      audio.removeEventListener("timeupdate", handlers.timeupdate);
      audio.removeEventListener("loadedmetadata", handlers.loadedmetadata);
      audio.removeEventListener("error", handlers.error);
    };
  }, [onPlay, onPause, onEnded]);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play().catch(() => setError("Playback failed"));
    }
  };

  const formatTime = (s: number) => {
    if (!isFinite(s)) return "0:00";
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  if (error) {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-600 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
        {error}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3 rounded-lg border bg-background p-3">
      <audio ref={audioRef} src={src} preload="metadata" autoPlay={autoPlay} />
      <Button
        onClick={togglePlay}
        size="sm"
        variant={isPlaying ? "secondary" : "default"}
        className="h-9 w-9 rounded-full p-0"
      >
        {isPlaying ? "⏸" : "▶️"}
      </Button>
      <div className="flex-1">
        <div className="h-1.5 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full bg-primary transition-all"
            style={{
              width: duration ? `${(currentTime / duration) * 100}%` : "0%",
            }}
          />
        </div>
        <div className="mt-1 flex justify-between text-xs text-muted-foreground">
          <span>{formatTime(currentTime)}</span>
          <span>{formatTime(duration)}</span>
        </div>
      </div>
    </div>
  );
}

// ── Standalone fetcher — given a TTS path, resolves the audio URL ──
export function TTSPlayer({
  ttsPath,
  language = "en",
}: {
  ttsPath: string;
  language?: string;
}) {
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ttsPath) return;
    // Fetch the base64 audio from the backend
    fetch(
      `/api/avatar/tts/audio?path=${encodeURIComponent(ttsPath)}&language=${language}`
    )
      .then((r) => r.json())
      .then((data) => {
        if (data.base64) {
          setAudioUrl(`data:audio/wav;base64,${data.base64}`);
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [ttsPath, language]);

  if (loading) return <div className="text-sm text-muted-foreground">Loading audio...</div>;
  if (!audioUrl) return <div className="text-sm text-muted-foreground">No audio available</div>;

  return <AudioPlayer src={audioUrl} autoPlay />;
}
