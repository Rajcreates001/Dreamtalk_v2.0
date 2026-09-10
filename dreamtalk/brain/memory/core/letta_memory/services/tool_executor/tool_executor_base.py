# Adapted from Letta (MemGPT) - Apache 2.0 License
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from dreamtalk.brain.memory.core.letta_memory.schemas.agent import AgentState
from dreamtalk.brain.memory.core.letta_memory.schemas.sandbox_config import SandboxConfig
from dreamtalk.brain.memory.core.letta_memory.schemas.tool import Tool
from dreamtalk.brain.memory.core.letta_memory.schemas.tool_execution_result import ToolExecutionResult
from dreamtalk.brain.memory.core.letta_memory.schemas.user import User
from dreamtalk.brain.memory.core.letta_memory.services.agent_manager import AgentManager
from dreamtalk.brain.memory.core.letta_memory.services.block_manager import BlockManager
from dreamtalk.brain.memory.core.letta_memory.services.message_manager import MessageManager
from dreamtalk.brain.memory.core.letta_memory.services.passage_manager import PassageManager
from dreamtalk.brain.memory.core.letta_memory.services.run_manager import RunManager


class ToolExecutor(ABC):
    """Abstract base class for tool executors."""

    def __init__(
        self,
        message_manager: MessageManager,
        agent_manager: AgentManager,
        block_manager: BlockManager,
        run_manager: RunManager,
        passage_manager: PassageManager,
        actor: User,
    ):
        self.message_manager = message_manager
        self.agent_manager = agent_manager
        self.block_manager = block_manager
        self.run_manager = run_manager
        self.passage_manager = passage_manager
        self.actor = actor

    @abstractmethod
    async def execute(
        self,
        function_name: str,
        function_args: dict,
        tool: Tool,
        actor: User,
        agent_state: Optional[AgentState] = None,
        sandbox_config: Optional[SandboxConfig] = None,
        sandbox_env_vars: Optional[Dict[str, Any]] = None,
    ) -> ToolExecutionResult:
        """Execute the tool and return the result."""
