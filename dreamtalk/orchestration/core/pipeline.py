# Dreamtalk - Orchestration Module
# Extracted from Handcrafted Persona Engine (MIT License) + Utsuwa (License)
# Processing pipeline abstraction — stages connecting ASR, LLM, TTS, animation.
#
# Sources:
#   - C#: TurnPipelineCoordinator, avatar pipeline (11-stage flow),
#     ITextFilter pipeline (priority-ordered), ConversationOrchestrator
#   - Utsuwa: engine/stages.ts (relationship stage progression),
#     engine/heuristics.ts (message analysis pipeline)

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, AsyncIterator, Optional

logger = logging.getLogger(__name__)


class PipelineStage(str, Enum):
    """Named stages in the conversation pipeline.

    From C# Persona Engine architecture doc (11-stage flow):
      1. Listen -> 2. Understand -> 3. Contextualize -> 4. Think ->
      5. Respond -> 6. Filter -> 7. Speak -> 8. Clone -> 9. Animate -> 10. Display
    """
    ASR = "asr"               # 1-2: Listen + Understand (microphone -> Whisper)
    VISION = "vision"         # 3: Contextualize (screen awareness, optional)
    LLM = "llm"               # 4-5: Think + Respond (LLM streaming)
    FILTER = "filter"         # 6: Profanity / safety filter
    TTS = "tts"               # 7-8: Speak + Clone (TTS synthesis + RVC)
    ANIMATION = "animation"   # 9: Animate (Live2D lip-sync, expressions)
    DISPLAY = "display"       # 10: Display (overlay, Spout, subtitles)


class StageHandler(ABC):
    """Abstract handler for a single pipeline stage.

    From C#: each stage is an injectable service registered via DI.
    From Utsuwa: stage behavior is defined declaratively (e.g. STAGE_BEHAVIORS).
    """

    @abstractmethod
    async def process(self, input_data: Any = None) -> Any:
        """Process input and return output for the next stage."""
        ...

    async def process_streaming(self, input_data: Any = None) -> AsyncIterator[Any]:
        """Optional: yield chunks for streaming stages (LLM, TTS)."""
        if False:
            yield  # pragma: no cover — override in subclasses that stream


class ProcessingPipeline:
    """Ordered pipeline of processing stages.

    Manages the sequential flow: ASR -> LLM -> Filter -> TTS -> Animate -> Display.
    Stages can be started/stopped and their handlers can be hot-swapped.

    Ported from C# TurnPipelineCoordinator + Utsuwa stage progression concepts.
    """

    def __init__(self) -> None:
        self._handlers: dict[PipelineStage, StageHandler] = {}
        self._is_running: bool = False
        self._order = [
            PipelineStage.ASR,
            PipelineStage.VISION,
            PipelineStage.LLM,
            PipelineStage.FILTER,
            PipelineStage.TTS,
            PipelineStage.ANIMATION,
            PipelineStage.DISPLAY,
        ]

    @property
    def is_running(self) -> bool:
        return self._is_running

    def register(self, stage: PipelineStage, handler: StageHandler) -> None:
        """Register a handler for a pipeline stage."""
        self._handlers[stage] = handler
        logger.debug("Pipeline stage '%s' registered with %s", stage.value, type(handler).__name__)

    def get_handler(self, stage: PipelineStage) -> Optional[StageHandler]:
        """Look up a registered handler."""
        return self._handlers.get(stage)

    async def initialize(self) -> None:
        """Prepare the pipeline (called by OrchestrationEngine on start)."""
        logger.info("Pipeline initializing with %d stages", len(self._handlers))
        self._is_running = False

    async def shutdown(self) -> None:
        """Shut down the pipeline."""
        self._is_running = False
        logger.info("Pipeline shut down")

    async def run_stage(self, stage: PipelineStage, input_data: Any = None) -> Any:
        """Run a single pipeline stage with the given input.

        Returns the handler's output to be passed to the next stage.
        """
        handler = self._handlers.get(stage)
        if handler is None:
            logger.warning("No handler for stage '%s' — skipping", stage.value)
            return input_data

        self._is_running = True
        try:
            result = await handler.process(input_data)
            return result
        except Exception:
            logger.exception("Stage '%s' failed", stage.value)
            raise
        finally:
            self._is_running = False

    async def run_stage_streaming(
        self, stage: PipelineStage, *args: Any, **kwargs: Any
    ) -> AsyncIterator[Any]:
        """Run a streaming pipeline stage (LLM / TTS).

        Yields chunks as they arrive from the handler.
        """
        handler = self._handlers.get(stage)
        if handler is None:
            logger.warning("No handler for streaming stage '%s'", stage.value)
            return

        self._is_running = True
        try:
            async for chunk in handler.process_streaming(*args, **kwargs):
                yield chunk
        except Exception:
            logger.exception("Streaming stage '%s' failed", stage.value)
            raise
        finally:
            self._is_running = False

    async def run_full_cycle(self, audio_input: Any = None) -> None:
        """Run a complete pipeline cycle from ASR through Display.

        Mirrors the C# avatar's single-turn 10-stage flow.
        """
        # 1-2: ASR
        transcription = await self.run_stage(PipelineStage.ASR, audio_input)
        if not transcription:
            return

        # 3: Vision (optional)
        visual_context = await self.run_stage(PipelineStage.VISION)

        # 4-5: LLM
        llm_output = ""
        async for chunk in self.run_stage_streaming(
            PipelineStage.LLM, transcription, visual_context
        ):
            llm_output += chunk

        # 6: Filter
        filtered = await self.run_stage(PipelineStage.FILTER, llm_output)

        # 7-8: TTS
        audio_output = await self.run_stage(PipelineStage.TTS, filtered)

        # 9: Animate
        await self.run_stage(PipelineStage.ANIMATION, audio_output)

        # 10: Display
        await self.run_stage(PipelineStage.DISPLAY)
