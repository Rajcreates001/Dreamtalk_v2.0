# Adapted from OpenAvatarChat (Apache 2.0)

from enum import Enum


class ChatStreamStatus(str, Enum):
    NOT_STARTED = "not_started"
    STARTED = "started"
    ENDED = "ended"
    CANCELLED = "cancelled"
