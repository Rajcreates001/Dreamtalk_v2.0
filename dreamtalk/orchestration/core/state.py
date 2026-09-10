# Dreamtalk - Orchestration Module
# Extracted from Handcrafted Persona Engine (MIT License) + Utsuwa (License)
# State management — conversation FSM and orchestration state container.
#
# Sources:
#   - C#: ConversationState (enum), ConversationTrigger (enum),
#     ConversationOrchestrator, ConversationSession state machine (Stateless)
#   - Utsuwa: state-updates.ts (applyStateUpdates, mergeUpdates, calculateMessageImpact),
#     stores/*.svelte.ts (Svelte runes state management pattern)

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ConversationState(str, Enum):
    """Finite-state-machine states for a conversation session.

    Ported from C# PersonaEngine.Lib.Core.Conversation.Abstractions.Session.ConversationState
    (C# enum with 16 values).
    """
    INITIAL = "initial"
    INITIALIZING = "initializing"
    IDLE = "idle"
    LISTENING = "listening"
    ACTIVE_TURN = "active_turn"
    PROCESSING_INPUT = "processing_input"
    WAITING_FOR_LLM = "waiting_for_llm"
    STREAMING_RESPONSE = "streaming_response"
    SPEAKING = "speaking"
    PAUSED = "paused"
    INTERRUPTED = "interrupted"
    CANCELLED = "cancelled"
    ERROR = "error"
    ENDED = "ended"


class ConversationTrigger(str, Enum):
    """Events that drive the conversation FSM.

    Ported from C# PersonaEngine.Lib.Core.Conversation.Abstractions.Session.ConversationTrigger
    (C# enum with 19 triggers).
    """
    INITIALIZE_REQUESTED = "initialize_requested"
    INITIALIZE_COMPLETE = "initialize_complete"
    STOP_REQUESTED = "stop_requested"
    PAUSE_REQUESTED = "pause_requested"
    RESUME_REQUESTED = "resume_requested"
    INPUT_DETECTED = "input_detected"
    INPUT_FINALIZED = "input_finalized"
    LLM_REQUEST_SENT = "llm_request_sent"
    LLM_STREAM_STARTED = "llm_stream_started"
    LLM_CHUNK_RECEIVED = "llm_chunk_received"
    LLM_STREAM_ENDED = "llm_stream_ended"
    TTS_REQUEST_SENT = "tts_request_sent"
    TTS_STREAM_STARTED = "tts_stream_started"
    TTS_CHUNK_RECEIVED = "tts_chunk_received"
    TTS_STREAM_ENDED = "tts_stream_ended"
    AUDIO_STREAM_STARTED = "audio_stream_started"
    AUDIO_STREAM_ENDED = "audio_stream_ended"
    ERROR_OCCURRED = "error_occurred"
    CANCEL_REQUESTED = "cancel_requested"
    CANCEL_COMPLETE = "cancel_complete"
    RETRY_REQUESTED = "retry_requested"


