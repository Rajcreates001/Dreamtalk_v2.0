# Dreamtalk - Orchestration Module
# Extracted from Utsuwa (License) + Handcrafted Persona Engine (MIT License)
# Core orchestration engine — manages the master lifecycle, sessions, and component wiring.
#
# Sources:
#   - Utsuwa: engine/events.ts (event checking), engine/stages.ts (stage progression),
#     engine/state-updates.ts (state application), stores/character.svelte.ts
#   - C#: AvatarApp (component initialization, update/render loop),
#     ConversationOrchestrator (session management, StartNewSessionAsync)

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Optional

from dreamtalk.orchestration.core.lifecycle import ComponentLifecycle, LifecycleState
from dreamtalk.orchestration.core.pipeline import PipelineStage, ProcessingPipeline
from dreamtalk.orchestration.core.state import (
    ConversationState,
    ConversationTrigger,
    OrchestrationState,
)

logger = logging.getLogger(__name__)


class OrchestrationEngine(ComponentLifecycle):
    """Master orchestration engine for the Dreamtalk avatar.

    Utsuwa-inspired lifecycle engine that manages the conversation pipeline,
    session state machine, and component lifecycle in one place.

    Architecture:
      - The engine owns a ProcessingPipeline (ASR -> LLM -> Filter -> TTS -> Animate -> Render).
      - It maintains an OrchestrationState FSM mirroring the C# ConversationState enum.
      - Components (ASR, TTS, Live2D, etc.) register as lifecycle-aware participants.
      - A single update() call drives one frame of the pipeline.

    Ported from:
      - Utsuwa: engine/* (events, stages, state-updates, memory)
      - C#: AvatarApp (render loop, component initialization),
        ConversationOrchestrator (session management)
    """

    def __init__(self, pipeline: Optional[ProcessingPipeline] = None) -> None:
        super().__init__()
        self._pipeline = pipeline or ProcessingPipeline()
        self._state = OrchestrationState()
        self._components: list[ComponentLifecycle] = []
        self._turn_task: Optional[asyncio.Task] = None
        self._loop_interval: float = 1.0 / 60.0  # ~60 fps

        # Register state-change callbacks (from C# event Action<ConversationState>)
        self._state_change_handlers: list[Callable[[ConversationState], None]] = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def pipeline(self) -> ProcessingPipeline:
        return self._pipeline

    @property
    def state(self) -> OrchestrationState:
        return self._state

    @property
    def current_conversation_state(self) -> ConversationState:
        return self._state.current

    @property
    def is_idle(self) -> bool:
        return self._state.current == ConversationState.IDLE

    # ------------------------------------------------------------------
    # Component registration
    # ------------------------------------------------------------------

    def register_component(self, component: ComponentLifecycle) -> None:
        """Register a lifecycle-aware component (mirrors C# DI registration)."""
        self._components.append(component)

    # ------------------------------------------------------------------
    # Lifecycle hooks  (from ComponentLifecycle ABC)
    # ------------------------------------------------------------------

    async def _on_start(self) -> None:
        logger.info("Orchestration engine starting...")
        # Initialize pipeline stages
        await self._pipeline.initialize()
        # Start all registered components
        for comp in self._components:
            await comp.start()
        # Enter idle state
        self._state.transition(ConversationTrigger.INITIALIZE_COMPLETE)

    async def _on_stop(self) -> None:
        logger.info("Orchestration engine stopping...")
        if self._turn_task and not self._turn_task.done():
            self._turn_task.cancel()
        for comp in reversed(self._components):
            await comp.stop()
        await self._pipeline.shutdown()

    async def _on_update(self, dt: float) -> None:
        """Main update tick — drives the conversation FSM and component updates.

        Mirrors C# AvatarApp.OnUpdate().
        """
        # Update all components
        for comp in self._components:
            await comp.update(dt)

        # Drive pipeline if in an active state
        if self._state.is_active_turn and not self._pipeline.is_running:
            await self._execute_turn()

    # ------------------------------------------------------------------
    # Turn execution  (from C# ConversationSession / TurnPipelineCoordinator)
    # ------------------------------------------------------------------

    async def _execute_turn(self) -> None:
        """Execute a single conversation turn through the pipeline.

        Flow (from C# AvatarApp architecture doc):
          1. Listen (ASR) -> 2. Understand (Whisper) -> 3. Contextualize (Vision) ->
          4. Think (LLM) -> 5. Respond (stream) -> 6. Filter (profanity) ->
          7. Speak (TTS) -> 8. Clone (RVC) -> 9. Animate (Live2D) -> 10. Display
        """
        self._state.transition(ConversationTrigger.INPUT_DETECTED)

        try:
            # Stage 1-2: ASR
            self._state.transition(ConversationTrigger.INPUT_FINALIZED)
            transcription = await self._pipeline.run_stage(PipelineStage.ASR)

            # Stage 3: Vision (optional)
            context = await self._pipeline.run_stage(PipelineStage.VISION)

            # Stage 4-5: LLM
            self._state.transition(ConversationTrigger.LLM_STREAM_STARTED)
            async for chunk in self._pipeline.run_stage_streaming(
                PipelineStage.LLM, transcription, context
            ):
                self._state.transition(ConversationTrigger.LLM_CHUNK_RECEIVED)
                # Yield to other tasks between chunks
                await asyncio.sleep(0)

            self._state.transition(ConversationTrigger.LLM_STREAM_ENDED)

            # Stage 6: Filter
            filtered_text = await self._pipeline.run_stage(PipelineStage.FILTER)

            # Stage 7-8: TTS + RVC
            self._state.transition(ConversationTrigger.TTS_STREAM_STARTED)
            audio = await self._pipeline.run_stage(PipelineStage.TTS, filtered_text)
            self._state.transition(ConversationTrigger.TTS_STREAM_ENDED)

            # Stage 9-10: Animate + Display
            await self._pipeline.run_stage(PipelineStage.ANIMATION, audio)
            await self._pipeline.run_stage(PipelineStage.DISPLAY)

            self._state.transition(ConversationTrigger.AUDIO_STREAM_ENDED)

        except Exception as exc:
            logger.exception("Turn execution failed")
            self._state.transition(ConversationTrigger.ERROR_OCCURRED)

    # ------------------------------------------------------------------
    # Session control  (from C# IConversationSession)
    # ------------------------------------------------------------------

    async def start_session(self) -> None:
        """Start a new conversation session (from C# StartNewSessionAsync)."""
        await self.start()
        self._state.transition(ConversationTrigger.INITIALIZE_REQUESTED)

    async def stop_session(self) -> None:
        """Stop the current session (from C# StopAsync)."""
        self._state.transition(ConversationTrigger.STOP_REQUESTED)
        await self.stop()

    async def pause_session(self) -> None:
        """Pause the session (from C# PauseAsync)."""
        self._state.transition(ConversationTrigger.PAUSE_REQUESTED)
        for comp in self._components:
            await comp.pause() if hasattr(comp, 'pause') else None

    async def resume_session(self) -> None:
        """Resume a paused session (from C# ResumeAsync)."""
        self._state.transition(ConversationTrigger.RESUME_REQUESTED)
        for comp in self._components:
            await comp.resume() if hasattr(comp, 'resume') else None

    def cancel_turn(self) -> None:
        """Cancel the current turn (from C# CancelAsync)."""
        if self._turn_task and not self._turn_task.done():
            self._turn_task.cancel()
        self._state.transition(ConversationTrigger.CANCEL_REQUESTED)

    def retry(self) -> None:
        """Retry from error state (from C# RetryAsync)."""
        self._state.transition(ConversationTrigger.RETRY_REQUESTED)

    # ------------------------------------------------------------------
    # State change subscribers
    # ------------------------------------------------------------------

    def on_state_change(self, handler: Callable[[ConversationState], None]) -> None:
        """Subscribe to conversation-state transitions (from C# StateChanged event)."""
        self._state_change_handlers.append(handler)

    def _notify_state_change(self, new_state: ConversationState) -> None:
        for handler in self._state_change_handlers:
            handler(new_state)
