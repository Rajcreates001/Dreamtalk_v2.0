"""Cognition API Router — reasoning, consciousness, and decision-making endpoints."""

import logging
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("dreamtalk.cognition.api")

router = APIRouter(prefix="/cognition", tags=["cognition"])


def _rule_based_reason(query: str, reasoning_type: str = "logical") -> dict:
    """Simple inline rule-based reasoning fallback."""
    query_lower = query.lower()
    trace = [f"Applied {reasoning_type} reasoning"]
    
    if reasoning_type == "logical":
        if "what" in query_lower or "how" in query_lower or "why" in query_lower:
            trace.append("Identified as informational query")
            return {"response": f"Based on logical analysis: {query}", "trace": trace, "confidence": 0.4}
        return {"response": f"Logical conclusion: {query}", "trace": trace, "confidence": 0.3}
    
    return {"response": f"Processed using {reasoning_type} reasoning: {query[:200]}", "trace": trace, "confidence": 0.3}

# ── Models ──────────────────────────────────────────────────────────────

class ReasoningRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None
    reasoning_type: str = "logical"  # logical, causal, spatial, temporal, analogical, moral
    role: str = "normal_user"

class ReasoningResponse(BaseModel):
    response: str
    reasoning_trace: List[str]
    confidence: float
    reasoning_type: str

class DecisionRequest(BaseModel):
    text: str
    role: str = "normal_user"
    emotion: Optional[Dict[str, float]] = None
    options: Optional[List[str]] = None

class DecisionResponse(BaseModel):
    decision: str
    reasoning: str
    confidence: float
    alternative_considered: List[str]

class ConsciousnessRequest(BaseModel):
    stimuli: List[str]
    context: Optional[Dict[str, Any]] = None

class ConsciousnessResponse(BaseModel):
    attention_focus: str
    awareness_level: float
    emotional_state: Dict[str, float]
    reflection: str

# ── Lazy-loaded reasoners ──────────────────────────────────────────────

_reasoners = {}
_consciousness = None

def _get_reasoner(reasoning_type: str = "logical"):
    """Lazy-load the appropriate reasoner."""
    global _reasoners
    if reasoning_type not in _reasoners:
        try:
            if reasoning_type == "snn":
                from dreamtalk.cognition.core.snn.brain_cog.brain_cog_api import BrainCogAPI
                _reasoners[reasoning_type] = BrainCogAPI()
            else:
                # Use a simpler reasoner for logical/causal etc.
                from dreamtalk.brain.cognition.base import BaseReasoner
                _reasoners[reasoning_type] = BaseReasoner(reasoning_type=reasoning_type)
        except Exception as e:
            logger.warning(f"Reasoner '{reasoning_type}' unavailable: {e}")
            _reasoners[reasoning_type] = None
    return _reasoners.get(reasoning_type)

def _get_consciousness():
    """Lazy-load consciousness module."""
    global _consciousness
    if _consciousness is None:
        try:
            from dreamtalk.cognition.neuroscience import CortexSimulation
            _consciousness = CortexSimulation()
        except Exception as e:
            logger.warning(f"Consciousness module unavailable: {e}")
            _consciousness = None
    return _consciousness

# ── Endpoints ──────────────────────────────────────────────────────────

@router.post("/reason", response_model=ReasoningResponse)
async def reason(request: ReasoningRequest):
    """Apply a specific reasoning type to a query."""
    reasoner = _get_reasoner(request.reasoning_type)
    if reasoner is None:
        # Fallback: inline rule-based reasoning
        result = _rule_based_reason(request.query, request.reasoning_type)
        return ReasoningResponse(
            response=result.get("response", f"Processed: {request.query[:200]}"),
            reasoning_trace=result.get("trace", ["Rule-based fallback"]),
            confidence=result.get("confidence", 0.3),
            reasoning_type=request.reasoning_type,
        )

    try:
        result = reasoner.reason(request.query, context=request.context)
        return ReasoningResponse(
            response=result.get("response", ""),
            reasoning_trace=result.get("trace", []),
            confidence=result.get("confidence", 0.8),
            reasoning_type=request.reasoning_type,
        )
    except Exception as e:
        logger.error(f"Reasoning failed: {e}")
        return ReasoningResponse(
            response=f"Reasoning unavailable: {e}",
            reasoning_trace=[],
            confidence=0.0,
            reasoning_type=request.reasoning_type,
        )


