from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from dreamtalk.backend.db.database import execute, fetchrow, fetch
from dreamtalk.backend.services.llm_service import chat_completion
from dreamtalk.digital_twin.models import (
    DigitalTwinResponse, TwinRole, ObservationType, LearningObservation,
    PersonalityProfile,
)
from dreamtalk.digital_twin.engine import DigitalTwinEngine

logger = logging.getLogger("dreamtalk.digital_twin.learning")

CONTINUOUS_LEARNING_PROMPT = """You are a conversation analyst for a digital twin platform called DreamTalk.

Analyze the user message and assistant response below. Extract learning signals that describe how the assistant should adapt. Return ONLY valid JSON — no extra text.

Return an array of objects with these fields:
- "observation_type": one of "fact", "preference", "correction", "personality_signal", "relationship_update", "communication_style", "emotional_signal", "behavioral_pattern"
- "key": a short snake_case identifier
- "value": the new value (string, number, or short phrase)
- "confidence": float 0-1 (how certain you are this is a stable signal)
- "source_excerpt": the exact sentence that supports this signal

Example:
[
  {"observation_type": "fact", "key": "user_name", "value": "Raj", "confidence": 1.0, "source_excerpt": "My name is Raj"},
  {"observation_type": "preference", "key": "formality_level", "value": "casual", "confidence": 0.8, "source_excerpt": "Just call me Raj"}
]

User message: {user_message}
Assistant response: {assistant_response}
"""


