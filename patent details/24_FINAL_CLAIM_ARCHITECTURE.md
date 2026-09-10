# 24 — FINAL CLAIM ARCHITECTURE

## Date: August 21, 2026

---

## Claim Strategy

Three independent claims at different levels of abstraction:
1. **System Claim** (broadest)
2. **Method Claim** (process-focused)
3. **Computer-Implemented Process Claim** (Indian CRI-friendly)

Plus dependent claims for specific features.

---

## INDEPENDENT CLAIM 1: SYSTEM CLAIM (BROAD)

### Concept
A system comprising:
- Spike train encoder (multi-strategy)
- 5 interconnected simulated brain areas with specific data flows
- Multimodal emotion fusion with confidence weighting
- Brain-state-modulated LLM integration
- Basal ganglia action selection

### Claim Elements

**E1:** A spike train encoder configured to convert text feature vectors into spike trains using at least one encoding strategy selected from rate encoding, time-to-first-spike encoding, phase encoding, and population encoding.

**E2:** A prefrontal cortex simulation module configured to process spike trains through a linear transformation with leaky rectified linear unit activation and dopamine-modulated eligibility trace updates.

**E3:** A dorsal anterior cingulate cortex simulation module configured to receive output from the prefrontal cortex simulation module and compute conflict scores using entropy-based conflict monitoring.

**E4:** An insula simulation module configured to compute emotional valence from emotion features using weighted integration with homeostasis drift toward equilibrium.

**E5:** A basal ganglia simulation module configured to receive output from the prefrontal cortex simulation module, the conflict score from the dorsal anterior cingulate cortex simulation module, and the emotional valence from the insula simulation module, and to select a conversational action type from a plurality of action types using direct and indirect pathway modulation and softmax selection.

**E6:** A multimodal emotion fusion module configured to dynamically weight emotion predictions from voice acoustic features and text sentiment analysis based on per-modality confidence scores.

**E7:** A large language model integration module configured to generate a response text using a system prompt modulated by the emotional valence, the selected conversational action type, and cognitive appraisal information derived from the brain area activations.

### Novel Element
The specific architectural arrangement wherein the basal ganglia simulation module receives outputs from the prefrontal cortex simulation module, the dorsal anterior cingulate cortex simulation module, and the insula simulation module, and the multimodal emotion fusion module provides emotion features to the insula simulation module, and the brain area activations modulate the large language model system prompt.

### Technical Effect
Generation of emotion-modulated, action-varied conversational responses through biologically-inspired neural processing, producing measurably different outputs than systems using only language model inference without intermediate cognitive processing.

---

## INDEPENDENT CLAIM 2: METHOD CLAIM

### Concept
A method comprising:
1. Encoding text features into spike trains
2. Processing through 5 brain areas
3. Fusing multimodal emotion
4. Selecting action type
5. Generating response with brain-state-modulated prompt

### Claim Elements

**M1:** Converting text input into a feature vector.

**M2:** Encoding the feature vector into a spike train using at least one neural encoding strategy.

**M3:** Processing the spike train through a simulated prefrontal cortex module to produce planning output, the simulated prefrontal cortex module maintaining an eligibility trace updated by a dopamine modulation signal.

**M4:** Processing the planning output through a simulated dorsal anterior cingulate cortex module to produce a conflict score, the simulated dorsal anterior cingulate cortex module updating connection weights using spike-timing-dependent plasticity.

**M5:** Processing emotion features through a simulated insula module to produce an emotional valence, the simulated insula module maintaining homeostasis that drifts toward equilibrium.

**M6:** Selecting a conversational action type from a plurality of action types using a simulated basal ganglia module that receives the planning output, the conflict score, and the emotional valence, the selection performed using direct and indirect pathway modulation and softmax selection.

**M7:** Independently detecting emotion from voice acoustic features and text sentiment analysis, computing per-modality confidence scores, and fusing the emotion predictions using dynamically computed weights based on the confidence scores.

**M8:** Generating a response text using a language model with a system prompt that includes the emotional valence, the selected action type, cognitive appraisal information, and brain area activation metrics.

---

## INDEPENDENT CLAIM 3: COMPUTER-IMPLEMENTED PROCESS CLAIM (INDIAN CRI-FRIENDLY)

### Concept
A computer-implemented process that produces a technical effect: the generation of synchronized multimodal output (text response + avatar expression parameters) from user input through neuromorphic processing.

### Claim Elements

**C1:** A computer-implemented process for generating emotion-aware conversational responses, the process comprising:

**C2:** receiving, at a processor, text input from a user;

**C3:** converting, by the processor, the text input into a numerical feature vector;

**C4:** encoding, by the processor, the numerical feature vector into a temporal spike train matrix using a selected neural encoding strategy, the spike train matrix representing the text input as a pattern of neural spike events over a plurality of timesteps;

**C5:** processing, by the processor, the spike train matrix through a first simulated neural module configured to perform planning and executive control using a linear transformation with leaky activation and eligibility trace learning, to produce a planning output;

**C6:** processing, by the processor, the planning output through a second simulated neural module configured to perform conflict monitoring using entropy-based analysis and spike-timing-dependent plasticity learning, to produce a conflict measure;

