# Dreamtalk - Orchestration Module
# Extracted from OpenAvatarChat (Apache 2.0)

import queue
import threading
import time
from collections import namedtuple
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Callable, Any, Tuple

from dreamtalk.orchestration.chat.engine.config import (
    ChatDataType,
    ChatSignalType,
    ChatSignalSourceType,
    ChatStreamConfig,
    ChatStreamStatus,
)

SignalFilterRule = namedtuple(
    "SignalFilter",
    ["signal_type", "source_type", "stream_type"],
    defaults=[None, None, None],
)


class ChatSignal:
    def __init__(self, type: Optional[ChatSignalType] = None,
                 source_type: Optional[ChatSignalSourceType] = None,
                 related_stream: Optional[Any] = None,
                 signal_data: Optional[Dict] = None,
                 source_name: Optional[str] = None):
        self.type = type
        self.source_type = source_type
        self.related_stream = related_stream
        self.signal_data = signal_data
        self.source_name = source_name


class SignalEmitter:
    def __init__(self, signal_queue: queue.Queue, source_name: Optional[str] = None):
        self.source_name = source_name
        self.signal_queue = signal_queue

    def emit(self, signal: ChatSignal):
        signal.source_name = self.source_name
        self.signal_queue.put_nowait(signal)


class SignalManager:
    def __init__(self):
        self.running_flags = [False]
        self.signal_queue = queue.Queue()
        self.signal_listeners: Dict[SignalFilterRule, List[Callable]] = {}

    def init(self):
        if self.signal_listeners:
            raise RuntimeError("SignalManager already initialized")
        self.running_flags[0] = True
        self._thread = threading.Thread(target=self._distribute, daemon=True)
        self._thread.start()

    def shutdown(self):
        self.running_flags[0] = False

    def get_emitter(self, source_name: Optional[str] = None) -> SignalEmitter:
        return SignalEmitter(self.signal_queue, source_name)

    def register_listener(self, listener: Callable, signal_filter: SignalFilterRule = SignalFilterRule(None, None, None)):
        self.signal_listeners.setdefault(signal_filter, []).append(listener)

    def _distribute(self):
        while self.running_flags[0]:
            try:
                signal = self.signal_queue.get(block=True, timeout=0.5)
            except queue.Empty:
                continue
            for listener in self.signal_listeners.get(SignalFilterRule(None, None, None), []):
                listener(signal)


class StreamManager:
    def __init__(self):
        self._streams: Dict[str, Any] = {}

    def find_stream(self, stream_id: Any):
        if stream_id is None:
            return None
        return self._streams.get(str(stream_id))

    def get_active_streams(self):
        return [s for s in self._streams.values()]


class HandlerManager:
    def __init__(self, engine):
        self.engine = engine
        self.handler_configs: Dict[str, Dict] = {}
        self.handlers: Dict[str, Any] = {}

    def initialize(self, engine_config: "ChatEngineConfigModel"):
        if engine_config.handler_configs:
            for name, cfg in engine_config.handler_configs.items():
                self.handler_configs[name] = cfg

    def register_handler(self, name: str, handler):
        self.handlers[name] = handler

    def load_handlers(self, engine_config, app=None, ui=None, parent_block=None):
        pass

    def get_enabled_handler_registries(self):
        return list(self.handlers.values())

    def find_client_handler(self, handler):
        return None

    def destroy(self):
        self.handlers.clear()


class LogicManager:
    def __init__(self, engine):
        self.engine = engine
        self.logic_configs: Dict[str, Dict] = {}
        self.logics: Dict[str, Any] = {}

    def initialize(self, engine_config):
        if engine_config.logic_configs:
            self.logic_configs = engine_config.logic_configs

    def register_logic(self, name: str, logic):
        self.logics[name] = logic

    def get_enabled_logics(self):
        return list(self.logics.values())

    def load_logics(self, engine_config):
        pass

    def destroy(self):
        self.logics.clear()
