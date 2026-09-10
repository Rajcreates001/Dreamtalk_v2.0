-- DreamTalk Migration 001: Initial schema
-- This is a reference migration. The actual schema is in schema.sql and schema_v2.sql.

-- Ensure required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Add missing columns if they don't exist
DO $$
BEGIN
    -- Add department_id to digital_twins if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='digital_twins' AND column_name='department_id') THEN
        ALTER TABLE digital_twins ADD COLUMN department_id UUID REFERENCES departments(id) ON DELETE SET NULL;
    END IF;
    
    -- Add twin_id to conversations if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='conversations' AND column_name='twin_id') THEN
        ALTER TABLE conversations ADD COLUMN twin_id UUID REFERENCES digital_twins(id) ON DELETE CASCADE;
    END IF;
    
    -- Add voice_id to digital_twins if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='digital_twins' AND column_name='voice_id') THEN
        ALTER TABLE digital_twins ADD COLUMN voice_id VARCHAR(255);
    END IF;
    
    -- Add personality_profile_id if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='digital_twins' AND column_name='personality_profile_id') THEN
        ALTER TABLE digital_twins ADD COLUMN personality_profile_id UUID REFERENCES personality_profiles(id) ON DELETE SET NULL;
    END IF;
END $$;