@router.post("/decide", response_model=DecisionResponse)
async def decide(request: DecisionRequest):
    """Make a decision based on text input, role, and emotion."""
    try:
        # Try brain pipeline
        from dreamtalk.pipeline.orchestrator import PipelineOrchestrator
        orch = PipelineOrchestrator()
        emotion = request.emotion or {}
        result = await orch.brain_pipeline.make_decision(
            text=request.text,
            role=request.role,
            emotion=emotion,
            model_name="rule_based",
        )
        return DecisionResponse(
            decision=result.response_text[:200],
            reasoning=result.reasoning_trace or "",
            confidence=result.confidence or 0.7,
            alternative_considered=result.alternatives or [],
        )
    except Exception as e:
        logger.warning(f"Brain pipeline unavailable: {e}")
        # Fallback: simple keyword-based decision
        return DecisionResponse(
            decision=f"Processed: {request.text[:100]}",
            reasoning="Rule-based fallback",
            confidence=0.3,
            alternative_considered=[],
        )


@router.post("/consciousness/update", response_model=ConsciousnessResponse)
async def update_consciousness(request: ConsciousnessRequest):
    """Update consciousness state with new stimuli."""
    cortex = _get_consciousness()
    if cortex is None:
        return ConsciousnessResponse(
            attention_focus="unknown",
            awareness_level=0.5,
            emotional_state={"valence": 0.0, "arousal": 0.0},
            reflection="Consciousness module not available",
        )

    try:
        result = cortex.process_stimuli(request.stimuli, request.context)
        return ConsciousnessResponse(
            attention_focus=result.get("focus", "ambient"),
            awareness_level=result.get("awareness", 0.5),
            emotional_state=result.get("emotion", {}),
            reflection=result.get("reflection", ""),
        )
    except Exception as e:
        logger.error(f"Consciousness update failed: {e}")
        return ConsciousnessResponse(
            attention_focus="error",
            awareness_level=0.0,
            emotional_state={},
            reflection=str(e),
        )


@router.get("/reasoners")
async def list_reasoners():
    """List available reasoning types."""
    return {
        "reasoners": [
            {"id": "logical", "name": "Logical Reasoning", "available": _get_reasoner("logical") is not None},
            {"id": "causal", "name": "Causal Reasoning", "available": _get_reasoner("causal") is not None},
            {"id": "spatial", "name": "Spatial Reasoning", "available": _get_reasoner("spatial") is not None},
            {"id": "temporal", "name": "Temporal Reasoning", "available": _get_reasoner("temporal") is not None},
            {"id": "analogical", "name": "Analogical Reasoning", "available": _get_reasoner("analogical") is not None},
            {"id": "moral", "name": "Moral Reasoning", "available": _get_reasoner("moral") is not None},
            {"id": "snn", "name": "Spiking Neural Network", "available": _get_reasoner("snn") is not None},
        ],
        "consciousness_available": _get_consciousness() is not None,
    }


@router.get("/health")
async def health():
    """Cognition system health check."""
    reasoners_available = sum(1 for r_type in ["logical", "causal", "spatial", "temporal", "analogical", "moral", "snn"]
                               if _get_reasoner(r_type) is not None)
    return {
        "status": "online",
        "module": "dreamtalk_cognition",
        "reasoners_available": reasoners_available,
        "consciousness_available": _get_consciousness() is not None,
    }
