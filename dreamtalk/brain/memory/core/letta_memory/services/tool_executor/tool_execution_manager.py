# Adapted from Letta (MemGPT) - Apache 2.0 License
import asyncio
import json
import traceback
from typing import Any, ClassVar, Dict, Optional, Type

from dreamtalk.brain.memory.core.letta_memory.constants import FUNCTION_RETURN_VALUE_TRUNCATED
from dreamtalk.brain.memory.core.letta_memory.helpers.datetime_helpers import AsyncTimer
from dreamtalk.brain.memory.core.letta_memory.log import get_logger
from dreamtalk.brain.memory.core.letta_memory.otel.context import get_ctx_attributes
from dreamtalk.brain.memory.core.letta_memory.otel.metric_registry import MetricRegistry
from dreamtalk.brain.memory.core.letta_memory.otel.tracing import trace_method
from dreamtalk.brain.memory.core.letta_memory.schemas.agent import AgentState
from dreamtalk.brain.memory.core.letta_memory.schemas.enums import ToolType
from dreamtalk.brain.memory.core.letta_memory.schemas.sandbox_config import SandboxConfig
from dreamtalk.brain.memory.core.letta_memory.schemas.tool import Tool
from dreamtalk.brain.memory.core.letta_memory.schemas.tool_execution_result import ToolExecutionResult
from dreamtalk.brain.memory.core.letta_memory.schemas.user import User
from dreamtalk.brain.memory.core.letta_memory.services.agent_manager import AgentManager
from dreamtalk.brain.memory.core.letta_memory.services.block_manager import BlockManager
from dreamtalk.brain.memory.core.letta_memory.services.message_manager import MessageManager
from dreamtalk.brain.memory.core.letta_memory.services.passage_manager import PassageManager
from dreamtalk.brain.memory.core.letta_memory.services.run_manager import RunManager
from dreamtalk.brain.memory.core.letta_memory.services.tool_executor.builtin_tool_executor import LettaBuiltinToolExecutor
from dreamtalk.brain.memory.core.letta_memory.services.tool_executor.core_tool_executor import LettaCoreToolExecutor
from dreamtalk.brain.memory.core.letta_memory.services.tool_executor.files_tool_executor import LettaFileToolExecutor
from dreamtalk.brain.memory.core.letta_memory.services.tool_executor.mcp_tool_executor import ExternalMCPToolExecutor
from dreamtalk.brain.memory.core.letta_memory.services.tool_executor.sandbox_tool_executor import SandboxToolExecutor
from dreamtalk.brain.memory.core.letta_memory.services.tool_executor.tool_executor_base import ToolExecutor
from dreamtalk.brain.memory.core.letta_memory.utils import get_friendly_error_msg


class ToolExecutorFactory:
    """Factory for creating appropriate tool executors based on tool type."""

    _executor_map: ClassVar[Dict[ToolType, Type[ToolExecutor]]] = {
        ToolType.LETTA_CORE: LettaCoreToolExecutor,
        ToolType.LETTA_MEMORY_CORE: LettaCoreToolExecutor,
        ToolType.LETTA_SLEEPTIME_CORE: LettaCoreToolExecutor,
        ToolType.LETTA_MULTI_AGENT_CORE: SandboxToolExecutor,
        ToolType.LETTA_BUILTIN: LettaBuiltinToolExecutor,
        ToolType.LETTA_FILES_CORE: LettaFileToolExecutor,
        ToolType.EXTERNAL_MCP: ExternalMCPToolExecutor,
    }

    @classmethod
    def get_executor(
        cls,
        tool_type: ToolType,
        message_manager: MessageManager,
        agent_manager: AgentManager,
        block_manager: BlockManager,
        run_manager: RunManager,
        passage_manager: PassageManager,
        actor: User,
    ) -> ToolExecutor:
        """Get the appropriate executor for the given tool type."""
        executor_class = cls._executor_map.get(tool_type, SandboxToolExecutor)
        return executor_class(
            message_manager=message_manager,
            agent_manager=agent_manager,
            block_manager=block_manager,
            run_manager=run_manager,
            passage_manager=passage_manager,
            actor=actor,
        )


class ToolExecutionManager:
    """Manager class for tool execution operations."""

    def __init__(
        self,
        message_manager: MessageManager,
        agent_manager: AgentManager,
        block_manager: BlockManager,
        run_manager: RunManager,
        passage_manager: PassageManager,
        actor: User,
        agent_state: Optional[AgentState] = None,
        sandbox_config: Optional[SandboxConfig] = None,
        sandbox_env_vars: Optional[Dict[str, Any]] = None,
    ):
        self.message_manager = message_manager
        self.agent_manager = agent_manager
        self.block_manager = block_manager
        self.run_manager = run_manager
        self.passage_manager = passage_manager
        self.agent_state = agent_state
        self.logger = get_logger(__name__)
        self.actor = actor
        self.sandbox_config = sandbox_config
        self.sandbox_env_vars = sandbox_env_vars

    @trace_method
    async def execute_tool_async(
        self, function_name: str, function_args: dict, tool: Tool, step_id: str | None = None
    ) -> ToolExecutionResult:
        """
        Execute a tool asynchronously and persist any state changes.
        """
        status = "error"  # set as default for tracking purposes
        try:
            executor = ToolExecutorFactory.get_executor(
                tool.tool_type,
                message_manager=self.message_manager,
                agent_manager=self.agent_manager,
                block_manager=self.block_manager,
                run_manager=self.run_manager,
                passage_manager=self.passage_manager,
                actor=self.actor,
            )

            def _metrics_callback(exec_time_ms: int, exc):
                return MetricRegistry().tool_execution_time_ms_histogram.record(
                    exec_time_ms, dict(get_ctx_attributes(), **{"tool.name": tool.name})
                )

            async with AsyncTimer(callback_func=_metrics_callback):
                result = await executor.execute(
                    function_name, function_args, tool, self.actor, self.agent_state, self.sandbox_config, self.sandbox_env_vars
                )
            status = result.status

            # trim result
            # Convert to string representation, preserving dict structure when within limit
            return_str = json.dumps(result.func_return) if isinstance(result.func_return, dict) else str(result.func_return)
            if len(return_str) > tool.return_char_limit:
                result.func_return = FUNCTION_RETURN_VALUE_TRUNCATED(return_str, len(return_str), tool.return_char_limit)
            return result

        except asyncio.CancelledError as e:
            self.logger.error(f"Aysnc cancellation error executing tool {function_name}: {str(e)}")
            error_message = get_friendly_error_msg(
                function_name=function_name,
                exception_name=type(e).__name__,
                exception_message=str(e),
            )
            return ToolExecutionResult(
                status="error",
                func_return=error_message,
                stderr=[traceback.format_exc()],
            )
        except Exception as e:
            status = "error"
            self.logger.info(f"Error executing tool {function_name}: {str(e)}")
            error_message = get_friendly_error_msg(
                function_name=function_name,
                exception_name=type(e).__name__,
                exception_message=str(e),
            )
            return ToolExecutionResult(
                status="error",
                func_return=error_message,
                stderr=[traceback.format_exc()],
            )
        finally:
            metric_attrs = {"tool.name": tool.name, "tool.execution_success": status == "success"}
            if status == "error" and step_id:
                metric_attrs["step.id"] = step_id
            MetricRegistry().tool_execution_counter.add(1, dict(get_ctx_attributes(), **metric_attrs))
