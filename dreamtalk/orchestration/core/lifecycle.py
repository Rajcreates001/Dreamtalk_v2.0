# Dreamtalk - Orchestration Module
# Extracted from Utsuwa (License) + Handcrafted Persona Engine (MIT License)
# Component lifecycle management — start/stop/pause/resume for all subsystems.
#
# Sources:
#   - Utsuwa: types/module.ts (ModuleDefinition lifecycle hooks: onEnable, onDisable,
#     onSettingsChange), stores/modules.svelte.ts (module registry)
#   - C#: IStartupTask, IRenderComponent (Initialize/Update/Render lifecycle),
#     ILive2DAnimationService (Start/Stop/Update), IDisposable pattern

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class LifecycleState(str, Enum):
    """Lifecycle states for a managed component.

    Mirrors the ModuleState from Utsuwa (enabled/configured/error)
    combined with C# IDisposable / IStartupTask patterns.
    """
    CREATED = "created"
    INITIALIZING = "initializing"
    STARTED = "started"
    PAUSED = "paused"
    ERROR = "error"
    DISPOSED = "disposed"


class ComponentLifecycle(ABC):
    """Abstract base for all lifecycle-managed engine components.

    Every subsystem (ASR, TTS, LLM, Live2D, display) extends this class
    to participate in the orchestration engine's lifecycle.

    Ported from:
      - Utsuwa ModuleDefinition hooks (onEnable, onDisable)
      - C# IStartupTask (Execute), ILive2DAnimationService (Start/Stop/Update),
        IRenderComponent (Initialize/Update/Render)
      - C# IDisposable pattern via async dispose
    """

    def __init__(self) -> None:
        self._lifecycle_state: LifecycleState = LifecycleState.CREATED
        self._update_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def state(self) -> LifecycleState:
        return self._lifecycle_state

    @property
    def is_started(self) -> bool:
        return self._lifecycle_state == LifecycleState.STARTED

    @property
    def is_paused(self) -> bool:
        return self._lifecycle_state == LifecycleState.PAUSED

    # ------------------------------------------------------------------
    # Lifecycle hooks  (override in subclasses)
    # ------------------------------------------------------------------

    async def _on_start(self) -> None:
        """Override to perform one-time initialization (from IStartupTask.Execute)."""
        pass

    async def _on_stop(self) -> None:
        """Override to perform cleanup (from IDisposable.Dispose)."""
        pass

    async def _on_update(self, dt: float) -> None:
        """Override to perform per-frame work (from IRenderComponent.Update)."""
        pass

    async def _on_pause(self) -> None:
        """Override to handle pause transition."""
        pass

    async def _on_resume(self) -> None:
        """Override to handle resume transition."""
        pass

    # ------------------------------------------------------------------
    # Public lifecycle API
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the component.

        From C# IStartupTask.Execute() + ILive2DAnimationService.Start().
        From Utsuwa ModuleDefinition.onEnable().
        """
        if self._lifecycle_state != LifecycleState.CREATED:
            return

        self._lifecycle_state = LifecycleState.INITIALIZING
        try:
            await self._on_start()
            self._lifecycle_state = LifecycleState.STARTED
            logger.debug("%s started", type(self).__name__)
        except Exception:
            self._lifecycle_state = LifecycleState.ERROR
            logger.exception("Failed to start %s", type(self).__name__)
            raise

    async def stop(self) -> None:
        """Stop the component.

        From C# ILive2DAnimationService.Stop() + IDisposable.Dispose().
        From Utsuwa ModuleDefinition.onDisable().
        """
        if self._lifecycle_state in (LifecycleState.DISPOSED, LifecycleState.CREATED):
            return

        if self._update_task and not self._update_task.done():
            self._update_task.cancel()
            try:
                await self._update_task
            except (asyncio.CancelledError, Exception):
                pass

        try:
            await self._on_stop()
        except Exception:
            logger.exception("Error stopping %s", type(self).__name__)
        finally:
            self._lifecycle_state = LifecycleState.DISPOSED

    async def update(self, dt: float) -> None:
        """Per-frame update.

        From C# IRenderComponent.Update() + ILive2DAnimationService.Update().
        """
        if self._lifecycle_state != LifecycleState.STARTED:
            return
        try:
            await self._on_update(dt)
        except Exception:
            logger.exception("Error updating %s", type(self).__name__)
            self._lifecycle_state = LifecycleState.ERROR

    async def pause(self) -> None:
        """Pause the component."""
        if self._lifecycle_state != LifecycleState.STARTED:
            return
        self._lifecycle_state = LifecycleState.PAUSED
        try:
            await self._on_pause()
        except Exception:
            logger.exception("Error pausing %s", type(self).__name__)

    async def resume(self) -> None:
        """Resume the component from pause."""
        if self._lifecycle_state != LifecycleState.PAUSED:
            return
        self._lifecycle_state = LifecycleState.STARTED
        try:
            await self._on_resume()
        except Exception:
            logger.exception("Error resuming %s", type(self).__name__)


class StartupTask(ABC):
    """One-time startup task executed after component initialization.

    Ported from C# IStartupTask (used in AvatarApp.OnLoad()).
    """

    @abstractmethod
    async def execute(self) -> None:
        """Perform the startup action."""
        ...
