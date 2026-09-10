# Dreamtalk - Orchestration Module
# Extracted from OpenAvatarChat (Apache 2.0)

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolResult:
    success: bool = True
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_content_str(self) -> str:
        if not self.success:
            return json.dumps({"error": self.error or "unknown error"}, ensure_ascii=False)
        return json.dumps(self.data, ensure_ascii=False, default=str)


class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict:
        ...

    @abstractmethod
    def execute(self, args: Dict[str, Any]) -> ToolResult:
        ...

    def get_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._schemas_cache: Optional[List[dict]] = None

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool
        self._schemas_cache = None

    def unregister(self, name: str) -> bool:
        if name in self._tools:
            del self._tools[name]
            self._schemas_cache = None
            return True
        return False

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def has_tools(self) -> bool:
        return len(self._tools) > 0

    @property
    def tool_names(self) -> List[str]:
        return list(self._tools.keys())

    def get_schemas(self) -> List[dict]:
        if self._schemas_cache is None:
            self._schemas_cache = [t.get_openai_schema() for t in self._tools.values()]
        return self._schemas_cache

    def execute(self, name: str, args: Dict[str, Any]) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(success=False, error=f"Unknown tool: {name}")
        try:
            return tool.execute(args)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class GetCurrentTimeTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_current_time"

    @property
    def description(self) -> str:
        return "获取当前日期和时间。只要用户在问现在几点、今天几号，就必须先调用此工具。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "timezone": {"type": "string", "description": "时区名称，如 'Asia/Shanghai'"},
            },
            "required": [],
        }

    def execute(self, args: Dict[str, Any]) -> ToolResult:
        from datetime import datetime
        now = datetime.now()
        weekday_cn = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        return ToolResult(success=True, data={
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "weekday": weekday_cn[now.weekday()],
        })


class GetSystemInfoTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_system_info"

    @property
    def description(self) -> str:
        return "获取当前系统基本信息（操作系统、主机名等）。"

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    def execute(self, args: Dict[str, Any]) -> ToolResult:
        import platform
        return ToolResult(success=True, data={
            "os": platform.system(),
            "os_version": platform.version(),
            "hostname": platform.node(),
            "python_version": platform.python_version(),
        })
