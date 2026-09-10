# Adapted from Letta (MemGPT) - Apache 2.0 License
from pydantic import Field

from dreamtalk.brain.memory.core.letta_memory.schemas.letta_base import OrmMetadataBase


class Prompt(OrmMetadataBase):
    id: str = Field(..., description="The id of the agent. Assigned by the database.")
    project_id: str | None = Field(None, description="The associated project id.")
    prompt: str = Field(..., description="The string contents of the prompt.")
