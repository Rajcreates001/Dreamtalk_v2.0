# Dr. Bidhan Chandra Roy — Persona Asset Inventory

> Research compiled: June 17, 2026
> Status: **No original voice recordings found** — synthetic voice required

---

## 1. AUDIO / VOICE ASSETS

| Asset | Source | Status | For Use In |
|-------|--------|--------|------------|
| Original speech recordings | **NONE FOUND PUBLICLY** | ❌ Unavailable | Voice cloning training |
| "Selected Speeches of Bidhan Chandra Roy" (book, 1144p) | St. Xavier's University Library / West Bengal Legislative Assembly Secretariat (2022) | ✅ Text available | LLM personality training, speech style |
| Dr. B.C. Roy Papers (archival collection) | Nehru Memorial Museum & Library, New Delhi | ✅ Archival | Biographical accuracy, quotes |
| YouTube narrated tributes | `youtube.com/watch?v=Ao2jYp7B21w`, `youtube.com/watch?v=QY9hNDTyXoU` | ✅ Reference only | Speech patterns, mannerisms |

### Voice Synthesis Path (required — no original audio)

Since no original voice recordings survive, choose one:

| Option | Method | Quality | Cost |
|--------|--------|---------|------|
| **A. Voice Actor** | Hire Bengali-accented English voice actor, record ~1hr medical monologues, fine-tune GPT-SoVITS/RVC | ⭐⭐⭐⭐⭐ Best | $200-500 |
| **B. LLM Voice Gen** | Use GPT-4o-audiopreview or ElevenLabs with period-appropriate prompt | ⭐⭐⭐⭐ Good | API costs |
| **C. Kokoro Hindi base** | Fine-tune Kokoro `hf_alpha` voice on Indian English medical speech | ⭐⭐⭐ Decent | Free |
| **D. Svara-TTS zero-shot** | Clone from modern Indian English doctor voiceovers via Svara-TTS | ⭐⭐⭐⭐ Good | GPU server |

> **Recommendation:** Option A (voice actor) for the 10-day MVP delivers the highest quality. 
> Option B (LLM voice gen) is fastest for prototyping.

---

## 2. PHOTO / IMAGE ASSETS

| Asset | Source | URL | Quality |
|-------|--------|-----|---------|
| Wikipedia portrait | Wikipedia Commons | en.wikipedia.org/wiki/Bidhan_Chandra_Roy | ✅ High-res B&W |
| IIM Calcutta Archives photo | iimc-archives.iimcal.ac.in/items/show/29 | Archive page | ✅ High quality |
| Pexels stock photos | pexels.com | Search "Dr Bidhan Chandra Roy" | ✅ 3,000+ options |
| Medical college portraits | Various institution websites | Multiple sources | ✅ Moderate |

### Use for:
- **MuseTalk input face** — High-res B&W portrait can drive lip-sync
- **LivePortrait source image** — Single photo for expression animation
- **Frontend avatar display** — Profile picture for chat UI
- **VRM avatar texture** — Can be applied to 3D avatar face

---

## 3. VIDEO FOOTAGE

| Asset | Source | Type | For Use In |
|-------|--------|------|------------|
| WION News tribute | wionews.com/videos/... | Modern documentary | Reference only |
| YouTube biography videos | Multiple channels | Narrated slideshows | Speech style reference |
| Original video of BC Roy speaking | **NONE FOUND** | — | ❌ Unavailable |

> No known video footage of Dr. BC Roy speaking exists publicly. 
> MuseTalk + LivePortrait will animate his photo using cloned voice + emotion.

---

## 4. BIOGRAPHICAL / TEXT DATA (For LLM Persona Training)

| Resource | Content | Quality | URL |
|----------|---------|---------|-----|
| **Wikipedia** | Full biography, political career, awards | ✅ Comprehensive | wikipedia.org |
| **Archive.org PDF book** | "Bidhan Chandra Roy" by Sengupta | ✅ 200+ page biography | archive.org/download/bidhanchandraroy00seng |
| **IIM Calcutta Archives** | Detailed life story, 26 paragraphs | ✅ Excellent detail | iimc-archives.iimcal.ac.in/items/show/29 |
| **CME India** | Medical history article | ✅ Detailed medical focus | cmeindia.in/history-today-in-medicine-dr-bidhan-chandra-roy |
| **Cureus Journal** | Academic tribute article (2024) | ✅ Peer-reviewed | cureus.com/articles/290978 |
| **JAPI (2026)** | "Beyond the White Coat" legacy article | ✅ Medical journal | japi.org/article/japi-73-12-94 |
| **Banglapedia** | Encyclopedia entry | ✅ Facts verified | en.banglapedia.org |
| **Grokipedia** | AI fact-checked article (2026) | ✅ Comprehensive | grokipedia.com |
| **Meditropics** | Detailed biography | ✅ Good summary | meditropics.com |

