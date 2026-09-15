"use client"

import { useState, useRef } from "react"
import { motion, AnimatePresence } from "motion/react"
import { useRouter } from "next/navigation"
import { cn } from "@/lib/utils"
import { Camera, Mic, Sparkles,
  Upload, Video, ChevronRight, ChevronLeft,
  Check, Loader2, FileText, Link, BookOpen,
  Wand2, Zap, Music,
} from "lucide-react"
import { digitalTwinApi } from "@/lib/api"
import { avatarRuntime } from "@/services/avatar/client"

const RELATIONSHIPS = [
  "Friend", "Father", "Mother", "Brother", "Sister",
  "Grandfather", "Grandmother", "Partner", "Teacher",
  "Doctor", "Mentor", "CEO", "Colleague", "Therapist",
  "Coach", "Best Friend", "Custom",
]

const PERSONALITY_TRAITS = [
  "Friendly", "Funny", "Calm", "Strict", "Motivational",
  "Professional", "Emotional", "Logical", "Patient",
  "Compassionate", "Creative", "Confident", "Witty",
  "Energetic", "Gentle",
]

const GENDERS = ["Male", "Female"]
const REGIONS = [
  "Indian English", "American", "British", "Australian",
  "Hindi", "Tamil", "Telugu", "Kannada", "Malayalam",
  "Marathi", "Punjabi", "Gujarati", "Bengali", "Urdu",
]
const AGE_GROUPS = ["Child", "Teen", "Young Adult", "Adult", "Senior"]
const ACCENTS = ["Professional", "Friendly", "Soft", "Calm", "Energetic", "Warm"]
const EMOTION_BIASES = ["Neutral", "Happy", "Calm", "Professional", "Supportive"]

/* These mirror the calls handleGenerate actually makes. The old list
 * included "Connecting Memories" and "Initializing Conversation", which
 * corresponded to nothing and ticked green regardless. */
const BUILD_STEPS = [
  { id: "face", label: "Building face mesh" },
  { id: "voice", label: "Cloning voice" },
  { id: "activate", label: "Activating avatar" },
  { id: "personality", label: "Adding personality" },
]

const STEP_LABELS = ["Photo", "Voice", "Brain", "Relationship", "Personality"]

