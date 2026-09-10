# Dreamtalk - Orchestration Module
# Extracted from OpenAvatarChat (Apache 2.0)

import json
import os
import threading
import time
from typing import Dict, List, Optional, cast

from pydantic import BaseModel, Field

from dreamtalk.orchestration.chat.handlers.base import (
    HandlerBase,
    HandlerBaseInfo,
    HandlerDetail,
    HandlerDataInfo,
)
from dreamtalk.orchestration.chat.engine.config import (
    ChatDataType,
    ChatEngineConfigModel,
    HandlerBaseConfigModel,
    ChatSignalType,
    ChatStreamConfig,
)
from dreamtalk.orchestration.chat.agent.tools import ToolRegistry, GetCurrentTimeTool, GetSystemInfoTool
from dreamtalk.orchestration.chat.agent.memory import SessionMemoryManager, MemoryConfig


class ToolUseConfig(BaseModel):
    enabled: bool = Field(default=True)
    max_tool_rounds: int = Field(default=5)
    register_demo_tools: bool = Field(default=True)


class ChatAgentConfig(HandlerBaseConfigModel):
    llm_model: str = Field(default="qwen-plus")
    api_key: Optional[str] = Field(default=None)
    api_url: Optional[str] = Field(default=None)
    enable_thinking: bool = Field(default=False)
    tool_use: ToolUseConfig = Field(default_factory=ToolUseConfig)
    max_dialogue_turns: int = Field(default=20)
    persona_snapshot: str = Field(default="性格：友善亲切，像朋友一样交流。")

    def to_memory_config(self) -> MemoryConfig:
        return MemoryConfig(max_dialogue_turns=self.max_dialogue_turns)


DEFAULT_STABLE_CORE = """\
你是一个具有视觉能力的实时数字人助手，正在通过摄像头与用户进行面对面对话。
- 用口语化的自然语言回答，语气亲切
- 保持简短（通常 2-3 句），除非用户明确要求详细说明
- 不要输出 Markdown 格式、代码块或列表符号
- 不要自称"AI"或"语言模型"，你就是这个数字人角色本身
"""


class PromptInput:
    def __init__(self, trigger_type: str = "user", response_hint: str = "",
                 persona_snapshot: str = "", environment_state: str = "",
                 perception_events: Optional[List[Dict]] = None,
                 dialogue_history: Optional[List[Dict]] = None):
        self.trigger_type = trigger_type
        self.response_hint = response_hint
        self.persona_snapshot = persona_snapshot
        self.environment_state = environment_state
        self.perception_events = perception_events or []
        self.dialogue_history = dialogue_history or []


class CompiledPrompt:
    def __init__(self, system_message: str = "", messages: Optional[List[Dict[str, str]]] = None):
        self.system_message = system_message
        self.messages = messages or []

    @property
    def full_messages(self) -> List[Dict[str, str]]:
        result = []
        if self.system_message:
            result.append({"role": "system", "content": self.system_message})
        result.extend(self.messages)
        return result


class PromptCompiler:
    def __init__(self, stable_core: str = DEFAULT_STABLE_CORE, persona_snapshot: str = ""):
        self.stable_core = stable_core
        self._persona_snapshot = persona_snapshot

    def compile(self, pi: PromptInput) -> CompiledPrompt:
        system_parts = [self.stable_core]
        snapshot = pi.persona_snapshot or self._persona_snapshot
        if snapshot:
            system_parts.append(snapshot)
        if pi.environment_state:
            system_parts.append(f"<environment-state>\n{pi.environment_state}\n</environment-state>")
        messages = list(pi.dialogue_history)
        for event in pi.perception_events:
            content = event.get("content", "")
            if content:
                messages.append({"role": "user", "content": f'<observation source="camera" event="true">\n{content}\n</observation>'})
        if pi.trigger_type == "user":
            messages.append({"role": "user", "content": pi.response_hint or "(user spoke)"})
        elif pi.response_hint:
            messages.append({"role": "user", "content": f'<observation source="system" event="true">\n{pi.response_hint}\n</observation>'})
        return CompiledPrompt(system_message="\n\n".join(system_parts), messages=messages)


