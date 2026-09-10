# Dreamtalk - Orchestration Module
# Extracted from OpenAvatarChat (Apache 2.0)

"""
Persona integration — bridge between OC (OpenClaw) and OAC persona system.
Manages L2 persona snapshot refresh via MCP with local YAML fallback.
"""

import time


class PersonaSnapshotManager:
    def __init__(
        self,
        refresh_interval: float = 600.0,
        local_default: str = "",
        mcp_client=None,
    ):
        self._refresh_interval = refresh_interval
        self._local_default = local_default
        self._mcp_client = mcp_client
        self._cached_snapshot: str = ""
        self._last_refresh: float = 0.0

    def set_mcp_client(self, mcp_client):
        self._mcp_client = mcp_client

    def get_snapshot(self) -> str:
        now = time.time()
        if (now - self._last_refresh) >= self._refresh_interval or not self._cached_snapshot:
            self._refresh()
        return self._cached_snapshot or self._local_default

    def force_refresh(self) -> str:
        self._refresh()
        return self._cached_snapshot or self._local_default

    def _refresh(self):
        self._last_refresh = time.time()
        if not self._mcp_client or not getattr(self._mcp_client, 'is_available', False):
            return
        try:
            result = self._mcp_client.call_tool_sync("get_agent_profile", {}, timeout=10.0)
            if isinstance(result, dict):
                text = result.get("result", "") or ""
                if isinstance(text, str) and text.strip():
                    self._cached_snapshot = text.strip()
        except Exception:
            pass
