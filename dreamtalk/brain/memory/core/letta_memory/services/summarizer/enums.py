# Adapted from Letta (MemGPT) - Apache 2.0 License
from enum import Enum


class SummarizationMode(str, Enum):
    """
    Represents possible modes of summarization for conversation trimming.
    """

    STATIC_MESSAGE_BUFFER = "static_message_buffer_mode"
    PARTIAL_EVICT_MESSAGE_BUFFER = "partial_evict_message_buffer_mode"
