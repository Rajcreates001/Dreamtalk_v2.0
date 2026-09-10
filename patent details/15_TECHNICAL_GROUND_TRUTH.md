# 15 — TECHNICAL GROUND TRUTH

## Date: August 21, 2026
## Verification Method: Direct code inspection

---

## CRITICAL NOTE

All claims in this document have been verified against the actual source code. Where code confirms the claim, it is marked SUPPORTED. Where code does not confirm, it is marked NOT SUPPORTED.

---

## A. Neuromorphic Brain Architecture

### A1. SNNEncoder

| Field | Value | Evidence |
|-------|-------|----------|
| **Location** | `pipeline/brain_pipeline.py:SNNEncoder` | SUPPORTED |
| **Purpose** | Convert feature vectors into spike trains | SUPPORTED |
| **Input** | numpy.ndarray (feature vector) | SUPPORTED |
| **Output** | numpy.ndarray (spike train matrix: features × timesteps) | SUPPORTED |
| **Strategies** | rate, ttfs, phase, population | SUPPORTED — 4 methods implemented |
| **Rate encoding** | Bernoulli sampling: `np.random.binomial(1, features[:, None], size=(len(features), self.timesteps))` | SUPPORTED |
| **TTFS encoding** | First-spike time = (1 - feature) × (timesteps - 1) | SUPPORTED |
| **Phase encoding** | Sinusoidal modulation: `np.sin(phases + features * 2π) > 0.5` | SUPPORTED |
| **Population encoding** | Gaussian tuning curves with sigma = 1/(1.5*(m-2)) | SUPPORTED |
| **Decode method** | `np.mean(spike_train, axis=1)` | SUPPORTED |
| **Default timesteps** | 16 | SUPPORTED |
| **Implementation status** | FULLY IMPLEMENTED | SUPPORTED |
| **Production status** | USED IN BRAIN PIPELINE | SUPPORTED |
| **Novelty relevance** | Application to NLP features for SNN brain processing | POTENTIALLY NOVEL |

### A2. PFCBrainArea (Prefrontal Cortex)

| Field | Value | Evidence |
|-------|-------|----------|
| **Location** | `pipeline/brain_pipeline.py:PFCBrainArea` | SUPPORTED |
| **Purpose** | Planning, reasoning, working memory, executive control | SUPPORTED |
| **Input** | decoded spike vector | SUPPORTED |
| **Processing** | Linear transform + LeakyReLU + membrane potential accumulation | SUPPORTED |
| **Formula** | `output = np.dot(input_vector, self.eligibility_trace.T)` | SUPPORTED |
| **LeakyReLU** | `np.maximum(output * 0.01, output)` | SUPPORTED |
| **Membrane potential** | `0.8 * old + 0.2 * output` | SUPPORTED |
| **Eligibility trace** | `self.eligibility_trace += self.dopamine * 0.001 * np.outer(output, input_vector)` | SUPPORTED |
| **Dopamine modulation** | Default 0.5, modulates eligibility trace update | SUPPORTED |
| **Working memory** | Integrates WorkingMemory instance | SUPPORTED |
| **Output** | numpy array + BrainAreaActivation state | SUPPORTED |
| **Implementation status** | FULLY IMPLEMENTED | SUPPORTED |
| **Novelty relevance** | Dopamine-modulated eligibility trace for NLP | POTENTIALLY NOVEL |

### A3. dACCBrainArea (Dorsal Anterior Cingulate Cortex)

| Field | Value | Evidence |
|-------|-------|----------|
| **Location** | `pipeline/brain_pipeline.py:dACCBrainArea` | SUPPORTED |
| **Purpose** | Conflict monitoring, error detection, decision | SUPPORTED |
| **Input** | PFC output vector | SUPPORTED |
| **Processing** | Linear + tanh + entropy conflict + STDP | SUPPORTED |
| **Conflict computation** | Entropy of softmax output: `-np.sum(soft * np.log(soft + 1e-8))` | SUPPORTED |
| **STDP update** | `self.stdp_trace += 0.01 * (np.outer(post_trace, pre_trace) - 0.02 * self.weights)` | SUPPORTED |
| **Weight update** | `self.weights += self.stdp_trace * 0.1` | SUPPORTED |
| **Conflict score** | Normalized entropy / log(output_dim) | SUPPORTED |
| **Output** | conflict_score + output vector | SUPPORTED |
| **Implementation status** | FULLY IMPLEMENTED | SUPPORTED |
| **Novelty relevance** | STDP conflict monitoring for conversational AI | POTENTIALLY NOVEL |

