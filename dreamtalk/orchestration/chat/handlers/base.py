# Dreamtalk - Orchestration Module
# Extracted from OpenAvatarChat (Apache 2.0)

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Any

from dreamtalk.orchestration.chat.engine.config import (
    ChatDataType,
    ChatEngineConfigModel,
    HandlerBaseConfigModel,
    ChatSignalType,
)


@dataclass
class HandlerBaseInfo:
    name: Optional[str] = None
    config_model: Optional[type] = None
    load_priority: int = 0


class ChatDataConsumeMode(Enum):
    ONCE = -1
    DEFAULT = 0


@dataclass
class HandlerDataInfo:
    type: ChatDataType = ChatDataType.NONE
    data_name: Optional[str] = None
    definition: Optional[Any] = None
    input_priority: int = 0
    input_consume_mode: ChatDataConsumeMode = ChatDataConsumeMode.DEFAULT
    output_stream_config: Optional[Any] = None


@dataclass
class HandlerDetail:
    inputs: Dict[ChatDataType, HandlerDataInfo] = field(default_factory=dict)
    outputs: Dict[ChatDataType, HandlerDataInfo] = field(default_factory=dict)
    signal_filters: List = field(default_factory=list)

    def validate(self):
        pass


class HandlerBase(ABC):
    def __init__(self):
        self.engine: Optional[Any] = None
        self.handler_root: Optional[str] = None

    def on_before_register(self):
        pass

    @abstractmethod
    def get_handler_info(self) -> HandlerBaseInfo:
        pass

    @abstractmethod
    def load(self, engine_config: ChatEngineConfigModel,
             handler_config: Optional[HandlerBaseConfigModel] = None):
        pass

    @abstractmethod
    def create_context(self, session_context, handler_config=None):
        pass

    def warmup_context(self, session_context, handler_context):
        pass

    @abstractmethod
    def start_context(self, session_context, handler_context):
        pass

    @abstractmethod
    def get_handler_detail(self, session_context, context) -> HandlerDetail:
        pass

    def on_signal(self, context, signal):
        pass

    @abstractmethod
    def handle(self, context, inputs, output_definitions):
        pass

    @abstractmethod
    def destroy_context(self, context):
        pass

    def destroy(self):
        pass


class ClientSessionDelegate(ABC):
    @abstractmethod
    async def get_data(self, modality, timeout=None):
        pass

    @abstractmethod
    def put_data(self, modality, data, timestamp=None, samplerate=None, loopback=False):
        pass

    @abstractmethod
    def get_timestamp(self):
        pass

    @abstractmethod
    def emit_signal(self, signal):
        pass

    @abstractmethod
    def clear_data(self):
        pass


class ClientHandlerBase(HandlerBase, ABC):
    @abstractmethod
    def on_setup_app(self, app, ui=None, parent_block=None):
        pass

    @abstractmethod
    def on_setup_session_delegate(self, session_context, handler_context, session_delegate):
        pass


@dataclass
class LogicBaseInfo:
    name: Optional[str] = None
    config_model: Optional[type] = None
    load_priority: int = 0


@dataclass
class LogicDetail:
    pass


class LogicBase(ABC):
    def __init__(self):
        self.engine: Optional[Any] = None
        self.logic_root: Optional[str] = None

    @abstractmethod
    def get_logic_info(self) -> LogicBaseInfo:
        pass

    def load(self, engine_config, logic_config=None):
        pass

    @abstractmethod
    def create_context(self, handler_registries, session_context, logic_config=None):
        pass

    @abstractmethod
    def get_logic_detail(self, session_context, context) -> LogicDetail:
        pass

    @abstractmethod
    def destroy_context(self, context):
        pass

    def destroy(self):
        pass
