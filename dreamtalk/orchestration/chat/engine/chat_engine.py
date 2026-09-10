# Dreamtalk - Orchestration Module
# Extracted from OpenAvatarChat (Apache 2.0)

import uuid
from dataclasses import dataclass
from typing import Optional, Dict

from dreamtalk.orchestration.chat.engine.config import ChatEngineConfigModel
from dreamtalk.orchestration.chat.engine.core import HandlerManager, LogicManager
from dreamtalk.orchestration.chat.engine.session import (
    ChatSession,
    SessionContext,
    SessionInfoData,
    HandlerEnv,
)


@dataclass
class EngineStates:
    inited: bool = False


class ChatEngine:
    def __init__(self):
        self.engine_config: Optional[ChatEngineConfigModel] = None
        self.handler_manager = HandlerManager(self)
        self.logic_manager = LogicManager(self)
        self.states = EngineStates()
        self.sessions: Dict[str, ChatSession] = {}

    def initialize(self, engine_config: ChatEngineConfigModel, app=None, ui=None, parent_block=None):
        if self.states.inited:
            return
        self.engine_config = engine_config
        self.handler_manager.initialize(engine_config)
        self.logic_manager.initialize(engine_config)
        self.handler_manager.load_handlers(engine_config, app, ui, parent_block)
        self.logic_manager.load_logics(engine_config)
        self.states.inited = True

    def _create_session(self, session_info: SessionInfoData):
        if not session_info.session_id:
            session_info.session_id = str(uuid.uuid4())
        if session_info.session_id in self.sessions:
            raise RuntimeError(f"Session {session_info.session_id} already exists")
        session = ChatSession(SessionContext(session_info), self.engine_config)
        self.sessions[session_info.session_id] = session
        return session

    def create_client_session(self, session_info: SessionInfoData, client_handler) -> tuple:
        if session_info.session_id in self.sessions:
            raise RuntimeError(f"Session {session_info.session_id} already exists")
        session = self._create_session(session_info)
        return session, None

    def stop_session(self, session_id: str):
        session = self.sessions.pop(session_id, None)
        if session:
            session.stop()

    def shutdown(self):
        self.logic_manager.destroy()
        self.handler_manager.destroy()
        self.states.inited = False
