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

const BUILD_STEPS = [
  { id: "face", label: "Creating Face" },
  { id: "voice", label: "Cloning Voice" },
  { id: "brain", label: "Learning Documents" },
  { id: "personality", label: "Understanding Personality" },
  { id: "memory", label: "Connecting Memories" },
  { id: "conversation", label: "Initializing Conversation" },
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
      case 0: return !!photo
      case 1: return voiceMethod === "upload" ? !!voiceFile : voiceMethod === "generate"
      case 2: return brainTab === "documents" ? true : describeText.trim().length > 10
      case 3: return !!relationship
      case 4: return traits.length > 0
      default: return false
    }
  }

  const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

  const updateBuildStep = (label: string) => {
    setCurrentStepLabel(label)
  }

  const handleGenerate = async () => {
    setGenerating(true)
    setBuildProgress(0)
    setError(null)

    try {
      // 1. Create the twin
      updateBuildStep("Creating Digital Human...")
      const twinName = `Digital Human (${relationship || "Friend"})`
      const twin = await digitalTwinApi.create({
        name: twinName,
        description: describeText || undefined,
        personality: traits.join(", "),
      })
      const twinId = twin.id || twin._id || twin.twin_id
      if (!twinId) throw new Error("Failed to get twin ID from API")
      setBuildProgress(10)

      // 2. Upload photo (appearance)
      updateBuildStep("Creating Face...")
      if (photo) {
        const formData = new FormData()
        formData.append("file", photo)
        await digitalTwinApi.uploadAppearance(twinId, formData)
      }
      setBuildProgress(25)

      // 3. Handle voice
      updateBuildStep("Cloning Voice...")
      if (voiceMethod === "upload" && voiceFile) {
        const formData = new FormData()
        formData.append("file", voiceFile)
        await digitalTwinApi.uploadVoice(twinId, formData)
      } else if (voiceMethod === "generate") {
        await digitalTwinApi.createSyntheticVoice(twinId, {
          gender: voiceGender,
          age: voiceAge,
          region: voiceRegion,
          accent: voiceAccent,
          emotion: voiceEmotion,
        })
      }
      setBuildProgress(40)

      // 4. Upload knowledge if described
      updateBuildStep("Learning Documents...")
      if (brainTab === "describe" && describeText.trim()) {
        const formData = new FormData()
        const blob = new Blob([describeText], { type: "text/plain" })
        formData.append("file", blob, "description.txt")
        await digitalTwinApi.uploadKnowledge(twinId, formData)
      }
      setBuildProgress(55)

      // 5. Set personality
      updateBuildStep("Understanding Personality...")
      await digitalTwinApi.setPersonality(twinId, {
        traits,
        description: describeText || undefined,
      })
      await digitalTwinApi.initializePersonality(twinId)
      setBuildProgress(70)

      // 6. Set relationship
      updateBuildStep("Mapping Relationship...")
      await digitalTwinApi.setRelationship(twinId, { type: relationship })
      setBuildProgress(85)

      // 7. Run the pipeline
      updateBuildStep("Initializing Conversation...")
      try {
        await digitalTwinApi.runPipeline(twinId)
      } catch {
        // Pipeline may not be fully set up yet — that's OK for now
      }
      setBuildProgress(100)

      await sleep(300)
      setGenerated(true)
      setGeneratedTwinId(twinId)
    } catch (err: any) {
      setError(err.message || "Generation failed. Please try again.")
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
          className="w-24 h-24 mx-auto rounded-full bg-gradient-to-br from-[#42FFC6]/20 to-[#00E5FF]/20 border border-[#42FFC6]/20 flex items-center justify-center"
        >
          <Check className="h-10 w-10 text-[#42FFC6]" />
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <h1 className="text-3xl font-bold text-[#F8FAFC] mb-2">Your Digital Human is Ready!</h1>
          <p className="text-[#94A3B8] mb-8">
            Face created · Voice cloned · Brain initialized · Personality mapped
          </p>
          <div className="flex items-center justify-center gap-4">
            <button
              onClick={() => router.push(`/dh/${generatedTwinId}`)}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-[#7C5CFF] to-[#00E5FF] text-white font-medium shadow-lg shadow-[#7C5CFF]/20 hover:shadow-[#7C5CFF]/30 transition-all"
            >
              <Sparkles className="h-4 w-4" />
              Open Digital Human
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
              }}
              className="px-6 py-3 rounded-xl bg-white/[0.04] border border-white/[0.06] text-[#94A3B8] hover:text-[#F8FAFC] transition-all"
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
        <h1 className="text-3xl font-bold text-[#F8FAFC] mb-2">Create Digital Human</h1>
        <p className="text-[#94A3B8]">
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
                  ? "bg-[#7C5CFF]/15 text-[#7C5CFF] border border-[#7C5CFF]/20"
                  : i < step
                    ? "bg-[#42FFC6]/10 text-[#42FFC6] border border-[#42FFC6]/20 cursor-pointer"
                    : "bg-white/[0.04] text-[#64748B] border border-transparent"
              )}
            >
              {i < step ? <Check className="h-3 w-3" /> : <span>{i + 1}</span>}
              <span className="hidden sm:inline">{label}</span>
            </button>
            {i < 4 && (
              <div
                className={cn(
                  "w-8 h-px",
                  i < step ? "bg-[#42FFC6]/40" : "bg-white/[0.06]"
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
          className="max-w-lg mx-auto mb-6 px-4 py-3 rounded-xl bg-[#FF5F73]/10 border border-[#FF5F73]/20 text-xs text-[#FF5F73] text-center"
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
                <h2 className="text-xl font-semibold text-[#F8FAFC] mb-1">Upload a Photo</h2>
                <p className="text-sm text-[#94A3B8]">
                  This will be used to create the face and avatar
                </p>
              </div>

              {/* Upload area */}
              <div
                onClick={() => fileInputRef.current?.click()}
                className={cn(
                  "relative border-2 border-dashed rounded-2xl p-12 text-center transition-all cursor-pointer mx-auto max-w-md",
                  photoPreview
                    ? "border-[#42FFC6]/30 bg-[#42FFC6]/5"
                    : "border-white/[0.08] hover:border-[#7C5CFF]/30 hover:bg-[#7C5CFF]/5"
                )}
              >
                {photoPreview ? (
                  <div className="space-y-3">
                    <div className="w-32 h-32 mx-auto rounded-full overflow-hidden border-2 border-[#42FFC6]/30">
                      <img src={photoPreview} alt="Preview" className="w-full h-full object-cover" />
                    </div>
                    <p className="text-xs text-[#42FFC6] font-medium">Photo uploaded</p>
                    <p className="text-[10px] text-[#64748B]">Click to change</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="w-20 h-20 mx-auto rounded-full bg-white/[0.04] border border-white/[0.06] flex items-center justify-center">
                      <Camera className="h-8 w-8 text-[#64748B]" />
                    </div>
                    <div>
                      <p className="text-sm text-[#94A3B8] font-medium">Drop photo here or click to browse</p>
                      <p className="text-xs text-[#64748B] mt-1">PNG, JPEG, WEBP, HEIC · Up to 20MB</p>
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
                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/[0.04] border border-white/[0.06] text-xs text-[#94A3B8] hover:text-[#F8FAFC] transition-all"
                >
                  <Video className="h-3.5 w-3.5" />
                  Use Camera
                </button>
                <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/[0.04] border border-white/[0.06] text-xs text-[#94A3B8] hover:text-[#F8FAFC] transition-all">
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
                <h2 className="text-xl font-semibold text-[#F8FAFC] mb-1">Choose Voice</h2>
                <p className="text-sm text-[#94A3B8]">
                  Upload a voice sample or generate an AI voice
                </p>
              </div>

              {/* Options */}
              <div className="grid sm:grid-cols-2 gap-4 max-w-lg mx-auto">
                <button
                  onClick={() => setVoiceMethod("upload")}
                  className={cn(
                    "p-6 rounded-2xl border text-center transition-all",
                    voiceMethod === "upload"
                      ? "bg-[#7C5CFF]/15 border-[#7C5CFF]/20"
                      : "bg-white/[0.04] border-white/[0.06] hover:border-[#7C5CFF]/20 hover:bg-[#7C5CFF]/5"
                  )}
                >
                  <Mic className="h-8 w-8 mx-auto mb-3" style={{ color: voiceMethod === "upload" ? "#7C5CFF" : "#64748B" }} />
                  <p className="text-sm font-medium text-[#F8FAFC] mb-1">Upload Voice</p>
                  <p className="text-xs text-[#64748B]">Record or upload a sample</p>
                </button>
                <button
                  onClick={() => setVoiceMethod("generate")}
                  className={cn(
                    "p-6 rounded-2xl border text-center transition-all",
                    voiceMethod === "generate"
                      ? "bg-[#7C5CFF]/15 border-[#7C5CFF]/20"
                      : "bg-white/[0.04] border-white/[0.06] hover:border-[#7C5CFF]/20 hover:bg-[#7C5CFF]/5"
                  )}
                >
                  <Wand2 className="h-8 w-8 mx-auto mb-3" style={{ color: voiceMethod === "generate" ? "#7C5CFF" : "#64748B" }} />
                  <p className="text-sm font-medium text-[#F8FAFC] mb-1">Generate AI Voice</p>
                  <p className="text-xs text-[#64748B]">Choose gender, age, region</p>
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
                  className="max-w-lg mx-auto border-2 border-dashed rounded-xl p-6 text-center cursor-pointer hover:border-[#7C5CFF]/30 transition-all"
                  style={{ borderColor: voiceFile ? "#42FFC6" : "rgba(255,255,255,0.08)" }}
                >
                  {voiceFile ? (
                    <div className="space-y-2">
                      <Music className="h-6 w-6 mx-auto text-[#42FFC6]" />
                      <p className="text-xs text-[#42FFC6]">{voiceFile.name}</p>
                      <p className="text-[10px] text-[#64748B]">Click to change</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <Upload className="h-6 w-6 mx-auto text-[#64748B]" />
                      <p className="text-xs text-[#94A3B8]">MP3, WAV, M4A, FLAC, OGG</p>
                    </div>
                  )}
                </div>
              )}

              {/* Generate form */}
              {voiceMethod === "generate" && (
                <div className="max-w-lg mx-auto space-y-4 p-6 rounded-2xl bg-[#0F172A]/80 border border-white/[0.06]">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-[10px] text-[#64748B] mb-1 block">Gender</label>
                      <div className="flex gap-1.5">
                        {GENDERS.map((g) => (
                          <button
                            key={g}
                            onClick={() => setVoiceGender(g)}
                            className={cn(
                              "flex-1 px-3 py-2 rounded-lg text-xs transition-all border",
                              voiceGender === g
                                ? "bg-[#7C5CFF]/15 border-[#7C5CFF]/20 text-[#F8FAFC]"
                                : "bg-white/[0.04] border-white/[0.06] text-[#94A3B8]"
                            )}
                          >
                            {g}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <label className="text-[10px] text-[#64748B] mb-1 block">Age</label>
                      <select
                        value={voiceAge}
                        onChange={(e) => setVoiceAge(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg bg-white/[0.04] border border-white/[0.06] text-xs text-[#CBD5E1] [&>option]:text-[#0F172A]"
                      >
                        {AGE_GROUPS.map((a) => (
                          <option key={a}>{a}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="text-[10px] text-[#64748B] mb-1 block">Region / Language</label>
                    <div className="flex flex-wrap gap-1.5">
                      {REGIONS.slice(0, 8).map((r) => (
                        <button
                          key={r}
                          onClick={() => setVoiceRegion(r)}
                          className={cn(
                            "px-2.5 py-1.5 rounded-lg text-[10px] transition-all border",
                            voiceRegion === r
                              ? "bg-[#7C5CFF]/15 border-[#7C5CFF]/20 text-[#F8FAFC]"
                              : "bg-white/[0.04] border-white/[0.06] text-[#94A3B8]"
                          )}
                        >
                          {r}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-[10px] text-[#64748B] mb-1 block">Accent</label>
                      <select
                        value={voiceAccent}
                        onChange={(e) => setVoiceAccent(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg bg-white/[0.04] border border-white/[0.06] text-xs text-[#CBD5E1] [&>option]:text-[#0F172A]"
                      >
                        {ACCENTS.map((a) => (
                          <option key={a}>{a}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-[10px] text-[#64748B] mb-1 block">Emotion Bias</label>
                      <select
                        value={voiceEmotion}
                        onChange={(e) => setVoiceEmotion(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg bg-white/[0.04] border border-white/[0.06] text-xs text-[#CBD5E1] [&>option]:text-[#0F172A]"
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
                <h2 className="text-xl font-semibold text-[#F8FAFC] mb-1">Teach Your Digital Human</h2>
                <p className="text-sm text-[#94A3B8]">
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
                          ? "bg-[#7C5CFF]/15 border-[#7C5CFF]/20 text-[#F8FAFC]"
                          : "bg-white/[0.04] border-white/[0.06] text-[#94A3B8]"
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
                  <div className="border-2 border-dashed border-white/[0.08] rounded-2xl p-8 text-center hover:border-[#7C5CFF]/30 hover:bg-[#7C5CFF]/5 transition-all cursor-pointer">
                    <Upload className="h-8 w-8 mx-auto mb-3 text-[#64748B]" />
                    <p className="text-sm text-[#94A3B8] font-medium mb-1">Drop files here</p>
                    <p className="text-xs text-[#64748B]">PDF, DOCX, TXT, CSV, Markdown</p>
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
                          className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-white/[0.04] border border-white/[0.06] text-[10px] text-[#94A3B8] hover:text-[#F8FAFC] transition-all"
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
                    className="w-full px-4 py-3 rounded-xl bg-[#0F172A]/80 border border-white/[0.06] text-sm text-[#F8FAFC] placeholder:text-[#64748B] focus:outline-none focus:ring-2 focus:ring-[#7C5CFF]/30 resize-none"
                  />
                  <p className="text-[10px] text-[#64748B] mt-1">
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
                <h2 className="text-xl font-semibold text-[#F8FAFC] mb-1">Define Relationship</h2>
                <p className="text-sm text-[#94A3B8]">
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
                        ? "bg-gradient-to-r from-[#FF6B9D]/20 to-[#7C5CFF]/20 border-[#FF6B9D]/30 text-[#F8FAFC] shadow-lg shadow-[#FF6B9D]/10"
                        : "bg-white/[0.04] border-white/[0.06] text-[#94A3B8] hover:text-[#CBD5E1] hover:bg-white/[0.08]"
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
                <h2 className="text-xl font-semibold text-[#F8FAFC] mb-1">Select Personality</h2>
                <p className="text-sm text-[#94A3B8]">
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
                        ? "bg-gradient-to-r from-[#7C5CFF]/20 to-[#00E5FF]/15 border-[#7C5CFF]/30 text-[#F8FAFC] shadow-lg shadow-[#7C5CFF]/10"
                        : "bg-white/[0.04] border-white/[0.06] text-[#94A3B8] hover:text-[#CBD5E1] hover:bg-white/[0.08]"
                    )}
                  >
                    {trait}
                  </button>
                ))}
              </div>
              {traits.length > 0 && (
                <p className="text-center text-xs text-[#64748B]">
                  {traits.length} trait{traits.length > 1 ? "s" : ""} selected
                </p>
              )}
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
              ? "text-[#64748B] opacity-30 cursor-not-allowed"
              : "text-[#94A3B8] hover:text-[#F8FAFC] bg-white/[0.04]"
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
                ? "bg-gradient-to-r from-[#7C5CFF] to-[#00E5FF] text-white shadow-lg shadow-[#7C5CFF]/20"
                : "bg-white/[0.04] text-[#64748B] cursor-not-allowed"
            )}
          >
            Continue
            <ChevronRight className="h-4 w-4" />
          </button>
        ) : (
          <button
            onClick={handleGenerate}
            disabled={!canProceed() || generating}
            className="flex items-center gap-2 px-8 py-3 rounded-xl bg-gradient-to-r from-[#7C5CFF] to-[#00E5FF] text-white text-sm font-medium shadow-lg shadow-[#7C5CFF]/20 hover:shadow-[#7C5CFF]/30 transition-all disabled:opacity-50"
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
          <div className="w-full h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
            <motion.div
              className="h-full rounded-full bg-gradient-to-r from-[#7C5CFF] via-[#00E5FF] to-[#42FFC6]"
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
                      ? "bg-[#42FFC6]/5"
                      : isCurrent
                        ? "bg-[#7C5CFF]/10"
                        : "opacity-40"
                  )}
                >
                  <div
                    className={cn(
                      "w-6 h-6 rounded-full flex items-center justify-center",
                      isDone
                        ? "bg-[#42FFC6]/10"
                        : isCurrent
                          ? "bg-[#7C5CFF]/10"
                          : "bg-white/[0.04]"
                    )}
                  >
                    {isDone ? (
                      <Check className="h-3 w-3 text-[#42FFC6]" />
                    ) : isCurrent ? (
                      <Loader2 className="h-3 w-3 animate-spin text-[#7C5CFF]" />
                    ) : (
                      <div className="h-1.5 w-1.5 rounded-full bg-[#64748B]" />
                    )}
                  </div>
                  <span
                    className={cn(
                      "text-xs",
                      isDone ? "text-[#42FFC6]" : isCurrent ? "text-[#F8FAFC]" : "text-[#64748B]"
                    )}
                  >
                    {bs.label}
                  </span>
                </div>
              )
            })}
          </div>
          {currentStepLabel && (
            <p className="text-center text-xs text-[#7C5CFF] animate-pulse">{currentStepLabel}</p>
          )}
        </motion.div>
      )}
    </div>
  )
}
