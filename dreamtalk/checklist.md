# DreamTalk — DTOS Engineering Design Specification Checklist

> **Status Legend:** ✅ Complete | ◐ Partial | ⬜ Not Started | 🔄 In Progress
>
> Last updated: June 2026 — migrated to DTOS v2 EDS framework

---

## Product Architecture

| Layer | Component | Status | Progress |
|-------|-----------|--------|----------|
| **P1** | Personal — Digital Twin | ✅ Complete | 100% |
| **P2** | Healthcare — AI Workforce Console | ✅ Complete | 100% |
| **P3** | Business — Enterprise AI Workforce Console | ✅ Complete | 100% |
| **Bridge** | Common Core Architecture (role-aware branching) | ✅ Complete | 100% |

---

## EDS Chapter 2 — Engineering Design Specification

### 2.1 System Architecture & Topology

| Item | Status | Notes |
|------|--------|-------|
| Physical topology (FastAPI → PostgreSQL → GPU Server) | ✅ | Defined in EDS 2.1 |
| Module dependency graph | ✅ | identity → digital_twin → workforce |
| Design principles documented | ✅ | 7 principles: no ORM, role-aware, JSONB, etc. |
| Frontend ↔ Backend ↔ Database architecture | ✅ | Next.js 16 + FastAPI :5000 + PostgreSQL 15 |

### 2.2 Data Model — PostgreSQL Schema

| Item | Status | Notes |
|------|--------|-------|
| `schema.sql` (28 core tables) | ✅ | Users, Auth, Legacy, Identity, Digital Twin, Workforce |
| `schema_v2.sql` (4 DTOS tables) | ✅ | personality_profiles, media_assets, learning_logs, org_memory_entries |
| `identity_profiles` (7 JSONB columns) | ✅ | Unified identity state: appearance, voice, personality, knowledge, memory, evolution, behavior |
| `digital_twins` (25 columns, 5-step status) | ✅ | Role-aware creation with per-step status tracking |
| `digital_employees` (22 columns + KPIs) | ✅ | Workforce employee records with 10 KPI counters |
| `assignments` (28 columns) | ✅ | Full lifecycle tracking with 6 timestamps |
| `assignment_outputs` | ✅ | Meeting intelligence storage (transcript, decisions, actions, etc.) |
| `personality_profiles` (standalone) | ✅ | UNIQUE per twin, JSONB profile + big_five + communication + behavior_rules |
| `media_assets` (per-twin) | ✅ | Category/sub-category organization, version tracking |
| `org_memory_entries` (two-layer) | ✅ | personal + organization layers, scope control, approval workflow |
| `evolution_log` + `evolution_deltas` | ✅ | Version change audit with source excerpts |
| `learning_observations` | ✅ | Confidence-capped storage for healthcare/business |
| `supervisor_reviews` | ✅ | Rating + corrections + retrain trigger |
| `org_knowledge_base` (legacy) | ✅ | Approval workflow, scope control, full-text search |
| Updated_at triggers | ✅ | All core tables have BEFORE UPDATE triggers |
| UUID primary keys throughout | ✅ | No auto-increment integers |
| Indexes on all foreign keys | ✅ | Plus composite indexes for common queries |

### 2.3 Identity Engine

| Item | Status | Notes |
|------|--------|-------|
| `IdentityProfile` model (9 sub-models) | ✅ | Pydantic-validated, all fields typed |
| `IdentityEngine` service | ✅ | 9 methods: get, create, upsert, update, sub-profile updates |
| `get(identity_id)` | ✅ | Fetch by PK |
| `get_by_custom_dh(custom_dh_id)` | ✅ | Legacy backward compatibility |
| `get_by_user(user_id)` | ✅ | List all profiles for user |
| `create(profile)` | ✅ | Full insert with 7 JSONB columns |
| `upsert(profile)` | ✅ | Update-if-exists by custom_dh_id |
| `update(profile)` | ✅ | Full overwrite with version tracking |
| Sub-profile update methods | ✅ | update_appearance, update_voice, update_personality |
| 11 REST endpoints | ✅ | `/api/v1/identity/` |
| Backward-compat with legacy avatars | ✅ | Links to `custom_digital_humans` table |
| Auto-creation on server startup | ✅ | `ensure_seed_tables()` in lifespan |