### A4. InsulaBrainArea

| Field | Value | Evidence |
|-------|-------|----------|
| **Location** | `pipeline/brain_pipeline.py:InsulaBrainArea` | SUPPORTED |
| **Purpose** | Interoception, emotional awareness, empathy | SUPPORTED |
| **Input** | emotion_features + text | SUPPORTED |
| **Processing** | Weighted integration + homeostasis + valence | SUPPORTED |
| **Cognitive appraisal** | `EMOTION_APPRAISAL_MAP` with 15 emotions | SUPPORTED |
| **Homeostasis** | `self._homeostasis += 0.02 * (0.0 - self._homeostasis)` | SUPPORTED |
| **Valence computation** | Keyword-based (happy/sad/angry/fear words) | SUPPORTED |
| **Output** | emotional_valence float | SUPPORTED |
| **Implementation status** | FULLY IMPLEMENTED | SUPPORTED |

### A5. IPLBrainArea (Inferior Parietal Lobule)

| Field | Value | Evidence |
|-------|-------|----------|
| **Location** | `pipeline/brain_pipeline.py:IPLBrainArea` | SUPPORTED |
| **Purpose** | Multimodal sensory integration | SUPPORTED |
| **Input** | visual_input + audio_input (numpy arrays) | SUPPORTED |
| **Processing** | Separate weight matrices → concatenation → integration | SUPPORTED |
| **Integration ratio** | `np.linalg.norm(v_proc) / (np.linalg.norm(a_proc) + 1e-8)` | SUPPORTED |
| **Output** | dict with visual_processed, audio_processed, integrated, integration_ratio | SUPPORTED |
| **Implementation status** | FULLY IMPLEMENTED | SUPPORTED |

### A6. BasalGangliaBrainArea

| Field | Value | Evidence |
|-------|-------|----------|
| **Location** | `pipeline/brain_pipeline.py:BasalGangliaBrainArea` | SUPPORTED |
| **Purpose** | Action selection via direct/indirect pathway | SUPPORTED |
| **Input** | pfc_output + dacc_conflict + insula_valence | SUPPORTED |
| **Processing** | D1/D2 modulation → softmax → action selection | SUPPORTED |
| **Action space** | 12 types: respond_greet, respond_question, respond_empathetic, respond_analytical, respond_humor, respond_redirect, respond_confirm, respond_elaborate, respond_advise, respond_learn, respond_defer, respond_terminate | SUPPORTED |
| **D1 modulation** | `d1_mod = self._d1_weights[i] * (1.0 - dacc_conflict)` | SUPPORTED |
| **D2 modulation** | `d2_mod = -self._d2_weights[i] * dacc_conflict` | SUPPORTED |
| **Softmax** | `np.exp(values - np.max(values)) / np.sum(np.exp(values - np.max(values)))` | SUPPORTED |
| **Exploration noise** | `np.random.randn(len(values)) * self._exploration_noise` | SUPPORTED |
| **TD learning** | `self.action_values[action] += self._learning_rate * reward` | SUPPORTED |
| **Output** | selected_action string | SUPPORTED |
| **Implementation status** | FULLY IMPLEMENTED | SUPPORTED |
| **Novelty relevance** | Basal ganglia for conversational action selection | POTENTIALLY NOVEL |

### A7. WorkingMemory