class ContinuousLearningEngine:
    """Post-conversation learning engine.

    For Personal avatars: primary source of intelligence, direct memory updates.
    For Healthcare/Business: writes low-confidence observations for review.
    """

    @staticmethod
    async def process_conversation(
        twin_id: str,
        interaction_id: str,
        user_message: str,
        assistant_response: str,
    ) -> dict:
        twin = await DigitalTwinEngine.get(twin_id)
        if not twin:
            logger.warning("Twin %s not found, skipping learning", twin_id)
            return {"status": "skipped", "reason": "twin_not_found"}

        observations = await ContinuousLearningEngine._extract_observations(
            user_message, assistant_response,
        )
        if not observations:
            return {"status": "no_signals", "observations": []}

        if twin.role == TwinRole.PERSONAL:
            result = await ContinuousLearningEngine._apply_direct(
                twin, interaction_id, observations,
            )
        else:
            result = await ContinuousLearningEngine._apply_low_confidence(
                twin, interaction_id, observations,
            )

        # Always bump interaction count
        await DigitalTwinEngine.increment_interactions(twin_id)
        await DigitalTwinEngine.bump_version(twin_id)

        return result

    @staticmethod
    async def _extract_observations(
        user_message: str, assistant_response: str,
    ) -> list[LearningObservation]:
        prompt = CONTINUOUS_LEARNING_PROMPT.format(
            user_message=user_message[:2000],
            assistant_response=assistant_response[:2000],
        )
        try:
            result = await chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1024,
            )
            raw = result["response"].strip()
            if raw.startswith("```"):
                raw = raw.strip("`").strip()
                if raw.startswith("json"):
                    raw = raw[4:].strip()
            data = json.loads(raw)
            return [LearningObservation(**d) for d in data]
        except Exception as e:
            logger.warning("Observation extraction failed: %s", e)
            return []

    @staticmethod
    async def _apply_direct(
        twin: DigitalTwinResponse,
        interaction_id: str,
        observations: list[LearningObservation],
    ) -> dict:
        """Personal twins: apply observations directly to memory profiles."""
        now = datetime.now(timezone.utc).isoformat()
        applied = []

        for obs in observations:
            obs.id = str(uuid.uuid4())
            obs.twin_id = twin.id
            obs.created_at = now
            obs.is_reviewed = True
            obs.is_confirmed = True
            obs.confidence = min(obs.confidence + 0.2, 1.0)
            obs.source = "conversation"

            await execute(
                """INSERT INTO learning_observations
                   (id, twin_id, observation_type, key, value, confidence,
                    source, source_excerpt, is_reviewed, is_confirmed, created_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)""",
                obs.id, obs.twin_id, obs.observation_type.value, obs.key,
                obs.value, obs.confidence, obs.source, obs.source_excerpt,
                obs.is_reviewed, obs.is_confirmed, obs.created_at,
            )

            # Apply to twin's personality/memory
            await ContinuousLearningEngine._update_twin_profile(twin, obs)
            applied.append(obs.model_dump())

        # Re-save personality
        await DigitalTwinEngine.save_personality(twin.id, twin.personality)

        return {
            "status": "applied",
            "twin_id": twin.id,
            "observations_applied": len(applied),
            "observations": applied,
        }

    @staticmethod
    async def _apply_low_confidence(
        twin: DigitalTwinResponse,
        interaction_id: str,
        observations: list[LearningObservation],
    ) -> dict:
        """Healthcare/Business: write low-confidence observations for review."""
        now = datetime.now(timezone.utc).isoformat()
        stored = []

        for obs in observations:
            obs.id = str(uuid.uuid4())
            obs.twin_id = twin.id
            obs.created_at = now
            obs.is_reviewed = False
            obs.is_confirmed = False
            # Cap confidence to avoid overriding validated knowledge
            obs.confidence = min(obs.confidence, 0.4)
            obs.source = "conversation"

            await execute(
                """INSERT INTO learning_observations
                   (id, twin_id, observation_type, key, value, confidence,
                    source, source_excerpt, is_reviewed, is_confirmed, created_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)""",
                obs.id, obs.twin_id, obs.observation_type.value, obs.key,
                obs.value, obs.confidence, obs.source, obs.source_excerpt,
                obs.is_reviewed, obs.is_confirmed, obs.created_at,
            )
            stored.append(obs.model_dump())

        return {
            "status": "stored_low_confidence",
            "twin_id": twin.id,
            "observations_stored": len(stored),
            "observations": stored,
            "message": "Observations stored with low confidence. Review required before they affect behavior.",
        }

    @staticmethod
    async def _update_twin_profile(
        twin: DigitalTwinResponse, obs: LearningObservation,
    ) -> None:
        """Update in-memory personality based on observation type."""
        p = twin.personality

        if obs.observation_type == ObservationType.PERSONALITY_SIGNAL:
            trait_map = {
                "empathy": "empathy",
                "professionalism": "professionalism",
                "humor": "humor",
                "creativity": "creativity",
                "confidence": "confidence",
                "patience": "patience",
                "friendliness": "friendliness",
                "leadership": "leadership",
                "curiosity": "curiosity",
                "formality": "formality",
                "optimism": "optimism",
                "emotional_stability": "emotional_stability",
            }
            if obs.key in trait_map:
                try:
                    current = getattr(p, trait_map[obs.key])
                    delta = (float(obs.value) - current) * 0.3  # gradual shift
                    setattr(p, trait_map[obs.key], max(0.0, min(1.0, current + delta)))
                except (ValueError, TypeError):
                    pass
            if obs.key == "communication_style":
                p.communication_style = str(obs.value)

        elif obs.observation_type == ObservationType.COMMUNICATION_STYLE:
            p.communication_style = str(obs.value)
            style_map = {
                "concise": "short",
                "detailed": "long",
                "balanced": "medium",
            }
            if obs.value in style_map:
                p.response_length_preference = style_map[obs.value]

        elif obs.observation_type == ObservationType.EMOTIONAL_SIGNAL:
            if obs.key == "empathy_shift":
                try:
                    p.empathy = max(0.0, min(1.0, p.empathy + float(obs.value) * 0.1))
                except (ValueError, TypeError):
                    pass

        elif obs.observation_type == ObservationType.RELATIONSHIP_UPDATE:
            twin.intelligence.relationship = twin.intelligence.relationship or {}
            if hasattr(twin.intelligence, "relationship") and twin.intelligence.relationship:
                rel = twin.intelligence.relationship
                if hasattr(rel, obs.key):
                    setattr(rel, obs.key, obs.value)

        elif obs.observation_type == ObservationType.FACT:
            pass  # Facts stored in observation table for query context

        elif obs.observation_type == ObservationType.PREFERENCE:
            pass  # Preferences stored for later use by chat orchestration

    @staticmethod
    async def get_observations(
        twin_id: str,
        reviewed: Optional[bool] = None,
        confirmed: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LearningObservation]:
        conditions = ["twin_id = $1"]
        params = [twin_id]
        idx = 2

        if reviewed is not None:
            conditions.append(f"is_reviewed = ${idx}")
            params.append(reviewed)
            idx += 1
        if confirmed is not None:
            conditions.append(f"is_confirmed = ${idx}")
            params.append(confirmed)
            idx += 1

        sql = f"""SELECT * FROM learning_observations
                  WHERE {' AND '.join(conditions)}
                  ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}"""
        params.extend([limit, offset])
        rows = await fetch(sql, *params)
        return [LearningObservation(**dict(r)) for r in rows]

    @staticmethod
    async def confirm_observation(obs_id: str, user_id: str) -> Optional[LearningObservation]:
        row = await fetchrow(
            "UPDATE learning_observations SET is_confirmed = TRUE, is_reviewed = TRUE, confirmed_at = $1 WHERE id = $2 RETURNING *",
            datetime.now(timezone.utc).isoformat(), obs_id,
        )
        if not row:
            return None
        return LearningObservation(**dict(row))

    @staticmethod
    async def get_learning_stats(twin_id: str) -> dict:
        row = await fetchrow(
            """SELECT
               COUNT(*) AS total,
               COUNT(*) FILTER (WHERE is_reviewed) AS reviewed,
               COUNT(*) FILTER (WHERE is_confirmed) AS confirmed,
               COUNT(*) FILTER (WHERE NOT is_reviewed) AS pending_review,
               COUNT(*) FILTER (WHERE observation_type = 'fact') AS facts,
               COUNT(*) FILTER (WHERE observation_type = 'preference') AS preferences,
               COUNT(*) FILTER (WHERE observation_type = 'correction') AS corrections,
               COUNT(*) FILTER (WHERE observation_type = 'personality_signal') AS personality_signals,
               COUNT(*) FILTER (WHERE observation_type = 'relationship_update') AS relationship_updates
               FROM learning_observations WHERE twin_id = $1""",
            twin_id,
        )
        return dict(row) if row else {}
