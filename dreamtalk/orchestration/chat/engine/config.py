# Dreamtalk - Orchestration Module
# Extracted from OpenAvatarChat (Apache 2.0)

from enum import Enum
from typing import Dict, Optional, List, Union
from pydantic import BaseModel, Field


class EngineChannelType(str, Enum):
    NONE = "none"
    TEXT = "text"
    AUDIO = "audio"
    VIDEO = "video"
    MOTION_DATA = "motion_data"
    EVENT = "event"
    DATA = "data"


class ChatDataType(Enum):
    def __init__(self, value: str, channel_type: EngineChannelType):
        self._value_ = value
        self.channel_type = channel_type

    NONE = ("none", EngineChannelType.NONE)
    HUMAN_TEXT = ("human_text", EngineChannelType.TEXT)
    AVATAR_TEXT = ("avatar_text", EngineChannelType.TEXT)
    HUMAN_VOICE_ACTIVITY = ("human_vad", EngineChannelType.EVENT)
    MIC_AUDIO = ("mic_audio", EngineChannelType.AUDIO)
    HUMAN_AUDIO = ("human_audio", EngineChannelType.AUDIO)
    AVATAR_AUDIO = ("avatar_audio", EngineChannelType.AUDIO)
    CAMERA_VIDEO = ("camera_video", EngineChannelType.VIDEO)
    AVATAR_VIDEO = ("avatar_video", EngineChannelType.VIDEO)
    AVATAR_MOTION_DATA = ("avatar_motion_data", EngineChannelType.MOTION_DATA)
    HUMAN_DUPLEX_AUDIO = ("human_duplex_audio", EngineChannelType.AUDIO)
    HUMAN_DUPLEX_TEXT = ("human_duplex_text", EngineChannelType.TEXT)
    CLIENT_PLAYBACK = ("client_playback", EngineChannelType.EVENT)
    PERCEPTION_CONTEXT = ("perception_context", EngineChannelType.DATA)
    ENVIRONMENT_EVENT = ("environment_event", EngineChannelType.EVENT)


class ChatSignalType(str, Enum):
    SESSION_START = "session_start"
    STREAM_BEGIN = "stream_begin"
    STREAM_END = "stream_end"
    STREAM_CANCEL = "stream_cancel"
    INTERRUPT = "interrupt"
    ERROR = "error"
    SESSION_STOP = "session_stop"
    SEMANTIC_WAIT = "semantic_wait"
    ENVIRONMENT_EVENT = "environment_event"


class ChatSignalSourceType(str, Enum):
    CLIENT = "client"
    LOGIC = "logic"
    HANDLER = "handler"


class ChatStreamStatus(str, Enum):
    NOT_STARTED = "not_started"
    STARTED = "started"
    ENDED = "ended"
    CANCELLED = "cancelled"


class ChatStreamConfig(BaseModel):
    forward_cancel_signal: bool = Field(default=True)
    source_type: ChatSignalSourceType = Field(default=ChatSignalSourceType.HANDLER)
    cancelable: bool = Field(default=True)
    auto_link_input: bool = Field(default=True)


class HandlerBaseConfigModel(BaseModel):
    enabled: bool = Field(default=True)
    module: Optional[str] = Field(default=None)
    concurrent_limit: int = Field(default=1)
    input_type_override: Optional[Dict[str, str]] = Field(default=None)
    output_type_override: Optional[Dict[str, str]] = Field(default=None)


class LogicBaseConfigModel(BaseModel):
    enabled: bool = Field(default=True)
    module: Optional[str] = Field(default=None)


class ChatEngineOutputSource(BaseModel):
    handler: Optional[Union[str, List[str]]]
    type: ChatDataType


class ChatEngineConfigModel(BaseModel):
    model_root: str = ""
    concurrent_limit: int = Field(default=1)
    handler_search_path: List[str] = Field(default_factory=list)
    logic_search_path: List[str] = Field(default_factory=list)
    handler_configs: Optional[Dict[str, Dict]] = None
    logic_configs: Optional[Dict[str, Dict]] = Field(default=None)
    outputs: Dict[EngineChannelType, ChatEngineOutputSource] = Field(default_factory=dict)
