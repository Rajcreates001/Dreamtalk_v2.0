# Dreamtalk - Memory Module
# Extracted from chatbot-memory

from dreamtalk.brain.memory.personality.chatbot_memory.config import ChatbotMemoryConfig
from dreamtalk.brain.memory.personality.chatbot_memory.personality import PersonalityManager
from dreamtalk.brain.memory.personality.chatbot_memory.evolution import PersonalityUpdater
from dreamtalk.brain.memory.personality.chatbot_memory.memory import MemoryManager

__all__ = [
    "ChatbotMemoryConfig",
    "PersonalityManager",
    "PersonalityUpdater",
    "MemoryManager",
]
