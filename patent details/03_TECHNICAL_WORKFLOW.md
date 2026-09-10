# 03 — TECHNICAL WORKFLOW

## Date: August 21, 2026

---

## Workflow 1: Complete Pipeline Execution

### Trigger
User submits a `PipelineRequest` with image_paths, voice_paths, text_input, role, and feature flags.

### Step 1: Face Analysis (Conditional: enable_3d_face=True, image_paths provided)

| Stage | Input | Processing | Output |
|-------|-------|------------|--------|
| Image Loading | File path | OpenCV imread → imdecode fallback | numpy BGR array |
| Quality Assessment | Image array | Laplacian variance, brightness, contrast | Quality dict |
| Super-Resolution | Low-quality image | INTER_CUBIC upscale + unsharp mask + CLAHE | Enhanced image |
| Face Detection | Enhanced image | MediaPipe → OpenCV DNN → Haar Cascade (cascade fallback) | Bounding boxes |
| Landmark Extraction | Detected face | MediaPipe FaceMesh (478 pts) or PFLD (98 pts) | Landmark array |
| Blendshape Estimation | Landmarks | MediaPipe 52 blendshape coefficients | Blendshape dict |
| 3D Mesh Generation | Image + landmarks | FlameFitter.fit_from_photo() → FLAME 3D model | OBJ + MTL + texture |
| Head Pose | Landmarks | Geometric estimation (yaw/pitch/roll) | Pose angles |
| Face Emotion | Blendshapes | Expression → MoodState mapping | Emotion from face |
| Quality Scoring | All metrics | Combined quality score (blur + brightness + face size + pose) | Quality score |

### Step 2: Voice Analysis (Conditional: enable_voice_clone=True, voice_paths provided)

| Stage | Input | Processing | Output |
|-------|-------|------------|--------|
| Audio Loading | File path | soundfile → scipy → librosa (cascade) | Float32 mono array |
| Enhancement | Raw audio | DC removal → normalize → bandpass (80-8kHz) → spectral subtraction | Enhanced audio |
| VAD | Enhanced audio | RMS energy (25ms frames, 10ms hop) → adaptive threshold | Voiced mask |
| Pitch Extraction | Audio + VAD | pYIN (C2-C7) → mean/std/median/quartiles/vibrato | Pitch features |
| Energy | Audio | RMS envelope | Energy features |
| Spectral | Audio | Centroid, bandwidth, rolloff, contrast, 13 MFCCs + covariance | Spectral features |
| Formants | Audio | LPC order 12 → root finding → F1-F4 | Formant features |
| Voice Quality | Audio + Pitch | Jitter (local/RAP/PPQ5), Shimmer (local/APQ3/APQ5), HNR | Quality features |
| Prosody | Audio + VAD | Speaking rate, pause detection, words per minute | Prosody features |
| Speaker Diarization | Audio + VAD | 39-dim MFCC+delta+delta2 → AgglomerativeClustering → silhouette scoring → segment merge | Speaker segments |
| Voice Embedding | Audio features | MFCC + spectral + pitch + energy → 256-dim vector | Embedding |
| Voice Emotion | All features | Rule-based scoring (7 emotions) → PAD mapping | Voice emotion |
| Gender/Age | Pitch + spectral | Threshold-based (pitch < 165Hz = male) | Gender + age estimate |
| Voice Cloning | Source audio | IndicF5 → RVC → OpenVoice → structural (cascade) | Cloned audio path |
| TTS Generation | Text input | Kokoro → Edge-TTS → gTTS → sine wave (cascade) | TTS audio path |

### Step 3: Emotion Detection (Conditional: enable_emotion=True, text_input provided)

| Stage | Input | Processing | Output |
|-------|-------|------------|--------|
| VADER Sentiment | Text | VADER polarity_scores() | Compound, pos, neg, neu |
| Hostility Detection | Text | Keyword weighted scoring (20 hostile terms) | Hostility score + triggers |
| Keyword Mood Scoring | Text | 10 keyword dictionaries (18 mood categories) | Mood scores dict |
| PAD Mapping | Primary mood | PAD_MOOD_MAP lookup (18 moods → P/A/D + activation) | PAD coordinates |
| EMA Smoothing | Current + historical valence | α=0.35 exponential moving average | Smoothed valence |
| Valence Trend | Last 5 values | Rising/falling/stable classification | Trend label |
| Intensity | Compound + PAD | Magnitude classification (low/medium/high) | Intensity |
| Cognitive Appraisal | Primary mood | InsulaBrainArea.EMOTION_APPRAISAL_MAP lookup | Appraisal label |
| Action Tendency | Activation | ACTION_TENDENCIES lookup (7 types) | Tendency label |

### Step 3b: Emotion Fusion (If both voice and text emotion available)

| Stage | Input | Processing | Output |
|-------|-------|------------|--------|
| Voice Re-prediction | Stored acoustic features | predict_emotion_from_voice() | Voice emotion dict |
| Confidence Computation | Voice + text confidence | voice_weight = min(vc*0.4+0.1, 0.6) | Normalized weights |
| PAD Fusion | Voice + text PAD | Weighted average of valence and arousal | Fused PAD |
| Mood Selection | Weights + confidences | Higher-weighted channel's mood | Fused mood |
| Provenance Recording | All intermediate values | vocal_contribution + textual_contribution + ensemble_weights | Full provenance |

