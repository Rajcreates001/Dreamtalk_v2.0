-- Dreamtalk - Complete Database Schema
-- PostgreSQL 15+

-- ============================================
-- EXTENSIONS
-- ============================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================
-- ENUMS
-- ============================================
CREATE TYPE user_role AS ENUM ('personal', 'healthcare', 'business', 'admin');
CREATE TYPE subscription_tier AS ENUM ('free', 'personal', 'healthcare', 'business', 'enterprise');
CREATE TYPE subscription_status AS ENUM ('active', 'canceled', 'expired', 'trialing', 'past_due');
CREATE TYPE interaction_status AS ENUM ('active', 'completed', 'interrupted', 'error');
CREATE TYPE digital_human_category AS ENUM ('healthcare', 'business', 'education', 'creative', 'personal', 'tech');
CREATE TYPE payment_provider AS ENUM ('stripe', 'razorpay', 'manual');
CREATE TYPE media_type AS ENUM ('image', 'audio', 'video', 'model_3d', 'document');
CREATE TYPE provider AS ENUM ('google', 'github', 'microsoft', 'email');

-- ============================================
-- USERS & AUTH
-- ============================================
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255),
    full_name       VARCHAR(255) NOT NULL,
    role            user_role NOT NULL DEFAULT 'personal',
    avatar_url      VARCHAR(512),
    is_verified     BOOLEAN DEFAULT FALSE,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    last_login_at   TIMESTAMPTZ
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

CREATE TABLE user_oauth (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider        provider NOT NULL,
    provider_id     VARCHAR(255) NOT NULL,
    provider_email  VARCHAR(255),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(provider, provider_id)
);

CREATE INDEX idx_user_oauth_user ON user_oauth(user_id);

CREATE TABLE user_sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    access_token    VARCHAR(1024) NOT NULL,
    refresh_token   VARCHAR(1024) NOT NULL,
    expires_at      TIMESTAMPTZ NOT NULL,
    refresh_expires_at TIMESTAMPTZ NOT NULL,
    ip_address      VARCHAR(45),
    user_agent      TEXT,
    is_revoked      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_user_sessions_token ON user_sessions(access_token);
CREATE INDEX idx_user_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_refresh ON user_sessions(refresh_token);

CREATE TABLE email_verifications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token           VARCHAR(512) UNIQUE NOT NULL,
    expires_at      TIMESTAMPTZ NOT NULL,
    used_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE password_resets (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token           VARCHAR(512) UNIQUE NOT NULL,
    expires_at      TIMESTAMPTZ NOT NULL,
    used_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- SUBSCRIPTIONS & BILLING
-- ============================================
CREATE TABLE subscriptions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tier                subscription_tier NOT NULL DEFAULT 'free',
    status              subscription_status NOT NULL DEFAULT 'trialing',
    current_period_start TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    current_period_end  TIMESTAMPTZ,
    canceled_at         TIMESTAMPTZ,
    trial_end           TIMESTAMPTZ,
    provider            payment_provider DEFAULT 'manual',
    provider_subscription_id VARCHAR(255),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);

