# Dreamtalk - Memory Module
# Extracted from Letta

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from dreamtalk.brain.memory.core.letta_memory.config import LettaConfig
from dreamtalk.brain.memory.core.letta_memory.memory import (
    Block,
    ContextWindowOverview,
    Memory,
    Passage,
    RecallMemory,
)

logger = logging.getLogger(__name__)


class Agent:
    def __init__(
        self,
        config: Optional[LettaConfig] = None,
        name: Optional[str] = None,
    ):
        self.config = config or LettaConfig()
        self.name = name or self.config.agent_name or "letta_agent"
        self.memory = self._init_memory()
        self._messages: List[Dict[str, Any]] = []
        self._archival_memories: List[Passage] = []
        self._recall_memories: List[RecallMemory] = []
        self._step_count: int = 0
        self._system_prompt = self.config.system_prompt or self._default_system_prompt()

    def _default_system_prompt(self) -> str:
        return (
            f"You are {self.name}, an AI agent with memory capabilities. "
            "You have core, persona, and human memory blocks that can be updated. "
            "Use the available functions to recall and store information."
        )

    def _init_memory(self) -> Memory:
        blocks = []
        for block_name in self.config.memory_blocks:
            blocks.append(Block(name=block_name, value="", limit=2048))
        return Memory(
            core=Block(name="core", value="", limit=2048),
            persona=Block(name="persona", value="", limit=2048),
            human=Block(name="human", value="", limit=2048),
            blocks=blocks,
        )

    def step(self, user_message: str) -> str:
        self._messages.append({"role": "user", "content": user_message, "timestamp": self._step_count})
        self._step_count += 1
        return f"[{self.name}] Received: {user_message[:50]}..."

    def get_context_window(self) -> ContextWindowOverview:
        return ContextWindowOverview(
            num_messages=len(self._messages),
            total_tokens=sum(len(m.get("content", "")) for m in self._messages),
            num_archival_memories=len(self._archival_memories),
            num_recall_memories=len(self._recall_memories),
            blocks=self.memory.blocks,
            memory=self.memory,
        )

    def update_memory_block(self, block_name: str, new_value: str) -> Block:
        block = self.memory.get_block_by_name(block_name)
        if block:
            block.update_value(new_value)
        elif block_name == "core" and self.memory.core:
            self.memory.core.update_value(new_value)
        elif block_name == "persona" and self.memory.persona:
            self.memory.persona.update_value(new_value)
        elif block_name == "human" and self.memory.human:
            self.memory.human.update_value(new_value)
        else:
            new_block = Block(name=block_name, value=new_value[:2048])
            self.memory.blocks.append(new_block)
            block = new_block
        return block

    def store_archival_memory(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Passage:
        passage = Passage(
            id=f"archival_{len(self._archival_memories)}_{self._step_count}",
            text=text,
            metadata=metadata or {},
        )
        self._archival_memories.append(passage)
        return passage

    def store_recall_memory(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> RecallMemory:
        import uuid
        recall = RecallMemory(
            id=str(uuid.uuid4()),
            content=content,
            timestamp=str(self._step_count),
            metadata=metadata or {},
        )
        self._recall_memories.append(recall)
        return recall

    def search_archival(self, query: str, limit: int = 5) -> List[Passage]:
        results = []
        for p in self._archival_memories:
            if query.lower() in p.text.lower():
                results.append(p)
                if len(results) >= limit:
                    break
        return results

    def get_messages(self) -> List[Dict[str, Any]]:
        return self._messages.copy()

    def get_state(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "step": self._step_count,
            "memory": self.memory.model_dump(),
            "message_count": len(self._messages),
            "archival_count": len(self._archival_memories),
            "recall_count": len(self._recall_memories),
        }
