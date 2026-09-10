# 11 — CLAIM CANDIDATES

## Date: August 21, 2026

---

## Claim Writing Principles

1. Claim the inventive technical mechanism, not the brand name
2. Do not claim generic "AI", "LLM", "RAG", "3D avatar", "TTS", "lip sync"
3. Include concrete technical relationships between components
4. Ensure specification supports every important claim element
5. Consider alternative embodiments
6. Avoid vague language ("configured to intelligently...")

---

## Independent Claims

### Claim 1: System Claim — Neuromorphic Brain Architecture

**Claimed Subject:** A computer-implemented system for generating emotion-aware conversational responses

**Required Elements:**
1. A spike train encoder configured to convert text feature vectors into spike trains using at least one of rate encoding, time-to-first-spike encoding, phase encoding, or population encoding
2. A prefrontal cortex simulation module configured to process spike trains through a linear transform with leaky ReLU activation and dopamine-modulated eligibility trace updates
3. A dorsal anterior cingulate cortex simulation module configured to compute conflict scores from prefrontal cortex output using entropy-based conflict monitoring and update connection weights using spike-timing-dependent plasticity
4. An insula simulation module configured to compute emotional valence from emotion features using weighted integration with homeostasis drift
5. A basal ganglia simulation module configured to select a conversational action type from a plurality of action types using direct and indirect pathway modulation and softmax selection
6. A large language model integration configured to generate a response text using the selected action type and emotional valence to modulate a system prompt

**Novel Element:** The specific interconnection of the five simulated brain areas with their respective learning rules (eligibility traces, STDP, homeostasis, TD learning) producing emotion-modulated action selection

**Technical Effect:** Generation of varied, context-appropriate, emotion-modulated conversational responses

**Prior-Art Risk:** MEDIUM-HIGH
**Section 3(k) Concern:** MODERATE — must frame as system producing technical effect
**Evidence:** `pipeline/brain_pipeline.py:BrainPipeline.make_decision()`

---

### Claim 2: System Claim — Multi-Modal Emotion Fusion

**Claimed Subject:** A computer-implemented system for multi-modal emotion detection

**Required Elements:**
1. A voice emotion predictor configured to extract acoustic features from audio including pitch, energy, spectral centroid, jitter, shimmer, harmonics-to-noise ratio, and speaking rate, and predict an emotion from the acoustic features
2. A text emotion detector configured to compute sentiment scores using lexicon-based analysis and map the sentiment scores to a pleasure-arousal-dominance emotion space
3. A fusion module configured to compute per-modality confidence scores and dynamically weight contributions from the voice emotion predictor and the text emotion detector based on the confidence scores
4. An output module configured to produce a fused emotion profile with provenance tracking of each modality's contribution

**Novel Element:** The dynamic confidence-weighted ensemble with bounded weights and transparent provenance tracking

**Technical Effect:** More accurate emotion detection by adapting to per-modality reliability

**Prior-Art Risk:** MEDIUM
**Section 3(k) Concern:** LOW-MODERATE
**Evidence:** `pipeline/voice_pipeline.py:fuse_emotion_profiles()`

---

### Claim 3: Method Claim — Conversational Response Generation

**Claimed Subject:** A computer-implemented method for generating emotion-aware conversational responses

**Required Elements:**
1. Receiving text input from a user
2. Converting the text input into a feature vector
3. Encoding the feature vector into a spike train using at least one neural encoding strategy
4. Processing the spike train through a simulated prefrontal cortex module to produce planning output
5. Processing the planning output through a simulated dorsal anterior cingulate cortex module to produce a conflict score
6. Processing emotion features through a simulated insula module to produce an emotional valence
7. Selecting a conversational action type from a plurality of action types using a simulated basal ganglia module that receives the planning output, conflict score, and emotional valence
8. Generating a response text using a language model with a system prompt modulated by the emotional valence and the selected action type

**Novel Element:** The sequential processing through simulated brain areas with biologically-inspired learning rules

**Technical Effect:** Emotion-modulated, action-varied conversational response generation

**Prior-Art Risk:** MEDIUM-HIGH
**Section 3(k) Concern:** MODERATE
**Evidence:** `pipeline/brain_pipeline.py:BrainPipeline.make_decision()`

