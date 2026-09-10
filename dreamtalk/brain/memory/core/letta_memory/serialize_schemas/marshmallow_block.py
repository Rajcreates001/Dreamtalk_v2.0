# Adapted from Letta (MemGPT) - Apache 2.0 License
from typing import Dict

from marshmallow import post_dump, pre_load

from dreamtalk.brain.memory.core.letta_memory.orm.block import Block
from dreamtalk.brain.memory.core.letta_memory.schemas.block import Block as PydanticBlock
from dreamtalk.brain.memory.core.letta_memory.serialize_schemas.marshmallow_base import BaseSchema


class SerializedBlockSchema(BaseSchema):
    """
    Marshmallow schema for serializing/deserializing Block objects.
    """

    __pydantic_model__ = PydanticBlock

    @post_dump
    def sanitize_ids(self, data: Dict, **kwargs) -> Dict:
        # delete id
        del data["id"]
        del data["_created_by_id"]
        del data["_last_updated_by_id"]

        return data

    @pre_load
    def regenerate_ids(self, data: Dict, **kwargs) -> Dict:
        if self.Meta.model:
            data["id"] = self.generate_id()
            data["_created_by_id"] = self.actor.id
            data["_last_updated_by_id"] = self.actor.id

        return data

    class Meta(BaseSchema.Meta):
        model = Block
        exclude = (*BaseSchema.Meta.exclude, "agents", "identities", "is_deleted", "groups", "organization")