---

## 5. KEY PERSONALITY TRAITS FOR LLM PROMPT

### Identity
- **Full Name:** Dr. Bidhan Chandra Roy
- **Title:** Bharat Ratna, Physician, Freedom Fighter, 2nd/1st Chief Minister of West Bengal (1948-1962)
- **Born:** July 1, 1882, Bankipore, Patna, Bihar
- **Died:** July 1, 1962, Kolkata (same date as birth)
- **Languages:** Bengali (native), English (fluent), Hindi, Sanskrit
- **Education:** BA Mathematics (Patna College), MRCP + FRCS (St. Bartholomew's Hospital, London)
- **Religion/Culture:** Brahmo Samaj (reformist Hindu)

### Personality Profile (Big Five)
| Trait | Level | Description |
|-------|-------|-------------|
| **Openness** | High | Founded institutions, planned cities, pioneered medical education |
| **Conscientiousness** | Very High | Applied 30x to St. Bartholomew's, completed 2 degrees in 2.25 years |
| **Extraversion** | Moderate-High | Political leader, public speaker, mayor, CM |
| **Agreeableness** | High | Free medical care for poor, donated to build hospitals |
| **Neuroticism** | Low | Calm under pressure (treated Gandhi, managed Partition refugee crisis) |

### Speaking Style
- Formal but warm
- References to Bhagavad Gita and Tagore (mother's influence)
- Authoritative medical tone with compassion
- Fought against discrimination (30 applications to London hospital)
- Motto: "Whatever your hand finds to do, do it with all your might"
- Key phrases: "Health is the foundation of freedom," "A nation's strength lies in its people's well-being"

### Medical Expertise
- General medicine, surgery (only person with both MRCP + FRCS in record time)
- Founded: Medical Council of India, Indian Medical Association
- Established: IPGMER, Chittaranjan Cancer Hospital, TB Hospital, Seva Sadan
- Personal physician to Mahatma Gandhi

### Key Achievements (for conversation)
1. **Medical:** Founded Indian Medical Association (1928), first president of Medical Council of India (1939)
2. **Governance:** 14-year CM of West Bengal, managed post-Partition refugee crisis
3. **Infrastructure:** Founded cities — Durgapur, Kalyani, Bidhannagar (Salt Lake), Ashokenagar, Habra
4. **Education:** VC of University of Calcutta (1942), established multiple medical colleges
5. **Freedom Struggle:** Civil Disobedience Movement, arrested 1930, Quit India Movement
6. **Awards:** Bharat Ratna (1961), National Doctors' Day (July 1) in his honor

---

## 6. ASSET SUMMARY FOR APPLICATION

| Category | Available? | Count | Ready to Use? |
|----------|-----------|-------|---------------|
| High-res portrait photo | ✅ Yes | 10+ options | ✅ Download from Wikipedia/Wikimedia |
| Biographical text | ✅ Yes | 10+ sources | ✅ Ready for LLM system prompt |
| Speech transcripts | ✅ Yes (book) | 1144 pages | ⏳ Need to digitize from library |
| Original voice recording | ❌ No | 0 | 🚫 Synthetic voice needed |
| Original video | ❌ No | 0 | 🚫 Image animation needed |
| Voice actor (recommended) | ⏳ TBD | — | 💰 ~$200-500 for recording session |

### Next Actions
1. [ ] Download Wikipedia portrait for MuseTalk/LivePortrait input
2. [ ] Extract biographical data into structured LLM system prompt
3. [ ] Source voice actor or set up LLM voice generation route
4. [ ] Digitize "Selected Speeches" book for speech pattern training
5. [ ] Configure Kvasi persona profile with Big Five + VoiceProfile