### Step 4: Brain Decision (Conditional: enable_decision=True, text_input provided)

| Stage | Input | Processing | Output |
|-------|-------|------------|--------|
| Working Memory Store | Text + role + emotion | Capacity-7 circular buffer with importance weighting | Updated memory |
| Feature Extraction | Text + role + emotion | Keyword scores, sentiment, hostility, length → float vector | Feature vector |
| Spike Encoding | Feature vector | SNNEncoder.encode() (rate/ttfs/phase/population) | Spike train matrix |
| Spike Decoding | Spike train | np.mean(axis=1) | Decoded vector |
| PFC Forward | Decoded spikes | Linear + LeakyReLU + membrane potential + eligibility trace | PFC output + state |
| dACC Forward | PFC output | Linear + tanh + entropy conflict + STDP update | Conflict score + output |
| Insula Forward | Emotion features + text | Weighted integration + homeostasis + valence | Emotional valence |
| IPL Forward | Visual (PFC) + Audio (None) | Cross-modal weight matrices → integration | Integrated features |
| Basal Ganglia Forward | PFC + dACC + Insula | D1/D2 modulation → softmax → action selection | Selected action |
| LLM Query | Text + system prompt + emotion context | HTTP POST to OpenAI-compatible API | Response text |
| Result Assembly | All brain states | BrainDecisionResult with 12+ fields | Complete result |

### Step 5: Facial Animation (Conditional: enable_animation=True)

| Stage | Input | Processing | Output |
|-------|-------|------------|--------|
| LivePortrait Check | System state | check_liveportrait_ready() | Ready status |
| Emotion → Animation | Emotion label | drive_from_emotion(source_image, emotion_label) | Video frames |
| OR Video Driving | Source + driving video | drive_from_video(source, driving) | Video frames |
| Audio Analysis | Audio path | RMS energy → lip_sync parameters | Animation parameters |

### Step 6: Object Detection (Conditional: enable_object_detection=True)

| Stage | Input | Processing | Output |
|-------|-------|------------|--------|
| YOLO Detection | Image path | YOLODetector.detect() | Object list |
| OR Blob Detection | Image | Threshold → contour → area filter | Object list |
| Scene Classification | Grayscale image | Brightness-based (bright/indoor/dark) | Scene label |
| Annotation | Image + detections | cv2.rectangle + cv2.putText | Annotated image |

### Step 7: Persistence

| Stage | Input | Processing | Output |
|-------|-------|------------|--------|
| Media Store | 3D mesh, cloned voice, TTS | MediaRepository.store_file() | Asset IDs |
| DB Store | All results | INSERT INTO pipeline_results (JSONB) | Record ID |
| Finalize | All steps | PipelineResult assembly | Final result |

---

## Workflow 2: Conversation Turn (Orchestration Engine)

```
User speaks/types
    │
    ▼
OrchestrationEngine._execute_turn()
    │
    ├─ State: INPUT_DETECTED
    │
    ├─ ASRHandler.process(audio)
    │   └─ Whisper transcription or text passthrough
    │
    ├─ State: INPUT_FINALIZED
    │
    ├─ VisionHandler.process()
    │   └─ Screen capture (optional)
    │
    ├─ State: LLM_STREAM_STARTED
    │
    ├─ LLMHandler.process_streaming(text, context)
    │   └─ Chunk-by-chunk response generation
    │   └─ State: LLM_CHUNK_RECEIVED (per chunk)
    │
    ├─ State: LLM_STREAM_ENDED
    │
    ├─ FilterHandler.process(text)
    │   └─ Profanity replacement (word-level)
    │
    ├─ TTSHandler.process(filtered_text)
    │   └─ Edge-TTS → Kokoro → sine wave fallback
    │
    ├─ State: TTS_STREAM_ENDED
    │
    ├─ AnimationHandler.process(audio_path)
    │   └─ Audio energy → lip_sync parameters
    │
    ├─ DisplayHandler.process(animation_data)
    │   └─ Display payload assembly
    │
    └─ State: AUDIO_STREAM_ENDED
```

---

## Workflow 3: Digital Twin Creation

```
User clicks "Create Digital Twin"
    │
    ▼
CreationPipeline.execute(user_id, request)
    │
    ├─ Step 1: Generate twin UUID
    ├─ Step 2: Determine role (personal/healthcare/business)
    ├─ Step 3: Create folder structure (MediaRepository)
    ├─ Step 4: INSERT INTO digital_twins (DB record)
    ├─ Step 5: Create identity_profile (JSONB)
    ├─ Step 6: Initialize memory system
    ├─ Step 7: PersonalityEngine.initialize(twin_id, role)
    ├─ Step 8: Initialize analytics
    ├─ Step 9: Initialize learning engine
    ├─ Step 10: Initialize media assets table
    └─ Step 11: Mark twin as "ready"
```

---

*End of Technical Workflow*
