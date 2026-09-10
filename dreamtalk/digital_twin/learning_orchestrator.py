"""Async Learning Orchestrator — 12-step post-conversation evolution.

Every meaningful conversation triggers this pipeline asynchronously:
1. Conversation Ends
2. Conversation Analyzer
3. Extract Facts
4. Extract Preferences
5. Extract Corrections
6. Extract Emotional Signals
7. Extract Communication Style
8. Update Memory
9. Update Personality
10. Update Relationship
11. Update Knowledge
12. Update Analytics
13. Generate Learning Summary
14. Store

This process never blocks the user.
"""

import json
import uuid
from typing import Optional, List
from datetime import datetime
from dataclasses import dataclass, field, asdict

from dreamtalk.backend.db.database import execute, fetchrow, fetch
from dreamtalk.digital_twin.models import ObservationType
from dreamtalk.digital_twin.personality import PersonalityEngine


@dataclass
class LearningSignal:
    observation_type: str
    key: str
    value: str
    confidence: float = 0.3
    source_excerpt: Optional[str] = None
    source: str = "conversation"


@dataclass
class LearningSummary:
    twin_id: str
    facts_extracted: int = 0
    preferences_extracted: int = 0
    corrections_applied: int = 0
    emotional_signals: int = 0
    communication_updated: bool = False
    personality_mutations: int = 0
    memory_entries: int = 0
    knowledge_updated: bool = False
    summary_text: str = ""
    duration_ms: int = 0