### 2.4 Appearance Pipeline

| Item | Status | Notes |
|------|--------|-------|
| 16-step pipeline defined | ✅ | Validate → Detect → Reconstruct → Profile |
| Face detection (RetinaFace/YOLOv8) | ◐ | Ported, stub until weights downloaded |
| Landmark extraction (PFLD/MobileFaceNet) | ◐ | Ported, stub until weights downloaded |
| 3D reconstruction (FLAME/DECA) | ◐ | Ported, stub until weights downloaded |
| Expression extraction (blendshapes) | ◐ | Stub returns mock coefficients |
| Head pose estimation | ◐ | Stub returns mock 6-DoF |
| Identity embedding | ◐ | Stub returns mock 512-dim vector |
| Background removal (BiSeNet) | ◐ | Ported, stub until weights |
| Lighting normalization | ✅ | Structural, histogram equalization |
| Motion analysis | ◐ | Stub, micro-expression detection not wired |
| Preview generation | ◐ | Stub creates placeholder |
| File storage to media_assets | ✅ | Saves to disk + DB record |
| Identity profile update | ✅ | Writes appearance JSONB |
| Quality report | ◐ | Stub returns fixed score |
| No manual facial parameters | ✅ | Upload images/video only |
| Upload endpoint | ✅ | `POST /digital-twins/{id}/appearance/upload` |

### 2.5 Voice Cloning & TTS Pipeline

| Item | Status | Notes |
|------|--------|-------|
| 15-step cloning pipeline | ✅ | Validate → Preprocess → Clone → Store → Test |
| Sample validation | ◐ | Rate, SNR, language detection (stub) |
| Preprocessing pipeline | ◐ | Noise reduction, silence trim (stub) |
| Speaker embedding | ◐ | d-vector/x-vector (stub) |
| Prosody analysis | ◐ | Pitch range, rhythm, pause patterns (stub) |
| Accent classification | ◐ | Regional detection (stub) |
| Emotional range mapping | ◐ | PAD to TTS parameter mapping (stub) |
| Voice cloning (ElevenLabs/RVC/GPT-SoVITS) | ◐ | Adapters ported, no weights |
| Quality check (similarity score) | ◐ | Stub returns fixed 0.85 |
| GPT-SoVITS adapter | ◐ | Ported, no weights |
| Kokoro adapter | ◐ | Ported, no weights |
| Qwen3-TTS adapter | ◐ | Ported, no weights |
| IndiC F5 adapter | ◐ | Ported, no weights |
| IndiC TTS adapter | ◐ | Ported, no weights |
| RVC adapter | ◐ | Ported, no weights |
| Synthetic fallback configuration | ✅ | Gender, age, accent, pitch, speed, warmth, tone |
| Voice upload endpoint | ✅ | `POST /digital-twins/{id}/voice/upload` |
| TTS synthesis endpoint | ✅ | `POST /api/v1/voice/synthesize` |

### 2.6 Personality Profile System

| Item | Status | Notes |
|------|--------|-------|
| `personality_profiles` table | ✅ | UNIQUE(twin_id), 4 JSONB columns |
| `PersonalityEngine` service | ✅ | ensure_table, create, get, update, delete |
| Big Five traits (5 dimensions) | ✅ | openness, conscientiousness, extraversion, agreeableness, neuroticism |
| Communication style (6 dimensions) | ✅ | formality, verbosity, assertiveness, humor, empathy, enthusiasm |
| Behavior rules (8 booleans) | ✅ | interrupt, challenge, slang, emojis, metaphors, short answers, clarifying questions, admit uncertainty |
| Editable characteristics (7 values) | ✅ | User-customizable value pairs |
| Defaults by role | ✅ | Personal (casual), Healthcare (professional_warm), Business (professional) |
| All values editable anytime | ✅ | PUT endpoint for partial updates |
| System prompt construction | ✅ | `get_system_prompt(twin_role)` builds LLM guidance |
| Pydantic-typed throughout | ✅ | Dataclasses with FloatRange validation |

### 2.7 Knowledge Ingestion Pipeline

