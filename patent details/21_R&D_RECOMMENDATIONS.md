# 21 — R&D RECOMMENDATIONS

## Date: August 21, 2026

---

## DECISION: OPTION C — MAJOR TECHNICAL IMPROVEMENT RECOMMENDED BEFORE FILING

The current implementation is functional but lacks:
1. Experimental validation (CRITICAL)
2. Measurable technical effects (CRITICAL)
3. Comparison with baselines (CRITICAL)
4. Some architectural refinements that would strengthen patentability

---

## P0 — ABSOLUTELY REQUIRED (Must complete before filing)

### R&D-1: Experimental Validation Suite

| Field | Value |
|-------|-------|
| **Problem** | No experiments have been performed. No measurable technical effects can be claimed. |
| **Current state** | Code exists, but no metrics collected |
| **Required change** | Build instrumentation into pipeline, run Experiment 1-3 from 19_EXPERIMENT_PLAN.md |
| **Why it strengthens patent** | Demonstrates measurable technical effect; required for any patent application |
| **Implementation complexity** | MEDIUM — add timing instrumentation + human evaluation protocol |
| **Experiment** | Experiments 1-3 |
| **Expected technical effect** | Quantified latency, accuracy, and improvement metrics |
| **Patent relevance** | CRITICAL — without this, no patent should be filed |
| **Estimated effort** | 2-3 weeks |

### R&D-2: Baseline Comparison Framework

| Field | Value |
|-------|-------|
| **Problem** | No comparison with baselines (LLM-only, single-modality emotion, etc.) |
| **Current state** | Only DreamTalk pipeline exists |
| **Required change** | Implement baseline configurations: (a) LLM-only, (b) voice-only emotion, (c) text-only emotion, (d) fixed-weight fusion |
| **Why it strengthens patent** | Shows the invention improves over known approaches |
| **Implementation complexity** | LOW — modify pipeline to bypass brain/emotion stages |
| **Experiment** | Experiments 1-2 |
| **Expected technical effect** | Quantified improvement over baselines |
| **Patent relevance** | HIGH |
| **Estimated effort** | 1 week |

---

## P1 — STRONGLY RECOMMENDED (Significantly strengthens patent)

### R&D-3: Adaptive Inference Routing (NEW FEATURE)

| Field | Value |
|-------|-------|
| **Problem** | All queries go through the full brain pipeline, wasting computation on simple queries |
| **Current state** | NOT CURRENTLY IMPLEMENTED |
| **Required change** | Route simple queries (low conflict) to rule-based response; route complex queries (high conflict) to LLM |
| **Why it strengthens patent** | Creates a new technical effect: brain-state-driven resource optimization |
| **Implementation complexity** | MEDIUM — add routing logic after dACC processing |
| **Experiment** | New experiment: adaptive vs fixed routing latency |
| **Expected technical effect** | 30-60% latency reduction for simple queries |
| **Patent relevance** | HIGH — creates additional claim scope |
| **Estimated effort** | 1-2 weeks |

**Implementation sketch:**
```
After dACC processing:
  if conflict_score < 0.3:
      → rule_based_response (fast, no LLM)
  elif conflict_score < 0.7:
      → small_LLM (medium)
  else:
      → full_LLM_with_brain_context (full)
```

### R&D-4: Closed-Loop Learning Validation

| Field | Value |
|-------|-------|
| **Problem** | STDP and TD learning are implemented but their effect is not measured |
| **Current state** | Learning rules exist in code |
| **Required change** | Run 50+ interaction sessions and measure learning impact |
| **Why it strengthens patent** | Demonstrates the system improves over time (unique differentiator) |
| **Implementation complexity** | LOW — code exists, need measurement |
| **Experiment** | Experiment 5 |
| **Expected technical effect** | Measurable improvement in action selection consistency |
| **Patent relevance** | HIGH |
| **Estimated effort** | 1 week |

### R&D-5: Brain-State-Driven Avatar Expression (NEW FEATURE)

| Field | Value |
|-------|-------|
| **Problem** | Avatar expression currently uses emotion labels, not brain states |
| **Current state** | Emotion labels drive blendshapes |
| **Required change** | Map brain area activations (PFC firing rate, dACC conflict, insula valence, BG action) directly to avatar expression parameters |
| **Why it strengthens patent** | Creates brain-to-avatar synchronization (novel technical effect) |
| **Implementation complexity** | HIGH — requires mapping brain states to blendshape parameters |
| **Experiment** | New experiment: brain-driven vs emotion-label-driven expression |
| **Expected technical effect** | More nuanced, continuous avatar expression |
| **Patent relevance** | HIGH — creates additional claim scope |
| **Estimated effort** | 2-3 weeks |

---

## P2 — OPTIONAL (Nice to have, but not required)

### R&D-6: Interruption Handling

| Field | Value |
|-------|-------|
| **Problem** | No graceful interruption handling when user speaks during avatar response |
| **Current state** | Basic abort controller in frontend |
| **Required change** | Implement multimodal cancellation token through TTS, animation, and LLM pipelines |
| **Why it strengthens patent** | Adds technical effect for real-time interaction |
| **Implementation complexity** | MEDIUM |
| **Patent relevance** | MEDIUM |
| **Estimated effort** | 1-2 weeks |

### R&D-7: Phoneme-Level Lip Sync

| Field | Value |
|-------|-------|
| **Problem** | Avatar lip sync uses audio energy, not phonemes |
| **Current state** | Energy-based lip parameters |
| **Required change** | Implement phoneme extraction and viseme mapping |
| **Why it strengthens patent** | Improves avatar animation quality |
| **Implementation complexity** | HIGH |
| **Patent relevance** | MEDIUM |
| **Estimated effort** | 3-4 weeks |

---

## R&D PRIORITY SUMMARY

| Priority | R&D Item | Effort | Patent Impact | Do Before Filing? |
|----------|---------|--------|--------------|-------------------|
| **P0** | Experimental Validation | 2-3 weeks | CRITICAL | **YES** |
| **P0** | Baseline Comparison | 1 week | HIGH | **YES** |
| P1 | Adaptive Inference Routing | 1-2 weeks | HIGH | RECOMMENDED |
| P1 | Closed-Loop Learning Validation | 1 week | HIGH | RECOMMENDED |
| P1 | Brain-State-Driven Avatar | 2-3 weeks | HIGH | RECOMMENDED |
| P2 | Interruption Handling | 1-2 weeks | MEDIUM | OPTIONAL |
| P2 | Phoneme Lip Sync | 3-4 weeks | MEDIUM | OPTIONAL |

---

## RECOMMENDED DEVELOPMENT ROADMAP

### Week 1-2: P0 Items
- Build instrumentation suite
- Run Experiment 1 (Brain vs no brain)
- Run Experiment 2 (Emotion fusion)
- Run Experiment 3 (Latency)
- Document all results

### Week 3-4: P1 Items
- Implement adaptive inference routing
- Validate closed-loop learning
- Run all remaining experiments

### Week 5-6: Filing Preparation
- Consult patent professional
- Conduct formal prior art search
- Draft complete specification
- Prepare drawings
- File application

---

*End of R&D Recommendations*