CREATE TABLE subscription_payments (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subscription_id     UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount              DECIMAL(12, 2) NOT NULL,
    currency            VARCHAR(3) DEFAULT 'INR',
    status              VARCHAR(50) NOT NULL,
    provider            payment_provider DEFAULT 'manual',
    provider_payment_id VARCHAR(255),
    paid_at             TIMESTAMPTZ DEFAULT NOW(),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_payments_subscription ON subscription_payments(subscription_id);
CREATE INDEX idx_payments_user ON subscription_payments(user_id);

-- ============================================
-- DIGITAL HUMANS (AVATARS)
-- ============================================
CREATE TABLE digital_humans (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    category        digital_human_category NOT NULL,
    accent_color    VARCHAR(7) DEFAULT '#10b981',
    emoji           VARCHAR(10),
    model_url       VARCHAR(1024),
    thumbnail_url   VARCHAR(1024),
    voice_id        VARCHAR(255),
    personality     TEXT,
    is_prebuilt     BOOLEAN DEFAULT TRUE,
    is_active       BOOLEAN DEFAULT TRUE,
    popularity      INTEGER DEFAULT 0,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_digital_humans_category ON digital_humans(category);
CREATE INDEX idx_digital_humans_prebuilt ON digital_humans(is_prebuilt);
CREATE INDEX idx_digital_humans_popular ON digital_humans(popularity DESC);

CREATE TABLE user_digital_humans (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    digital_human_id  UUID NOT NULL REFERENCES digital_humans(id) ON DELETE CASCADE,
    is_favorite       BOOLEAN DEFAULT FALSE,
    nickname          VARCHAR(255),
    custom_voice_id   VARCHAR(255),
    custom_personality TEXT,
    interaction_count INTEGER DEFAULT 0,
    last_interaction  TIMESTAMPTZ,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, digital_human_id)
);

CREATE INDEX idx_user_dh_user ON user_digital_humans(user_id);
CREATE INDEX idx_user_dh_fav ON user_digital_humans(user_id, is_favorite);

CREATE TABLE custom_digital_humans (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name              VARCHAR(255) NOT NULL,
    description       TEXT,
    category          digital_human_category DEFAULT 'personal',
    model_config      JSONB DEFAULT '{}',
    voice_config      JSONB DEFAULT '{}',
    personality       TEXT,
    style             VARCHAR(50) DEFAULT 'realistic',
    color_scheme      VARCHAR(50) DEFAULT 'emerald',
    outfit            VARCHAR(50) DEFAULT 'default',
    hair_style        VARCHAR(50) DEFAULT 'default',
    eye_glow          VARCHAR(7) DEFAULT '#10b981',
    thumbnail_url     VARCHAR(1024),
    is_active         BOOLEAN DEFAULT TRUE,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_custom_dh_user ON custom_digital_humans(user_id);

-- ============================================
-- INTERACTIONS (CALLS / CONVERSATIONS)
-- ============================================
CREATE TABLE interactions (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    digital_human_id  UUID REFERENCES digital_humans(id) ON DELETE SET NULL,
    custom_dh_id      UUID REFERENCES custom_digital_humans(id) ON DELETE SET NULL,
    title             VARCHAR(255),
    status            interaction_status DEFAULT 'active',
    duration_seconds  INTEGER DEFAULT 0,
    message_count     INTEGER DEFAULT 0,
    rating            SMALLINT CHECK (rating >= 1 AND rating <= 5),
    notes             TEXT,
    started_at        TIMESTAMPTZ DEFAULT NOW(),
    ended_at          TIMESTAMPTZ
);

CREATE INDEX idx_interactions_user ON interactions(user_id);
CREATE INDEX idx_interactions_status ON interactions(status);
CREATE INDEX idx_interactions_started ON interactions(started_at DESC);

CREATE TABLE interaction_messages (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    interaction_id    UUID NOT NULL REFERENCES interactions(id) ON DELETE CASCADE,
    role              VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content           TEXT NOT NULL,
    emotion           VARCHAR(50),
    audio_url         VARCHAR(1024),
    tts_duration_ms   INTEGER,
    metadata          JSONB DEFAULT '{}',
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_interaction ON interaction_messages(interaction_id);
CREATE INDEX idx_messages_created ON interaction_messages(created_at);

-- ============================================
-- MEDIA ASSETS
-- ============================================
CREATE TABLE media (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    media_type        media_type NOT NULL,
    file_path         VARCHAR(1024) NOT NULL,
    file_size         BIGINT,
    mime_type         VARCHAR(127),
    original_name     VARCHAR(512),
    alt_text          TEXT,
    checksum          VARCHAR(64),
    metadata          JSONB DEFAULT '{}',
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_media_user ON media(user_id);
CREATE INDEX idx_media_type ON media(media_type);

-- ============================================
-- VOICE PROFILES
-- ============================================
CREATE TABLE IF NOT EXISTS voice_profiles (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name              VARCHAR(255) NOT NULL,
    provider_voice_id VARCHAR(255),
    provider          VARCHAR(50) DEFAULT 'indicf5',
    language          VARCHAR(10) DEFAULT 'hi',
    ref_audio_path    VARCHAR(1024),
    ref_text          TEXT DEFAULT '',
    voice_settings    JSONB DEFAULT '{"speed": 1.0, "pitch": 1.0, "intensity": 0.5}',
    sample_url        VARCHAR(1024),
    is_cloned         BOOLEAN DEFAULT FALSE,
    is_active         BOOLEAN DEFAULT TRUE,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_voice_profiles_user ON voice_profiles(user_id);

-- ============================================
-- HEALTHCARE-SPECIFIC DATA
-- ============================================
CREATE TABLE healthcare_patients (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    patient_name      VARCHAR(255) NOT NULL,
    patient_email     VARCHAR(255),
    condition         TEXT,
    status            VARCHAR(50) DEFAULT 'active',
    last_interaction  TIMESTAMPTZ,
    notes             TEXT,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_hc_patients_user ON healthcare_patients(user_id);
CREATE INDEX idx_hc_patients_status ON healthcare_patients(status);

CREATE TABLE healthcare_schedules (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    patient_id        UUID REFERENCES healthcare_patients(id) ON DELETE CASCADE,
    digital_human_id  UUID REFERENCES digital_humans(id) ON DELETE SET NULL,
    scheduled_date    DATE NOT NULL,
    scheduled_time    TIME,
    duration_minutes  INTEGER DEFAULT 30,
    status            VARCHAR(50) DEFAULT 'scheduled',
    notes             TEXT,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_hc_schedule_user ON healthcare_schedules(user_id);
CREATE INDEX idx_hc_schedule_date ON healthcare_schedules(scheduled_date);

-- ============================================
-- BUSINESS-SPECIFIC DATA
-- ============================================
CREATE TABLE business_clients (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_name      VARCHAR(255) NOT NULL,
    contact_name      VARCHAR(255),
    contact_email     VARCHAR(255),
    status            VARCHAR(50) DEFAULT 'active',
    revenue           DECIMAL(12, 2) DEFAULT 0,
    last_interaction  TIMESTAMPTZ,
    notes             TEXT,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_biz_clients_user ON business_clients(user_id);

-- ============================================
-- USER SETTINGS & PREFERENCES
-- ============================================
CREATE TABLE user_settings (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id           UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    llm_provider      VARCHAR(50) DEFAULT 'openai',
    llm_model         VARCHAR(100) DEFAULT 'gpt-4o',
    tts_provider      VARCHAR(50) DEFAULT 'elevenlabs',
    tts_voice         VARCHAR(100) DEFAULT 'default',
    stt_provider      VARCHAR(50) DEFAULT 'whisper',
    theme             VARCHAR(20) DEFAULT 'dark',
    language          VARCHAR(10) DEFAULT 'en',
    notification_enabled BOOLEAN DEFAULT TRUE,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- RATE LIMITING & USAGE
-- ============================================
CREATE TABLE usage_logs (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action            VARCHAR(100) NOT NULL,
    tokens_used       INTEGER DEFAULT 0,
    duration_ms       INTEGER,
    metadata          JSONB DEFAULT '{}',
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_usage_user ON usage_logs(user_id);
CREATE INDEX idx_usage_action ON usage_logs(action);
CREATE INDEX idx_usage_created ON usage_logs(created_at);

-- ============================================
-- AI WORKFORCE PLATFORM (organizations, employees, assignments)
-- ============================================
CREATE TABLE organizations (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name              VARCHAR(255) NOT NULL,
    org_type          VARCHAR(20) NOT NULL DEFAULT 'business',
    description       TEXT,
    industry          VARCHAR(100),
    size              VARCHAR(20) DEFAULT 'small',
    address           TEXT,
    website           VARCHAR(512),
    logo_url          VARCHAR(1024),
    created_by        UUID REFERENCES users(id) ON DELETE SET NULL,
    settings          JSONB DEFAULT '{}',
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_orgs_type ON organizations(org_type);
CREATE INDEX idx_orgs_created_by ON organizations(created_by);

CREATE TABLE departments (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id                UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name                  VARCHAR(255) NOT NULL,
    description           TEXT,
    head_employee_id      UUID,
    parent_department_id  UUID REFERENCES departments(id) ON DELETE SET NULL,
    employee_count        INTEGER DEFAULT 0,
    settings              JSONB DEFAULT '{}',
    created_at            TIMESTAMPTZ DEFAULT NOW(),
    updated_at            TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(org_id, name)
);

CREATE INDEX idx_depts_org ON departments(org_id);
CREATE INDEX idx_depts_parent ON departments(parent_department_id);

CREATE TABLE digital_employees (
    id                        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id                    UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    department_id             UUID REFERENCES departments(id) ON DELETE SET NULL,
    twin_id                   UUID REFERENCES digital_twins(id) ON DELETE SET NULL,

    -- Identity
    name                      VARCHAR(255) NOT NULL,
    title                     VARCHAR(255),
    employee_id               VARCHAR(100),
    role                      VARCHAR(100),
    level                     VARCHAR(20) DEFAULT 'junior',

    -- Work management
    status                    VARCHAR(30) DEFAULT 'available',
    supervisor_id             UUID REFERENCES digital_employees(id) ON DELETE SET NULL,
    is_active                 BOOLEAN DEFAULT TRUE,

    -- Permissions & capacity
    can_access_org_knowledge  BOOLEAN DEFAULT TRUE,
    can_escalate_to_human     BOOLEAN DEFAULT TRUE,
    max_concurrent_assignments INTEGER DEFAULT 1,
    current_assignments       INTEGER DEFAULT 0,

    -- Performance tracking
    total_assignments         INTEGER DEFAULT 0,
    completed_assignments     INTEGER DEFAULT 0,
    avg_rating                REAL DEFAULT 0.0,
    avg_response_time_seconds REAL DEFAULT 0.0,
    human_escalations         INTEGER DEFAULT 0,
    knowledge_contributions   INTEGER DEFAULT 0,

    -- Version
    employee_version          VARCHAR(20) DEFAULT '1.0.0',
    last_trained              TIMESTAMPTZ,
    last_deployed             TIMESTAMPTZ,

    created_at                TIMESTAMPTZ DEFAULT NOW(),
    updated_at                TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(org_id, name)
);

CREATE INDEX idx_emp_org ON digital_employees(org_id);
CREATE INDEX idx_emp_dept ON digital_employees(department_id);
CREATE INDEX idx_emp_status ON digital_employees(status);
CREATE INDEX idx_emp_supervisor ON digital_employees(supervisor_id);

CREATE TABLE assignments (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id            UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    department_id     UUID REFERENCES departments(id) ON DELETE SET NULL,
    employee_id       UUID NOT NULL REFERENCES digital_employees(id) ON DELETE CASCADE,
    assigned_by       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assignment_type   VARCHAR(50) NOT NULL,
    title             VARCHAR(255) NOT NULL,
    description       TEXT,

    scheduled_start   TIMESTAMPTZ,
    scheduled_end     TIMESTAMPTZ,
    actual_start      TIMESTAMPTZ,
    actual_end        TIMESTAMPTZ,
    duration_minutes  INTEGER DEFAULT 0,

    priority          VARCHAR(20) DEFAULT 'normal',
    instructions      TEXT,
    metadata          JSONB DEFAULT '{}',

    -- Healthcare
    patient_name      VARCHAR(255),
    patient_id        VARCHAR(255),

    -- Business
    meeting_link      VARCHAR(1024),
    agenda            TEXT,
    participants      JSONB DEFAULT '[]',

    status            VARCHAR(30) DEFAULT 'scheduled',
    is_completed      BOOLEAN DEFAULT FALSE,

    -- Outputs & review
    output_id         UUID,
    needs_review      BOOLEAN DEFAULT FALSE,
    reviewed_by       UUID REFERENCES users(id) ON DELETE SET NULL,
    review_rating     REAL,
    review_notes      TEXT,

    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_assign_org ON assignments(org_id);
CREATE INDEX idx_assign_employee ON assignments(employee_id);
CREATE INDEX idx_assign_status ON assignments(status);
CREATE INDEX idx_assign_type ON assignments(assignment_type);
CREATE INDEX idx_assign_scheduled ON assignments(scheduled_start);

CREATE TABLE assignment_outputs (
    id                            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assignment_id                 UUID NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
    org_id                        UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    employee_id                   UUID NOT NULL REFERENCES digital_employees(id) ON DELETE CASCADE,

    raw_transcript                TEXT,
    clean_transcript              TEXT,
    summary                       TEXT,
    decisions                     JSONB DEFAULT '[]',
    action_items                  JSONB DEFAULT '[]',
    risks                         JSONB DEFAULT '[]',
    key_topics                    JSONB DEFAULT '[]',
    questions_asked               JSONB DEFAULT '[]',
    follow_ups                    JSONB DEFAULT '[]',
    sentiment_analysis            JSONB DEFAULT '{}',

    -- Healthcare
    diagnosis_summary             TEXT,
    prescription_draft            TEXT,
    recommendations               JSONB DEFAULT '[]',
    follow_up_reminders           JSONB DEFAULT '[]',

    -- Knowledge
    knowledge_promotion_suggestions JSONB DEFAULT '[]',

    created_at                    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_outputs_assignment ON assignment_outputs(assignment_id);
CREATE INDEX idx_outputs_org ON assignment_outputs(org_id);

CREATE TABLE org_knowledge_base (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id                UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    department_id         UUID REFERENCES departments(id) ON DELETE SET NULL,
    source                VARCHAR(50) DEFAULT 'manual',
    source_assignment_id  UUID REFERENCES assignments(id) ON DELETE SET NULL,
    source_employee_id    UUID REFERENCES digital_employees(id) ON DELETE SET NULL,
    title                 VARCHAR(512) NOT NULL,
    content               TEXT NOT NULL,
    content_type          VARCHAR(50) DEFAULT 'knowledge',
    scope                 VARCHAR(20) DEFAULT 'organization',
    tags                  JSONB DEFAULT '[]',
    approved_by           UUID REFERENCES users(id) ON DELETE SET NULL,
    is_approved           BOOLEAN DEFAULT FALSE,
    version               VARCHAR(20) DEFAULT '1.0.0',
    created_at            TIMESTAMPTZ DEFAULT NOW(),
    updated_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_orgkb_org ON org_knowledge_base(org_id);
CREATE INDEX idx_orgkb_approved ON org_knowledge_base(is_approved);
CREATE INDEX idx_orgkb_content_type ON org_knowledge_base(content_type);

CREATE TABLE supervisor_reviews (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assignment_id         UUID NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
    employee_id           UUID NOT NULL REFERENCES digital_employees(id) ON DELETE CASCADE,
    reviewer_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating                REAL NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comments              TEXT,
    corrections           JSONB DEFAULT '[]',
    knowledge_promoted    BOOLEAN DEFAULT FALSE,
    promote_to_training   BOOLEAN DEFAULT FALSE,
    retrain_triggered     BOOLEAN DEFAULT FALSE,
    created_at            TIMESTAMPTZ DEFAULT NOW(),
    updated_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_reviews_employee ON supervisor_reviews(employee_id);
CREATE INDEX idx_reviews_assignment ON supervisor_reviews(assignment_id);

-- ============================================
-- DIGITAL TWIN CREATION ENGINE (primary)
-- ============================================
CREATE TABLE digital_twins (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id               UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Step 1: Digital Identity
    name                  VARCHAR(255) NOT NULL,
    description           TEXT,
    category              digital_human_category DEFAULT 'personal',
    language              VARCHAR(10) DEFAULT 'en',
    timezone              VARCHAR(50) DEFAULT 'UTC',
    visibility            VARCHAR(20) DEFAULT 'private',
    avatar_image_url      VARCHAR(1024),

    -- Role (determines creation + intelligence pipeline)
    role                  VARCHAR(20) NOT NULL DEFAULT 'personal',

    -- Lifecycle status
    status                VARCHAR(30) DEFAULT 'draft',

    -- Step 2: Appearance (AI-driven)
    appearance_data       JSONB DEFAULT '{}',
    appearance_status     VARCHAR(20) DEFAULT 'pending',
    appearance_preview_url VARCHAR(1024),

    -- Step 3: Voice (cloning-first)
    voice_data            JSONB DEFAULT '{}',
    voice_status          VARCHAR(20) DEFAULT 'pending',
    voice_preview_url     VARCHAR(1024),

    -- Step 4: Personality (structured traits)
    personality_data      JSONB DEFAULT '{}',
    personality_status    VARCHAR(20) DEFAULT 'pending',

    -- Step 5: Intelligence config (role-specific)
    intelligence_data     JSONB DEFAULT '{}',
    intelligence_status   VARCHAR(20) DEFAULT 'pending',

    -- Personal: relationship
    relationship_data     JSONB DEFAULT '{}',

    -- Version / evolution tracking
    twin_version          VARCHAR(20) DEFAULT '1.0.0',
    interaction_count     INTEGER DEFAULT 0,
    evolution_count       INTEGER DEFAULT 0,
    last_interaction       TIMESTAMPTZ,

    -- Timestamps
    created_at            TIMESTAMPTZ DEFAULT NOW(),
    updated_at            TIMESTAMPTZ DEFAULT NOW(),
    published_at          TIMESTAMPTZ,

    -- Migration compat
    custom_dh_id          UUID REFERENCES custom_digital_humans(id) ON DELETE SET NULL,

    UNIQUE(user_id, name)
);

CREATE INDEX idx_digital_twins_user ON digital_twins(user_id);
CREATE INDEX idx_digital_twins_role ON digital_twins(role);
CREATE INDEX idx_digital_twins_status ON digital_twins(status);

CREATE TABLE knowledge_sources (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    twin_id           UUID NOT NULL REFERENCES digital_twins(id) ON DELETE CASCADE,
    source_type       VARCHAR(50) NOT NULL,
    source_name       VARCHAR(255),
    original_filename VARCHAR(512),
    file_path         VARCHAR(1024),
    file_size         BIGINT,
    mime_type         VARCHAR(127),
    status            VARCHAR(20) DEFAULT 'uploaded',
    page_count        INTEGER DEFAULT 0,
    word_count        INTEGER DEFAULT 0,
    chunk_count       INTEGER DEFAULT 0,
    error_message     TEXT,
    checksum          VARCHAR(64),
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_knowledge_sources_twin ON knowledge_sources(twin_id);
CREATE INDEX idx_knowledge_sources_status ON knowledge_sources(status);

CREATE TABLE knowledge_chunks (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id         UUID NOT NULL REFERENCES knowledge_sources(id) ON DELETE CASCADE,
    twin_id           UUID NOT NULL REFERENCES digital_twins(id) ON DELETE CASCADE,
    chunk_index       INTEGER NOT NULL,
    content           TEXT NOT NULL,
    metadata          JSONB DEFAULT '{}',
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_knowledge_chunks_source ON knowledge_chunks(source_id);
CREATE INDEX idx_knowledge_chunks_twin ON knowledge_chunks(twin_id);

CREATE TABLE learning_observations (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    twin_id           UUID NOT NULL REFERENCES digital_twins(id) ON DELETE CASCADE,
    observation_type  VARCHAR(50) NOT NULL,
    key               VARCHAR(255) NOT NULL,
    value             TEXT NOT NULL,
    confidence        REAL DEFAULT 0.3,
    source            VARCHAR(50) DEFAULT 'conversation',
    source_excerpt    TEXT,
    is_reviewed       BOOLEAN DEFAULT FALSE,
    is_confirmed      BOOLEAN DEFAULT FALSE,
    reviewed_by       UUID REFERENCES users(id),
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    confirmed_at      TIMESTAMPTZ
);

CREATE INDEX idx_learning_obs_twin ON learning_observations(twin_id);
CREATE INDEX idx_learning_obs_type ON learning_observations(observation_type);
CREATE INDEX idx_learning_obs_reviewed ON learning_observations(is_reviewed);

-- ============================================
-- IDENTITY ENGINE (unified avatar state, legacy)
-- ============================================
CREATE TABLE identity_profiles (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    custom_dh_id      UUID NOT NULL REFERENCES custom_digital_humans(id) ON DELETE CASCADE,
    identity_version  VARCHAR(20) DEFAULT '1.0.0',
    appearance        JSONB DEFAULT '{}',
    voice             JSONB DEFAULT '{}',
    personality       JSONB DEFAULT '{}',
    knowledge         JSONB DEFAULT '{}',
    memory            JSONB DEFAULT '{}',
    evolution         JSONB DEFAULT '{}',
    behavior          JSONB DEFAULT '{}',
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(custom_dh_id)
);

CREATE INDEX idx_identity_user ON identity_profiles(user_id);
CREATE INDEX idx_identity_custom_dh ON identity_profiles(custom_dh_id);

CREATE TABLE evolution_log (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    identity_id       UUID NOT NULL REFERENCES identity_profiles(id) ON DELETE CASCADE,
    from_version      VARCHAR(20) NOT NULL,
    to_version        VARCHAR(20) NOT NULL,
    trigger           VARCHAR(50) DEFAULT 'post_conversation',
    summary           TEXT,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_evolution_log_identity ON evolution_log(identity_id);
CREATE INDEX idx_evolution_log_created ON evolution_log(created_at DESC);

CREATE TABLE evolution_deltas (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    identity_id       UUID NOT NULL REFERENCES identity_profiles(id) ON DELETE CASCADE,
    interaction_id    UUID REFERENCES interactions(id) ON DELETE SET NULL,
    delta_type        VARCHAR(50) NOT NULL,
    key               VARCHAR(255) NOT NULL,
    old_value         TEXT,
    new_value         TEXT NOT NULL,
    confidence         REAL DEFAULT 1.0,
    source_excerpt    TEXT,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_evolution_deltas_identity ON evolution_deltas(identity_id);
CREATE INDEX idx_evolution_deltas_type ON evolution_deltas(delta_type);

-- ============================================
-- TRIGGERS: updated_at
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_subscriptions_updated_at BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_digital_humans_updated_at BEFORE UPDATE ON digital_humans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_custom_dh_updated_at BEFORE UPDATE ON custom_digital_humans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_voice_profiles_updated_at BEFORE UPDATE ON voice_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_healthcare_patients_updated_at BEFORE UPDATE ON healthcare_patients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_healthcare_schedules_updated_at BEFORE UPDATE ON healthcare_schedules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_business_clients_updated_at BEFORE UPDATE ON business_clients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_user_settings_updated_at BEFORE UPDATE ON user_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_identity_profiles_updated_at BEFORE UPDATE ON identity_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_digital_twins_updated_at BEFORE UPDATE ON digital_twins
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_organizations_updated_at BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_departments_updated_at BEFORE UPDATE ON departments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_digital_employees_updated_at BEFORE UPDATE ON digital_employees
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_assignments_updated_at BEFORE UPDATE ON assignments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_org_knowledge_base_updated_at BEFORE UPDATE ON org_knowledge_base
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_supervisor_reviews_updated_at BEFORE UPDATE ON supervisor_reviews
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================
-- SEED DATA: Pre-built digital humans
-- ============================================
INSERT INTO digital_humans (name, description, category, accent_color, emoji, personality, popularity) VALUES
('Dr. Aria', 'A compassionate healthcare companion for medical advice and support.', 'healthcare', '#10b981', '👩‍⚕️', 'Empathetic, knowledgeable, professional', 100),
('Mr. Carter', 'An executive coach for business strategy and leadership.', 'business', '#3b82f6', '👨‍💼', 'Strategic, direct, motivational', 95),
('Prof. Sage', 'An academic tutor for education and learning support.', 'education', '#8b5cf6', '👨‍🏫', 'Patient, thorough, encouraging', 90),
('Luna', 'A creative partner for brainstorming and artistic exploration.', 'creative', '#ec4899', '🧑‍🎤', 'Imaginative, playful, inspiring', 92),
('Atlas', 'A life coach for personal growth and daily motivation.', 'personal', '#f59e0b', '🧑‍🤝‍🧑', 'Supportive, wise, action-oriented', 88),
('Nova', 'A tech support specialist for troubleshooting and guidance.', 'tech', '#06b6d4', '👩‍💻', 'Analytical, patient, clear', 85),
('Dr. Rivera', 'A licensed therapist for mental health and wellness.', 'healthcare', '#10b981', '👩‍⚕️', 'Calm, understanding, insightful', 87),
('Coach Mike', 'A fitness trainer for workout plans and motivation.', 'personal', '#f97316', '💪', 'Energetic, disciplined, encouraging', 82),
('Ella', 'A language learning partner for practice and fluency.', 'education', '#8b5cf6', '🌍', 'Encouraging, clear, culturally aware', 84),
('Captain Rex', 'A motivational speaker for inspiration and goal-setting.', 'personal', '#ef4444', '🚀', 'Bold, charismatic, driven', 78),
('Dr. Chen', 'A nutritionist for diet planning and healthy eating.', 'healthcare', '#10b981', '🥗', 'Knowledgeable, practical, supportive', 80),
('Serena', 'A meditation guide for mindfulness and relaxation.', 'personal', '#a855f7', '🧘', 'Calm, soothing, present', 83);
