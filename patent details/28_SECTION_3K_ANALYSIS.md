# 28 — SECTION 3(k) ANALYSIS

## Date: August 21, 2026

---

## Legal Framework

Section 3(k) of the Indian Patents Act, 1970 (as amended) states:

> "The following inventions shall not be regarded as inventions for the purposes of this Act, namely —
> (a) an invention which is frivolous or which claims anything obviously contrary to well established natural laws;
> (b) the discovery of a scientific principle or the discovery of any abstract theory or discovery of any living or non-living substance or thing;
> (c) the mere discovery of a new form of a known substance which does not result in the enhancement of the known efficacy of that substance;
> (d) ...
> (k) a mathematical or business method or a computer programme per se or algorithms;"

**Note:** The Indian Patent Office's guidelines on Computer-Related Inventions (CRI) provide additional guidance. The key test is whether the invention produces a **technical effect** or **technical contribution** beyond the mere implementation of an algorithm on a computer.

---

## Analysis of DreamTalk Against Section 3(k)

### Element-by-Element Assessment

| Element | Is it an algorithm? | Is it a mathematical method? | Is it a computer program per se? | Does it produce technical effect? | Section 3(k) Risk |
|---------|--------------------|-----------------------------|---------------------------------|----------------------------------|--------------------|
| SNN spike encoding | YES — encoding algorithm | YES — mathematical transformation | YES — implemented in software | Minimal alone; meaningful in system context | HIGH |
| PFC eligibility trace | YES — learning algorithm | YES — matrix operations | YES — NumPy implementation | Minimal alone; meaningful in system context | HIGH |
| dACC conflict monitoring | YES — entropy computation | YES — mathematical formula | YES — NumPy implementation | Monitors system state; modest technical effect | HIGH |
| STDP learning | YES — learning algorithm | YES — weight update formula | YES — NumPy implementation | Improves system over time | HIGH |
| Basal ganglia selection | YES — softmax algorithm | YES — probability computation | YES — NumPy implementation | Selects response type; functional effect | HIGH |
| Emotion fusion | YES — weighting algorithm | YES — weighted average | YES — Python implementation | Improves emotion detection accuracy | MEDIUM |
| Brain area architecture | SYSTEM ARCHITECTURE | Not primarily mathematical | Not per se — architectural arrangement | Produces varied, emotion-modulated responses | MEDIUM |
| Brain states → LLM prompt | DATA TRANSFORMATION | Not primarily mathematical | System integration | Produces measurably different LLM output | MEDIUM |
| Complete pipeline | SYSTEM ARCHITECTURE | Not primarily mathematical | Not per se — system integration | End-to-end technical process | LOW-MEDIUM |

---

## Key Finding

**Individually, most elements face HIGH Section 3(k) risk** because they are algorithms implemented in software on conventional hardware.

**However, the system as a whole may survive Section 3(k) scrutiny** if:

1. The claims are framed as a **system architecture** producing a technical effect, not as individual algorithms
2. The **technical effect** is clearly demonstrated (measurable improvement in response quality, latency, etc.)
3. The claims specify **concrete technical relationships** between components, not just a list of algorithms
4. The specification describes how the components **interact** to produce the technical effect

---

## Indian CRI Guidelines Assessment

The Indian Patent Office's CRI guidelines (2017, as amended) state:

> "If the claimed invention is only a computer programme, it is excluded under Section 3(k). However, if it has a technical effect or technical contribution, it may be patentable."

> "A computer programme with technical effect may be patentable. The technical effect should be beyond the normal physical interactions between the programme and the computer on which it runs."

### DreamTalk's Technical Effect Arguments

**FOR patentability:**
1. The system processes text through biologically-inspired neural simulations, producing brain area activations that are qualitatively different from conventional neural network outputs
2. The brain states are used to modulate LLM prompting, producing measurably different responses
3. The emotion fusion improves emotion detection accuracy (if experiments confirm)
4. The complete pipeline produces synchronized multimodal output (text + avatar expression)
5. The STDP/TD learning improves system performance over time

**AGAINST patentability:**
1. All brain areas are simulated in NumPy/PyTorch on conventional hardware — no neuromorphic hardware
2. The "biological" brain areas are mathematical transformations, not actual neural simulations
3. The system is a software application running on a standard computer
4. The LLM integration is prompt engineering, not a technical transformation
5. Individual algorithms (softmax, entropy, weighted average) are well-known

---

## Risk Mitigation Strategies

### Strategy 1: Frame as System Architecture
**Claim:** "A system comprising [components] configured to [technical relationships] producing [technical effect]"
**Risk:** MODERATE — system claims may survive if technical effect is demonstrated

### Strategy 2: Emphasize Technical Effect
**Focus:** The measurable improvement in response quality, emotion accuracy, and action variety
**Risk:** MODERATE — requires experimental evidence

### Strategy 3: Emphasize Data Transformation
**Focus:** The specific transformation of text features into spike trains, through brain areas, into brain states, into LLM prompts
**Risk:** LOW-MEDIUM — data transformation arguments are generally accepted

### Strategy 4: Avoid Pure Algorithm Claims
**Avoid:** "A method comprising: encoding using rate encoding..." (algorithm claim)
**Prefer:** "A system comprising a spike train encoder configured to convert text features into temporal spike train matrices that are processed by a simulated prefrontal cortex module..." (system claim)

---

## Section 3(k) Risk Summary

| Claim Type | Section 3(k) Risk | Mitigation |
|-----------|-------------------|------------|
| Individual algorithm claims | HIGH | Avoid |
| System architecture claims | MEDIUM | Frame as technical system |
| Method claims (process flow) | MEDIUM | Emphasize technical effect |
| CRI claims (Indian-specific) | MEDIUM | Emphasize technical contribution |

---

## Recommendation

**Section 3(k) risk is MODERATE for the overall system claim** if:
1. Experimental evidence demonstrates measurable technical effect
2. Claims are framed as system architecture, not individual algorithms
3. Specification describes concrete technical relationships between components
4. Prior art search confirms the combination is not obvious

**Section 3(k) risk is HIGH for individual algorithm claims.** Avoid claiming individual algorithms.

---

*End of Section 3(k) Analysis*
