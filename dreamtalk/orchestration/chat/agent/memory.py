# Dreamtalk - Orchestration Module
# Extracted from OpenAvatarChat (Apache 2.0)

import json
import time
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class DialogueTurn:
    role: str
    content: str
    timestamp: float = 0.0
    intent: Optional[str] = None
    trigger_type: str = "user"

    def to_llm_message(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


class WorkingMemory:
    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self._dialogue: List[DialogueTurn] = []
        self.current_intent: Optional[str] = None
        self.session_mode: str = "chitchat"
        self._compact_summary: Optional[str] = None

    def add_turn(self, turn: DialogueTurn):
        self._dialogue.append(turn)
        if len(self._dialogue) > self.max_turns:
            self._dialogue = self._dialogue[-self.max_turns:]

    def add_user_turn(self, content: str, intent: Optional[str] = None):
        self.add_turn(DialogueTurn(role="user", content=content, timestamp=time.time(), intent=intent))
        if intent:
            self.current_intent = intent

    def add_assistant_turn(self, content: str):
        self.add_turn(DialogueTurn(role="assistant", content=content, timestamp=time.time()))

    def add_system_turn(self, content: str, trigger_type: str = "event"):
        self.add_turn(DialogueTurn(role="system", content=content, timestamp=time.time(), trigger_type=trigger_type))

    def get_recent_turns(self, n: Optional[int] = None) -> List[DialogueTurn]:
        count = n if n is not None else self.max_turns
        return list(self._dialogue[-count:])

    def get_llm_messages(self, n: Optional[int] = None) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []
        if self._compact_summary:
            messages.append({"role": "user", "content": f"<dialogue-summary>\n{self._compact_summary}\n</dialogue-summary>"})
            messages.append({"role": "assistant", "content": "好的，我记住了之前的对话内容。"})
        messages.extend(t.to_llm_message() for t in self.get_recent_turns(n))
        return messages

    @property
    def turn_count(self) -> int:
        return len(self._dialogue)

    def should_compact(self, threshold: int) -> bool:
        return len(self._dialogue) >= threshold

    def compact(self, llm_client, model: str, keep_recent: int = 5) -> Optional[str]:
        if len(self._dialogue) <= keep_recent:
            return None
        old_turns = self._dialogue[:-keep_recent]
        self._dialogue = self._dialogue[-keep_recent:]
        summary = f"（之前进行了 {len(old_turns)} 轮对话）"
        self._compact_summary = summary if not self._compact_summary else f"{self._compact_summary}\n{summary}"
        return summary

    def clear(self):
        self._dialogue.clear()
        self.current_intent = None
        self.session_mode = "chitchat"
        self._compact_summary = None


@dataclass
class MemoryConfig:
    max_dialogue_turns: int = 20
    perception_max_entries: int = 100
    perception_decay_rate: float = 0.1
    perception_aggregation_window: float = 10.0
    summary_update_interval_turns: int = 5


class PerceptionEntry:
    def __init__(self, content: str, category: str, importance: float = 0.5,
                 timestamp: Optional[float] = None, metadata: Optional[Dict] = None):
        self.content = content
        self.category = category
        self.importance = importance
        self.timestamp = timestamp or time.time()
        self.metadata = metadata or {}


class PerceptionBuffer:
    def __init__(self, max_entries: int = 100):
        self.max_entries = max_entries
        self.entries: List[PerceptionEntry] = []

    def add(self, content: str, category: str, importance: float = 0.5, metadata: Optional[Dict] = None):
        self.entries.append(PerceptionEntry(content, category, importance, metadata=metadata))
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]

    def get_state_summary(self, max_length: int = 500) -> str:
        scene_entries = [e for e in self.entries if e.category == "scene"]
        scene_entries.sort(key=lambda x: x.timestamp, reverse=True)
        parts = [e.content for e in scene_entries]
        return "\n".join(parts) if parts else ""

    def get_recent_events(self, max_age: float = 60.0) -> List[PerceptionEntry]:
        cutoff = time.time() - max_age
        return [e for e in self.entries if e.category in ("event", "user_action") and e.timestamp >= cutoff]

    def clear(self):
        self.entries.clear()


class SessionMemoryManager:
    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig()
        self.working_memory = WorkingMemory(max_turns=self.config.max_dialogue_turns)
        self.perception_buffer = PerceptionBuffer(max_entries=self.config.perception_max_entries)

    def record_user_input(self, content: str, intent: Optional[str] = None, perception_snapshot: Optional[str] = None):
        self.working_memory.add_user_turn(content, intent=intent)

    def record_assistant_response(self, content: str):
        self.working_memory.add_assistant_turn(content)

    def record_system_event(self, content: str, trigger_type: str = "event"):
        self.working_memory.add_system_turn(content, trigger_type=trigger_type)

    def record_perception(self, content: str, category: str, importance: float = 0.5,
                          metadata: Optional[Dict] = None, event_type: Optional[str] = None):
        self.perception_buffer.add(content, category, importance, metadata=metadata)

    def get_environment_state(self, max_length: int = 500) -> str:
        return self.perception_buffer.get_state_summary(max_length=max_length)

    def get_recent_perception_events(self, max_age: float = 60.0) -> List[Dict]:
        entries = self.perception_buffer.get_recent_events(max_age=max_age)
        return [{"source": "camera", "content": e.content, "event_type": e.metadata.get("event_type", "")} for e in entries]

    def get_dialogue_for_llm(self, n: Optional[int] = None) -> List[Dict[str, str]]:
        return self.working_memory.get_llm_messages(n)

    def should_compact(self) -> bool:
        return self.working_memory.should_compact(15)

    def check_and_compact(self, llm_client, model: str, task_brief: str = "", env_state: str = ""):
        if self.should_compact():
            self.working_memory.compact(llm_client, model)

    def destroy(self):
        self.working_memory.clear()
        self.perception_buffer.clear()