**C7:** processing, by the processor, emotion features through a third simulated neural module configured to perform emotional appraisal using weighted integration with homeostatic regulation, to produce an emotional state value;

**C8:** selecting, by the processor, a response strategy from a set of available response strategies using a fourth simulated neural module configured to perform action selection using competing excitatory and inhibitory pathway modulation and probabilistic selection;

**C9:** generating, by the processor, a response text using a language model, wherein the language model receives a prompt that includes the emotional state value, the selected response strategy, the conflict measure, and cognitive state information derived from the simulated neural modules;

**C10:** the process producing a technical effect of generating varied, emotion-modulated conversational responses through neuromorphic processing that differs from direct language model inference.

---

## DEPENDENT CLAIMS

### Group 1: Encoding (Depends on any independent claim)

**D1.1:** The system/process of any preceding claim, wherein the spike train encoder supports rate encoding using Bernoulli sampling where spike probability is proportional to feature value.

**D1.2:** The system/process of any preceding claim, wherein the spike train encoder supports time-to-first-spike encoding where the time of the first spike is inversely proportional to the feature value.

**D1.3:** The system/process of any preceding claim, wherein the spike train encoder supports population encoding using Gaussian tuning curves with adjustable bandwidth.

### Group 2: Brain Area Details (Depends on any independent claim)

**D2.1:** The system/process of any preceding claim, wherein the prefrontal cortex simulation module maintains an eligibility trace matrix of dimensions [hidden_dim × input_dim], the eligibility trace updated as: trace += dopamine × learning_rate × outer(output, input).

**D2.2:** The system/process of any preceding claim, wherein the dorsal anterior cingulate cortex simulation module computes the conflict score as the normalized entropy of the softmax output distribution.

**D2.3:** The system/process of any preceding claim, wherein the insula simulation module maintains a homeostasis value that converges toward zero at a rate of 0.02 per timestep.

**D2.4:** The system/process of any preceding claim, wherein the basal ganglia simulation module comprises a set of direct pathway weights and indirect pathway weights, the direct pathway weights modulated by one minus the conflict score and the indirect pathway weights modulated by the conflict score.

**D2.5:** The system/process of any preceding claim, wherein the plurality of action types includes at least: greeting, questioning, empathetic response, analytical response, humor, redirection, confirmation, elaboration, advising, learning, deferral, and termination.

**D2.6:** The system/process of any preceding claim, wherein the basal ganglia simulation module updates action values using temporal difference learning with a configurable learning rate.

### Group 3: Emotion Fusion (Depends on any independent claim)

**D3.1:** The system/process of any preceding claim, wherein the dynamic weight for each modality is computed as a function of the per-modality confidence score, bounded by a maximum weight to prevent any single modality from dominating the fusion.

**D3.2:** The system/process of any preceding claim, wherein the multimodal emotion fusion module records provenance information indicating each modality's contribution to the fused emotion profile.

**D3.3:** The system/process of any preceding claim, wherein the voice acoustic features include at least: pitch statistics, energy statistics, spectral centroid, jitter, shimmer, harmonics-to-noise ratio, and speaking rate.

### Group 4: Working Memory (Depends on any independent claim)

**D4.1:** The system/process of any preceding claim, further comprising a working memory module with a fixed capacity, wherein items in the working memory decay in strength over time and experience interference from newer items.

### Group 5: Learning (Depends on any independent claim)

**D5.1:** The system/process of any preceding claim, wherein the dorsal anterior cingulate cortex simulation module updates its connection weights using spike-timing-dependent plasticity, the weight update proportional to the outer product of post-synaptic and pre-synaptic activity minus a weight decay term.

**D5.2:** The system/process of any preceding claim, wherein the prefrontal cortex simulation module updates its eligibility trace using a dopamine modulation signal derived from the conflict score computed by the dorsal anterior cingulate cortex simulation module.

---

## CLAIM SCOPE ANALYSIS

| Claim Level | Scope | Defensibility | Support |
|-------------|-------|--------------|---------|
| Independent 1 (System) | Broadest | Moderate | Supported by code |
| Independent 2 (Method) | Broad | Moderate | Supported by code |
| Independent 3 (CRI) | Indian-specific | Moderate | Supported by code |
| Dependent Groups 1-5 | Narrower | Stronger | Fully supported |

---

## DESIGN-AROUND ANALYSIS

### How a Competitor Might Avoid the Claims

1. **Replace SNN with conventional neural network** → Would avoid spike encoding claims but not the 5-brain-area architecture claims
2. **Remove one brain area** → Would avoid the "5 interconnected brain areas" claim but not the "plurality of simulated neural modules" claim
3. **Replace STDP with backpropagation** → Would avoid STDP claims but not the overall architecture claims
4. **Use fixed-weight emotion fusion** → Would avoid dynamic weighting claims but not the fusion claims
5. **Use rule-based action selection** → Would avoid basal ganglia claims but not the overall system claims

### Strengthening Against Design-Around

- Include dependent claims for specific brain area configurations
- Include claims for the "plurality of simulated neural modules" (not just "5")
- Include claims for "brain-state-modulated language model prompting" (not just specific brain areas)
- Include claims for the emotion fusion with confidence weighting (independent of brain architecture)

---

*End of Final Claim Architecture*
