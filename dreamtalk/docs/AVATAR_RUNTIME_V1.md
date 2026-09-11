# DreamTalk Avatar Runtime v1

The canonical runtime is exposed under `/api/v1/avatar`. It combines profile
media, automatic language and emotion analysis, conversational response
generation, IndicF5 voice cloning, lip-sync data, 2D video, and realtime 3D
animation parameters.

## Runtime flow

1. Create a profile with one clean voice recording, its transcript (recommended),
   and one or more clear face images.
2. The voice is normalized to mono 24 kHz WAV and validated with real IndicF5
   synthesis. The appearance pipeline detects the face and creates OBJ/texture
   assets for the 3D client.
3. Text is script-detected; audio is transcribed with Faster-Whisper. Hindi,
   Marathi, Bengali, Assamese, Gujarati, Punjabi, Odia, Tamil, Telugu, Kannada,
   Malayalam, and English are supported.
4. Text emotion and vocal prosody are fused. The response is generated in the
   detected language and synthesized using the profile's reference voice.
5. The response includes audio, timestamped viseme keyframes, ARKit/VRM
   blendshapes, idle motion, and optional 2D MP4 rendering.

Voice-reference quality note: IndicF5 is documented for 11 Indian languages and
supports cross-language conditioning between them. English remains available to
the runtime through ASR, the LLM, and generic TTS, but an English-only reference
sample is marked with a clone-quality warning. For production Indian-language
voice cloning, record 20-60 seconds of clean speech in any supported Indian
language and provide its exact transcript.

## Main endpoints

- `GET /api/v1/avatar/status` — truthful readiness of speech, ASR, 2D, 3D, and LivePortrait.
- `POST /api/v1/avatar/profiles` — multipart profile creation (`voice_sample`, `face_images`).
- `GET /api/v1/avatar/profiles/{id}/manifest` — frontend 2D/3D assets and endpoint contract.
- `POST /api/v1/avatar/profiles/{id}/respond` — text conversation with optional cloned audio/video.
- `POST /api/v1/avatar/profiles/{id}/respond/audio` — spoken input, auto language, vocal emotion, response.
- `POST /api/v1/avatar/profiles/{id}/speak-2d` — direct text → cloned voice → lip-synced MP4.
- `POST /api/v1/avatar/profiles/{id}/render-2d` — supplied audio → lip-synced MP4.
- `POST /api/v1/avatar/tts/generate` — cloned speech only.
- `POST /api/v1/avatar/lipsync/analyze` — viseme timeline for a 3D renderer.
- `WS /api/v1/avatar/ws/realtime` — text/audio conversation events.

Example direct 2D request:

```json
{
  "text": "வணக்கம், இன்று எப்படி இருக்கிறீர்கள்?",
  "language": "auto",
  "emotion": "happy",
  "strict_clone": true,
  "engine": "auto"
}
```

`engine=auto` chooses MuseTalk when CUDA is available. On CPU-only Docker it
uses the bounded-memory audio-reactive renderer, which produces a real H.264/AAC
MP4 and reports `neural: false`. MuseTalk can be forced on a high-memory CPU host
with `MUSETALK_ALLOW_CPU=true`, though CUDA is strongly recommended.

## Docker

- Frontend: `http://localhost:4000`
- Backend/API docs: `http://localhost:5050/docs`
- IndicF5 service: `http://localhost:8002`

The source, avatar media, and output directories are bind-mounted. Code updates
therefore require only a service restart; an image rebuild is not required for
the current stack. A future clean image build will include the declared ASR,
MuseTalk, EGL, and GLES dependencies.