class ChatAgentContext:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.config: Optional[ChatAgentConfig] = None
        self.llm_client = None
        self.memory: Optional[SessionMemoryManager] = None
        self.compiler: Optional[PromptCompiler] = None
        self.tool_registry: Optional[ToolRegistry] = None
        self.input_buffer: str = ""
        self.is_generating: bool = False
        self.last_interaction_time: float = 0.0
        self._generate_lock: threading.Lock = threading.Lock()
        self.active_stream_keys: set = set()
        self.signal_emitter = None
        self.data_submitter = None
        self.session_history = None
        self.stream_manager = None


class ChatAgentHandler(HandlerBase):
    def __init__(self):
        super().__init__()

    def get_handler_info(self) -> HandlerBaseInfo:
        return HandlerBaseInfo(config_model=ChatAgentConfig)

    def load(self, engine_config: ChatEngineConfigModel, handler_config: Optional[HandlerBaseConfigModel] = None):
        pass

    def create_context(self, session_context, handler_config=None) -> ChatAgentContext:
        context = ChatAgentContext(session_context.session_info.session_id)
        context.config = handler_config if isinstance(handler_config, ChatAgentConfig) else ChatAgentConfig()
        api_key = context.config.api_key or os.getenv("DASHSCOPE_API_KEY")
        if context.config.api_url:
            try:
                from openai import OpenAI
                context.llm_client = OpenAI(api_key=api_key, base_url=context.config.api_url)
            except Exception:
                pass
        context.memory = SessionMemoryManager(config=context.config.to_memory_config())
        context.compiler = PromptCompiler(persona_snapshot=context.config.persona_snapshot)
        context.tool_registry = self._build_tool_registry(context.config)
        return context

    def start_context(self, session_context, handler_context):
        pass

    def get_handler_detail(self, session_context, context) -> HandlerDetail:
        return HandlerDetail(
            inputs={ChatDataType.HUMAN_TEXT: HandlerDataInfo(type=ChatDataType.HUMAN_TEXT)},
            outputs={ChatDataType.AVATAR_TEXT: HandlerDataInfo(type=ChatDataType.AVATAR_TEXT)},
        )

    def handle(self, context, inputs, output_definitions):
        c = cast(ChatAgentContext, context)
        if inputs.type == ChatDataType.HUMAN_TEXT:
            self._handle_human_text(c, inputs, output_definitions)

    def _handle_human_text(self, context: ChatAgentContext, inputs, output_definitions):
        text = inputs.data.get_main_data() if hasattr(inputs, 'data') and inputs.data else ""
        if isinstance(text, str):
            context.input_buffer += text
        if not getattr(inputs, 'is_last_data', True):
            return
        full_text = context.input_buffer.strip()
        context.input_buffer = ""
        if not full_text or not context.llm_client:
            return
        with context._generate_lock:
            context.is_generating = True
            context.last_interaction_time = time.time()
            if context.memory:
                context.memory.record_user_input(full_text)
            pi = PromptInput(trigger_type="user", response_hint=full_text,
                             dialogue_history=context.memory.get_dialogue_for_llm(10) if context.memory else [])
            compiled = context.compiler.compile(pi)
            messages = compiled.full_messages
            kwargs = dict(model=context.config.llm_model, messages=messages, stream=True)
            try:
                response = context.llm_client.chat.completions.create(**kwargs)
                full_response = ""
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                if full_response and context.memory:
                    context.memory.record_assistant_response(full_response)
            except Exception:
                pass
            context.is_generating = False

    def destroy_context(self, context):
        c = cast(ChatAgentContext, context)
        if c.memory:
            c.memory.destroy()

    @staticmethod
    def _build_tool_registry(config: ChatAgentConfig) -> ToolRegistry:
        registry = ToolRegistry()
        if config.tool_use.enabled and config.tool_use.register_demo_tools:
            registry.register(GetCurrentTimeTool())
            registry.register(GetSystemInfoTool())
        return registry
