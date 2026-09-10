# Adapted from Letta (MemGPT) - Apache 2.0 License
from pydantic import BaseModel


class Health(BaseModel):
    """
    Health check response body
    """

    version: str
    status: str
