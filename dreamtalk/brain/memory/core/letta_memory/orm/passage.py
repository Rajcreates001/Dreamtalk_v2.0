# Adapted from Letta (MemGPT) - Apache 2.0 License
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import JSON, Column, Index
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from dreamtalk.brain.memory.core.letta_memory.config import LettaConfig
from dreamtalk.brain.memory.core.letta_memory.constants import MAX_EMBEDDING_DIM
from dreamtalk.brain.memory.core.letta_memory.orm.custom_columns import CommonVector, EmbeddingConfigColumn
from dreamtalk.brain.memory.core.letta_memory.orm.mixins import ArchiveMixin, FileMixin, OrganizationMixin, SourceMixin
from dreamtalk.brain.memory.core.letta_memory.orm.sqlalchemy_base import SqlalchemyBase
from dreamtalk.brain.memory.core.letta_memory.schemas.passage import Passage as PydanticPassage
from dreamtalk.brain.memory.core.letta_memory.settings import DatabaseChoice, settings

config = LettaConfig()

if TYPE_CHECKING:
    from dreamtalk.brain.memory.core.letta_memory.orm.organization import Organization
    from dreamtalk.brain.memory.core.letta_memory.orm.passage_tag import PassageTag


class BasePassage(SqlalchemyBase, OrganizationMixin):
    """Base class for all passage types with common fields"""

    __abstract__ = True
    __pydantic_model__ = PydanticPassage

    id: Mapped[str] = mapped_column(primary_key=True, doc="Unique passage identifier")
    text: Mapped[str] = mapped_column(doc="Passage text content")
    embedding_config: Mapped[Optional[dict]] = mapped_column(EmbeddingConfigColumn, nullable=True, doc="Embedding configuration")
    metadata_: Mapped[dict] = mapped_column(JSON, doc="Additional metadata")
    # dual storage: json column for fast retrieval, junction table for efficient queries
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, doc="Tags associated with this passage")

    # Vector embedding field based on database type - nullable for text-only search
    if settings.database_engine is DatabaseChoice.POSTGRES:
        from pgvector.sqlalchemy import Vector

        embedding = mapped_column(Vector(MAX_EMBEDDING_DIM), nullable=True)
    else:
        embedding = Column(CommonVector, nullable=True)

    @declared_attr
    def organization(cls) -> Mapped["Organization"]:
        """Relationship to organization - use lazy='raise' to prevent accidental blocking in async contexts"""
        return relationship("Organization", back_populates="passages", lazy="raise")


class SourcePassage(BasePassage, FileMixin, SourceMixin):
    """Passages derived from external files/sources"""

    __tablename__ = "source_passages"

    file_name: Mapped[str] = mapped_column(doc="The name of the file that this passage was derived from")

    @declared_attr
    def organization(cls) -> Mapped["Organization"]:
        return relationship("Organization", back_populates="source_passages", lazy="raise")

    @declared_attr
    def __table_args__(cls):
        # TODO (cliandy): investigate if this is necessary, may be for SQLite compatability or do we need to add as well?
        if settings.database_engine is DatabaseChoice.POSTGRES:
            return (
                Index("source_passages_org_idx", "organization_id"),
                Index("source_passages_created_at_id_idx", "created_at", "id"),
                Index("source_passages_file_id_idx", "file_id"),
                {"extend_existing": True},
            )
        return (
            Index("source_passages_created_at_id_idx", "created_at", "id"),
            Index("source_passages_file_id_idx", "file_id"),
            {"extend_existing": True},
        )


class ArchivalPassage(BasePassage, ArchiveMixin):
    """Passages stored in archives as archival memories"""

    __tablename__ = "archival_passages"

    # junction table for efficient tag queries (complements json column above)
    passage_tags: Mapped[List["PassageTag"]] = relationship(
        "PassageTag", back_populates="passage", cascade="all, delete-orphan", lazy="noload"
    )

    @declared_attr
    def organization(cls) -> Mapped["Organization"]:
        return relationship("Organization", back_populates="archival_passages", lazy="raise")

    @declared_attr
    def __table_args__(cls):
        if settings.database_engine is DatabaseChoice.POSTGRES:
            return (
                Index("ix_archival_passages_org_archive", "organization_id", "archive_id"),
                Index("archival_passages_created_at_id_idx", "created_at", "id"),
                Index("ix_archival_passages_archive_id", "archive_id"),
                {"extend_existing": True},
            )
        return (
            Index("ix_archival_passages_org_archive", "organization_id", "archive_id"),
            Index("archival_passages_created_at_id_idx", "created_at", "id"),
            Index("ix_archival_passages_archive_id", "archive_id"),
            {"extend_existing": True},
        )
