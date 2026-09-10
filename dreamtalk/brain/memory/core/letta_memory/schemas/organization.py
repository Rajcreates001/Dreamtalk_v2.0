# Adapted from Letta (MemGPT) - Apache 2.0 License
from datetime import datetime
from typing import Optional

from pydantic import Field

from dreamtalk.brain.memory.core.letta_memory.helpers.datetime_helpers import get_utc_time
from dreamtalk.brain.memory.core.letta_memory.schemas.enums import PrimitiveType
from dreamtalk.brain.memory.core.letta_memory.schemas.letta_base import LettaBase
from dreamtalk.brain.memory.core.letta_memory.utils import create_random_username


class OrganizationBase(LettaBase):
    __id_prefix__ = PrimitiveType.ORGANIZATION.value


class Organization(OrganizationBase):
    id: str = OrganizationBase.generate_id_field()
    name: str = Field(create_random_username(), description="The name of the organization.", json_schema_extra={"default": "SincereYogurt"})
    created_at: Optional[datetime] = Field(default_factory=get_utc_time, description="The creation date of the organization.")
    privileged_tools: bool = Field(False, description="Whether the organization has access to privileged tools.")


class OrganizationCreate(OrganizationBase):
    name: Optional[str] = Field(None, description="The name of the organization.")
    privileged_tools: Optional[bool] = Field(False, description="Whether the organization has access to privileged tools.")


class OrganizationUpdate(OrganizationBase):
    name: Optional[str] = Field(None, description="The name of the organization.")
    privileged_tools: Optional[bool] = Field(False, description="Whether the organization has access to privileged tools.")
