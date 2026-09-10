# Adapted from Letta (MemGPT) - Apache 2.0 License
from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from dreamtalk.brain.memory.core.letta_memory.orm.base import Base


class SourcesAgents(Base):
    """Agents can have zero to many sources"""

    __tablename__ = "sources_agents"
    __table_args__ = (Index("ix_sources_agents_source_id", "source_id"),)

    agent_id: Mapped[String] = mapped_column(String, ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True)
    source_id: Mapped[String] = mapped_column(String, ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True)
