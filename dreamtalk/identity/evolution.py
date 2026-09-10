from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from dreamtalk.backend.db.database import execute
from dreamtalk.identity.models import (
    IdentityProfile, EvolutionDelta, EvolutionLogEntry,
    PersonalityProfile, BigFiveTraits,
)
from dreamtalk.identity.engine import IdentityEngine
from dreamtalk.backend.services.llm_service import chat_completion

logger = logging.getLogger("dreamtalk.identity.evolution")

EVOLUTION_EXTRACT_PROMPT = """You are a conversation analyst extracting learning signals from a chat exchange.

Analyze the user message and assistant response below. Extract structured deltas that will be used to evolve the assistant's identity profile. Return ONLY valid JSON with no extra text.

Return an array of objects with these fields:
- "delta_type": one of "fact", "preference", "correction", "personality_shift", "relationship_update"
- "key": a short snake_case identifier for what changed
- "new_value": the updated value (string, number, or object)
- "confidence": float 0-1
- "source_excerpt": the exact sentence or phrase from the conversation that supports this delta

Example:
[
  {"delta_type": "fact", "key": "user_name", "new_value": "Raj", "confidence": 1.0, "source_excerpt": "My name is Raj"},
  {"delta_type": "preference", "key": "formality_level", "new_value": "casual", "confidence": 0.8, "source_excerpt": "Just call me Raj, no need for formalities"}
]

User message: {user_message}
Assistant response: {assistant_response}
"""


class EvolutionEngine:
    """Post-conversation learning — extracts deltas, bumps version, logs evolution."""

    @staticmethod
    async def process_conversation(
        identity_id: str,
        interaction_id: str,
        user_message: str,
        assistant_response: str,
    ) -> Optional[EvolutionLogEntry]:
        """Analyze a single turn and produce evolution deltas."""
        profile = await IdentityEngine.get(identity_id)
        if not profile:
            logger.warning("Identity %s not found, skipping evolution", identity_id)
            return None

        deltas = await EvolutionEngine._extract_deltas(user_message, assistant_response)
        if not deltas:
            logger.info("No deltas extracted for interaction %s", interaction_id)
            return None

        log_entry = await EvolutionEngine._apply_deltas(
            identity_id, interaction_id, profile, deltas,
        )
        return log_entry

    @staticmethod
    async def _extract_deltas(user_message: str, assistant_response: str) -> list[EvolutionDelta]:
        """Call LLM to extract structured deltas from conversation."""
        prompt = EVOLUTION_EXTRACT_PROMPT.format(
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
            deltas_data = json.loads(raw)
            return [EvolutionDelta(**d) for d in deltas_data]
        except Exception as e:
            logger.warning("Evolution extraction failed: %s", e)
            return []

    @staticmethod
    async def _apply_deltas(
        identity_id: str,
        interaction_id: str,
        profile: IdentityProfile,
        deltas: list[EvolutionDelta],
    ) -> EvolutionLogEntry:
        """Apply extracted deltas to the identity profile and log evolution."""
        now = datetime.now(timezone.utc).isoformat()
        from_version = profile.identity_version

        for delta in deltas:
            delta.identity_id = identity_id
            delta.interaction_id = interaction_id
            delta.created_at = now

            EvolutionEngine._apply_single_delta(profile, delta)

        # Bump version
        parts = profile.identity_version.split(".")
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        profile.evolution.evolution_count += 1
        profile.evolution.interaction_count += 1
        profile.evolution.previous_versions.append(profile.identity_version)
        profile.identity_version = f"{major}.{minor}.{patch + 1}"
        profile.evolution.version = profile.identity_version
        profile.evolution.last_evolved = now

        await IdentityEngine.update(profile)

        # Persist deltas
        for delta in deltas:
            delta.id = str(uuid.uuid4())
            await execute(
                """INSERT INTO evolution_deltas
                   (id, identity_id, interaction_id, delta_type, key,
                    old_value, new_value, confidence, source_excerpt, created_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)""",
                delta.id, delta.identity_id, delta.interaction_id,
                delta.delta_type, delta.key,
                json.dumps(delta.old_value) if delta.old_value else None,
                json.dumps(delta.new_value) if delta.new_value else str(delta.new_value),
                delta.confidence, delta.source_excerpt, delta.created_at,
            )

        # Create log entry
        delta_summaries = [f"{d.delta_type}:{d.key}" for d in deltas]
        log_entry = EvolutionLogEntry(
            id=str(uuid.uuid4()),
            identity_id=identity_id,
            from_version=from_version,
            to_version=profile.identity_version,
            deltas=deltas,
            trigger="post_conversation",
            summary=f"Extracted {len(deltas)} delta(s): {', '.join(delta_summaries)}",
            created_at=now,
        )
        await execute(
            """INSERT INTO evolution_log
               (id, identity_id, from_version, to_version, trigger, summary, created_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7)""",
            log_entry.id, log_entry.identity_id, log_entry.from_version,
            log_entry.to_version, log_entry.trigger, log_entry.summary,
            log_entry.created_at,
        )
        return log_entry

    @staticmethod
    def _apply_single_delta(profile: IdentityProfile, delta: EvolutionDelta) -> None:
        """Route a delta to the appropriate sub-profile field."""
        if delta.delta_type == "fact":
            profile.memory.facts.append(f"{delta.key}: {delta.new_value}")
        elif delta.delta_type == "preference":
            profile.memory.preferences[delta.key] = delta.new_value
        elif delta.delta_type == "correction":
            profile.memory.corrections = getattr(profile.memory, "corrections", {})
            profile.memory.corrections[delta.key] = delta.new_value
        elif delta.delta_type == "personality_shift":
            if hasattr(profile.personality.big_five, delta.key):
                setattr(profile.personality.big_five, delta.key, float(delta.new_value))
        elif delta.delta_type == "relationship_update":
            profile.memory.relationship[delta.key] = delta.new_value
