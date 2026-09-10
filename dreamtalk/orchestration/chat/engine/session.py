# Dreamtalk - Orchestration Module
# Extracted from OpenAvatarChat (Apache 2.0)

import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Callable

from dreamtalk.orchestration.chat.engine.core import SignalManager, StreamManager
from dreamtalk.orchestration.chat.engine.config import ChatEngineConfigModel


@dataclass
class SessionInfoData:
    session_id: str
    timestamp_base: int = 16000


@dataclass
class SharedStates:
    active: bool = False


class SessionContext:
    def __init__(self, session_info: SessionInfoData):
        self.session_info = session_info
        self.shared_states = SharedStates()

    def cleanup(self):
        pass

    def get_clock(self):
        return None


class HandlerEnv:
    def __init__(self, handler, context, config=None):
        self.handler = handler
        self.context = context
        self.config = config or {}
        self.input_queue: queue.Queue = queue.Queue()


class HandlerRecord:
    def __init__(self, env: HandlerEnv):
        self.env = env
        self.pump_thread: Optional[threading.Thread] = None


class ChatSession:
    def __init__(self, session_context: SessionContext, engine_config: ChatEngineConfigModel):
        self.session_context = session_context
        self.signal_manager = SignalManager()
        self.signal_manager.init()
        self.stream_manager = StreamManager()
        self.handlers: Dict[str, HandlerRecord] = {}

    def prepare_handler(self, handler, handler_info, handler_config):
        env = HandlerEnv(handler=handler, context=handler.create_context(self.session_context, handler_config))
        self.handlers[handler_info.name] = HandlerRecord(env=env)
        return env

    def start(self):
        if self.session_context.shared_states.active:
            return
        self.session_context.shared_states.active = True
        for name, record in self.handlers.items():
            record.env.handler.start_context(self.session_context, record.env.context)

    def stop(self):
        self.session_context.shared_states.active = False
        for name, record in self.handlers.items():
            record.env.handler.destroy_context(record.env.context)
        self.signal_manager.shutdown()
        self.handlers.clear()
        self.session_context.cleanup()


class ChatDataSubmitter:
    def __init__(self):
        self.streamers: Dict[ChatDataType, List] = {}

    def register_streamer(self, streamer):
        self.streamers.setdefault(streamer.data_type, []).append(streamer)

    def get_streamer(self, data_type: "ChatDataType"):
        streamers = self.streamers.get(data_type, [])
        return streamers[0] if streamers else None

    def submit(self, data, finish_stream: Optional[bool] = None):
        pass

    def update_input_stream(self, chat_data):
        pass