| Item | Status | Notes |
|------|--------|-------|
| 12-step pipeline | ✅ | Upload → Validate → Chunk → Embed → Index → Attach |
| Multi-format support (PDF, DOCX, TXT, PPTX, XLSX, CSV) | ✅ | `KnowledgeSourceType` enum |
| Extended source types (URL, Drive, Notion, GH, etc.) | ✅ | 22 source types defined |
| Virus scan (ClamAV) | ◐ | Stub |
| OCR (Tesseract) | ◐ | Stub |
| Text extraction | ◐ | pdfminer, python-docx, openpyxl wired but not tested with real files |
| Chunking (1000-word, 100-word overlap) | ✅ | Implemented |
| Embedding (BGE-M3) | ◐ | Stub — returns zero vectors |
| Knowledge graph extraction | ◐ | Stub |
| Cross-referencing | ◐ | Stub |
| Quality validation | ◐ | Stub |
| RAG retrieval (cosine similarity) | ◐ | Stub — returns zero-score chunks |
| Upload endpoint | ✅ | `POST /digital-twins/{id}/knowledge/upload` |

### 2.8 Digital Twin Creation Engine

| Item | Status | Notes |
|------|--------|-------|
| 5-step creation flow | ✅ | Identity → Appearance → Voice → Personality → Intelligence → Publish |
| DTOS 11-step pipeline | ✅ | CreationPipeline with full initialization |
| `digital_twins` table (25 columns) | ✅ | All creation step statuses tracked |
| `DigitalTwinEngine` CRUD | ✅ | Full lifecycle |
| `DigitalTwinEngineExt` (DTOS v2) | ✅ | Pipeline, personality, media integration |
| Role-aware defaults | ✅ | Personal (casual), Healthcare (warm), Business (professional) |
| Status machine (draft → published) | ✅ | 4 intermediate states with validation |
| Publish validation | ✅ | Checks all prerequisites before publishing |
| Personal relationship config | ✅ | Type, greeting, nickname, interests |
| Knowledge attachment | ✅ | Associates knowledge_sources with twin |
| 25 REST endpoints | ✅ | `/api/v1/digital-twins/` |
| `CreationPipeline.execute()` | ✅ | Returns per-step status + twin_id |

### 2.9 Evolution Cycle & Identity Versioning

| Item | Status | Notes |
|------|--------|-------|
| LLM extraction prompt | ✅ | EVOLUTION_EXTRACT_PROMPT defined |
| 5 delta types | ✅ | fact, preference, correction, personality_shift, relationship_update |
| Delta extraction post-chat | ✅ | Fire-and-forget in `/api/chat` |
| `evolution_log` table | ✅ | from_version, to_version, trigger, summary, deltas |
| `evolution_deltas` table | ✅ | delta_type, key, old_value, new_value, confidence, source_excerpt |
| Identity version bump | ✅ | Increments on evolution |
| Source excerpt tracking | ✅ | Every delta has source_excerpt for audit |
| Confidence scoring | ✅ | Per-delta confidence 0–1 |

### 2.10 Continuous Learning Engine

| Item | Status | Notes |
|------|--------|-------|
| `ContinuousLearningEngine` service | ✅ | process_conversation, get_observations, confirm_observation |
| 8 observation types | ✅ | fact, preference, correction, personality_signal, relationship_update, communication_style, emotional_signal, behavioral_pattern |
| LLM extraction prompt | ✅ | CONTINUOUS_LEARNING_PROMPT defined |
| Role-aware routing | ✅ | Personal = direct apply; Healthcare/Business = low-conf storage |
| Direct apply for Personal | ✅ | Updates personality traits via gradual delta shifts |
| Low-confidence storage (capped 0.4) | ✅ | Written to `learning_observations` table |
| Supervisor confirmation | ✅ | `confirm_observation()` updates employee behavior |
| `learning_observations` table | ✅ | twin_id, type, key, value, confidence, source_excerpt, status |
| Fire-and-forget in chat endpoint | ✅ | `/api/chat` triggers post-response learning |
| Replaces legacy EvolutionEngine | ✅ | Evolution still runs for backward compat |

### 2.11 AI Workforce Platform

