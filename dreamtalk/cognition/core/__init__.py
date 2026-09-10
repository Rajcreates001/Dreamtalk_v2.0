# Dreamtalk - Cognition Module
# Top-level re-exports for all four cognitive sub-modules

from dreamtalk.cognition.core.snn.brain_cog import (
    BrainCogAPI,
    BrainCogConfig,
    SNNInferenceEngine,
)

from dreamtalk.cognition.core.neuroscience.cortex import (
    CortexAPI,
    CortexConfig,
    CortexInferenceEngine,
)

from dreamtalk.cognition.core.consciousness.aura import (
    AuraAPI,
    AuraConfig,
    AuraInferenceEngine,
)

from dreamtalk.cognition.core.neurological.neurologique import (
    NeurologiqueAPI,
    NeurologiqueConfig,
    NeuroInferenceEngine,
)

__all__ = [
    "BrainCogAPI", "BrainCogConfig", "SNNInferenceEngine",
    "CortexAPI", "CortexConfig", "CortexInferenceEngine",
    "AuraAPI", "AuraConfig", "AuraInferenceEngine",
    "NeurologiqueAPI", "NeurologiqueConfig", "NeuroInferenceEngine",
]
