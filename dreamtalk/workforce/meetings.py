from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from dreamtalk.backend.db.database import fetchrow
from dreamtalk.backend.services.llm_service import chat_completion
from dreamtalk.workforce.models import AssignmentOutput, MeetingIntelligenceResponse

logger = logging.getLogger("dreamtalk.workforce.meetings")

MEETING_SUMMARIZE_PROMPT = """You are a meeting intelligence system. Analyze the following conversation transcript and produce structured outputs.

Return ONLY valid JSON with these fields:
- "summary": A 3-5 sentence executive summary
- "decisions": Array of key decisions made
- "action_items": Array of action items with responsible party
- "risks": Array of risks or concerns identified
- "key_topics": Array of main topics discussed
- "questions_asked": Array of important questions raised
- "follow_ups": Array of follow-up items
- "sentiment_analysis": {"overall": "positive|neutral|negative", "score": 0.0-1.0}
- "important_decisions": Array of critical decisions (business)
- "diagnosis_summary": Brief diagnosis summary (healthcare only)
- "recommendations": Array of recommendations
- "knowledge_promotion_suggestions": Array of items that should become org knowledge

Transcript:
{transcript}
"""


class MeetingIntelligence:
    """Post-meeting intelligence: transcript → structured outputs."""

    @staticmethod
    async def process_transcript(
        assignment_id: str,
        org_id: str,
        employee_id: str,
        raw_transcript: str,
    ) -> AssignmentOutput:
        """Analyze a completed conversation/meeting transcript."""
        output = AssignmentOutput(
            assignment_id=assignment_id,
            org_id=org_id,
            employee_id=employee_id,
            raw_transcript=raw_transcript,
            clean_transcript=MeetingIntelligence._clean_transcript(raw_transcript),
        )

        insights = await MeetingIntelligence._extract_insights(raw_transcript[:8000])

        output.summary = insights.get("summary", "")
        output.decisions = insights.get("decisions", [])
        output.action_items = insights.get("action_items", [])
        output.risks = insights.get("risks", [])
        output.key_topics = insights.get("key_topics", [])
        output.questions_asked = insights.get("questions_asked", [])
        output.follow_ups = insights.get("follow_ups", [])
        output.sentiment_analysis = insights.get("sentiment_analysis", {"overall": "neutral", "score": 0.5})
        output.important_decisions = insights.get("important_decisions", [])
        output.diagnosis_summary = insights.get("diagnosis_summary", "")
        output.recommendations = insights.get("recommendations", [])
        output.knowledge_promotion_suggestions = insights.get("knowledge_promotion_suggestions", [])

        return output

    @staticmethod
    async def _extract_insights(transcript: str) -> dict:
        prompt = MEETING_SUMMARIZE_PROMPT.format(transcript=transcript)
        try:
            result = await chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2048,
            )
            raw = result["response"].strip()
            if raw.startswith("```"):
                raw = raw.strip("`").strip()
                if raw.startswith("json"):
                    raw = raw[4:].strip()
            return json.loads(raw)
        except Exception as e:
            logger.warning("Meeting intelligence extraction failed: %s", e)
            return {
                "summary": "[Intelligence extraction unavailable]",
                "decisions": [], "action_items": [], "risks": [],
                "key_topics": [], "questions_asked": [], "follow_ups": [],
                "sentiment_analysis": {"overall": "neutral", "score": 0.5},
                "knowledge_promotion_suggestions": [],
            }

    @staticmethod
    def _clean_transcript(raw: str) -> str:
        import re
        cleaned = re.sub(r"\[.*?\]", "", raw)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()
