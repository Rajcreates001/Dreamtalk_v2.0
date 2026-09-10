# 27 — OPEN SOURCE LICENSE AUDIT

## Date: August 21, 2026

---

## Key Dependencies and Licenses

| Dependency | License | Risk | Notes |
|-----------|---------|------|-------|
| **FastAPI** | MIT | LOW | Permissive, no patent concerns |
| **PyTorch** | BSD-3-Clause | LOW | Permissive, no patent concerns |
| **NumPy** | BSD-3-Clause | LOW | Permissive |
| **librosa** | MIT | LOW | Permissive |
| **MediaPipe** | Apache 2.0 | LOW | Permissive, includes patent grant |
| **OpenCV** | Apache 2.0 | LOW | Permissive, includes patent grant |
| **Three.js** | MIT | LOW | Permissive |
| **@pixiv/three-vrm** | MIT | LOW | Permissive |
| **Next.js** | MIT | LOW | Permissive |
| **React** | MIT | LOW | Permissive |
| **VADER** | MIT | LOW | Permissive |
| **soundfile** | BSD | LOW | Permissive |
| **scipy** | BSD-3-Clause | LOW | Permissive |
| **httpx** | BSD-3-Clause | LOW | Permissive |
| **asyncpg** | Apache 2.0 | LOW | Permissive |
| **celery** | BSD-3-Clause | LOW | Permissive |
| **redis-py** | MIT | LOW | Permissive |
| **weaviate-client** | BSD-3-Clause | LOW | Permissive |
| **sentry-sdk** | MIT | LOW | Permissive |
| **Kokoro TTS** | Apache 2.0 | LOW | Permissive, includes patent grant |
| **IndicF5** | MIT | LOW | Permissive |
| **RVC** | MIT (inferred) | MEDIUM | Need to verify actual license |
| **OpenVoice** | MIT (inferred) | MEDIUM | Need to verify actual license |
| **BrainCog** | UNKNOWN | HIGH | Must check license before filing |
| **SpikingJelly** | UNKNOWN | HIGH | Must check license before filing |
| **fairseq** | MIT | LOW | Permissive |
| **edge-tts** | MIT | LOW | Permissive |
| **deepface** | MIT | LOW | Permissive |
| **whisper** | MIT | LOW | Permissive |
| **DeepSeek** | UNKNOWN | MEDIUM | Proprietary LLM, check terms |

---

## Critical License Concerns

### BrainCog
- **Status:** UNKNOWN — must verify
- **Risk:** If BrainCog uses GPL or AGPL, and DreamTalk links to it, DreamTalk may be required to open-source
- **Action:** Check BrainCog license immediately
- **Impact on patent:** If GPL/AGPL, may affect commercialization but not necessarily patentability

### SpikingJelly
- **Status:** UNKNOWN — must verify
- **Risk:** Same as BrainCog
- **Action:** Check license

### RVC
- **Status:** Inferred MIT — must verify
- **Risk:** If non-permissive, voice cloning cascade may be affected
- **Action:** Check actual license

### OpenVoice
- **Status:** Inferred MIT — must verify
- **Risk:** Same as RVC
- **Action:** Check actual license

---

## Patent Implications

| Concern | Impact | Action |
|---------|--------|--------|
| GPL/AGPL dependencies | May require open-sourcing DreamTalk | Check all dependencies |
| Patent grant clauses (Apache 2.0) | Some licenses include patent grants | Review Apache 2.0 dependencies |
| Patent retaliation clauses | Some licenses have patent retaliation | Review all licenses |
| Commercial use restrictions | Some licenses restrict commercial use | Check all dependencies |

---

## Recommended Actions

1. **Run `pip-licenses`** on the dt_venv to get exact licenses
2. **Check BrainCog, SpikingJelly, RVC, OpenVoice** licenses specifically
3. **Review Apache 2.0 patent grant clauses** for MediaPipe, OpenCV, Kokoro
4. **Check for any AGPL dependencies** that might require open-sourcing
5. **Document all findings** for patent counsel

---

*End of Open Source License Audit*
