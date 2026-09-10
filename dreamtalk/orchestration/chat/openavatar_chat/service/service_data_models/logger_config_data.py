# Adapted from OpenAvatarChat (Apache 2.0)

from pydantic import BaseModel, Field


class LoggerConfigData(BaseModel):
    log_level: str = Field(default="INFO")