---

## Dependent Claims

### Claim 4: Dependent on Claim 1 — Spike Encoding

**Subject:** The system of claim 1, wherein the spike train encoder supports a plurality of encoding strategies selectable at runtime, including rate encoding using Bernoulli sampling, time-to-first-spike encoding using inverse feature-to-time mapping, phase encoding using sinusoidal modulation, and population encoding using Gaussian tuning curves.

**Evidence:** `pipeline/brain_pipeline.py:SNNEncoder`

### Claim 5: Dependent on Claim 1 — Eligibility Trace

**Subject:** The system of claim 1, wherein the prefrontal cortex simulation module maintains an eligibility trace matrix that is updated using a dopamine modulation signal, and wherein the dopamine modulation signal is derived from a conflict score computed by the dorsal anterior cingulate cortex module.

**Evidence:** `pipeline/brain_pipeline.py:PFCBrainArea.forward()`

### Claim 6: Dependent on Claim 1 — Working Memory

**Subject:** The system of claim 1, further comprising a working memory module with a fixed capacity limit, wherein items in the working memory decay in strength over time and experience interference from newer items, and wherein the working memory provides context to the prefrontal cortex module.

**Evidence:** `pipeline/brain_pipeline.py:WorkingMemory`

### Claim 7: Dependent on Claim 2 — Weight Bounds

**Subject:** The system of claim 2, wherein the dynamic weighting is bounded such that no single modality contributes more than a predetermined maximum weight to the fused emotion profile, and wherein the weights are computed as a function of per-modality confidence scores.

**Evidence:** `pipeline/voice_pipeline.py:fuse_emotion_profiles()` — `voice_weight = min(voice_confidence * 0.4 + 0.1, 0.6)`

### Claim 8: Dependent on Claim 1 — Action Types

**Subject:** The system of claim 1, wherein the plurality of action types includes at least: greeting, questioning, empathetic response, analytical response, humor, redirection, confirmation, elaboration, advising, learning, deferral, and termination.

**Evidence:** `pipeline/brain_pipeline.py:BasalGangliaBrainArea.ACTION_SPACE`

### Claim 9: Dependent on Claim 1 — TD Learning

**Subject:** The system of claim 1, wherein the basal ganglia simulation module updates action values using temporal difference learning with a learning rate parameter.

**Evidence:** `pipeline/brain_pipeline.py:BasalGangliaBrainArea.update()`

### Claim 10: System Claim — Complete Pipeline

**Subject:** A computer-implemented system for creating and operating a digital twin, the system comprising:
1. A face analysis pipeline configured to detect faces, extract landmarks, and generate 3D mesh models from images
2. A voice analysis pipeline configured to extract acoustic features, detect speakers, and clone voices from audio
3. An emotion fusion module as defined in claim 2
4. A neuromorphic brain architecture as defined in claim 1
5. An animation pipeline configured to generate facial animation parameters from emotion profiles
6. A persistence module configured to store pipeline results in a database

**Evidence:** `pipeline/orchestrator.py`

---

## Claim Risk Assessment

| Claim | Prior-Art Risk | Section 3(k) Risk | Evidence Strength |
|-------|---------------|-------------------|-------------------|
| Claim 1 (System - Brain) | MEDIUM-HIGH | MODERATE | HIGH |
| Claim 2 (System - Fusion) | MEDIUM | LOW-MODERATE | HIGH |
| Claim 3 (Method - Response) | MEDIUM-HIGH | MODERATE | HIGH |
| Claim 4 (Encoding) | MEDIUM | MODERATE | HIGH |
| Claim 5 (Eligibility) | MEDIUM | MODERATE | HIGH |
| Claim 6 (Working Memory) | LOW-MEDIUM | LOW | HIGH |
| Claim 7 (Weight Bounds) | LOW-MEDIUM | LOW | HIGH |
| Claim 8 (Action Types) | LOW-MEDIUM | LOW | HIGH |
| Claim 9 (TD Learning) | MEDIUM | MODERATE | HIGH |
| Claim 10 (Pipeline) | MEDIUM-HIGH | LOW | HIGH |

---

*End of Claim Candidates*
