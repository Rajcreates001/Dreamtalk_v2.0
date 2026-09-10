# 13 — MISSING INFORMATION

## Date: August 21, 2026

---

## Critical Missing Items

### A. Invention

| # | Question | Why It Matters | Who Should Answer | Priority |
|---|----------|---------------|-------------------|----------|
| A1 | Who conceived the neuromorphic brain architecture? | Determines inventorship | Team lead / project owner | CRITICAL |
| A2 | Who conceived the emotion fusion mechanism? | Determines inventorship | Team lead / project owner | CRITICAL |
| A3 | Who conceived the spike encoding for NLP? | Determines inventorship | Team lead / project owner | CRITICAL |
| A4 | Was the brain architecture designed as a unified invention or assembled incrementally? | Affects claim scope | Inventor | CRITICAL |
| A5 | Are there alternative embodiments not implemented in code? | Expands claim scope | Inventor | HIGH |

### B. Architecture

| # | Question | Why It Matters | Who Should Answer | Priority |
|---|----------|---------------|-------------------|----------|
| B1 | Are there other pipeline configurations not shown in code? | Alternative embodiments | Developer | HIGH |
| B2 | Is the 5-brain-area architecture fixed or configurable? | Claim breadth | Developer | HIGH |
| B3 | Can brain areas be added/removed/replaced? | Alternative embodiments | Developer | MEDIUM |
| B4 | What is the actual data flow during production use vs test? | Accuracy of specification | Developer | HIGH |

### C. Algorithms

| # | Question | Why It Matters | Who Should Answer | Priority |
|---|----------|---------------|-------------------|----------|
| C1 | Were the spike encoding strategies designed specifically for this system? | Inventive contribution | Inventor | HIGH |
| C2 | Were the brain area weight matrices initialized randomly or trained? | Technical detail | Developer | HIGH |
| C3 | Has the STDP learning been validated to produce meaningful weight updates? | Experimental evidence | Developer | HIGH |
| C4 | Has the eligibility trace in PFC been validated to improve responses? | Experimental evidence | Developer | HIGH |
| C5 | What are the actual dopamine signal values during operation? | Technical detail | Developer | MEDIUM |

### D. Data Flow

| # | Question | Why It Matters | Who Should Answer | Priority |
|---|----------|---------------|-------------------|----------|
| D1 | What is the actual latency of the complete pipeline? | Technical effect measurement | Developer | CRITICAL |
| D2 | What is the latency of each brain area processing step? | Technical effect measurement | Developer | HIGH |
| D3 | What is the end-to-end latency from user input to avatar response? | User experience metric | Developer | CRITICAL |
| D4 | Are there any buffering or synchronization issues? | Technical detail | Developer | HIGH |

### E. AI Models

| # | Question | Why It Matters | Who Should Answer | Priority |
|---|----------|---------------|-------------------|----------|
| E1 | Which LLM is used in production? | Technical detail | Developer | HIGH |
| E2 | What model parameters are used (temperature, max_tokens)? | Technical detail | Developer | MEDIUM |
| E3 | Is the LLM fine-tuned or used as-is? | Technical detail | Developer | HIGH |
| E4 | What is the LLM's actual response quality with brain-augmented prompts vs without? | Experimental evidence | Developer | CRITICAL |

### F. Emotion

| # | Question | Why It Matters | Who Should Answer | Priority |
|---|----------|---------------|-------------------|----------|
| F1 | Has the emotion fusion been validated against ground truth? | Experimental evidence | Developer | CRITICAL |
| F2 | What is the accuracy of voice emotion detection? | Technical effect | Developer | HIGH |
| F3 | What is the accuracy of text emotion detection? | Technical effect | Developer | HIGH |
| F4 | Does the fused emotion improve over single-modality detection? | Technical effect | Developer | CRITICAL |
| F5 | What is the impact of emotion fusion on avatar expression accuracy? | Technical effect | Developer | HIGH |

### G. Avatar / Animation