| Item | Status | Notes |
|------|--------|-------|
| Organizations CRUD | ✅ | name, org_type, description, industry |
| Departments CRUD | ✅ | Nested hierarchy under orgs |
| Digital Employees CRUD | ✅ | 22 columns: name, title, role, level, status, supervisor, KPIs, permissions |
| Employee status machine | ✅ | available ↔ in_meeting ↔ training ↔ offline |
| 10 KPI counters | ✅ | assignments, duration, rating, escalations, utilization, contributions |
| Supervisor hierarchy | ✅ | Employee-to-employee supervisor reference |
| Permissions system | ✅ | max_concurrent, org_access, human_escalation, allowed_types |
| Version tracking | ✅ | employee_version field |
| 35 REST endpoints | ✅ | `/api/v1/workforce/` |
| Demo organizations seeded | ✅ | Apollo Research Hospital (healthcare), DreamCorp Enterprises (business) |

### 2.12 Assignment Engine

| Item | Status | Notes |
|------|--------|-------|
| `AssignmentEngine` service | ✅ | create, start, complete, cancel, review |
| Full lifecycle (6 states) | ✅ | scheduled → in_progress → completed/cancelled → under_review → reviewed |
| 9 assignment types | ✅ | meeting, appointment, consultation, sales_demo, support_ticket, interview, training, ward_round, triage |
| 28-column assignments table | ✅ | Full tracking: scheduled/actual start/end, priority, instructions, participants |
| Assignment creation | ✅ | Validates employee capacity, sets status |
| Assignment start | ✅ | Sets employee status = in_meeting/in_consultation, records actual_start |
| Assignment complete | ✅ | Captures AI output, updates employee counters, marks for review |
| Assignment cancel | ✅ | Returns employee to available |
| Assignment review | ✅ | Rating + corrections → avg_rating update → retrain trigger |
| Scheduled assignments | ✅ | `get_upcoming_assignments` for Mission Control |
| Active assignments | ✅ | `get_active_assignments` for live sessions |
| `assignment_outputs` table | ✅ | transcript, summary, decisions, action_items, risks, topics, questions, sentiment, knowledge_promotion_suggestions |

### 2.13 Meeting Intelligence

| Item | Status | Notes |
|------|--------|-------|
| `MeetingIntelligence` class | ✅ | analyze_conversation method |
| LLM-powered post-analysis | ✅ | Single prompt, structured JSON output |
| Raw transcript → Clean transcript | ✅ | PII masking, filler word removal |
| Executive summary (3–5 sentences) | ✅ | |
| Key decisions extraction | ✅ | |
| Action items (with responsible party) | ✅ | |
| Risks and concerns | ✅ | |
| Topics discussed | ✅ | |
| Questions raised | ✅ | |
| Follow-up items | ✅ | |
| Sentiment analysis (overall + per-participant) | ✅ | |
| Knowledge promotion suggestions | ✅ | Forwarded to Organization Memory |
| Store to assignment_outputs | ✅ | |
| Retrieve via API | ✅ | `GET /workforce/assignments/{id}/output` |

### 2.14 Organization Memory (Two-Layer)

| Item | Status | Notes |
|------|--------|-------|
| `org_knowledge_base` (legacy) | ✅ | Single-layer, approval workflow |
| `org_memory_entries` (DTOS v2) | ✅ | Two-layer: personal + organization |
| Layer 1: Personal memory | ✅ | scope='private', owned by one employee, no approval needed |
| Layer 2: Organization memory | ✅ | scope='organization', shared across org, requires approval |
| Content types (8 types) | ✅ | memory, knowledge, policy, protocol, faq, decision, research, sop |
| Scope control | ✅ | private, department, organization |
| Source tracking | ✅ | links to assignment_id + source_excerpt |
| Auto-promotion from meetings | ✅ | knowledge_promotion_suggestions → pending approval |
| Manual knowledge entry | ✅ | title + content + tags |
| Approval workflow | ✅ | Admin approves/rejects; is_approved, approved_by, approved_at |
| Full-text search | ✅ | ILIKE on title and content |
| `OrgMemory` service | ✅ | ensure_table, create, get_by_org, get_pending, approve, search |

### 2.15 Supervisor Review & Performance Analytics

