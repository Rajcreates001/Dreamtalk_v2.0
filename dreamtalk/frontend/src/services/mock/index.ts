// ═══════════════════════════════════════════════════════════════════
// Mock service implementations. Deterministic-ish, timed to feel real.
// Kept behind the facade so swapping to the live backend is one flag.
// ═══════════════════════════════════════════════════════════════════
import type {
  Avatar,
  CreateAvatarInput,
  FaceAnalysis,
  Job,
  JobStage,
  Language,
  SpeakRequest,
  SpeakResult,
  SystemStatus,
  VoiceAnalysis,
} from "../types"
import { MOCK_AVATARS, MOCK_LANGUAGES, MOCK_SYSTEM, delay } from "./data"

let avatars = [...MOCK_AVATARS]
const jobs = new Map<string, Job>()

const uid = (p: string) => `${p}_${Math.random().toString(36).slice(2, 10)}`

const JOB_STAGES: JobStage[] = [
  "face_analysis",
  "reconstruction",
  "voice_processing",
  "speaker_profile",
  "avatar_preparation",
]

export const mockSystemService = {
  async status(): Promise<SystemStatus> {
    await delay(300)
    return MOCK_SYSTEM
  },
  async languages(): Promise<Language[]> {
    await delay(200)
    return MOCK_LANGUAGES
  },
}

export const mockAvatarService = {
  async list(): Promise<Avatar[]> {
    await delay(400)
    return [...avatars]
  },
  async get(id: string): Promise<Avatar | null> {
    await delay(250)
    return avatars.find((a) => a.avatarId === id) ?? null
  },
  async create(input: CreateAvatarInput): Promise<Avatar> {
    await delay(300)
    const avatar: Avatar = {
      avatarId: uid("astra"),
      name: input.name || "Untitled",
      languages: input.languages,
      status: "processing",
      createdAt: new Date().toISOString(),
      visualIdentity: !!input.faceFileName,
      voiceIdentity: !!input.voiceFileName,
    }
    avatars = [avatar, ...avatars]
    return avatar
  },
  async remove(id: string): Promise<void> {
    await delay(200)
    avatars = avatars.filter((a) => a.avatarId !== id)
  },
}

export const mockFaceService = {
  async analyze(file: File): Promise<FaceAnalysis> {
    await delay(1400)
    // Heuristic mock: tiny files read as low quality.
    const lowQ = file.size > 0 && file.size < 25_000
    if (lowQ) {
      return {
        status: "low_quality",
        confidence: 0.42,
        faces: 1,
        quality: "low",
        message: "Image resolution is too low for a clean reconstruction.",
      }
    }
    return {
      status: "ready",
      confidence: 0.96,
      faces: 1,
      quality: "excellent",
      resolution: { width: 1024, height: 1024 },
      pose: { yaw: 3, pitch: -2, roll: 1 },
      lighting: "good",
      message: "Face detected — ready to build.",
    }
  },
}

export const mockVoiceService = {
  async analyze(blob: Blob, durationSec: number): Promise<VoiceAnalysis> {
    await delay(1100)
    if (durationSec > 0 && durationSec < 4) {
      return {
        status: "too_short",
        durationSec,
        clarity: 0.5,
        quality: "fair",
        message: "Voice sample is too short — aim for 8–15 seconds.",
      }
    }
    return {
      status: "ready",
      durationSec: durationSec || 12,
      clarity: 0.93,
      quality: "excellent",
      sampleRate: 48000,
      message: "Voice captured clearly.",
    }
  },
}

export const mockJobService = {
  async create(avatarId: string): Promise<Job> {
    const job: Job = {
      jobId: uid("job"),
      status: "processing",
      progress: 0,
      stage: "queued",
      avatarId,
      meta: {
        device: "cuda:0 (mock)",
        gpu: MOCK_SYSTEM.gpu,
        model: "astra-recon-v1",
        resolution: "1024×1024",
      },
    }
    jobs.set(job.jobId, job)
    return { ...job }
  },
  /** Advances the mock job a little each poll and returns the snapshot. */
  async get(jobId: string): Promise<Job> {
    await delay(600)
    const job = jobs.get(jobId)
    if (!job) throw new Error("Job not found")
    if (job.status === "processing") {
      job.progress = Math.min(100, job.progress + 12 + Math.random() * 10)
      const idx = Math.min(
        JOB_STAGES.length - 1,
        Math.floor((job.progress / 100) * JOB_STAGES.length),
      )
      job.stage = JOB_STAGES[idx]
      if (job.progress >= 100) {
        job.progress = 100
        job.status = "completed"
        job.stage = "done"
        job.meta = { ...job.meta, inferenceMs: 4200 + Math.floor(Math.random() * 1500) }
        // Promote the linked avatar to ready.
        if (job.avatarId) {
          avatars = avatars.map((a) =>
            a.avatarId === job.avatarId ? { ...a, status: "ready" } : a,
          )
        }
      }
    }
    return { ...job }
  },
}

export const mockSpeechService = {
  async speak(_avatarId: string, req: SpeakRequest): Promise<SpeakResult> {
    await delay(1600)
    const durationSec = Math.max(1.5, req.text.length * 0.06)
    return {
      audioUrl: "", // no real audio in mock
      durationSec,
      visemes: [
        { time: 0.0, viseme: "sil", weight: 0 },
        { time: 0.2, viseme: "AA", weight: 0.8 },
        { time: 0.5, viseme: "E", weight: 0.6 },
        { time: 0.8, viseme: "M", weight: 0.9 },
      ],
    }
  },
}
