"use client";

import React, { useState, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/loading-states";

interface VoiceRecorderProps {
  onRecordingComplete?: (blob: Blob) => void;
  maxDuration?: number; // seconds
}

export function VoiceRecorder({
  onRecordingComplete,
  maxDuration = 30,
}: VoiceRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [duration, setDuration] = useState(0);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: "audio/webm;codecs=opus",
      });

      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const url = URL.createObjectURL(blob);
        setAudioUrl(url);
        onRecordingComplete?.(blob);
        stream.getTracks().forEach((t) => t.stop());
      };

      mediaRecorder.start(100); // collect data every 100ms
      setIsRecording(true);
      setIsPaused(false);
      setDuration(0);
      setAudioUrl(null);
      setUploadResult(null);

      timerRef.current = setInterval(() => {
        setDuration((d) => {
          if (d >= maxDuration) {
            stopRecording();
            return d;
          }
          return d + 1;
        });
      }, 1000);
    } catch (err) {
      console.error("Failed to start recording:", err);
    }
  }, [maxDuration, onRecordingComplete]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state !== "inactive") {
      mediaRecorderRef.current?.stop();
    }
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setIsRecording(false);
    setIsPaused(false);
  }, []);

  const pauseRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.pause();
      setIsPaused(true);
      if (timerRef.current) clearInterval(timerRef.current);
    }
  }, []);

  const resumeRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === "paused") {
      mediaRecorderRef.current.resume();
      setIsPaused(false);
      timerRef.current = setInterval(() => {
        setDuration((d) => d + 1);
      }, 1000);
    }
  }, []);

  const uploadForCloning = useCallback(
    async (blob: Blob) => {
      setIsUploading(true);
      try {
        const formData = new FormData();
        formData.append("audio", blob, "voice_sample.webm");
        const resp = await fetch("/api/v1/digital-twins/voice/upload", {
          method: "POST",
          body: formData,
        });
        const data = await resp.json();
        setUploadResult(
          resp.ok
            ? `Voice profile created! ID: ${data.voice_id || "unknown"}`
            : `Upload failed: ${data.detail || "unknown error"}`
        );
      } catch (err) {
        setUploadResult(`Upload error: ${err}`);
      } finally {
        setIsUploading(false);
      }
    },
    []
  );

  const formatTime = (s: number) =>
    `${Math.floor(s / 60)
      .toString()
      .padStart(2, "0")}:${(s % 60).toString().padStart(2, "0")}`;

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          🎤 Voice Recorder
          {isRecording && (
            <span className="flex items-center gap-1 text-sm text-red-500">
              <span className="h-2 w-2 animate-pulse rounded-full bg-red-500" />
              REC
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Timer */}
        <div className="text-center text-3xl font-mono">
          {formatTime(duration)}
          <span className="text-sm text-muted-foreground">
            {" "}
            / {formatTime(maxDuration)}
          </span>
        </div>

        {/* Progress bar */}
        <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full bg-primary transition-all"
            style={{ width: `${(duration / maxDuration) * 100}%` }}
          />
        </div>

        {/* Controls */}
        <div className="flex justify-center gap-3">
          {!isRecording ? (
            <Button
              onClick={startRecording}
              size="lg"
              className="rounded-full bg-red-500 px-6 hover:bg-red-600"
            >
              🎙️ Start Recording
            </Button>
          ) : (
            <>
              {!isPaused ? (
                <Button onClick={pauseRecording} variant="outline" size="lg">
                  ⏸️ Pause
                </Button>
              ) : (
                <Button onClick={resumeRecording} variant="outline" size="lg">
                  ▶️ Resume
                </Button>
              )}
              <Button
                onClick={stopRecording}
                size="lg"
                variant="destructive"
              >
                ⏹️ Stop
              </Button>
            </>
          )}
        </div>

        {/* Playback */}
        {audioUrl && (
          <div className="space-y-3">
            <audio src={audioUrl} controls className="w-full" />
            <Button
              onClick={() => {
                const a = chunksRef.current[0];
                if (a) uploadForCloning(a);
              }}
              disabled={isUploading}
              className="w-full"
              variant="outline"
            >
              {isUploading ? (
                <Spinner size="sm" />
              ) : (
                "🔧 Use for Voice Cloning"
              )}
            </Button>
            {uploadResult && (
              <p
                className={`text-center text-sm ${
                  uploadResult.includes("failed")
                    ? "text-red-500"
                    : "text-green-500"
                }`}
              >
                {uploadResult}
              </p>
            )}
          </div>
        )}

        <p className="text-center text-xs text-muted-foreground">
          Record a 10-30 second voice sample for cloning. Speak naturally.
        </p>
      </CardContent>
    </Card>
  );
}
