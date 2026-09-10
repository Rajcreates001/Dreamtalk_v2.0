# 19 — EXPERIMENT PLAN

## Date: August 21, 2026

---

## CRITICAL: No experiments have been performed. This is the #1 weakness of the patent application.

---

## EXPERIMENT 1: Brain-Augmented vs Non-Augmented Response Quality

### Objective
Demonstrate that the SNN brain architecture produces measurably different (and better) conversational responses than LLM-only.

### Hypothesis
Brain-augmented responses show higher emotional appropriateness, action variety, and contextual relevance than LLM-only responses.

### Baseline
LLM-only: User input → LLM with static system prompt → Response

### Experimental
Brain-augmented: User input → SNNEncoder → 5 brain areas → Brain states → LLM with emotion-modulated system prompt → Response

### Dataset
50+ conversation scenarios across healthcare, business, and personal roles, including:
- Happy user queries
- Sad user queries
- Angry/hostile user queries
- Neutral queries
- Complex emotional queries (e.g., "I trusted you but you lied")

### Variables
- Independent: Brain processing (on/off)
- Dependent: Response emotional appropriateness, action type variety, conflict score correlation

### Metrics
- Human evaluation: Emotional appropriateness (1-5 scale)
- Action type distribution (entropy measure)
- Conflict score correlation with response quality
- Response length and coherence

### Expected Result
Brain-augmented responses show higher emotional appropriateness and more varied action types.

### Actual Result
NOT YET MEASURED

### Evidence Location
NOT YET GENERATED

### Priority: CRITICAL

---

## EXPERIMENT 2: Emotion Fusion vs Single Modality

### Objective
Demonstrate that fused emotion detection outperforms voice-only or text-only emotion detection.

### Hypothesis
Fused emotion accuracy > max(voice accuracy, text accuracy) on a test set with known ground truth.

### Baseline 1
Voice-only emotion detection

### Baseline 2
Text-only emotion detection

### Baseline 3
50/50 fixed-weight fusion

### Experimental
Confidence-weighted dynamic fusion

### Dataset
50+ audio+text pairs with labeled emotion ground truth, including:
- Congruent cases (voice and text agree)
- Incongruent cases (voice and text disagree, e.g., sarcastic)
- Noisy audio cases (voice less reliable)
- Ambiguous text cases (text less reliable)

### Variables
- Independent: Fusion method (voice-only, text-only, 50/50, confidence-weighted)
- Dependent: Emotion classification accuracy, PAD error

### Metrics
- Accuracy (correct mood classification)
- PAD mean absolute error
- Per-modality weight distribution
- Confidence calibration

### Expected Result
Confidence-weighted fusion outperforms all baselines, especially on incongruent and noisy cases.

### Actual Result
NOT YET MEASURED

### Priority: CRITICAL

---

## EXPERIMENT 3: End-to-End Pipeline Latency

### Objective
Measure the complete pipeline latency from user input to response generation.

### Hypothesis
Complete pipeline latency is within acceptable range for conversational interaction (< 5 seconds).

### Baseline
LLM-only latency (input → LLM response)

### Experimental
Full pipeline latency (input → face + voice + emotion + brain + LLM response)

### Dataset
10+ queries with timing instrumentation at each pipeline stage.

### Metrics
- Per-stage latency (emotion detection, SNN encoding, brain areas, LLM)
- Total pipeline latency
- Standard deviation
- Bottleneck identification

### Actual Result
NOT YET MEASURED

### Priority: HIGH

---

## EXPERIMENT 4: Brain State Correlation with Response Quality

### Objective
Demonstrate that brain area activations (conflict score, insula valence, BG action) correlate with response quality.

### Hypothesis
Higher conflict scores correlate with more complex emotional scenarios; insula valence correlates with emotional appropriateness.

### Dataset
30+ queries with human-rated response quality and recorded brain states.

### Metrics
- Pearson correlation: conflict_score × response_complexity
- Pearson correlation: insula_valence × emotional_appropriateness
- BG action type distribution across emotional categories

### Actual Result
NOT YET MEASURED

### Priority: HIGH

---

## EXPERIMENT 5: Learning (STDP + TD) Impact

### Objective
Demonstrate that STDP learning in dACC and TD learning in basal ganglia improve action selection over repeated interactions.

### Hypothesis
After 50+ interactions, the system shows improved action selection consistency and reduced conflict scores.

### Dataset
50+ sequential interactions simulating a conversation session.

### Metrics
- Conflict score trend over interactions
- Action selection consistency (same emotion → same action type)
- Weight convergence

### Actual Result
NOT YET MEASURED

### Priority: MEDIUM

---

## EXPERIMENT 6: Action Selection Variety

### Objective
Demonstrate that basal ganglia action selection produces varied response types across different emotional contexts.

### Hypothesis
Different emotional contexts produce different dominant action types.

### Dataset
Queries labeled by emotional category.

### Metrics
- Action type distribution per emotion category
- Entropy of action selection
- Chi-squared test for emotion-action association

### Actual Result
NOT YET MEASURED

### Priority: MEDIUM

---

## EXPERIMENT 7: Voice Cloning Quality

### Objective
Measure voice cloning quality across the cascade engines.

### Hypothesis
Higher-priority engines produce higher quality clones; fallback engines still produce acceptable quality.

### Dataset
10+ voice samples across languages.

### Metrics
- Mean Opinion Score (MOS) for each engine
- Speaker similarity score
- Cloning success rate per engine
- Cascade fallback rate

### Actual Result
NOT YET MEASURED

### Priority: MEDIUM

---

## EXPERIMENT 8: System Stability Under Load

### Objective
Demonstrate system stability under concurrent users.

### Dataset
10+ concurrent conversation sessions.

### Metrics
- Response time under load
- Error rate
- Memory usage
- CPU/GPU utilization

### Actual Result
NOT YET MEASURED

### Priority: LOW

---

## STATISTICAL REQUIREMENTS

| Requirement | Minimum |
|-------------|---------|
| Sample size per experiment | 30+ data points |
| Repeats per condition | 3+ |
| Statistical test | t-test or Mann-Whitney for pairwise; ANOVA for multi-group |
| Significance level | p < 0.05 |
| Effect size | Report Cohen's d |

---

## IMPLEMENTATION PRIORITY

| Priority | Experiment | Why |
|----------|-----------|-----|
| P0 | Experiment 1 (Brain vs no brain) | Most critical for patent — demonstrates the core invention's value |
| P0 | Experiment 2 (Emotion fusion) | Most critical for secondary invention |
| P1 | Experiment 3 (Latency) | Demonstrates practical feasibility |
| P1 | Experiment 4 (Brain correlation) | Demonstrates technical effect |
| P2 | Experiment 5 (Learning) | Demonstrates STDP/TD value |
| P2 | Experiment 6 (Action variety) | Demonstrates BG value |
| P2 | Experiment 7 (Voice cloning) | Demonstrates cascade value |
| P3 | Experiment 8 (Stability) | Nice to have |

---

*End of Experiment Plan*
