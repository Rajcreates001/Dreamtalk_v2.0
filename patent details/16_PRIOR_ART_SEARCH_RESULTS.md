# 16 — PRIOR ART SEARCH RESULTS

## Date: August 21, 2026

---

## ⚠️ CRITICAL LIMITATION

**Web search tool was unavailable during this analysis.** All prior art identifications below are based on domain knowledge of the neuromorphic computing, SNN, and conversational AI fields. These must be **independently verified** by searching:

- Google Patents (https://patents.google.com/)
- WIPO PATENTSCOPE (https://patentscope.wipo.int/)
- Espacenet (https://worldwide.espacenet.com/)
- USPTO (https://www.uspto.gov/)
- Indian Patent Office (https://ipindiaonline.gov.in/)
- Google Scholar
- IEEE Xplore
- ACM Digital Library
- arXiv
- GitHub

**No search results below should be treated as confirmed prior art until independently verified.**

---

## Category A: Spiking Neural Networks for NLP

### A1. BrainCog

| Field | Value | Status |
|-------|-------|--------|
| **Platform** | BrainCog (brain-inspired computing framework) | KNOWN IN DOMAIN |
| **Source** | https://github.com/THU-BrainCog | NEEDS VERIFICATION |
| **Relevance** | Provides brain area abstractions (PFC, basal ganglia, etc.) for SNN simulation | HIGH RISK |
| **Key difference** | BrainCog is a general-purpose SNN framework; DreamTalk applies it specifically to conversational AI with LLM integration | NEEDS VERIFICATION |
| **Patent status** | UNKNOWN — REQUIRES SEARCH | CRITICAL |
| **Risk** | BrainCog may have patents or publications covering brain area simulation | HIGH |

### A2. SpikingJelly

| Field | Value | Status |
|-------|-------|--------|
| **Platform** | SpikingJelly (SNN framework) | KNOWN IN DOMAIN |
| **Source** | https://github.com/fangwei123456/SpikingJelly | NEEDS VERIFICATION |
| **Relevance** | SNN training/inference framework; provides encoding strategies | MEDIUM RISK |
| **Key difference** | SpikingJelly is a framework, not a conversational system | LOW-MEDIUM |
| **Patent status** | UNKNOWN | MEDIUM |

### A3. SNN Text Classification Literature

| Field | Value | Status |
|-------|-------|--------|
| **Area** | SNN for text/sentiment classification | KNOWN IN DOMAIN |
| **Examples** | Various papers on rate-encoded SNN for text | NEEDS VERIFICATION |
| **Relevance** | SNN applied to NLP is a known research direction | MEDIUM RISK |
| **Key difference** | DreamTalk uses SNN not for classification but for cognitive processing with 5 brain areas | NEEDS VERIFICATION |
| **Risk** | Academic papers may disclose similar approaches | MEDIUM |

---

## Category B: Brain-Inspired Cognitive Architectures

### B1. ACT-R / SOAR / Global Workspace Theory

| Field | Value | Status |
|-------|-------|--------|
| **Area** | Cognitive architectures for AI | KNOWN IN DOMAIN |
| **Examples** | ACT-R, SOAR, LIDA, Global Workspace Theory | WELL-ESTABLISHED |
| **Relevance** | Cognitive architectures with multiple modules are well-known | HIGH RISK |
| **Key difference** | DreamTalk uses SNN specifically, not symbolic/probabilistic modules; integrates with LLM | NEEDS VERIFICATION |
| **Patent status** | Many patents exist in this space | HIGH |

### B2. Computational Neuroscience Models

| Field | Value | Status |
|-------|-------|--------|
| **Area** | PFC, dACC, Insula, Basal Ganglia computational models | KNOWN IN DOMAIN |
| **Examples** | O'Reilly prefrontal cortex models, Frank basal ganglia models, ACC conflict monitoring models | WELL-ESTABLISHED |
| **Relevance** | Individual brain area models are well-published | HIGH RISK |
| **Key difference** | DreamTalk combines 5 specific areas in a specific architecture for conversational AI | NEEDS VERIFICATION |
| **Risk** | The specific combination may be novel, but individual models are known | MEDIUM-HIGH |

---

## Category C: Multimodal Emotion Recognition

### C1. Audio-Visual Emotion Fusion

| Field | Value | Status |
|-------|-------|--------|
| **Area** | Multimodal emotion recognition | WELL-ESTABLISHED |
| **Examples** | IEMOCAP, CMU-MOSEI, RECOLA datasets and methods | WELL-ESTABLISHED |
| **Relevance** | Emotion fusion from voice+text is a known research area | HIGH RISK |
| **Key difference** | DreamTalk's specific confidence-weighted dynamic ensemble with bounded weights may be different | NEEDS VERIFICATION |
| **Patent status** | Many patents in this space | HIGH |

### C2. PAD Emotion Model

| Field | Value | Status |
|-------|-------|--------|
| **Area** | Pleasure-Arousal-Dominance emotion model | WELL-ESTABLISHED |
| **Source** | Mehrabian (1996), Russell (1980) | WELL-ESTABLISHED |
| **Relevance** | PAD is a published psychological model | PRIOR ART |
| **Key difference** | DreamTalk applies PAD to conversational AI, not inventing PAD itself | CANNOT CLAIM PAD |
| **Risk** | PAD model itself cannot be claimed | HIGH |

---

## Category D: Conversational AI Avatars

### D1. Soul Machines / UneeQ / Replika

| Field | Value | Status |
|-------|-------|--------|
| **Area** | Digital humans with emotion | COMMERCIAL PRODUCTS |
| **Examples** | Soul Machines (NZ), UneeQ (NZ), Replika (US) | KNOWN IN DOMAIN |
| **Relevance** | Digital humans with emotion and conversation exist | HIGH RISK |
| **Key difference** | DreamTalk's SNN brain processing is different from their architectures | NEEDS VERIFICATION |
| **Patent status** | Soul Machines has patents; UneeQ has patents | HIGH |

### D2. NVIDIA Avatar / Omniverse

| Field | Value | Status |
|-------|-------|--------|
| **Area** | Real-time avatar rendering | NVIDIA RESEARCH |
| **Examples** | NVIDIA Omniverse Audio2Face, ACE | KNOWN IN DOMAIN |
| **Relevance** | Real-time avatar animation from audio exists | MEDIUM RISK |
| **Key difference** | DreamTalk's SNN brain processing is different | NEEDS VERIFICATION |
| **Patent status** | NVIDIA has extensive patents | MEDIUM |

### D3. LivePortrait / MuseTalk

| Field | Value | Status |
|-------|-------|--------|
| **Area** | Expression-driven face animation | OPEN SOURCE |
| **Examples** | LivePortrait (KwaiVGI), MuseTalk | KNOWN IN DOMAIN |
| **Relevance** | Face animation from driving video/expression exists | LOW-MEDIUM RISK |
| **Key difference** | DreamTalk uses these as components, not as the invention | COMPONENT |
| **Patent status** | Open source, likely no patents | LOW |

---

## Category E: Voice Cloning and TTS

### E1. ElevenLabs / Resemble.ai / Coqui

| Field | Value | Status |
|-------|-------|--------|
| **Area** | Voice cloning and TTS | COMMERCIAL |
| **Examples** | ElevenLabs, Resemble.ai, Coqui TTS | KNOWN IN DOMAIN |
| **Relevance** | Voice cloning is well-established | MEDIUM RISK |
| **Key difference** | DreamTalk's cascade with emotion preservation may be different | NEEDS VERIFICATION |
| **Patent status** | ElevenLabs has patents | MEDIUM |

### E2. RVC / OpenVoice / IndicF5

| Field | Value | Status |
|-------|-------|--------|
| **Area** | Open-source voice conversion | OPEN SOURCE |
| **Examples** | RVC, OpenVoice (MyShell), IndicF5 (AI4Bharat) | KNOWN IN DOMAIN |
| **Relevance** | Individual engines are known; cascade may be novel | LOW-MEDIUM |
| **Key difference** | DreamTalk's specific 4-engine cascade with emotion preservation | NEEDS VERIFICATION |

---

## Category F: Spike Encoding Strategies

### F1. Rate/TTFS/Phase/Population Encoding

| Field | Value | Status |
|-------|-------|--------|
| **Area** | Spike encoding strategies | WELL-ESTABLISHED |
| **Examples** | Rate coding (Adrian 1926), TTFS, phase coding, population coding | NEUROSCIENCE FUNDAMENTALS |
| **Relevance** | All 4 encoding strategies are well-known | PRIOR ART |
| **Key difference** | DreamTalk applies them to NLP features; the combination may be novel | NEEDS VERIFICATION |
| **Risk** | Individual strategies cannot be claimed | HIGH |

---

## Category G: STDP Learning

### G1. Spike-Timing-Dependent Plasticity

| Field | Value | Status |
|-------|-------|--------|
| **Area** | STDP learning rule | WELL-ESTABLISHED |
| **Examples** | Bi & Poo (1998), many SNN papers | NEUROSCIENCE FUNDAMENTALS |
| **Relevance** | STDP is a published learning rule | PRIOR ART |
| **Key difference** | DreamTalk applies STDP to dACC conflict monitoring in conversational AI | NEEDS VERIFICATION |
| **Risk** | STDP itself cannot be claimed | HIGH |

---

## SEARCH COVERAGE ASSESSMENT

| Category | Searched? | Confidence | Risk |
|----------|-----------|------------|------|
| SNN for NLP | NOT VERIFIED | LOW (domain knowledge only) | HIGH |
| Brain-inspired cognitive architectures | NOT VERIFIED | LOW | HIGH |
| Multimodal emotion fusion | NOT VERIFIED | LOW | HIGH |
| Conversational AI avatars | NOT VERIFIED | LOW | HIGH |
| Voice cloning cascade | NOT VERIFIED | LOW | MEDIUM |
| Spike encoding | NOT VERIFIED | LOW | HIGH |
| STDP | NOT VERIFIED | LOW | HIGH |
| Basal ganglia AI | NOT VERIFIED | LOW | MEDIUM |

**OVERALL SEARCH CONFIDENCE: LOW**

**CRITICAL: Formal patent search by a professional patent searcher is REQUIRED before filing.**

---

## CLOSEST PRIOR ART (Based on Domain Knowledge)

### Closest 1: BrainCog Framework

- **What it provides:** Brain area abstractions (PFC, basal ganglia, etc.) for SNN simulation
- **What DreamTalk adds:** Application to conversational AI with LLM integration, emotion fusion, 12-type action selection
- **Risk level:** HIGH — may have overlapping claims

### Closest 2: Cognitive Architecture + LLM Papers

- **What exists:** Papers combining cognitive architectures with LLMs (e.g., "Cognitive Architectures for Language Agents")
- **What DreamTalk adds:** SNN-specific implementation with 5 brain areas and STDP learning
- **Risk level:** MEDIUM-HIGH

### Closest 3: Multimodal Emotion Fusion

- **What exists:** Many papers on audio-visual emotion fusion
- **What DreamTalk adds:** Specific confidence-weighted dynamic ensemble with bounded weights for conversational AI
- **Risk level:** MEDIUM

---

*End of Prior Art Search Results*
*⚠️ FORMAL PATENT SEARCH REQUIRED BEFORE FILING*