export default function CreateDigitalHumanPage() {
  const router = useRouter()
  const [step, setStep] = useState(0)
  const [photo, setPhoto] = useState<File | null>(null)
  const [photoPreview, setPhotoPreview] = useState<string | null>(null)
  const [voiceMethod, setVoiceMethod] = useState<"upload" | "generate" | null>(null)
  const [voiceFile, setVoiceFile] = useState<File | null>(null)
  const [brainTab, setBrainTab] = useState<"documents" | "describe">("documents")
  const [describeText, setDescribeText] = useState("")
  const [relationship, setRelationship] = useState("")
  const [traits, setTraits] = useState<string[]>([])
  const [voiceGender, setVoiceGender] = useState("Male")
  const [voiceAge, setVoiceAge] = useState("Adult")
  const [voiceRegion, setVoiceRegion] = useState("Indian English")
  const [voiceAccent, setVoiceAccent] = useState("Professional")
  const [voiceEmotion, setVoiceEmotion] = useState("Neutral")
  const [generating, setGenerating] = useState(false)
  const [buildProgress, setBuildProgress] = useState(0)
  const [currentStepLabel, setCurrentStepLabel] = useState("")
  const [generated, setGenerated] = useState(false)
  const [generatedTwinId, setGeneratedTwinId] = useState<string>("")
  const [error, setError] = useState<string | null>(null)
  const [avatarName, setAvatarName] = useState("")
  const [consent, setConsent] = useState(false)
  /** Non-fatal problems from the optional brain/personality calls. */
  const [warnings, setWarnings] = useState<string[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const cameraInputRef = useRef<HTMLInputElement>(null)

  const handlePhotoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      const file = e.target.files[0]
      setPhoto(file)
      setPhotoPreview(URL.createObjectURL(file))
    }
  }

  const handleVoiceUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setVoiceFile(e.target.files[0])
    }
  }

  const toggleTrait = (trait: string) => {
    setTraits((prev) =>
      prev.includes(trait) ? prev.filter((t) => t !== trait) : [...prev, trait]
    )
  }

  const canProceed = () => {
    switch (step) {
      case 0: return !!photo && avatarName.trim().length > 0
      // Cloning needs a real recording of the real voice. The synthetic
      // option produces a stand-in voice and no clone, so it cannot satisfy
      // this step on its own.
      case 1: return !!voiceFile
      case 2: return brainTab === "documents" ? true : describeText.trim().length > 10
      case 3: return !!relationship
      // Building the avatar sends a face photo and a voice recording to the
      // runtime, which derives a face mesh and a voice clone from them. That
      // is biometric data, so it must not be uploaded on an assumption.
      case 4: return traits.length > 0 && consent
      default: return false
    }
  }

  const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

  const updateBuildStep = (label: string) => {
    setCurrentStepLabel(label)
  }

  /* ═══════════════════════════════════════════════════════════════════
   * This wizard used to build only a `digital_twins` row: it uploaded the
   * photo and voice to that subsystem, reported "Face created · Voice
   * cloned", and finished. But digital_twins rows never leave status
   * "draft" and never gain a mesh, a texture or a voice clone — every twin
   * in the database is proof of that. The avatars that can actually speak
   * live in `avatar_profiles`, built by POST /api/v1/avatar/profiles, and
   * nothing in the UI ever called it. That is why the app appeared to
   * create no avatars: the only creation path could not produce one.
   *
   * The runtime call is now the step that matters, and it is the step that
   * is allowed to fail the build. The twin-side calls that follow carry the
   * optional brain/personality extras and are reported as warnings.
   * ═══════════════════════════════════════════════════════════════════ */
  const handleGenerate = async () => {
    setGenerating(true)
    setBuildProgress(0)
    setError(null)
    setWarnings([])

    try {
      if (!photo) throw new Error("A face photo is required to build an avatar.")
      if (!voiceFile) {
        throw new Error(
          "A voice recording is required to clone a voice. Go back to the Voice step and upload a sample."
        )
      }
      if (!consent) throw new Error("Consent is required before biometric data is uploaded.")

      // 1. Build the real avatar: face mesh, GLB, texture and voice clone.
      //    This is the long pole — the runtime runs FLAME and the clone
      //    engine inline — so the progress bar sits here deliberately.
      updateBuildStep(
        "Building face mesh and cloning voice… this takes several minutes, keep this tab open"
      )
      setBuildProgress(15)
      const profile = await avatarRuntime.createProfile({
        name: avatarName.trim(),
        voiceSample: voiceFile,
        faceImages: [photo],
        consentConfirmed: true,
        consentSubjectName: avatarName.trim(),
        language: "auto",
      })
      if (!profile?.id) throw new Error("The avatar runtime did not return a profile.")
      if (!profile.appearance?.glb_url) {
        throw new Error("The avatar was saved, but its 3D head could not be generated. Please retry with a clear front-facing photo.")
      }
      if (!profile.voice?.validation?.cloned) {
        throw new Error(String(profile.voice?.validation_error || "The avatar was saved, but voice cloning could not be verified. Please retry when the voice engine is available."))
      }
      setBuildProgress(70)

      // Make it the avatar /live talks to.
      updateBuildStep("Activating avatar…")
      await avatarRuntime.activate(profile.id)
      setBuildProgress(80)

      /* 2. Optional extras. A failure here leaves a working avatar that
       *    simply lacks the personality/knowledge trimmings, so it is
       *    surfaced as a warning rather than thrown away as an error. */
      updateBuildStep("Adding personality and knowledge…")
      const notes: string[] = []
      try {
        const twin = await digitalTwinApi.create({
          name: avatarName.trim(),
          description: describeText || undefined,
          personality: traits.join(", "),
        })
        const twinId = twin.id || twin._id || twin.twin_id
        if (twinId) {
          if (brainTab === "describe" && describeText.trim()) {
            const formData = new FormData()
            formData.append("file", new Blob([describeText], { type: "text/plain" }), "description.txt")
            await digitalTwinApi.uploadKnowledge(twinId, formData)
          }
          await digitalTwinApi.setPersonality(twinId, {
            traits,
            description: describeText || undefined,
          })
          await digitalTwinApi.initializePersonality(twinId)
          if (relationship) await digitalTwinApi.setRelationship(twinId, { type: relationship })
        }
      } catch (err) {
        notes.push(
          err instanceof Error
            ? `Personality and knowledge were not saved: ${err.message}`
            : "Personality and knowledge were not saved."
        )
      }
      setWarnings(notes)
      setBuildProgress(100)

      await sleep(300)
      setGenerated(true)
      setGeneratedTwinId(profile.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed. Please try again.")
      setGenerating(false)
    }
  }

  if (generated) {
    return (
      <div className="max-w-2xl mx-auto text-center py-16 space-y-8">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 200, damping: 15 }}
          className="w-24 h-24 mx-auto rounded-full bg-gradient-to-br from-secondary/20 to-secondary/20 border border-secondary/20 flex items-center justify-center"
        >
          <Check className="h-10 w-10 text-secondary" />
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <h1 className="text-3xl font-bold text-foreground mb-2">
            {avatarName.trim() || "Your avatar"} is ready
          </h1>
          <p className="text-foreground-muted mb-2">
            Face mesh built · Voice cloned · Set as your active avatar
          </p>
          {/* Anything the optional brain/personality step could not save is
              stated here rather than folded into the success line. */}
          {warnings.length > 0 && (
            <ul className="mx-auto mb-4 max-w-md space-y-1 text-xs text-foreground-muted">
              {warnings.map((w) => <li key={w}>{w}</li>)}
            </ul>
          )}
          <div className="mt-6 flex items-center justify-center gap-4">
            <button
              onClick={() => router.push("/live")}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-primary to-secondary text-white font-medium shadow-lg shadow-primary/20 hover:shadow-primary/30 transition-all"
            >
              <Sparkles className="h-4 w-4" />
              Talk to {avatarName.trim() || "your avatar"}
            </button>
            <button
              onClick={() => {
                setStep(0)
                setGenerated(false)
                setPhoto(null)
                setPhotoPreview(null)
                setVoiceMethod(null)
                setVoiceFile(null)
                setDescribeText("")
                setRelationship("")
                setTraits([])
                setError(null)
                setAvatarName("")
                setConsent(false)
                setWarnings([])
              }}
              className="px-6 py-3 rounded-xl bg-foreground/[0.04] border border-foreground/[0.06] text-foreground-muted hover:text-foreground transition-all"
            >
              Create Another
            </button>
          </div>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* ── Header ── */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-10"
      >
        <h1 className="text-3xl font-bold text-foreground mb-2">Create Digital Human</h1>
        <p className="text-foreground-muted">
          Step {step + 1} of 5 · {STEP_LABELS[step]}
        </p>
      </motion.div>

      {/* ── Progress Bar ── */}
      <div className="flex items-center justify-center gap-2 mb-10">
        {STEP_LABELS.map((label, i) => (
          <div key={label} className="flex items-center gap-2">
            <button
              onClick={() => i < step && setStep(i)}
              className={cn(
                "flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs transition-all",
                i === step
                  ? "bg-primary/15 text-primary border border-primary/20"
                  : i < step
                    ? "bg-secondary/10 text-secondary border border-secondary/20 cursor-pointer"
                    : "bg-foreground/[0.04] text-foreground-muted border border-transparent"
              )}
            >
              {i < step ? <Check className="h-3 w-3" /> : <span>{i + 1}</span>}
              <span className="hidden sm:inline">{label}</span>
            </button>
            {i < 4 && (
              <div
                className={cn(
                  "w-8 h-px",
                  i < step ? "bg-secondary/40" : "bg-foreground/[0.06]"
                )}
              />
            )}
          </div>
        ))}
      </div>

      {/* ── Error ── */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -5 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-lg mx-auto mb-6 px-4 py-3 rounded-xl bg-destructive/10 border border-destructive/20 text-xs text-destructive text-center"
        >
          {error}
        </motion.div>
      )}

      {/* ── Step Content ── */}
      <AnimatePresence mode="wait">
        <motion.div
          key={step}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.3 }}
        >
          {/* ═══════════ STEP 1: PHOTO ═══════════ */}
          {step === 0 && (
            <div className="space-y-6">
              <div className="text-center">
                <h2 className="text-xl font-semibold text-foreground mb-1">Name and Photo</h2>
                <p className="text-sm text-foreground-muted">
                  The photo becomes the 3D face mesh and the 2D talking head
                </p>
              </div>

              <div className="mx-auto max-w-md">
                <label htmlFor="avatar-name" className="mb-1.5 block text-sm font-medium text-foreground">
                  Avatar name
                </label>
                <input
                  id="avatar-name"
                  type="text"
                  value={avatarName}
                  onChange={(e) => setAvatarName(e.target.value)}
                  placeholder="e.g. KB"
                  maxLength={60}
                  className="w-full rounded-xl border border-foreground/[0.08] bg-foreground/[0.04] px-4 py-2.5 text-sm text-foreground outline-none placeholder:text-foreground-muted focus:border-primary/40"
                />
              </div>

              {/* Upload area */}
              <div
                onClick={() => fileInputRef.current?.click()}
                className={cn(
                  "relative border-2 border-dashed rounded-2xl p-12 text-center transition-all cursor-pointer mx-auto max-w-md",
                  photoPreview
                    ? "border-secondary/30 bg-secondary/5"
                    : "border-foreground/[0.08] hover:border-primary/30 hover:bg-primary/5"
                )}
              >
                {photoPreview ? (
                  <div className="space-y-3">
                    <div className="w-32 h-32 mx-auto rounded-full overflow-hidden border-2 border-secondary/30">
                      <img src={photoPreview} alt="Preview" className="w-full h-full object-cover" />
                    </div>
                    <p className="text-xs text-secondary font-medium">Photo uploaded</p>
                    <p className="text-[10px] text-foreground-muted">Click to change</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="w-20 h-20 mx-auto rounded-full bg-foreground/[0.04] border border-foreground/[0.06] flex items-center justify-center">
                      <Camera className="h-8 w-8 text-foreground-muted" />
                    </div>
                    <div>
                      <p className="text-sm text-foreground-muted font-medium">Drop photo here or click to browse</p>
                      <p className="text-xs text-foreground-muted mt-1">PNG, JPEG, WEBP, HEIC · Up to 20MB</p>
                    </div>
                  </div>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handlePhotoUpload}
                  className="hidden"
                />
              </div>

              {/* Quick actions */}
              <div className="flex justify-center gap-3">
                <button
                  onClick={() => cameraInputRef.current?.click()}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-foreground/[0.04] border border-foreground/[0.06] text-xs text-foreground-muted hover:text-foreground transition-all"
                >
                  <Video className="h-3.5 w-3.5" />
                  Use Camera
                </button>
                <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-foreground/[0.04] border border-foreground/[0.06] text-xs text-foreground-muted hover:text-foreground transition-all">
                  <Upload className="h-3.5 w-3.5" />
                  Upload Video
                </button>
              </div>
              <input ref={cameraInputRef} type="file" accept="image/*" capture="environment" onChange={handlePhotoUpload} className="hidden" />
            </div>
          )}

          {/* ═══════════ STEP 2: VOICE ═══════════ */}
          {step === 1 && (
            <div className="space-y-6">
              <div className="text-center">
                <h2 className="text-xl font-semibold text-foreground mb-1">Choose Voice</h2>
                <p className="text-sm text-foreground-muted">
                  Around thirty seconds of clear speech is enough to clone this voice
                </p>
              </div>

              {/* Options */}
              <div className="grid sm:grid-cols-2 gap-4 max-w-lg mx-auto">
                <button
                  onClick={() => setVoiceMethod("upload")}
                  className={cn(
                    "p-6 rounded-2xl border text-center transition-all",
                    voiceMethod === "upload"
                      ? "bg-primary/15 border-primary/20"
                      : "bg-foreground/[0.04] border-foreground/[0.06] hover:border-primary/20 hover:bg-primary/5"
                  )}
                >
                  <Mic className="h-8 w-8 mx-auto mb-3" style={{ color: voiceMethod === "upload" ? "var(--primary)" : "var(--foreground-muted)" }} />
                  <p className="text-sm font-medium text-foreground mb-1">Upload Voice</p>
                  <p className="text-xs text-foreground-muted">Required to clone this voice</p>
                </button>
                <button
                  onClick={() => setVoiceMethod("generate")}
                  className={cn(
                    "p-6 rounded-2xl border text-center transition-all",
                    voiceMethod === "generate"
                      ? "bg-primary/15 border-primary/20"
                      : "bg-foreground/[0.04] border-foreground/[0.06] hover:border-primary/20 hover:bg-primary/5"
                  )}
                >
                  <Wand2 className="h-8 w-8 mx-auto mb-3" style={{ color: voiceMethod === "generate" ? "var(--primary)" : "var(--foreground-muted)" }} />
                  <p className="text-sm font-medium text-foreground mb-1">Generate AI Voice</p>
                  <p className="text-xs text-foreground-muted">Choose gender, age, region</p>
                </button>
              </div>

              {/* Upload form */}
              {voiceMethod === "upload" && (
                <div
                  onClick={() => {
                    const input = document.createElement("input")
                    input.type = "file"
                    input.accept = "audio/*"
                    input.onchange = (e: any) => {
                      if (e.target.files?.[0]) setVoiceFile(e.target.files[0])
                    }
                    input.click()
                  }}
                  className="max-w-lg mx-auto border-2 border-dashed rounded-xl p-6 text-center cursor-pointer hover:border-primary/30 transition-all"
                  style={{ borderColor: voiceFile ? "var(--secondary)" : "rgba(255,255,255,0.08)" }}
                >
                  {voiceFile ? (
                    <div className="space-y-2">
                      <Music className="h-6 w-6 mx-auto text-secondary" />
                      <p className="text-xs text-secondary">{voiceFile.name}</p>
                      <p className="text-[10px] text-foreground-muted">Click to change</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <Upload className="h-6 w-6 mx-auto text-foreground-muted" />
                      <p className="text-xs text-foreground-muted">MP3, WAV, M4A, FLAC, OGG</p>
                    </div>
                  )}
                </div>
              )}

              {/* Generate form */}
              {voiceMethod === "generate" && (
                <div className="max-w-lg mx-auto space-y-4 p-6 rounded-2xl bg-card/80 border border-foreground/[0.06]">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-[10px] text-foreground-muted mb-1 block">Gender</label>
                      <div className="flex gap-1.5">
                        {GENDERS.map((g) => (
                          <button
                            key={g}
                            onClick={() => setVoiceGender(g)}
                            className={cn(
                              "flex-1 px-3 py-2 rounded-lg text-xs transition-all border",
                              voiceGender === g
                                ? "bg-primary/15 border-primary/20 text-foreground"
                                : "bg-foreground/[0.04] border-foreground/[0.06] text-foreground-muted"
                            )}
                          >
                            {g}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <label className="text-[10px] text-foreground-muted mb-1 block">Age</label>
                      <select
                        value={voiceAge}
                        onChange={(e) => setVoiceAge(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg bg-foreground/[0.04] border border-foreground/[0.06] text-xs text-foreground [&>option]:text-card"
                      >
                        {AGE_GROUPS.map((a) => (
                          <option key={a}>{a}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="text-[10px] text-foreground-muted mb-1 block">Region / Language</label>
                    <div className="flex flex-wrap gap-1.5">
                      {REGIONS.slice(0, 8).map((r) => (
                        <button
                          key={r}
                          onClick={() => setVoiceRegion(r)}
                          className={cn(
                            "px-2.5 py-1.5 rounded-lg text-[10px] transition-all border",
                            voiceRegion === r
                              ? "bg-primary/15 border-primary/20 text-foreground"
                              : "bg-foreground/[0.04] border-foreground/[0.06] text-foreground-muted"
                          )}
                        >
                          {r}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-[10px] text-foreground-muted mb-1 block">Accent</label>
                      <select
                        value={voiceAccent}
                        onChange={(e) => setVoiceAccent(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg bg-foreground/[0.04] border border-foreground/[0.06] text-xs text-foreground [&>option]:text-card"
                      >
                        {ACCENTS.map((a) => (
                          <option key={a}>{a}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-[10px] text-foreground-muted mb-1 block">Emotion Bias</label>
                      <select
                        value={voiceEmotion}
                        onChange={(e) => setVoiceEmotion(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg bg-foreground/[0.04] border border-foreground/[0.06] text-xs text-foreground [&>option]:text-card"
                      >
                        {EMOTION_BIASES.map((e) => (
                          <option key={e}>{e}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ═══════════ STEP 3: BRAIN ═══════════ */}
          {step === 2 && (
            <div className="space-y-6">
              <div className="text-center">
                <h2 className="text-xl font-semibold text-foreground mb-1">Teach Your Digital Human</h2>
                <p className="text-sm text-foreground-muted">
                  Upload documents or describe the person
                </p>
              </div>

              {/* Tabs */}
              <div className="flex justify-center gap-2">
                {[
                  { id: "documents", label: "Upload Documents", icon: FileText },
                  { id: "describe", label: "Describe the Person", icon: BookOpen },
                ].map((tab) => {
                  const Icon = tab.icon
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setBrainTab(tab.id as "documents" | "describe")}
                      className={cn(
                        "flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-medium transition-all border",
                        brainTab === tab.id
                          ? "bg-primary/15 border-primary/20 text-foreground"
                          : "bg-foreground/[0.04] border-foreground/[0.06] text-foreground-muted"
                      )}
                    >
                      <Icon className="h-3.5 w-3.5" />
                      {tab.label}
                    </button>
                  )
                })}
              </div>

              {brainTab === "documents" && (
                <div className="max-w-lg mx-auto space-y-3">
                  <div className="border-2 border-dashed border-foreground/[0.08] rounded-2xl p-8 text-center hover:border-primary/30 hover:bg-primary/5 transition-all cursor-pointer">
                    <Upload className="h-8 w-8 mx-auto mb-3 text-foreground-muted" />
                    <p className="text-sm text-foreground-muted font-medium mb-1">Drop files here</p>
                    <p className="text-xs text-foreground-muted">PDF, DOCX, TXT, CSV, Markdown</p>
                  </div>
                  <div className="flex justify-center gap-2">
                    {[
                      { icon: Link, label: "Website URL" },
                      { icon: Link, label: "YouTube" },
                    ].map((item) => {
                      const Icon = item.icon
                      return (
                        <button
                          key={item.label}
                          className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-foreground/[0.04] border border-foreground/[0.06] text-[10px] text-foreground-muted hover:text-foreground transition-all"
                        >
                          <Icon className="h-3 w-3" />
                          {item.label}
                        </button>
                      )
                    })}
                  </div>
                </div>
              )}

              {brainTab === "describe" && (
                <div className="max-w-lg mx-auto">
                  <textarea
                    value={describeText}
                    onChange={(e) => setDescribeText(e.target.value)}
                    placeholder="My grandfather was a retired teacher. He loved helping students, gardening, and reading history books. He always spoke calmly and believed everyone deserved respect..."
                    rows={8}
                    className="w-full px-4 py-3 rounded-xl bg-card/80 border border-foreground/[0.06] text-sm text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-primary/30 resize-none"
                  />
                  <p className="text-[10px] text-foreground-muted mt-1">
                    Write naturally. The AI will understand.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* ═══════════ STEP 4: RELATIONSHIP ═══════════ */}
          {step === 3 && (
            <div className="space-y-6">
              <div className="text-center">
                <h2 className="text-xl font-semibold text-foreground mb-1">Define Relationship</h2>
                <p className="text-sm text-foreground-muted">
                  How will you interact with this Digital Human?
                </p>
              </div>
              <div className="flex flex-wrap justify-center gap-2 max-w-xl mx-auto">
                {RELATIONSHIPS.map((r) => (
                  <button
                    key={r}
                    onClick={() => setRelationship(r)}
                    className={cn(
                      "px-4 py-2.5 rounded-xl text-sm transition-all border",
                      relationship === r
                        ? "bg-gradient-to-r from-primary/20 to-primary/20 border-primary/30 text-foreground shadow-lg shadow-primary/10"
                        : "bg-foreground/[0.04] border-foreground/[0.06] text-foreground-muted hover:text-foreground hover:bg-foreground/[0.08]"
                    )}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* ═══════════ STEP 5: PERSONALITY ═══════════ */}
          {step === 4 && (
            <div className="space-y-6">
              <div className="text-center">
                <h2 className="text-xl font-semibold text-foreground mb-1">Select Personality</h2>
                <p className="text-sm text-foreground-muted">
                  Choose traits that describe this Digital Human
                </p>
              </div>
              <div className="flex flex-wrap justify-center gap-2 max-w-xl mx-auto">
                {PERSONALITY_TRAITS.map((trait) => (
                  <button
                    key={trait}
                    onClick={() => toggleTrait(trait)}
                    className={cn(
                      "px-4 py-2.5 rounded-xl text-sm transition-all border",
                      traits.includes(trait)
                        ? "bg-gradient-to-r from-primary/20 to-secondary/15 border-primary/30 text-foreground shadow-lg shadow-primary/10"
                        : "bg-foreground/[0.04] border-foreground/[0.06] text-foreground-muted hover:text-foreground hover:bg-foreground/[0.08]"
                    )}
                  >
                    {trait}
                  </button>
                ))}
              </div>
              {traits.length > 0 && (
                <p className="text-center text-xs text-foreground-muted">
                  {traits.length} trait{traits.length > 1 ? "s" : ""} selected
                </p>
              )}

              {/* A face mesh and a voice clone are biometric data derived from
                  the uploads. Building must be an explicit, informed act. */}
              <div className="mx-auto max-w-xl rounded-2xl border border-foreground/[0.08] bg-foreground/[0.04] p-4">
                <label className="flex cursor-pointer items-start gap-3">
                  <input
                    type="checkbox"
                    checked={consent}
                    onChange={(e) => setConsent(e.target.checked)}
                    className="mt-0.5 h-4 w-4 shrink-0 accent-[var(--primary)]"
                  />
                  <span className="text-xs text-foreground-muted">
                    I confirm I am the person in this photo and recording, or I have their
                    permission. I understand DreamTalk will derive a{" "}
                    <span className="font-medium text-foreground">face mesh</span> and a{" "}
                    <span className="font-medium text-foreground">clone of this voice</span>{" "}
                    from the files I uploaded, and store them on this server so the avatar
                    can speak later.
                  </span>
                </label>
              </div>
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      {/* ── Navigation Buttons ── */}
      <div className="flex items-center justify-between mt-10 max-w-lg mx-auto">
        <button
          onClick={() => setStep((s) => Math.max(0, s - 1))}
          disabled={step === 0 || generating}
          className={cn(
            "flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm transition-all",
            step === 0 || generating
              ? "text-foreground-muted opacity-30 cursor-not-allowed"
              : "text-foreground-muted hover:text-foreground bg-foreground/[0.04]"
          )}
        >
          <ChevronLeft className="h-4 w-4" />
          Back
        </button>

        {step < 4 ? (
          <button
            onClick={() => setStep((s) => s + 1)}
            disabled={!canProceed()}
            className={cn(
              "flex items-center gap-1.5 px-6 py-2.5 rounded-xl text-sm font-medium transition-all",
              canProceed()
                ? "bg-gradient-to-r from-primary to-secondary text-white shadow-lg shadow-primary/20"
                : "bg-foreground/[0.04] text-foreground-muted cursor-not-allowed"
            )}
          >
            Continue
            <ChevronRight className="h-4 w-4" />
          </button>
        ) : (
          <button
            onClick={handleGenerate}
            disabled={!canProceed() || generating}
            className="flex items-center gap-2 px-8 py-3 rounded-xl bg-gradient-to-r from-primary to-secondary text-white text-sm font-medium shadow-lg shadow-primary/20 hover:shadow-primary/30 transition-all disabled:opacity-50"
          >
            {generating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Zap className="h-4 w-4" />
            )}
            {generating ? "Generating..." : "Generate Digital Human"}
          </button>
        )}
      </div>

      {/* ── Build Progress ── */}
      {generating && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-lg mx-auto mt-8 space-y-4"
        >
          <div className="w-full h-1.5 rounded-full bg-foreground/[0.06] overflow-hidden">
            <motion.div
              className="h-full rounded-full bg-gradient-to-r from-primary via-secondary to-secondary"
              initial={{ width: "0%" }}
              animate={{ width: `${buildProgress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
          <div className="space-y-2">
            {BUILD_STEPS.map((bs, i) => {
              const pct = ((i + 1) / BUILD_STEPS.length) * 100
              const isDone = buildProgress >= pct
              const isCurrent = buildProgress >= pct - (100 / BUILD_STEPS.length) && !isDone
              return (
                <div
                  key={bs.id}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2 rounded-xl transition-all",
                    isDone
                      ? "bg-secondary/5"
                      : isCurrent
                        ? "bg-primary/10"
                        : "opacity-40"
                  )}
                >
                  <div
                    className={cn(
                      "w-6 h-6 rounded-full flex items-center justify-center",
                      isDone
                        ? "bg-secondary/10"
                        : isCurrent
                          ? "bg-primary/10"
                          : "bg-foreground/[0.04]"
                    )}
                  >
                    {isDone ? (
                      <Check className="h-3 w-3 text-secondary" />
                    ) : isCurrent ? (
                      <Loader2 className="h-3 w-3 animate-spin text-primary" />
                    ) : (
                      <div className="h-1.5 w-1.5 rounded-full bg-foreground-muted" />
                    )}
                  </div>
                  <span
                    className={cn(
                      "text-xs",
                      isDone ? "text-secondary" : isCurrent ? "text-foreground" : "text-foreground-muted"
                    )}
                  >
                    {bs.label}
                  </span>
                </div>
              )
            })}
          </div>
          {currentStepLabel && (
            <p className="text-center text-xs text-primary animate-pulse">{currentStepLabel}</p>
          )}
        </motion.div>
      )}
    </div>
  )
}
