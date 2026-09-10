# Dreamtalk - Cognition Module
# Extracted from Cortex (https://github.com/anomalyco/Cortex)
# License: MIT

from dreamtalk.cognition.core.neuroscience.cortex.core.memory import (
    compute_heat_decay,
    compute_surprise,
    compute_importance,
    compute_valence,
    compute_metamemory_confidence,
    compute_session_coherence,
    compute_actr_decay,
)
from dreamtalk.cognition.core.neuroscience.cortex.core.emotion import (
    detect_emotions,
    compute_arousal,
    compute_emotional_valence,
    compute_importance_boost,
    compute_decay_resistance,
    tag_memory_emotions,
)
from dreamtalk.cognition.core.neuroscience.cortex.core.hippocampus import (
    ReplayDirection,
    ReplayEvent,
    ReplaySequence,
    ReplayResult,
    run_swr_replay,
    format_restoration,
    should_micro_checkpoint,
)

__all__ = [
    "compute_heat_decay",
    "compute_surprise",
    "compute_importance",
    "compute_valence",
    "compute_metamemory_confidence",
    "compute_session_coherence",
    "compute_actr_decay",
    "detect_emotions",
    "compute_arousal",
    "compute_emotional_valence",
    "compute_importance_boost",
    "compute_decay_resistance",
    "tag_memory_emotions",
    "ReplayDirection",
    "ReplayEvent",
    "ReplaySequence",
    "ReplayResult",
    "run_swr_replay",
    "format_restoration",
    "should_micro_checkpoint",
]
