# 17 — CLAIM-ELEMENT PRIOR ART MATRIX

## Date: August 21, 2026

---

## PRIMARY INVENTION: Neuromorphic SNN Brain for Conversational AI

### Claim Elements

| Element | Description | Prior Art (Known) | Disclosure Level | DreamTalk Difference | Risk |
|---------|-------------|-------------------|-----------------|---------------------|------|
| **E1** | Spike train encoding of text features | Rate/TTFS/phase/population encoding are neuroscience fundamentals | FULLY DISCLOSED in literature | Application to NLP features for conversational AI | MEDIUM |
| **E2** | PFC simulation with eligibility traces | Eligibility traces are known in RL (Schultz 1997, Singh & Sutton 1996) | FULLY DISCLOSED | Dopamine-modulated eligibility trace in conversational PFC | MEDIUM |
| **E3** | dACC conflict monitoring via entropy | ACC conflict monitoring models exist (Botvinick 2001) | FULLY DISCLOSED | Entropy-based conflict for conversational response quality | MEDIUM |
| **E4** | STDP learning in dACC | STDP is a published learning rule (Bi & Poo 1998) | FULLY DISCLOSED | STDP applied to dACC weight updates in conversational AI | MEDIUM |
| **E5** | Insula with cognitive appraisal | Insula computational models exist | PARTIALLY DISCLOSED | Insula with homeostasis for conversational emotion processing | MEDIUM |
| **E6** | IPL multimodal integration | Multimodal integration models exist | PARTIALLY DISCLOSED | IPL integrating PFC output with audio features | LOW-MEDIUM |
| **E7** | Basal ganglia D1/D2 action selection | BG models exist (Frank 2005, Gurney 2001) | FULLY DISCLOSED | 12-type conversational action selection with softmax | MEDIUM |
| **E8** | Working memory with capacity 7 | Miller's 7±2 is well-known | FULLY DISCLOSED | Working memory in conversational SNN brain | LOW |
| **E9** | 5 brain areas interconnected | Individual brain area models exist | INDIVIDUALLY DISCLOSED | Specific 5-area architecture for conversational AI | MEDIUM-HIGH |
| **E10** | Brain states → LLM system prompt | Prompt engineering is known | FULLY DISCLOSED | Brain area activations (not just emotion labels) modulating LLM | LOW-MEDIUM |
| **E11** | 12 action types for response selection | Action selection is known | FULLY DISCLOSED | 12 conversational response types via BG competition | LOW-MEDIUM |
| **E12** | TD learning in basal ganglia | TD learning is well-known (Sutton & Barto) | FULLY DISCLOSED | TD learning for conversational action value update | LOW |

### Combination Analysis

| Combination | Prior Art? | Difference | Risk |
|-------------|-----------|------------|------|
| E1+E2+E3+E4+E5+E6+E7+E8+E9 | NOT FOUND as combination | 5-brain-area architecture for conversational AI | MEDIUM-HIGH |
| E9+E10 | NOT FOUND | Brain states modulating LLM prompting | MEDIUM |
| E7+E11 | NOT FOUND | 12-type conversational action selection via BG | MEDIUM |
| E3+E4 | NOT FOUND | dACC with STDP for conversational conflict monitoring | MEDIUM |
| E1+E9 | NOT FOUND | Spike encoding feeding into 5-brain-area system | MEDIUM |

---

## SECONDARY INVENTION: Multi-Modal Emotion Fusion

### Claim Elements

| Element | Description | Prior Art (Known) | Disclosure Level | DreamTalk Difference | Risk |
|---------|-------------|-------------------|-----------------|---------------------|------|
| **F1** | Voice emotion from acoustic features | Voice emotion recognition is well-known | FULLY DISCLOSED | 7-feature category scoring for 7 emotions | LOW-MEDIUM |
| **F2** | Text emotion from VADER + keywords | VADER is published; keyword matching is known | FULLY DISCLOSED | 18-mood keyword dictionaries with weights | LOW |
| **F3** | Confidence-weighted fusion | Weighted fusion is known in signal processing | FULLY DISCLOSED | Specific formula: weight = min(conf*0.4+0.1, 0.6) | MEDIUM |
| **F4** | Bounded weights (max 0.6) | Weight bounding is known | PARTIALLY DISCLOSED | Specific 0.6 bound for conversational emotion | LOW-MEDIUM |
| **F5** | Provenance tracking | Explainable AI is known | PARTIALLY DISCLOSED | Full contribution tracking (vocal, textual, ensemble) | LOW |
| **F6** | PAD space fusion | PAD is published (Mehrabian) | FULLY DISCLOSED | PAD fusion from voice+text with dynamic weights | MEDIUM |

### Combination Analysis

| Combination | Prior Art? | Difference | Risk |
|-------------|-----------|------------|------|
| F1+F2+F3+F4+F5+F6 | NOT FOUND as exact combination | Dynamic confidence-weighted PAD fusion with provenance for conversational AI | MEDIUM |
| F3+F4 | NOT FOUND | Bounded confidence weighting for emotion fusion | LOW-MEDIUM |

---

## PRIOR ART RISK SUMMARY

| Element Group | Overall Prior Art Risk | Key Threat | Mitigation |
|--------------|----------------------|------------|------------|
| SNN Brain Architecture (E1-E12) | MEDIUM-HIGH | BrainCog, cognitive architectures | Claim the specific conversational AI application and LLM integration |
| Emotion Fusion (F1-F6) | MEDIUM | Audio-visual emotion fusion literature | Claim the specific dynamic weighting and provenance |
| Pipeline Integration | MEDIUM | General multi-stage AI pipelines | Claim the brain-cognition-specific pipeline |
| Voice Cloning Cascade | LOW-MEDIUM | Individual cloning engines | Claim the cascade with emotion preservation |

---

## CRITICAL FINDING

**The individual elements of the SNN brain architecture are ALL known in prior art.** The novelty, if any, lies in:

1. The **specific combination** of 5 brain areas for conversational AI
2. The **application** to LLM-controlled conversational response generation
3. The **integration** of brain states into LLM system prompts
4. The **12-type action selection** via basal ganglia competition

**The combination risk is HIGH** — a skilled person starting from BrainCog or cognitive architecture literature might arrive at a similar system.

**The key differentiator is the LLM integration** — using brain area activations (not just emotion labels) to modulate LLM behavior. This is the most likely novel contribution.

---

*End of Prior Art Claim Matrix*
