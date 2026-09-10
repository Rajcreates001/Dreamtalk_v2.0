# Dreamtalk - Orchestration Module
# Extracted from hermes-agent (MIT License)

"""AIAgent — core conversation loop with tool calling.

Simplified from hermes-agent ``run_agent.py`` (~5.5K LOC) and
``agent/conversation_loop.py`` (~4.5K LOC). Retains the essential
architecture: initialization, message processing loop, tool dispatch,
error handling, and session persistence.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from dreamtalk.orchestration.agents.config import get_config, AgentConfig
from dreamtalk.orchestration.agents.core.session import SessionDB
from dreamtalk.orchestration.agents.tools.registry import registry

logger = logging.getLogger(__name__)

# Default system prompt
DEFAULT_SYSTEM_PROMPT = """You are Dreamtalk, an AI assistant with tool-calling capabilities.

You have access to the following tool categories: {toolsets}.

Rules:
- Use tools when they help answer the user's request.
- If a tool returns an error, explain it and try an alternative approach.
- Be concise, accurate, and helpful."""


class AIAgent:
    """AI agent with tool calling capabilities.

    Manages conversation flow, tool execution, and response handling
    for LLM models that support tool/function calling (OpenAI format).
    """

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        provider: Optional[str] = None,
        api_mode: str = "chat_completions",
        max_iterations: int = 30,
        max_tokens: Optional[int] = None,
        enabled_toolsets: Optional[List[str]] = None,
        disabled_toolsets: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
        session_db: Optional[SessionDB] = None,
        quiet_mode: bool = False,
        stream_callback: Optional[Callable] = None,
        tool_progress_callback: Optional[Callable] = None,
        status_callback: Optional[Callable] = None,
    ):
        cfg = get_config()

        self.model = model or cfg.model
        self.base_url = base_url or cfg.base_url
        self.api_key = api_key or cfg.resolve_api_key()
        self.provider = provider or cfg.provider
        self.api_mode = api_mode or cfg.api_mode
        self.max_iterations = max_iterations or cfg.max_iterations
        self.max_tokens = max_tokens or cfg.max_tokens
        self.quiet_mode = quiet_mode

        self.enabled_toolsets = enabled_toolsets or cfg.enabled_toolsets
        self.disabled_toolsets = disabled_toolsets or cfg.disabled_toolsets

        self.session_id = session_id or str(uuid.uuid4())
        self._session_db = session_db
        self._session_db_created = False
        self._parent_session_id = None

        # Callbacks
        self.stream_callback = stream_callback
        self.tool_progress_callback = tool_progress_callback
        self.status_callback = status_callback

        # Conversation state
        self._system_prompt = system_prompt
        self._cached_system_prompt: Optional[str] = None

        # Tool schemas (resolved once at init)
        self._resolve_tools()

        # Iteration tracking
        self._interrupt_requested = False
        self._api_call_count = 0

        # Token tracking
        self.session_total_tokens = 0
        self.session_input_tokens = 0
        self.session_output_tokens = 0

        logger.info(
            "AIAgent initialized: model=%s provider=%s toolsets=%s",
            self.model, self.provider, self.enabled_toolsets,
        )

    # ------------------------------------------------------------------
    # Tool resolution
    # ------------------------------------------------------------------

    def _resolve_tools(self):
        """Resolve tool schemas from enabled/disabled toolsets."""
        from dreamtalk.orchestration.agents.tools.toolsets import resolve_toolset, get_all_toolsets

        tool_names: set = set()
        if self.enabled_toolsets:
            for ts in self.enabled_toolsets:
                resolved = resolve_toolset(ts)
                tool_names.update(resolved)
        else:
            for ts in get_all_toolsets():
                tool_names.update(resolve_toolset(ts))

        if self.disabled_toolsets:
            for ts in self.disabled_toolsets:
                tool_names.difference_update(resolve_toolset(ts))

        self.tool_names = sorted(tool_names)
        self.tools = registry.get_definitions(tool_names)

    # ------------------------------------------------------------------
    # Session persistence
    # ------------------------------------------------------------------

    def _ensure_session_db(self):
        if self._session_db_created or self._session_db is None:
            return
        try:
            self._session_db.create_session(
                session_id=self.session_id,
                source="dreamtalk",
                model=self.model,
                system_prompt=self._cached_system_prompt or "",
            )
            self._session_db_created = True
        except Exception as e:
            logger.warning("Session DB create failed: %s", e)

    def _persist_session(self, messages: List[Dict]):
        if self._session_db is None:
            return
        try:
            self._ensure_session_db()
            self._session_db.save_messages(self.session_id, messages)
        except Exception as e:
            logger.warning("Session persist failed: %s", e)

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    def _build_system_prompt(self, system_message: Optional[str] = None) -> str:
        if system_message:
            return system_message
        if self._system_prompt:
            return self._system_prompt
        toolsets_str = ", ".join(self.enabled_toolsets or [])
        return DEFAULT_SYSTEM_PROMPT.format(toolsets=toolsets_str)

    # ------------------------------------------------------------------
    # API call
    # ------------------------------------------------------------------

    def _call_api(self, messages: List[Dict]) -> Dict[str, Any]:
        """Make an OpenAI-compatible chat completion API call."""
        from openai import OpenAI

        client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if self.tools:
            kwargs["tools"] = self.tools
        if self.max_tokens:
            kwargs["max_tokens"] = self.max_tokens

        response = client.chat.completions.create(**kwargs)
        return {
            "choices": [
                {
                    "message": {
                        "role": c.message.role,
                        "content": c.message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in (c.message.tool_calls or [])
                        ] if c.message.tool_calls else None,
                    },
                    "finish_reason": c.finish_reason,
                }
                for c in response.choices
            ],
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            } if response.usage else {},
        }

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    def _execute_tool(self, tool_call: Dict) -> Dict[str, Any]:
        """Execute a single tool call and return a tool result message."""
        name = tool_call["function"]["name"]
        try:
            raw_args = tool_call["function"]["arguments"]
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except json.JSONDecodeError as e:
            return {
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps({"error": f"Invalid JSON args: {e}"}),
            }

        if self.tool_progress_callback:
            self.tool_progress_callback(name, args)

        logger.debug("Tool call: %s args=%s", name, args)
        result = registry.dispatch(name, args, task_id=self.session_id)
        logger.debug("Tool result: %s -> %s chars", name, len(result))

        return {
            "role": "tool",
            "tool_call_id": tool_call["id"],
            "content": result,
        }

    # ------------------------------------------------------------------
    # Main conversation loop
    # ------------------------------------------------------------------

    def run_conversation(
        self,
        user_message: str,
        system_message: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Run a complete conversation turn with tool calling.

        Returns dict with keys:
            final_response (str): The assistant's final text.
            messages (list): Full message history for this turn.
            api_calls (int): Number of API calls made.
            completed (bool): Whether the loop reached a final response.
        """
        messages: List[Dict] = list(conversation_history or [])

        # System prompt
        if not self._cached_system_prompt:
            self._cached_system_prompt = self._build_system_prompt(system_message)

        # Message assembly: system + history + user
        api_messages = [{"role": "system", "content": self._cached_system_prompt}]
        api_messages.extend(messages)
        api_messages.append({"role": "user", "content": user_message})

        api_call_count = 0
        final_response = ""
        failed = False

        # Main loop
        while api_call_count < self.max_iterations:
            if self._interrupt_requested:
                final_response = final_response or "[Interrupted]"
                break

            api_call_count += 1

            try:
                response = self._call_api(api_messages)
            except Exception as e:
                logger.exception("API call failed on iteration %d", api_call_count)
                final_response = f"API call failed: {e}"
                failed = True
                break

            # Update token tracking
            usage = response.get("usage", {})
            self.session_total_tokens += usage.get("total_tokens", 0)
            self.session_input_tokens += usage.get("prompt_tokens", 0)
            self.session_output_tokens += usage.get("completion_tokens", 0)

            choice = response["choices"][0]
            msg = choice["message"]
            finish = choice.get("finish_reason", "stop")

            # Store assistant message
            assistant_msg = {"role": "assistant", "content": msg.get("content", "")}
            if msg.get("tool_calls"):
                assistant_msg["tool_calls"] = msg["tool_calls"]
            api_messages.append(assistant_msg)

            # Tool calls present → execute and continue
            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    tool_result_msg = self._execute_tool(tc)
                    api_messages.append(tool_result_msg)

                if self.quiet_mode:
                    logger.info(
                        "Iteration %d: %d tool call(s) executed",
                        api_call_count, len(msg["tool_calls"]),
                    )
                continue

            # No tool calls — this is the final response
            final_response = msg.get("content", "") or ""
            break

        # Persist to session store
        self._persist_session(api_messages)

        return {
            "final_response": final_response,
            "messages": api_messages,
            "api_calls": api_call_count,
            "completed": not failed and bool(final_response),
        }

    def chat(self, message: str) -> str:
        """Simple interface — returns just the final response string."""
        result = self.run_conversation(message)
        return result.get("final_response", "") or ""

    def interrupt(self):
        """Request interruption of the current conversation loop."""
        self._interrupt_requested = True
