"""
DreamTalk — Analytics Pipeline

Provides data for:
- Emotion analytics dashboard
- Brain activity visualization
- Conversation quality metrics
- Real-time streaming stats
"""

import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger("dreamtalk.pipeline.analytics")


@dataclass
class EmotionEvent:
    timestamp: float
    mood: str
    valence: float
    arousal: float
    confidence: float


@dataclass
class BrainEvent:
    timestamp: float
    pfc_rate: float
    dacc_conflict: float
    insula_valence: float
    bg_action: str
    firing_rate: float


class AnalyticsCollector:
    """Collects and aggregates analytics data from pipeline runs."""

    def __init__(self, max_events: int = 500):
        self._emotion_events: deque = deque(maxlen=max_events)
        self._brain_events: deque = deque(maxlen=max_events)
        self._conversation_metrics: deque = deque(maxlen=100)
        self._session_stats: Dict[str, Any] = {
            "total_conversations": 0,
            "total_messages": 0,
            "total_emotion_detections": 0,
            "avg_response_time_ms": 0,
            "avg_confidence": 0,
            "started_at": time.time(),
        }

    def record_emotion(self, emotion_data: Dict):
        event = EmotionEvent(
            timestamp=time.time(),
            mood=emotion_data.get("primary_mood", "neutral"),
            valence=emotion_data.get("valence", 0.0),
            arousal=emotion_data.get("arousal", 0.5),
            confidence=emotion_data.get("confidence", 0.5),
        )
        self._emotion_events.append(event)
        self._session_stats["total_emotion_detections"] += 1

    def record_brain_state(self, brain_data: Dict):
        event = BrainEvent(
            timestamp=time.time(),
            pfc_rate=brain_data.get("pfc_firing_rate", 0),
            dacc_conflict=brain_data.get("dacc_conflict", 0),
            insula_valence=brain_data.get("insula_valence", 0),
            bg_action=brain_data.get("basal_ganglia_action", ""),
            firing_rate=brain_data.get("spiking_activity", {}).get("total_firing_rate", 0),
        )
        self._brain_events.append(event)

    def record_conversation(self, response_time_ms: float, confidence: float, tokens: int):
        self._conversation_metrics.append({
            "timestamp": time.time(),
            "response_time_ms": response_time_ms,
            "confidence": confidence,
            "tokens": tokens,
        })
        self._session_stats["total_messages"] += 1
        n = self._session_stats["total_messages"]
        old_avg_rt = self._session_stats["avg_response_time_ms"]
        old_avg_conf = self._session_stats["avg_confidence"]
        self._session_stats["avg_response_time_ms"] = old_avg_rt + (response_time_ms - old_avg_rt) / n
        self._session_stats["avg_confidence"] = old_avg_conf + (confidence - old_avg_conf) / n

    def get_emotion_analytics(self, window_minutes: int = 30) -> Dict:
        cutoff = time.time() - (window_minutes * 60)
        events = [e for e in self._emotion_events if e.timestamp > cutoff]
        if not events:
            return {"events": [], "summary": {"total": 0}}

        mood_counts = {}
        for e in events:
            mood_counts[e.mood] = mood_counts.get(e.mood, 0) + 1

        avg_valence = sum(e.valence for e in events) / len(events)
        avg_arousal = sum(e.arousal for e in events) / len(events)
        avg_confidence = sum(e.confidence for e in events) / len(events)

        dominant_mood = max(mood_counts, key=mood_counts.get) if mood_counts else "neutral"

        return {
            "summary": {
                "total_detections": len(events),
                "dominant_mood": dominant_mood,
                "mood_distribution": mood_counts,
                "avg_valence": round(avg_valence, 3),
                "avg_arousal": round(avg_arousal, 3),
                "avg_confidence": round(avg_confidence, 3),
                "window_minutes": window_minutes,
            },
            "timeline": [
                {
                    "timestamp": e.timestamp,
                    "mood": e.mood,
                    "valence": round(e.valence, 3),
                    "arousal": round(e.arousal, 3),
                }
                for e in events[-50:]
            ],
        }

    def get_brain_analytics(self, window_minutes: int = 30) -> Dict:
        cutoff = time.time() - (window_minutes * 60)
        events = [e for e in self._brain_events if e.timestamp > cutoff]
        if not events:
            return {"events": [], "summary": {"total": 0}}

        action_counts = {}
        for e in events:
            action_counts[e.bg_action] = action_counts.get(e.bg_action, 0) + 1

        return {
            "summary": {
                "total_processes": len(events),
                "avg_pfc_rate": round(sum(e.pfc_rate for e in events) / len(events), 3),
                "avg_dacc_conflict": round(sum(e.dacc_conflict for e in events) / len(events), 3),
                "avg_firing_rate": round(sum(e.firing_rate for e in events) / len(events), 3),
                "dominant_action": max(action_counts, key=action_counts.get) if action_counts else "none",
                "action_distribution": action_counts,
            },
            "timeline": [
                {
                    "timestamp": e.timestamp,
                    "pfc_rate": round(e.pfc_rate, 3),
                    "dacc_conflict": round(e.dacc_conflict, 3),
                    "insula_valence": round(e.insula_valence, 3),
                    "bg_action": e.bg_action,
                    "firing_rate": round(e.firing_rate, 3),
                }
                for e in events[-50:]
            ],
        }

    def get_session_stats(self) -> Dict:
        uptime = time.time() - self._session_stats["started_at"]
        return {
            **self._session_stats,
            "uptime_seconds": round(uptime, 0),
            "active_emotion_events": len(self._emotion_events),
            "active_brain_events": len(self._brain_events),
        }


_collector: Optional[AnalyticsCollector] = None


def get_analytics() -> AnalyticsCollector:
    global _collector
    if _collector is None:
        _collector = AnalyticsCollector()
    return _collector
