# Dreamtalk - Cognition Module
# Extracted from Aura (https://github.com/anomalyco/aura)
# License: MIT

from dreamtalk.cognition.core.consciousness.aura.core.consciousness import (
    RIIU,
    PhiCore,
    PhiComputer,
    PhiResult,
    PhiConfig,
)
from dreamtalk.cognition.core.consciousness.aura.core.affect import (
    AffectiveCircumplex,
    get_circumplex,
)
from dreamtalk.cognition.core.consciousness.aura.core.motivation import (
    MotivationEngine,
    ResourceBudget,
    DriveType,
    Intention,
)
from dreamtalk.cognition.core.consciousness.aura.core.response import (
    ResponseGenerator,
    CognitiveMode,
)
from dreamtalk.cognition.core.consciousness.aura.core.caa import (
    ProductionCAA,
    VectorRegistry,
    AlphaController,
    ModeCollapseDetector,
)

__all__ = [
    "RIIU", "PhiCore", "PhiComputer", "PhiResult", "PhiConfig",
    "AffectiveCircumplex", "get_circumplex",
    "MotivationEngine", "ResourceBudget", "DriveType", "Intention",
    "ResponseGenerator", "CognitiveMode",
    "ProductionCAA", "VectorRegistry", "AlphaController", "ModeCollapseDetector",
]