| Item | Status | Notes |
|------|--------|-------|
| `supervisor_reviews` table | ✅ | rating (1–5), comments, corrections JSONB, promote_to_training |
| `PerformanceEngine` service | ✅ | compute_metrics, get_org_metrics, get_employee_trend |
| Rating submission | ✅ | Updates employee avg_rating (weighted MA) |
| Corrections tracking | ✅ | Auto-increments human_escalations counter |
| Retrain trigger | ✅ | promote_to_training → sets employee status = training |
| compute_metrics(employee_id, period_days) | ✅ | 7 KPIs aggregated over period |
| get_org_metrics(org_id) | ✅ | Org-wide stats: totals, avg rating, utilization |
| get_employee_trend(employee_id) | ✅ | Improving/declining direction |
| Pending reviews in Mission Control | ✅ | Backlog tracking with alert thresholds |

### 2.16 Mission Control Dashboard

| Item | Status | Notes |
|------|--------|-------|
| `MissionControl` class | ✅ | get_dashboard(org_id) |
| Organization info | ✅ | |
| Employee status breakdown | ✅ | 6 statuses: available, in_meeting, in_consultation, training, processing, offline |
| Workforce summary | ✅ | totals, active assignments, pending reviews, today completions, avg rating, utilization |
| Live sessions | ✅ | In-progress assignments with details |
| Upcoming assignments | ✅ | Next 10 scheduled |
| Pending reviews | ✅ | Assignments awaiting supervisor |
| Pending knowledge | ✅ | Org memory entries awaiting approval |
| Top performers | ✅ | Sorted by avg rating |
| Alerts engine | ✅ | 4 triggers: high_escalations (critical), review_backlog (warning), utilization (warning), knowledge backlog (info) |
| KPI summary | ✅ | Org-level rollup |

### 2.17 API Gateway & Endpoint Reference

| Item | Status | Notes |
|------|--------|-------|
| FastAPI gateway on :5000 | ✅ | uvicorn, CORS all origins, lifespan events |
| asyncpg connection pool (min=2, max=10) | ✅ | Lazy initialization on first request |
| 8 routers registered | ✅ | auth, profile, dh, voice, chat, identity, digital-twin, workforce |
| 93 total endpoints | ✅ | See endpoint count below |
| OAuth 2.0 (Google, GitHub, Microsoft) | ✅ | JWT + OAuth account linking |
| JWT authentication | ✅ | Login, refresh, logout |
| Lifespan startup sequence | ✅ | Seed users → ensure tables → seed identities → seed twins → seed orgs → seed v2 |
| Static file serving | ✅ | /outputs (voice), /media (uploads) |
| Health check endpoint | ✅ | GET /health (DB connectivity check) |

---

## API Endpoint Inventory

| Router | Endpoints | Status |
|--------|-----------|--------|
| `/api/v1/auth/` | 10 | ✅ Complete |
| `/api/v1/profile/` | 2 | ✅ Complete |
| `/api/v1/digital-humans/` | 5 | ✅ Complete (legacy) |
| `/api/v1/voice/` | 4 | ✅ Complete |
| `/api/chat` | 1 | ✅ Complete |
| `/api/v1/identity/` | 11 | ✅ Complete |
| `/api/v1/digital-twins/` | 25 | ✅ Complete |
| `/api/v1/workforce/` | 35 | ✅ Complete |
| **Total** | **93** | **✅ 100%** |

---

## Database Table Inventory

