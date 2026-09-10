-- DreamTalk v2 Schema Extensions — Digital Twin Operating System
-- Adds tables for: Personality Profiles, Media Assets, Learning Logs, Organization Memory
-- Run AFTER schema.sql

-- ============================================
-- PERSONALITY PROFILES (Standalone, not in memory)
-- ============================================
CREATE TABLE IF NOT EXISTS personality_profiles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    twin_id         UUID NOT NULL REFERENCES digital_twins(id) ON DELETE CASCADE,
    profile         JSONB NOT NULL DEFAULT '{}',
    big_five        JSONB DEFAULT '{}',
    communication   JSONB DEFAULT '{}',
    behavior_rules  JSONB DEFAULT '{}',
    version         VARCHAR(20) DEFAULT '1.0.0',
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(twin_id)
);

CREATE INDEX IF NOT EXISTS idx_personality_twin ON personality_profiles(twin_id);

-- ============================================
-- MEDIA ASSETS (Per-twin asset tracking)
-- ============================================
CREATE TABLE IF NOT EXISTS media_assets (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    twin_id         UUID NOT NULL REFERENCES digital_twins(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category        VARCHAR(50) NOT NULL,
    sub_category    VARCHAR(50) NOT NULL,
    filename        VARCHAR(512) NOT NULL,
    file_path       VARCHAR(1024) NOT NULL,
    file_size       BIGINT DEFAULT 0,
    mime_type       VARCHAR(127),
    checksum        VARCHAR(64),
    is_original     BOOLEAN DEFAULT TRUE,
    version         INTEGER DEFAULT 1,
    processing_status VARCHAR(30) DEFAULT 'stored',
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_media_assets_twin ON media_assets(twin_id);
CREATE INDEX IF NOT EXISTS idx_media_assets_category ON media_assets(twin_id, category);

-- ============================================
-- LEARNING LOGS (Per-conversation learning audit)
-- ============================================
CREATE TABLE IF NOT EXISTS learning_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    twin_id         UUID NOT NULL REFERENCES digital_twins(id) ON DELETE CASCADE,
    interaction_id  UUID,
    summary         JSONB DEFAULT '{}',
    signals_count   INTEGER DEFAULT 0,
    pipeline_steps  JSONB DEFAULT '[]',
    duration_ms     INTEGER DEFAULT 0,
    status          VARCHAR(20) DEFAULT 'pending',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_learning_logs_twin ON learning_logs(twin_id);
CREATE INDEX IF NOT EXISTS idx_learning_logs_created ON learning_logs(created_at DESC);

-- ============================================
-- ORGANIZATION MEMORY (Two-layer: personal + org)
-- ============================================
CREATE TABLE IF NOT EXISTS org_memory_entries (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id            UUID REFERENCES organizations(id) ON DELETE CASCADE,
    department_id     UUID REFERENCES departments(id) ON DELETE SET NULL,
    twin_id           UUID REFERENCES digital_twins(id) ON DELETE SET NULL,
    employee_id       UUID REFERENCES digital_employees(id) ON DELETE SET NULL,

    memory_layer      VARCHAR(20) NOT NULL DEFAULT 'personal',
        -- 'personal' = Layer 1: owned by one digital employee
        -- 'organization' = Layer 2: shared across org

    title             VARCHAR(512) NOT NULL,
    content           TEXT NOT NULL,
    content_type      VARCHAR(50) DEFAULT 'memory',

    -- Scope & access
    scope             VARCHAR(20) DEFAULT 'private',
        -- 'private' = only the owning twin/employee
        -- 'department' = visible to department
        -- 'organization' = visible to entire org

    -- Source tracking
    source            VARCHAR(50) DEFAULT 'conversation',
    source_assignment_id UUID REFERENCES assignments(id) ON DELETE SET NULL,
    source_excerpt    TEXT,

    -- Approval
    is_approved       BOOLEAN DEFAULT FALSE,
    approved_by        UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_at        TIMESTAMPTZ,

    -- Version
    version           VARCHAR(20) DEFAULT '1.0.0',
    is_active         BOOLEAN DEFAULT TRUE,

    tags              JSONB DEFAULT '[]',
    metadata          JSONB DEFAULT '{}',

    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orgmem_org ON org_memory_entries(org_id);
CREATE INDEX IF NOT EXISTS idx_orgmem_twin ON org_memory_entries(twin_id);
CREATE INDEX IF NOT EXISTS idx_orgmem_layer ON org_memory_entries(memory_layer);
CREATE INDEX IF NOT EXISTS idx_orgmem_scope ON org_memory_entries(scope);
CREATE INDEX IF NOT EXISTS idx_orgmem_approved ON org_memory_entries(is_approved);
CREATE INDEX IF NOT EXISTS idx_orgmem_content_type ON org_memory_entries(content_type);

-- ============================================
-- TRIGGER: updated_at for new tables
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER IF NOT EXISTS trg_personality_profiles_updated_at BEFORE UPDATE ON personality_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER IF NOT EXISTS trg_org_memory_entries_updated_at BEFORE UPDATE ON org_memory_entries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
