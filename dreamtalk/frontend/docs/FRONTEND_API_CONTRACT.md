# DreamTalk Astra — Frontend API Contract

This is the boundary between the frontend (Claude Code) and the backend/AI
(Codex). The frontend consumes these endpoints through a typed service facade
(`src/services/`). Types live in `src/services/types.ts`.

**Mock mode.** The app ships walkable with **no backend**: the facade returns
mock data when `NEXT_PUBLIC_USE_MOCK_API !== "false"` (the default). Set
`NEXT_PUBLIC_USE_MOCK_API=false` to hit the live routes below. Mocks are
isolated in `src/services/mock/` and never imported by components directly.

Base URL: `NEXT_PUBLIC_API_URL` (default `http://localhost:5001`).
All bodies/responses are JSON unless marked `multipart/form-data`.
Wire format is `snake_case`; the frontend maps it to `camelCase` types.

---

## Languages

`GET /api/languages` → `Language[]`

```json
[{ "code": "en-IN", "name": "English (India)", "native": "English" }]
```

Return **only** languages the backend can actually synthesize.

## Face / identity analysis

`POST /api/analyze/face` — `multipart/form-data` with `file`

```json
{
  "status": "ready",            // idle|scanning|detected|multiple_faces|no_face|low_quality|ready
  "confidence": 0.96,           // 0..1
  "faces": 1,
  "quality": "excellent",       // low|fair|good|excellent
  "resolution": { "width": 1024, "height": 1024 },
  "pose": { "yaw": 3, "pitch": -2, "roll": 1 },
  "lighting": "good",           // poor|uneven|good
  "message": "Face detected — ready to build."
}
```

## Voice analysis

`POST /api/analyze/voice` — `multipart/form-data` with `file`, `duration`

```json
{ "status": "ready", "duration_sec": 12, "clarity": 0.93, "quality": "excellent", "sample_rate": 48000, "message": "Voice captured clearly." }
```
`status`: `idle|analyzing|too_short|low_quality|ready`.

## Avatars

- `GET /api/avatars` → `Avatar[]`
- `GET /api/avatars/{id}` → `Avatar`
- `POST /api/avatars` `{ name, languages, consent }` → `Avatar`
- `DELETE /api/avatars/{id}` → `204`

```json
{
  "avatar_id": "astra_ab12cd34",
  "name": "Aarav",
  "model_url": "https://.../aarav.glb",
  "texture_url": "https://.../aarav.png",
  "voice_id": "spk_123",
  "languages": ["en-IN", "hi-IN"],
  "status": "ready",            // draft|processing|ready|failed
  "created_at": "2026-09-10T10:00:00Z",
  "visual_identity": true,
  "voice_identity": true
}
```

## Processing jobs

- `POST /api/jobs` `{ avatar_id }` → `Job`
- `GET /api/jobs/{job_id}` → `Job` (frontend polls until terminal)

```json
{
  "job_id": "job_9f8e",
  "status": "processing",       // queued|processing|completed|failed
  "progress": 62,               // 0..100
  "stage": "voice_processing",  // queued|face_analysis|reconstruction|voice_processing|speaker_profile|avatar_preparation|done
  "avatar_id": "astra_ab12cd34",
  "meta": { "device": "cuda:0", "gpu": "RTX 4090", "model": "astra-recon-v1", "resolution": "1024x1024", "inference_ms": 4200 }
}
```

## Speech

`POST /api/avatars/{id}/speak`

Request:
```json
{ "text": "Namaste", "language": "en-IN", "emotion": "neutral", "emotion_intensity": 0.5 }
```
Response:
```json
{
  "audio_url": "https://.../clip.wav",
  "animation_url": "https://.../visemes.json",
  "duration": 3.4,
  "visemes": [{ "time": 0.25, "viseme": "AA", "weight": 0.8 }]
}
```
Lip sync **must** be driven by `audio.currentTime`, never `setTimeout` (§70).

## System / models

`GET /api/system/status` → `SystemStatus`

```json
{
  "backend": "online",
  "gpu": "NVIDIA RTX 4090",
  "vram_gb": 24,
  "cuda": true,
  "models": [{ "key": "tts", "name": "IndicF5 TTS", "state": "ready", "size_mb": 1240 }]
}
```
`state`: `installed|missing|loading|ready`.

---

## Error convention

Non-2xx returns `{ "detail": "human-readable message" }`. The frontend shows
friendly copy (§47) and never raw stack traces outside developer mode.
