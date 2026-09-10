"use client"

import { useState, useRef } from "react"
import { motion } from "motion/react"
import { cn } from "@/lib/utils"
import {
  Camera, Upload, Loader2, Check, Download,
  Sparkles, RotateCw, Zap, Smile, Eye, Play, Video,
} from "lucide-react"
import { API_BASE_URL } from "@/lib/constants"
import { Spinner } from "@/components/loading-states"

export default function AvatarStudioPage() {
  const [photo, setPhoto] = useState<File | null>(null)
  const [photoPreview, setPhotoPreview] = useState<string | null>(null)
  const [processing, setProcessing] = useState(false)
  const [resultVideo, setResultVideo] = useState<string | null>(null)
  const [resultImage, setResultImage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<string>("")
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setPhoto(file)
    setPhotoPreview(URL.createObjectURL(file))
    setResultVideo(null)
    setResultImage(null)
    setError(null)
  }

  const generateFromEmotion = async (emotion: string) => {
    if (!photo) {
      setError("Please upload a photo first")
      return
    }
    setProcessing(true)
    setError(null)
    setStatus(`Generating ${emotion} expression...`)

    try {
      const formData = new FormData()
      formData.append("image", photo)
      formData.append("emotion", emotion)

      const res = await fetch(`${API_BASE_URL}/api/avatar/video/liveportrait/generate-from-emotion`, {
        method: "POST",
        body: formData,
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()

      if (data.video_path) {
        setResultVideo(`${API_BASE_URL}/api/avatar/static/${data.video_path.split("/").pop()}`)
      }
      if (data.image_path) {
        setResultImage(`${API_BASE_URL}/api/avatar/static/${data.image_path.split("/").pop()}`)
      }
      setStatus("Done!")
    } catch (err: any) {
      setError(err.message || "Generation failed")
      setStatus("")
    } finally {
      setProcessing(false)
    }
  }

  const EMOTIONS = [
    { name: "Happy", emoji: "😊", color: "#22c55e" },
    { name: "Sad", emoji: "😢", color: "#3b82f6" },
    { name: "Surprised", emoji: "😮", color: "#f59e0b" },
    { name: "Angry", emoji: "😠", color: "#ef4444" },
    { name: "Neutral", emoji: "😐", color: "#6b7280" },
    { name: "Wink", emoji: "😉", color: "#a855f7" },
  ]

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-purple-500" /> Avatar Studio
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Upload a photo and animate it with LivePortrait
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Upload Section */}
        <div className="space-y-4">
          <div
            className={cn(
              "relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all",
              photoPreview ? "border-green-500/50 bg-green-500/5" : "border-muted-foreground/20 hover:border-muted-foreground/40"
            )}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleUpload}
              className="hidden"
            />
            {photoPreview ? (
              <img src={photoPreview} alt="Source" className="max-h-64 mx-auto rounded-lg" />
            ) : (
              <div className="space-y-3">
                <Camera className="h-12 w-12 mx-auto text-muted-foreground/40" />
                <p className="text-sm text-muted-foreground">Click to upload a face photo</p>
                <p className="text-xs text-muted-foreground/60">PNG, JPG, WebP</p>
              </div>
            )}
          </div>

          {/* Emotion Buttons */}
          {photoPreview && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold">Generate Expression</h3>
              <div className="grid grid-cols-3 gap-2">
                {EMOTIONS.map((em) => (
                  <button
                    key={em.name}
                    onClick={() => generateFromEmotion(em.name.toLowerCase())}
                    disabled={processing}
                    className="flex items-center gap-2 rounded-lg border p-3 text-sm hover:bg-accent disabled:opacity-50 transition-all"
                  >
                    <span className="text-lg">{em.emoji}</span>
                    <span>{em.name}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {processing && (
            <div className="flex items-center gap-3 p-4 rounded-lg bg-primary/5 border border-primary/20">
              <Spinner size="md" />
              <div>
                <div className="text-sm font-medium">{status || "Processing..."}</div>
                <div className="text-xs text-muted-foreground">LivePortrait is animating your photo</div>
              </div>
            </div>
          )}

          {error && (
            <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-sm text-red-500">
              {error}
            </div>
          )}
        </div>

        {/* Result Section */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold">Result</h3>
          {resultVideo ? (
            <div className="rounded-xl overflow-hidden border">
              <video src={resultVideo} controls autoPlay loop className="w-full" />
            </div>
          ) : resultImage ? (
            <div className="rounded-xl overflow-hidden border">
              <img src={resultImage} alt="Result" className="w-full" />
            </div>
          ) : (
            <div className="border-2 border-dashed rounded-xl p-12 text-center text-muted-foreground/40">
              <Video className="h-12 w-12 mx-auto mb-3" />
              <p className="text-sm">Upload a photo and pick an expression</p>
              <p className="text-xs mt-1">LivePortrait will animate the face</p>
            </div>
          )}

          {/* How it works */}
          <div className="p-4 rounded-xl border bg-card text-sm space-y-2">
            <h4 className="font-semibold">How it works</h4>
            <div className="flex items-start gap-2 text-muted-foreground">
              <span className="text-blue-500 font-bold">1.</span>
              Upload a clear face photo
            </div>
            <div className="flex items-start gap-2 text-muted-foreground">
              <span className="text-blue-500 font-bold">2.</span>
              Choose an expression (happy, sad, etc.)
            </div>
            <div className="flex items-start gap-2 text-muted-foreground">
              <span className="text-blue-500 font-bold">3.</span>
              LivePortrait animates the face using neural rendering
            </div>
            <div className="flex items-start gap-2 text-muted-foreground">
              <span className="text-blue-500 font-bold">4.</span>
              Download the result or use in your digital twin
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