# Valid state transitions — maps (current_state, trigger) -> next_state
# Simplified from the Stateless FSM in C# ConversationSession.ConfigureStateMachine()
_TRANSITION_TABLE: dict[tuple[ConversationState, ConversationTrigger], ConversationState] = {
    # Initialization
    (ConversationState.INITIAL, ConversationTrigger.INITIALIZE_REQUESTED): ConversationState.INITIALIZING,
    (ConversationState.INITIALIZING, ConversationTrigger.INITIALIZE_COMPLETE): ConversationState.IDLE,
    (ConversationState.INITIALIZING, ConversationTrigger.ERROR_OCCURRED): ConversationState.ERROR,
    # Idle
    (ConversationState.IDLE, ConversationTrigger.INPUT_DETECTED): ConversationState.LISTENING,
    (ConversationState.IDLE, ConversationTrigger.STOP_REQUESTED): ConversationState.ENDED,
    (ConversationState.IDLE, ConversationTrigger.PAUSE_REQUESTED): ConversationState.PAUSED,
    # Listening
    (ConversationState.LISTENING, ConversationTrigger.INPUT_FINALIZED): ConversationState.ACTIVE_TURN,
    (ConversationState.LISTENING, ConversationTrigger.INPUT_DETECTED): ConversationState.LISTENING,
    (ConversationState.LISTENING, ConversationTrigger.ERROR_OCCURRED): ConversationState.ERROR,
    # Active turn flow
    (ConversationState.ACTIVE_TURN, ConversationTrigger.LLM_REQUEST_SENT): ConversationState.WAITING_FOR_LLM,
    (ConversationState.ACTIVE_TURN, ConversationTrigger.ERROR_OCCURRED): ConversationState.ERROR,
    (ConversationState.ACTIVE_TURN, ConversationTrigger.CANCEL_REQUESTED): ConversationState.CANCELLED,
    (ConversationState.WAITING_FOR_LLM, ConversationTrigger.LLM_STREAM_STARTED): ConversationState.STREAMING_RESPONSE,
    (ConversationState.WAITING_FOR_LLM, ConversationTrigger.ERROR_OCCURRED): ConversationState.ERROR,
    (ConversationState.WAITING_FOR_LLM, ConversationTrigger.CANCEL_REQUESTED): ConversationState.CANCELLED,
    (ConversationState.STREAMING_RESPONSE, ConversationTrigger.LLM_CHUNK_RECEIVED): ConversationState.STREAMING_RESPONSE,
    (ConversationState.STREAMING_RESPONSE, ConversationTrigger.LLM_STREAM_ENDED): ConversationState.SPEAKING,
    (ConversationState.STREAMING_RESPONSE, ConversationTrigger.ERROR_OCCURRED): ConversationState.ERROR,
    (ConversationState.STREAMING_RESPONSE, ConversationTrigger.CANCEL_REQUESTED): ConversationState.CANCELLED,
    # Speaking
    (ConversationState.SPEAKING, ConversationTrigger.AUDIO_STREAM_ENDED): ConversationState.IDLE,
    (ConversationState.SPEAKING, ConversationTrigger.INPUT_DETECTED): ConversationState.INTERRUPTED,
    (ConversationState.SPEAKING, ConversationTrigger.ERROR_OCCURRED): ConversationState.ERROR,
    (ConversationState.SPEAKING, ConversationTrigger.CANCEL_REQUESTED): ConversationState.CANCELLED,
    # Interrupted
    (ConversationState.INTERRUPTED, ConversationTrigger.AUDIO_STREAM_ENDED): ConversationState.LISTENING,
    # Paused
    (ConversationState.PAUSED, ConversationTrigger.RESUME_REQUESTED): ConversationState.IDLE,
    (ConversationState.PAUSED, ConversationTrigger.STOP_REQUESTED): ConversationState.ENDED,
    # Cancelled
    (ConversationState.CANCELLED, ConversationTrigger.CANCEL_COMPLETE): ConversationState.IDLE,
    # Error
    (ConversationState.ERROR, ConversationTrigger.RETRY_REQUESTED): ConversationState.IDLE,
    (ConversationState.ERROR, ConversationTrigger.STOP_REQUESTED): ConversationState.ENDED,
    # Ended
    (ConversationState.ENDED, ConversationTrigger.STOP_REQUESTED): ConversationState.ENDED,
}


@dataclass
class OrchestrationState:
    """Container for the engine's runtime FSM state.

    Mirrors the C# ConversationSession's state machine + context tracking.
    """

    current: ConversationState = ConversationState.INITIAL
    previous: Optional[ConversationState] = None
    session_id: str = ""
    turn_id: str = ""
    error_message: str = ""

    # Utsuwa-inspired interaction stats (from engine/heuristics.ts + state-updates.ts)
    interaction_count: int = 0
    last_input_time: Optional[float] = None

    @property
    def is_active_turn(self) -> bool:
        return self.current in {
            ConversationState.ACTIVE_TURN,
            ConversationState.WAITING_FOR_LLM,
            ConversationState.STREAMING_RESPONSE,
            ConversationState.SPEAKING,
        }

    @property
    def can_accept_input(self) -> bool:
        return self.current in {
            ConversationState.IDLE,
            ConversationState.LISTENING,
        }

    def transition(self, trigger: ConversationTrigger) -> None:
        """Apply a trigger to the state machine.

        Mirrors C# ConversationSession._stateMachine.FireAsync(trigger).
        If the transition is not defined, the trigger is silently ignored
        (same as the C# behaviour for invalid transitions).
        """
        key = (self.current, trigger)
        next_state = _TRANSITION_TABLE.get(key)
        if next_state is None:
            return  # Ignored trigger (no-op, matching C# Stateless behaviour)

        self.previous = self.current
        self.current = next_state

    def reset(self) -> None:
        """Reset to initial state."""
        self.current = ConversationState.INITIAL
        self.previous = None
        self.error_message = ""
