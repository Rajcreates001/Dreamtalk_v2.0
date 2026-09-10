# Adapted from Letta (MemGPT) - Apache 2.0 License
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from dreamtalk.brain.memory.core.letta_memory.orm.base import Base


class IdentitiesBlocks(Base):
    """Identities may have one or many blocks associated with them."""

    __tablename__ = "identities_blocks"

    identity_id: Mapped[str] = mapped_column(String, ForeignKey("identities.id", ondelete="CASCADE"), primary_key=True)
    block_id: Mapped[str] = mapped_column(String, ForeignKey("block.id", ondelete="CASCADE"), primary_key=True)