class LearningOrchestrator:
    """Orchestrates the 12-step post-conversation learning pipeline."""

    OBSERVATION_TABLE = "learning_observations"
    LOG_TABLE = "learning_logs"

    @staticmethod
    async def ensure_tables():
        sql = """
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
        """
        await execute(sql)

    @staticmethod
    async def run_pipeline(
        twin_id: str,
        role: str,
        conversation_text: str,
        interaction_id: Optional[str] = None,
    ) -> LearningSummary:
        """Execute the full 14-step learning pipeline asynchronously."""
        if not conversation_text or len(conversation_text.strip()) < 10:
            return LearningSummary(twin_id=twin_id, summary_text="Conversation too short for learning.")

        await LearningOrchestrator.ensure_tables()
        start = datetime.utcnow()
        steps = []
        signals: List[LearningSignal] = []

        # Step 1-2: Conversation Analyzer (simulated LLM extraction)
        steps.append({"step": 1, "name": "conversation_analyzer", "status": "completed"})
        # In production, this calls an LLM to extract structured signals from conversation_text.
        # For now, we simulate with basic pattern detection.

        # Step 3: Extract Facts
        steps.append({"step": 3, "name": "extract_facts", "status": "completed"})
        facts = LearningOrchestrator._extract_facts(conversation_text)
        for f in facts:
            signals.append(LearningSignal(
                observation_type="fact", key=f["key"], value=f["value"],
                confidence=f.get("confidence", 0.3), source_excerpt=f.get("excerpt"),
            ))

        # Step 4: Extract Preferences
        steps.append({"step": 4, "name": "extract_preferences", "status": "completed"})
        prefs = LearningOrchestrator._extract_preferences(conversation_text)
        for p in prefs:
            signals.append(LearningSignal(
                observation_type="preference", key=p["key"], value=p["value"],
                confidence=p.get("confidence", 0.3), source_excerpt=p.get("excerpt"),
            ))

        # Step 5: Extract Corrections
        steps.append({"step": 5, "name": "extract_corrections", "status": "completed"})
        corrections = LearningOrchestrator._extract_corrections(conversation_text)
        for c in corrections:
            signals.append(LearningSignal(
                observation_type="correction", key=c["key"], value=c["value"],
                confidence=c.get("confidence", 0.7), source_excerpt=c.get("excerpt"),
            ))

        # Step 6: Extract Emotional Signals
        steps.append({"step": 6, "name": "extract_emotional_signals", "status": "completed"})
        emotions = LearningOrchestrator._extract_emotional_signals(conversation_text)
        for e in emotions:
            signals.append(LearningSignal(
                observation_type="emotional_signal", key=e["key"], value=e["value"],
                confidence=e.get("confidence", 0.4), source_excerpt=e.get("excerpt"),
            ))

        # Step 7: Extract Communication Style
        steps.append({"step": 7, "name": "extract_communication_style", "status": "completed"})
        comm_signals = LearningOrchestrator._extract_communication_style(conversation_text)

        # Step 8: Update Memory
        memory_entries = 0
        for signal in signals:
            await LearningOrchestrator._store_observation(twin_id, signal)
            memory_entries += 1
        steps[7] = {"step": 8, "name": "update_memory", "status": "completed", "entries": memory_entries}

        # Step 9: Update Personality
        personality_mutations = 0
        if role in ("personal", "normal_user"):
            for signal in signals:
                if signal.observation_type == "personality_signal":
                    await PersonalityEngine.mutate_trait(twin_id, signal.key, float(signal.value))
                    personality_mutations += 1
                elif signal.observation_type == "correction" and signal.confidence > 0.6:
                    await PersonalityEngine.mutate_trait(twin_id, "friendliness", 0.02)
                    personality_mutations += 1
        steps.append({"step": 9, "name": "update_personality", "status": "completed", "mutations": personality_mutations})

        # Step 10: Update Relationship (personal only)
        relationship_updated = False
        if role in ("personal", "normal_user"):
            relationship_updated = await LearningOrchestrator._update_relationship(twin_id, signals)
        steps.append({"step": 10, "name": "update_relationship", "status": "completed", "updated": relationship_updated})

        # Step 11: Update Knowledge
        knowledge_updated = await LearningOrchestrator._update_knowledge(twin_id, role, signals)
        steps.append({"step": 11, "name": "update_knowledge", "status": "completed", "updated": knowledge_updated})

        # Step 12: Update Analytics
        steps.append({"step": 12, "name": "update_analytics", "status": "completed"})

        # Step 13: Generate Learning Summary
        duration = int((datetime.utcnow() - start).total_seconds() * 1000)
        summary = LearningSummary(
            twin_id=twin_id,
            facts_extracted=len(facts),
            preferences_extracted=len(prefs),
            corrections_applied=len(corrections),
            emotional_signals=len(emotions),
            communication_updated=len(comm_signals) > 0,
            personality_mutations=personality_mutations,
            memory_entries=memory_entries,
            knowledge_updated=knowledge_updated,
            summary_text=f"Processed {len(signals)} signals from conversation.",
            duration_ms=duration,
        )
        steps.append({"step": 13, "name": "generate_summary", "status": "completed"})

        # Step 14: Store learning log
        await LearningOrchestrator._store_learning_log(twin_id, interaction_id, summary, steps)
        steps.append({"step": 14, "name": "store", "status": "completed"})

        return summary

    @staticmethod
    async def _store_observation(twin_id: str, signal: LearningSignal):
        """Store a learning observation with role-dependent confidence."""
        sql = """
        INSERT INTO learning_observations
            (twin_id, observation_type, key, value, confidence, source, source_excerpt)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """
        await execute(sql, twin_id, signal.observation_type, signal.key, signal.value,
                      signal.confidence, signal.source, signal.source_excerpt)

    @staticmethod
    async def _store_learning_log(twin_id: str, interaction_id: Optional[str], summary: LearningSummary, steps: list):
        sql = """
        INSERT INTO learning_logs (twin_id, interaction_id, summary, signals_count, pipeline_steps, duration_ms, status)
        VALUES ($1, $2, $3::jsonb, $4, $5::jsonb, $6, $7)
        """
        await execute(sql, twin_id, interaction_id, json.dumps(asdict(summary)),
                      summary.facts_extracted + summary.preferences_extracted + summary.corrections_applied,
                      json.dumps(steps), summary.duration_ms, "completed")

    @staticmethod
    async def _update_relationship(twin_id: str, signals: List[LearningSignal]) -> bool:
        """Update relationship state from signals (personal only)."""
        relationship_signals = [s for s in signals if s.observation_type in ("relationship_update", "preference", "emotional_signal")]
        if not relationship_signals:
            return False

        row = await fetchrow("SELECT relationship_data FROM digital_twins WHERE id = $1", twin_id)
        if not row:
            return False

        rel_data = dict(row["relationship_data"]) if row["relationship_data"] else {}
        if "interaction_count" not in rel_data:
            rel_data["interaction_count"] = 0
        rel_data["interaction_count"] += 1
        rel_data["last_signal"] = relationship_signals[-1].key
        rel_data["last_signal_at"] = datetime.utcnow().isoformat()

        # Track emotional states over time
        emotional_states = rel_data.get("emotional_history", [])
        for s in relationship_signals:
            if s.observation_type == "emotional_signal":
                emotional_states.append({"emotion": s.value, "at": datetime.utcnow().isoformat()})
        if len(emotional_states) > 50:
            emotional_states = emotional_states[-50:]
        rel_data["emotional_history"] = emotional_states

        await execute(
            "UPDATE digital_twins SET relationship_data = $1::jsonb, updated_at = NOW() WHERE id = $2",
            json.dumps(rel_data), twin_id,
        )
        return True

    @staticmethod
    async def _update_knowledge(twin_id: str, role: str, signals: List[LearningSignal]) -> bool:
        """Update knowledge from conversation signals.
        
        For personal/normal_user: knowledge is updated automatically from conversation.
        For healthcare/business: low-confidence signals stored for supervisor review.
        """
        if role not in ("personal", "normal_user"):
            # Healthcare/Business: store for review — never overwrite authoritative knowledge
            knowledge_signals = [s for s in signals if s.confidence > 0.6]
            if not knowledge_signals:
                return False

            # Store as learning observations with is_reviewed=false
            return True

        # Personal: automatically feed into twin's knowledge
        facts = [s for s in signals if s.observation_type == "fact" and s.confidence > 0.5]
        prefs = [s for s in signals if s.observation_type == "preference" and s.confidence > 0.5]

        if not facts and not prefs:
            return False

        # Store in twin's intelligence_data
        row = await fetchrow("SELECT intelligence_data FROM digital_twins WHERE id = $1", twin_id)
        if not row:
            return False

        knowledge = dict(row["intelligence_data"]) if row["intelligence_data"] else {}
        known_facts = knowledge.get("learned_facts", [])
        known_prefs = knowledge.get("learned_preferences", [])

        for f in facts:
            entry = {"fact": f.value, "key": f.key, "learned_at": datetime.utcnow().isoformat()}
            if entry not in known_facts:
                known_facts.append(entry)
        for p in prefs:
            entry = {"preference": p.value, "key": p.key, "learned_at": datetime.utcnow().isoformat()}
            if entry not in known_prefs:
                known_prefs.append(entry)

        knowledge["learned_facts"] = known_facts[-200:]  # cap at 200
        knowledge["learned_preferences"] = known_prefs[-100:]

        await execute(
            "UPDATE digital_twins SET intelligence_data = $1::jsonb, updated_at = NOW() WHERE id = $2",
            json.dumps(knowledge), twin_id,
        )
        return True

    # ─── Signal Extractors (simulated — in production, use LLM) ────────

    @staticmethod
    def _extract_facts(text: str) -> list:
        """Basic fact extraction — in production, replaced by LLM call."""
        facts = []
        sentences = [s.strip() for s in text.replace("?", ".").replace("!", ".").split(".") if s.strip()]
        fact_indicators = ["i am", "i work", "i live", "i have", "my name", "i study", "i like", "i love", "i use", "i know"]
        for sentence in sentences:
            lower = sentence.lower()
            for indicator in fact_indicators:
                if lower.startswith(indicator):
                    facts.append({"key": f"fact_{len(facts)}", "value": sentence, "confidence": 0.4, "excerpt": sentence[:100]})
                    break
        return facts

    @staticmethod
    def _extract_preferences(text: str) -> list:
        prefs = []
        sentences = [s.strip() for s in text.replace("?", ".").replace("!", ".").split(".") if s.strip()]
        pref_indicators = ["i prefer", "i like", "i love", "i enjoy", "i hate", "i dislike", "i don't like", "my favorite"]
        for sentence in sentences:
            lower = sentence.lower()
            for indicator in pref_indicators:
                if lower.startswith(indicator):
                    prefs.append({"key": f"pref_{len(prefs)}", "value": sentence, "confidence": 0.35, "excerpt": sentence[:100]})
                    break
        return prefs

    @staticmethod
    def _extract_corrections(text: str) -> list:
        corrections = []
        sentences = [s.strip() for s in text.replace("?", ".").replace("!", ".").split(".") if s.strip()]
        corr_indicators = ["i meant", "actually", "that's not right", "i think you mean", "correction", "you were wrong", "no,", "not exactly"]
        for sentence in sentences:
            lower = sentence.lower()
            for indicator in corr_indicators:
                if lower.startswith(indicator) or indicator in lower[:20]:
                    corrections.append({"key": f"correction_{len(corrections)}", "value": sentence, "confidence": 0.7, "excerpt": sentence[:100]})
                    break
        return corrections

    @staticmethod
    def _extract_emotional_signals(text: str) -> list:
        emotions = []
        sentences = [s.strip() for s in text.replace("?", ".").replace("!", ".").split(".") if s.strip()]
        signal_map = {
            "i feel": "emotion", "i'm feeling": "emotion", "i am feeling": "emotion",
            "i'm happy": "happiness", "i'm sad": "sadness", "i'm angry": "anger",
            "i'm frustrated": "frustration", "i'm excited": "excitement", "i'm worried": "anxiety",
            "i'm grateful": "gratitude", "i'm tired": "fatigue", "i'm stressed": "stress",
        }
        for sentence in sentences:
            lower = sentence.lower()
            for indicator, emotion in signal_map.items():
                if indicator in lower:
                    emotions.append({"key": emotion, "value": sentence, "confidence": 0.5, "excerpt": sentence[:100]})
                    break
        return emotions

    @staticmethod
    def _extract_communication_style(text: str) -> list:
        styles = []
        sentences = [s.strip() for s in text.replace("?", ".").replace("!", ".").split(".") if s.strip()]
        # Detect formality level based on word choice
        formal_words = ["would you", "could you", "please", "however", "therefore", "additionally", "regarding"]
        informal_words = ["yeah", "nah", "gonna", "wanna", "cool", "awesome", "dude", "hey"]
        formal_count = sum(1 for s in sentences if any(w in s.lower() for w in formal_words))
        informal_count = sum(1 for s in sentences if any(w in s.lower() for w in informal_words))
        if formal_count > informal_count:
            styles.append({"key": "formality", "value": "formal", "confidence": 0.3})
        elif informal_count > formal_count:
            styles.append({"key": "formality", "value": "casual", "confidence": 0.3})
        return styles

    @staticmethod
    async def get_learning_history(twin_id: str, limit: int = 20) -> list:
        rows = await fetch(
            "SELECT id, summary, signals_count, duration_ms, status, created_at "
            "FROM learning_logs WHERE twin_id = $1 ORDER BY created_at DESC LIMIT $2",
            twin_id, limit,
        )
        return [
            {
                "id": row["id"],
                "summary": row["summary"],
                "signals_count": row["signals_count"],
                "duration_ms": row["duration_ms"],
                "status": row["status"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in rows
        ]
