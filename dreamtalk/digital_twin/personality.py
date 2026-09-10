"""Standalone Personality Engine — stored separately from memory.

Every Digital Twin owns its own personality profile with:
- Big Five Traits (OCEAN)
- Behavior Rules
- Communication Style
- Response Preferences
- 7 editable characteristics

All values remain editable by the user at any time.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List
from datetime import datetime
import json
import uuid

from dreamtalk.backend.db.database import fetchrow, execute, fetch


@dataclass
class BigFiveTraits:
    openness: float = 0.5       # 0.0-1.0
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    neuroticism: float = 0.5    # inverse = emotional_stability


@dataclass
class CommunicationStyle:
    formality: float = 0.5        # 0=casual, 1=formal
    verbosity: float = 0.5        # 0=concise, 1=verbose
    assertiveness: float = 0.5    # 0=passive, 1=assertive
    humor: float = 0.5            # 0=serious, 1=humorous
    empathy: float = 0.5          # 0=clinical, 1=warm
    enthusiasm: float = 0.5       # 0=reserved, 1=enthusiastic


@dataclass
class BehaviorRules:
    interrupt_allowed: bool = False
    challenge_user: bool = False
    use_slang: bool = False
    use_emojis: bool = False
    use_metaphors: bool = True
    give_short_answers: bool = False
    ask_clarifying_questions: bool = True
    admit_uncertainty: bool = True


@dataclass
class PersonalityProfile:
    """Complete personality configuration for a Digital Twin."""

    # Big Five
    big_five: BigFiveTraits = field(default_factory=BigFiveTraits)

    # Characteristics (editable)
    tone: str = "neutral"           # neutral, warm, professional, playful, authoritative, soothing
    humor_level: float = 0.3       # 0.0-1.0
    empathy_level: float = 0.7     # 0.0-1.0
    professionalism: float = 0.7   # 0.0-1.0
    confidence: float = 0.7        # 0.0-1.0
    creativity: float = 0.5        # 0.0-1.0
    patience: float = 0.7          # 0.0-1.0
    friendliness: float = 0.7      # 0.0-1.0

    # Communication
    communication_style: CommunicationStyle = field(default_factory=CommunicationStyle)
    behavior_rules: BehaviorRules = field(default_factory=BehaviorRules)

    # Response preferences
    preferred_greeting: str = ""
    preferred_farewell: str = ""
    catchphrases: List[str] = field(default_factory=list)
    topics_to_avoid: List[str] = field(default_factory=list)
    topics_of_interest: List[str] = field(default_factory=list)

    # Version tracking
    personality_version: str = "1.0.0"


class PersonalityEngine:
    """Manages personality profiles independently from memory and knowledge."""

    TABLE = "personality_profiles"

    @staticmethod
    async def ensure_table():
        sql = """
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
        """
        await execute(sql)

    @staticmethod
    def _role_defaults(role: str) -> PersonalityProfile:
        if role == "healthcare":
            return PersonalityProfile(
                tone="professional",
                empathy_level=0.85,
                professionalism=0.9,
                confidence=0.85,
                humor_level=0.1,
                friendliness=0.6,
                patience=0.8,
                creativity=0.3,
                big_five=BigFiveTraits(
                    openness=0.4, conscientiousness=0.9, extraversion=0.5,
                    agreeableness=0.7, neuroticism=0.2,
                ),
                communication_style=CommunicationStyle(
                    formality=0.9, verbosity=0.6, assertiveness=0.6,
                    humor=0.1, empathy=0.8, enthusiasm=0.4,
                ),
                behavior_rules=BehaviorRules(
                    interrupt_allowed=False, challenge_user=False,
                    give_short_answers=False, ask_clarifying_questions=True,
                ),
                preferred_greeting="Hello, I'm Dr. {name}. How can I help you today?",
                topics_to_avoid=["unproven treatments", "self-diagnosis"],
            )
        elif role == "business":
            return PersonalityProfile(
                tone="professional",
                empathy_level=0.5,
                professionalism=0.85,
                confidence=0.8,
                humor_level=0.2,
                friendliness=0.5,
                patience=0.6,
                creativity=0.6,
                big_five=BigFiveTraits(
                    openness=0.6, conscientiousness=0.85, extraversion=0.6,
                    agreeableness=0.5, neuroticism=0.3,
                ),
                communication_style=CommunicationStyle(
                    formality=0.8, verbosity=0.5, assertiveness=0.7,
                    humor=0.2, empathy=0.4, enthusiasm=0.6,
                ),
                behavior_rules=BehaviorRules(
                    interrupt_allowed=False, challenge_user=True,
                    give_short_answers=True, ask_clarifying_questions=True,
                ),
                preferred_greeting="Good morning. Ready for our session?",
            )
        else:
            return PersonalityProfile(
                tone="warm",
                empathy_level=0.75,
                professionalism=0.5,
                confidence=0.6,
                humor_level=0.5,
                friendliness=0.8,
                patience=0.8,
                creativity=0.7,
                big_five=BigFiveTraits(
                    openness=0.7, conscientiousness=0.5, extraversion=0.6,
                    agreeableness=0.75, neuroticism=0.4,
                ),
                communication_style=CommunicationStyle(
                    formality=0.3, verbosity=0.5, assertiveness=0.4,
                    humor=0.5, empathy=0.7, enthusiasm=0.6,
                ),
                behavior_rules=BehaviorRules(
                    interrupt_allowed=False, challenge_user=False,
                    use_slang=True, use_emojis=True, use_metaphors=True,
                    give_short_answers=False, ask_clarifying_questions=True,
                ),
                preferred_greeting="Hey there! Ready to chat?",
                catchphrases=["That's interesting!", "Tell me more about that."],
            )

    @staticmethod
    async def initialize(twin_id: str, role: str = "personal") -> PersonalityProfile:
        await PersonalityEngine.ensure_table()
        profile = PersonalityEngine._role_defaults(role)
        profile_json = json.dumps(asdict(profile))
        big_five_json = json.dumps(asdict(profile.big_five))
        comm_json = json.dumps(asdict(profile.communication_style))
        rules_json = json.dumps(asdict(profile.behavior_rules))

        sql = """
        INSERT INTO personality_profiles (twin_id, profile, big_five, communication, behavior_rules, version)
        VALUES ($1, $2::jsonb, $3::jsonb, $4::jsonb, $5::jsonb, $6)
        ON CONFLICT (twin_id) DO UPDATE
        SET profile = $2::jsonb, big_five = $3::jsonb, communication = $4::jsonb,
            behavior_rules = $5::jsonb, version = $6, updated_at = NOW()
        """
        await execute(sql, twin_id, profile_json, big_five_json, comm_json, rules_json, profile.personality_version)
        return profile

    @staticmethod
    async def get(twin_id: str) -> Optional[PersonalityProfile]:
        row = await fetchrow("SELECT profile FROM personality_profiles WHERE twin_id = $1", twin_id)
        if not row:
            return None
        data = dict(row["profile"])
        return PersonalityProfile(**data)

    @staticmethod
    async def update(twin_id: str, updates: dict) -> bool:
        existing = await PersonalityEngine.get(twin_id)
        if not existing:
            return False

        for key, value in updates.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
            elif key == "big_five" and isinstance(value, dict):
                for k, v in value.items():
                    if hasattr(existing.big_five, k):
                        setattr(existing.big_five, k, v)
            elif key == "communication_style" and isinstance(value, dict):
                for k, v in value.items():
                    if hasattr(existing.communication_style, k):
                        setattr(existing.communication_style, k, v)
            elif key == "behavior_rules" and isinstance(value, dict):
                for k, v in value.items():
                    if hasattr(existing.behavior_rules, k):
                        setattr(existing.behavior_rules, k, v)

        version_parts = existing.personality_version.split(".")
        existing.personality_version = f"{version_parts[0]}.{int(version_parts[1]) + 1}.0"

        profile_json = json.dumps(asdict(existing))
        big_five_json = json.dumps(asdict(existing.big_five))
        comm_json = json.dumps(asdict(existing.communication_style))
        rules_json = json.dumps(asdict(existing.behavior_rules))

        sql = """
        UPDATE personality_profiles
        SET profile = $1::jsonb, big_five = $2::jsonb, communication = $3::jsonb,
            behavior_rules = $4::jsonb, version = $5, updated_at = NOW()
        WHERE twin_id = $6
        """
        await execute(sql, profile_json, big_five_json, comm_json, rules_json, existing.personality_version, twin_id)
        return True

    @staticmethod
    async def mutate_trait(twin_id: str, trait: str, delta: float, max_delta: float = 0.05):
        """Gradually mutate a single personality trait (used by learning engine)."""
        profile = await PersonalityEngine.get(twin_id)
        if not profile:
            return

        if hasattr(profile, trait):
            current = getattr(profile, trait)
            new_val = max(0.0, min(1.0, current + delta * max_delta))
            setattr(profile, trait, new_val)

        version_parts = profile.personality_version.split(".")
        profile.personality_version = f"{version_parts[0]}.{version_parts[1]}.{int(version_parts[2]) + 1}"

        profile_json = json.dumps(asdict(profile))
        big_five_json = json.dumps(asdict(profile.big_five))
        comm_json = json.dumps(asdict(profile.communication_style))
        rules_json = json.dumps(asdict(profile.behavior_rules))

        sql = """
        UPDATE personality_profiles
        SET profile = $1::jsonb, big_five = $2::jsonb, communication = $3::jsonb,
            behavior_rules = $4::jsonb, version = $5, updated_at = NOW()
        WHERE twin_id = $6
        """
        await execute(sql, profile_json, big_five_json, comm_json, rules_json, profile.personality_version, twin_id)

    @staticmethod
    async def delete(twin_id: str):
        await execute("DELETE FROM personality_profiles WHERE twin_id = $1", twin_id)
