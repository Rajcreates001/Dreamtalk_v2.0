# Adapted from Letta (MemGPT) - Apache 2.0 License
from typing import Any, Dict, Optional

from dreamtalk.brain.memory.core.letta_memory.constants import MCP_TOOL_TAG_NAME_PREFIX
from dreamtalk.brain.memory.core.letta_memory.log import get_logger
from dreamtalk.brain.memory.core.letta_memory.otel.tracing import trace_method
from dreamtalk.brain.memory.core.letta_memory.schemas.agent import AgentState
from dreamtalk.brain.memory.core.letta_memory.schemas.sandbox_config import SandboxConfig
from dreamtalk.brain.memory.core.letta_memory.schemas.tool import Tool
from dreamtalk.brain.memory.core.letta_memory.schemas.tool_execution_result import ToolExecutionResult
from dreamtalk.brain.memory.core.letta_memory.schemas.user import User
from dreamtalk.brain.memory.core.letta_memory.services.mcp_manager import MCPManager
from dreamtalk.brain.memory.core.letta_memory.services.tool_executor.tool_executor_base import ToolExecutor
from dreamtalk.brain.memory.core.letta_memory.utils import get_friendly_error_msg

logger = get_logger(__name__)

# MCP error class names that represent expected user-facing errors
# These are checked by class name to avoid import dependencies on fastmcp/mcp packages
MCP_EXPECTED_ERROR_CLASSES = {"McpError", "ToolError"}


class ExternalMCPToolExecutor(ToolExecutor):
    """Executor for external MCP tools."""

    @trace_method
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
        mcp_server_tag = [tag for tag in tool.tags if tag.startswith(f"{MCP_TOOL_TAG_NAME_PREFIX}:")]
        if not mcp_server_tag:
            raise ValueError(f"Tool {tool.name} does not have a valid MCP server tag")
        mcp_server_name = mcp_server_tag[0].split(":")[1]

        mcp_manager = MCPManager()
        # TODO: may need to have better client connection management

        environment_variables = {}
        agent_id = None
        if agent_state:
            environment_variables = agent_state.get_agent_env_vars_as_dict()
            agent_id = agent_state.id

        try:
            function_response, success = await mcp_manager.execute_mcp_server_tool(
                mcp_server_name=mcp_server_name,
                tool_name=function_name,
                tool_args=function_args,
                environment_variables=environment_variables,
                actor=actor,
                agent_id=agent_id,
            )

            return ToolExecutionResult(
                status="success" if success else "error",
                func_return=function_response,
            )
        except Exception as e:
            # Check if this is an expected MCP error (ToolError, McpError)
            # These are user-facing errors from the external MCP server (e.g., "No connected account found")
            # We handle them gracefully instead of letting them propagate as exceptions

            # Handle ExceptionGroup wrapping (Python 3.11+ async TaskGroup can wrap exceptions)
            exception_to_check = e
            if hasattr(e, "exceptions") and e.exceptions:
                # If it's an ExceptionGroup with a single wrapped exception, unwrap it
                if len(e.exceptions) == 1:
                    exception_to_check = e.exceptions[0]

            if exception_to_check.__class__.__name__ in MCP_EXPECTED_ERROR_CLASSES:
                logger.info(f"MCP tool '{function_name}' returned expected error: {str(exception_to_check)}")
                error_message = get_friendly_error_msg(
                    function_name=function_name,
                    exception_name=exception_to_check.__class__.__name__,
                    exception_message=str(exception_to_check),
                )
                return ToolExecutionResult(
                    status="error",
                    func_return=error_message,
                )
            # Re-raise unexpected errors
            raise