| Field | Value | Evidence |
|-------|-------|----------|
| **Location** | `pipeline/brain_pipeline.py:WorkingMemory` | SUPPORTED |
| **Capacity** | 7 items (Miller's number) | SUPPORTED |
| **Decay** | `strength -= decay_rate * age` | SUPPORTED |
| **Interference** | FIFO eviction when full | SUPPORTED |
| **Attention focus** | Tracks last stored key | SUPPORTED |
| **Implementation status** | FULLY IMPLEMENTED | SUPPORTED |

---

## B. Emotion System

### B1. TextEmotionDetector

| Field | Value | Evidence |
|-------|-------|----------|
| **Location** | `pipeline/brain_pipeline.py:TextEmotionDetector` | SUPPORTED |
| **VADER integration** | `SentimentIntensityAnalyzer()` | SUPPORTED |
| **Hostile words** | 20 terms with weights | SUPPORTED |
| **Positive words** | 22 terms with weights | SUPPORTED |
| **Sad words** | 21 terms with weights | SUPPORTED |
| **Fear words** | 12 terms with weights | SUPPORTED |
| **Pity words** | 14 terms with weights | SUPPORTED |
| **Betrayal words** | 22 terms with weights | SUPPORTED |
| **Haste words** | 20 terms with weights | SUPPORTED |
| **Trust words** | 16 terms with weights | SUPPORTED |
| **Hope words** | 17 terms with weights | SUPPORTED |
| **Surprise words** | 10 terms with weights | SUPPORTED |
| **Confused words** | 7 terms with weights | SUPPORTED |
| **Mood scores** | 18 categories | SUPPORTED |
| **PAD mapping** | 18 moods → PAD coordinates | SUPPORTED |
| **EMA smoothing** | α=0.35 | SUPPORTED |
| **Hostility detection** | Weighted sum ≥ 0.5 | SUPPORTED |
| **Implementation status** | FULLY IMPLEMENTED | SUPPORTED |

### B2. Emotion Fusion

| Field | Value | Evidence |
|-------|-------|----------|
| **Location** | `pipeline/voice_pipeline.py:fuse_emotion_profiles` | SUPPORTED |
| **Voice emotion** | `predict_emotion_from_voice()` with 7 acoustic features | SUPPORTED |
| **Text emotion** | `TextEmotionDetector.analyze()` | SUPPORTED |
| **Confidence computation** | `voice_weight = min(voice_confidence * 0.4 + 0.1, 0.6)` | SUPPORTED |
| **Weight normalization** | `voice_weight /= total_weight` | SUPPORTED |
| **PAD fusion** | Weighted average of valence and arousal | SUPPORTED |
| **Provenance** | vocal_contribution + textual_contribution + ensemble_weights | SUPPORTED |
| **Implementation status** | FULLY IMPLEMENTED | SUPPORTED |

### B3. Voice Emotion Prediction

| Field | Value | Evidence |
|-------|-------|----------|
| **Location** | `pipeline/voice_pipeline.py:predict_emotion_from_voice` | SUPPORTED |
| **Features** | pitch_norm, energy_norm, centroid_norm, jitter_norm, shimmer_norm, hnr_norm, rate_norm | SUPPORTED |
| **Emotions** | happy, sad, angry, fearful, calm, excited, neutral | SUPPORTED |
| **Scoring** | Weighted linear combination per emotion | SUPPORTED |
| **PAD mapping** | Each emotion → valence + arousal | SUPPORTED |
| **Implementation status** | FULLY IMPLEMENTED | SUPPORTED |

---

## C. Pipeline Orchestration

### C1. PipelineOrchestrator

| Field | Value | Evidence |
|-------|-------|----------|
| **Location** | `pipeline/orchestrator.py` | SUPPORTED |
| **Steps** | 6 steps: Face → Voice → Emotion → Brain → Animation → Object Detection | SUPPORTED |
| **Async** | `async def run_full_pipeline` | SUPPORTED |
| **Error handling** | try/except per step, non-fatal failures | SUPPORTED |
| **DB persistence** | INSERT INTO pipeline_results | SUPPORTED |
| **Media storage** | MediaRepository.store_file() | SUPPORTED |
| **Implementation status** | FULLY IMPLEMENTED | SUPPORTED |

### C2. OrchestrationEngine

| Field | Value | Evidence |
|-------|-------|----------|
| **Location** | `orchestration/core/engine.py` | SUPPORTED |
| **FSM states** | IDLE, INPUT_DETECTED, INPUT_FINALIZED, LLM_STREAM_STARTED, LLM_CHUNK_RECEIVED, LLM_STREAM_ENDED, TTS_STREAM_STARTED, TTS_STREAM_ENDED, AUDIO_STREAM_ENDED | SUPPORTED |
| **Turn execution** | `_execute_turn()` with 10-stage flow | SUPPORTED |
| **Component lifecycle** | `ComponentLifecycle` ABC with start/stop/update | SUPPORTED |
| **60fps loop** | `self._loop_interval = 1.0 / 60.0` | SUPPORTED |
| **Implementation status** | FULLY IMPLEMENTED | SUPPORTED |

---

## D. Voice Pipeline

### D1. VoicePipeline

| Field | Value | Evidence |
|-------|-------|----------|
| **Location** | `pipeline/voice_pipeline.py` | SUPPORTED |
| **Audio loading** | Multi-backend: soundfile → scipy → librosa | SUPPORTED |
| **Enhancement** | DC removal → normalize → bandpass → spectral subtraction | SUPPORTED |
| **VAD** | RMS energy with adaptive threshold | SUPPORTED |
| **Pitch** | pYIN with vibrato detection | SUPPORTED |
| **Spectral** | Centroid, bandwidth, rolloff, contrast, 13 MFCCs | SUPPORTED |
| **Formants** | LPC order 12 → F1-F4 | SUPPORTED |
| **Voice quality** | Jitter (local/RAP/PPQ5), Shimmer (local/APQ3/APQ5), HNR | SUPPORTED |
| **Speaker diarization** | 39-dim MFCC+delta+delta2 → AgglomerativeClustering → silhouette | SUPPORTED |
| **Voice embedding** | 256-dim (MFCC + spectral + pitch + energy) | SUPPORTED |
| **Voice cloning** | IndicF5 → RVC → OpenVoice → structural (cascade) | SUPPORTED |
| **TTS** | Kokoro → Edge-TTS → gTTS → sine wave (cascade) | SUPPORTED |
| **Implementation status** | FULLY IMPLEMENTED | SUPPORTED |

---

## E. Face Pipeline

### E1. FacePipeline

| Field | Value | Evidence |
|-------|-------|----------|
| **Location** | `pipeline/face_pipeline.py` | SUPPORTED |
| **Detection** | MediaPipe → OpenCV DNN → Haar Cascade (cascade fallback) | SUPPORTED |
| **Landmarks** | 478 (MediaPipe) or 98 (PFLD) | SUPPORTED |
| **Blendshapes** | 52 MediaPipe blendshapes | SUPPORTED |
| **3D mesh** | FLAME via FlameFitter | SUPPORTED |
| **Super-resolution** | INTER_CUBIC + unsharp mask + CLAHE | SUPPORTED |
| **Quality assessment** | Laplacian variance, brightness, contrast | SUPPORTED |
| **Emotion from face** | Blendshape → MoodState mapping | SUPPORTED |
| **Implementation status** | FULLY IMPLEMENTED | SUPPORTED |

---

## F. BrainPipeline Integration

### F1. BrainPipeline.make_decision()

| Field | Value | Evidence |
|-------|-------|----------|
| **Location** | `pipeline/brain_pipeline.py:BrainPipeline` | SUPPORTED |
| **Flow** | WorkingMemory → SNNEncoder → PFC → dACC → Insula → IPL → BasalGanglia → LLM | SUPPORTED |
| **Role prompts** | normal_user, healthcare, business | SUPPORTED |
| **Emotion context** | Appended to system prompt with mood, valence, arousal, appraisal, action_tendency | SUPPORTED |
| **LLM integration** | httpx POST to OpenAI-compatible API | SUPPORTED |
| **Fallback** | Rule-based response with hostility detection | SUPPORTED |
| **Result** | BrainDecisionResult with 12+ fields | SUPPORTED |
| **Reasoning path** | List of processing steps recorded | SUPPORTED |
| **Network synchrony** | Cross-area firing rate standard deviation | SUPPORTED |
| **Implementation status** | FULLY IMPLEMENTED | SUPPORTED |

---

## G. Digital Twin

### G1. CreationPipeline

| Field | Value | Evidence |
|-------|-------|----------|
| **Location** | `digital_twin/creation_pipeline.py` | SUPPORTED |
| **Steps** | 11-step pipeline | SUPPORTED |
| **Role mapping** | personal/healthcare/business → normal_user/healthcare/business | SUPPORTED |
| **DB schema** | digital_twins table with 5-step config (appearance, voice, personality, intelligence, relationship) | SUPPORTED |
| **Identity profile** | JSONB with 7 fields | SUPPORTED |
| **Personality** | PersonalityEngine.initialize() | SUPPORTED |
| **Implementation status** | FULLY IMPLEMENTED | SUPPORTED |

---

## H. Frontend

### H1. VRMViewer

| Field | Value | Evidence |
|-------|-------|----------|
| **Location** | `frontend/src/components/vrm/vrm-viewer.tsx` | SUPPORTED |
| **Technology** | Three.js + @pixiv/three-vrm + React Three Fiber | SUPPORTED |
| **Loading** | GLTFLoader → VRMLoaderPlugin | SUPPORTED |
| **Optimization** | removeUnnecessaryVertices, removeUnnecessaryJoints | SUPPORTED |
| **Lighting** | Ambient + hemisphere + directional with shadows | SUPPORTED |
| **Animation** | AnimationMixer with useFrame loop | SUPPORTED |
| **Implementation status** | FULLY IMPLEMENTED | SUPPORTED |

### H2. useChat Hook

| Field | Value | Evidence |
|-------|-------|----------|
| **Location** | `frontend/src/hooks/use-chat.ts` | SUPPORTED |
| **WebSocket** | Auto-reconnect with 3s delay | SUPPORTED |
| **Message types** | message, emotion, speaking, pipeline_update, typing | SUPPORTED |
| **Pipeline polling** | 2s interval | SUPPORTED |
| **Abort controller** | For stopping generation | SUPPORTED |
| **Implementation status** | FULLY IMPLEMENTED | SUPPORTED |

---

## VERIFICATION SUMMARY

| Component | Claimed Status | Actual Status | Verified? |
|-----------|---------------|---------------|-----------|
| SNNEncoder (4 strategies) | Implemented | IMPLEMENTED | ✅ |
| PFCBrainArea (eligibility traces) | Implemented | IMPLEMENTED | ✅ |
| dACCBrainArea (STDP) | Implemented | IMPLEMENTED | ✅ |
| InsulaBrainArea (cognitive appraisal) | Implemented | IMPLEMENTED | ✅ |
| IPLBrainArea (multimodal) | Implemented | IMPLEMENTED | ✅ |
| BasalGangliaBrainArea (action selection) | Implemented | IMPLEMENTED | ✅ |
| WorkingMemory (decay/interference) | Implemented | IMPLEMENTED | ✅ |
| TextEmotionDetector (18 moods) | Implemented | IMPLEMENTED | ✅ |
| EmotionFusion (dynamic weighting) | Implemented | IMPLEMENTED | ✅ |
| VoicePipeline (full analysis) | Implemented | IMPLEMENTED | ✅ |
| FacePipeline (multi-backend) | Implemented | IMPLEMENTED | ✅ |
| PipelineOrchestrator (6-stage) | Implemented | IMPLEMENTED | ✅ |
| OrchestrationEngine (FSM) | Implemented | IMPLEMENTED | ✅ |
| BrainPipeline (integration) | Implemented | IMPLEMENTED | ✅ |
| CreationPipeline (11-step) | Implemented | IMPLEMENTED | ✅ |
| VRMViewer (3D) | Implemented | IMPLEMENTED | ✅ |
| PADEmotionEngine (50+ states) | Implemented | IMPLEMENTED | ✅ |

**ALL CLAIMED COMPONENTS VERIFIED AS IMPLEMENTED.**

---

*End of Technical Ground Truth*
