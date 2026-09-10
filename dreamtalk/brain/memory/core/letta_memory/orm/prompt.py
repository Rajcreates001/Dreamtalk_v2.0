# Adapted from Letta (MemGPT) - Apache 2.0 License
from sqlalchemy.orm import Mapped, mapped_column

from dreamtalk.brain.memory.core.letta_memory.orm.mixins import ProjectMixin
from dreamtalk.brain.memory.core.letta_memory.orm.sqlalchemy_base import SqlalchemyBase
from dreamtalk.brain.memory.core.letta_memory.schemas.prompt import Prompt as PydanticPrompt


class Prompt(SqlalchemyBase, ProjectMixin):
    __pydantic_model__ = PydanticPrompt
    __tablename__ = "prompts"

    id: Mapped[str] = mapped_column(primary_key=True, doc="Unique passage identifier")
    prompt: Mapped[str] = mapped_column(doc="The string contents of the prompt.")