| # | Question | Why It Matters | Who Should Answer | Priority |
|---|----------|---------------|-------------------|----------|
| G1 | What is the actual avatar animation latency? | Technical effect | Developer | HIGH |
| G2 | Is the FLAME 3D mesh generation working in production? | Implementation status | Developer | HIGH |
| G3 | Is LivePortrait wired for real-time animation? | Implementation status | Developer | HIGH |
| G4 | What is the frame rate of avatar animation? | Technical effect | Developer | HIGH |

### H. Voice

| # | Question | Why It Matters | Who Should Answer | Priority |
|---|----------|---------------|-------------------|----------|
| H1 | What is the actual voice cloning quality (MOS score)? | Technical effect | Developer | HIGH |
| H2 | Which TTS engine is actually used in production? | Technical detail | Developer | MEDIUM |
| H3 | What languages are actually supported in production? | Technical detail | Developer | MEDIUM |
| H4 | What is the TTS latency? | Technical effect | Developer | HIGH |

### I. Experiments

| # | Question | Why It Matters | Who Should Answer | Priority |
|---|----------|---------------|-------------------|----------|
| I1 | Has any experiment been run comparing brain-augmented vs non-augmented responses? | Critical for patent | Developer | CRITICAL |
| I2 | Has the emotion fusion been measured against baselines? | Critical for patent | Developer | CRITICAL |
| I3 | Has the pipeline latency been measured? | Technical effect | Developer | CRITICAL |
| I4 | Has the voice cloning quality been measured? | Technical effect | Developer | HIGH |
| I5 | Has the avatar animation accuracy been measured? | Technical effect | Developer | HIGH |

### J. Prior Art

| # | Question | Why It Matters | Who Should Answer | Priority |
|---|----------|---------------|-------------------|----------|
| J1 | Has any prior art search been conducted? | Determines novelty | Patent professional | CRITICAL |
| J2 | Are there similar products or patents in this space? | Novelty risk | Patent professional | CRITICAL |
| J3 | Has BrainCog or similar SNN libraries been checked for similar claims? | Prior art risk | Patent professional | HIGH |

### K. Public Disclosure

| # | Question | Why It Matters | Who Should Answer | Priority |
|---|----------|---------------|-------------------|----------|
| K1 | Is there a public GitHub repository? | Novelty destruction risk | Project owner | CRITICAL |
| K2 | When was the repository first made public? | Filing deadline | Project owner | CRITICAL |
| K3 | What technical details are publicly visible? | Scope of disclosure | Project owner | CRITICAL |
| K4 | Have there been any papers, presentations, or demos? | Disclosure risk | Project owner | HIGH |

### L. Ownership

| # | Question | Why It Matters | Who Should Answer | Priority |
|---|----------|---------------|-------------------|----------|
| L1 | Who owns the intellectual property? | Filing authority | Legal / project owner | CRITICAL |
| L2 | Is the code developed as work-for-hire? | Ownership determination | Legal | CRITICAL |
| L3 | Are there any assignment agreements? | Ownership chain | Legal | HIGH |
| L4 | Is a university or institution involved? | Ownership complexity | Project owner | HIGH |
| L5 | Are there any open-source license obligations? | Filing restrictions | Legal | HIGH |

### M. Filing

| # | Question | Why It Matters | Who Should Answer | Priority |
|---|----------|---------------|-------------------|----------|
| M1 | Is an Indian patent filing planned? | Jurisdiction | Project owner | CRITICAL |
| M2 | Is international filing (PCT) planned? | Jurisdiction | Project owner | HIGH |
| M3 | Is a provisional application planned? | Filing strategy | Patent professional | HIGH |
| M4 | What is the budget for patent filing? | Resource planning | Project owner | MEDIUM |

---

## Priority Summary

| Priority | Count | Items |
|----------|-------|-------|
| CRITICAL | 18 | A1-A4, D1, D3, E4, F1, F4, I1-I3, J1-J2, K1-K3, L1-L2, M1 |
| HIGH | 17 | A5, B1-B2, C1-C4, D2, E1-E3, F2-F3, F5, G1-G2, H1, I4, J3, K4, L3-L4, M2-M3 |
| MEDIUM | 7 | B3-B4, C5, G3-G4, H2-H4, L5, M4 |

---

*End of Missing Information*