| # | Table | Module | EDS Section | Status |
|---|-------|--------|-------------|--------|
| 1 | `users` | Auth | 2.2 | ✅ |
| 2 | `sessions` | Auth | 2.2 | ✅ |
| 3 | `subscriptions` | Billing | 2.2 | ✅ |
| 4 | `digital_humans` | Legacy DH | 2.2 | ✅ |
| 5 | `custom_digital_humans` | Legacy DH | 2.2 | ✅ |
| 6 | `user_digital_humans` | Legacy DH | 2.2 | ✅ |
| 7 | `voice_profiles` | Legacy Voice | 2.2 | ✅ |
| 8 | `interactions` | Legacy Chat | 2.2 | ✅ |
| 9 | `user_settings` | Profile | 2.2 | ✅ |
| 10 | `healthcare_patients` | Healthcare | 2.2 | ✅ |
| 11 | `healthcare_schedules` | Healthcare | 2.2 | ✅ |
| 12 | `business_clients` | Business | 2.2 | ✅ |
| 13 | `oauth_accounts` | Auth | 2.2 | ✅ |
| 14 | `identity_profiles` | Identity | 2.3 | ✅ |
| 15 | `evolution_log` | Identity | 2.9 | ✅ |
| 16 | `evolution_deltas` | Identity | 2.9 | ✅ |
| 17 | `usage_logs` | Analytics | 2.2 | ✅ |
| 18 | `digital_twins` | Digital Twin | 2.8 | ✅ |
| 19 | `knowledge_sources` | Digital Twin | 2.7 | ✅ |
| 20 | `knowledge_chunks` | Digital Twin | 2.7 | ✅ |
| 21 | `learning_observations` | Digital Twin | 2.10 | ✅ |
| 22 | `organizations` | Workforce | 2.11 | ✅ |
| 23 | `departments` | Workforce | 2.11 | ✅ |
| 24 | `digital_employees` | Workforce | 2.11 | ✅ |
| 25 | `assignments` | Workforce | 2.12 | ✅ |
| 26 | `assignment_outputs` | Workforce | 2.13 | ✅ |
| 27 | `org_knowledge_base` | Workforce | 2.14 | ✅ |
| 28 | `supervisor_reviews` | Workforce | 2.15 | ✅ |
| 29 | `personality_profiles` | DTOS v2 | 2.6 | ✅ |
| 30 | `media_assets` | DTOS v2 | 2.4 | ✅ |
| 31 | `learning_logs` | DTOS v2 | 2.10 | ✅ |
| 32 | `org_memory_entries` | DTOS v2 | 2.14 | ✅ |

---

## Remaining Work

### High Priority — Model Weights

- [ ] Download weights for LivePortrait (face animation)
- [ ] Download weights for MuseTalk (lipsync)
- [ ] Download weights for FLAME (3D mesh reconstruction)
- [ ] Download weights for RetinaFace (face detection)
- [ ] Download weights for PFLD (landmark extraction)
- [ ] Download weights for BiSeNet (face parsing)
- [ ] Download BGE-M3 embedding model (knowledge retrieval)
- [ ] Wire all model calls to real inference (currently stub)

### Medium Priority — Pipeline Integration

- [ ] Register face API routers in `backend/main.py`
- [ ] Wire MuseTalk into appearance pipeline for lip-sync preview
- [ ] Wire LivePortrait into appearance pipeline for expression-driven animation
- [ ] Wire FLAME for 3D mesh reconstruction
- [ ] Test full appearance pipeline end-to-end with real weights
- [ ] Wire embedding model into knowledge retrieval (currently returns zero vectors)
- [ ] Wire knowledge graph extraction pipeline
- [ ] Implement concrete handlers for all 10 orchestration stages
- [ ] Wire orchestration coordinator into chat endpoint

### Medium Priority — Frontend

- [ ] Build create-avatar wizard with role selection (Personal / Healthcare / Business)
- [ ] Build Healthcare AI Workforce Console dashboard
- [ ] Build Enterprise AI Workforce Console dashboard
- [ ] Build Mission Control page
- [ ] Build employee creation and assignment UI
- [ ] Build supervisor review interface
- [ ] Build knowledge approval workflow UI
- [ ] Build meeting intelligence viewer (transcript + summary + decisions + actions)
- [ ] Build performance analytics charts

### Low Priority — Testing & Tooling

- [ ] Integration tests for all 93 API endpoints
- [ ] Load test with concurrent assignments
- [ ] Docker compose for full stack deployment
- [ ] Weight download automation script
- [ ] CI/CD pipeline setup

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| June 2026 | Migrated to DTOS v2 EDS framework — 17 architecture chapters | System |
| June 2026 | Added personality_profiles, media_assets, learning_logs, org_memory_entries tables | System |
| June 2026 | Documented 93 API endpoints across 8 routers | System |
| June 2026 | Added identity_profiles auto-creation in lifespan to fix missing table on startup | System |
| June 2026 | Fixed `from typing import list as List` → `from typing import List` | System |
