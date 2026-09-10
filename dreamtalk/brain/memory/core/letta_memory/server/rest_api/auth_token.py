# Adapted from Letta (MemGPT) - Apache 2.0 License
import uuid

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from dreamtalk.brain.memory.core.letta_memory.server.server import SyncServer

security = HTTPBearer()


def get_current_user(server: SyncServer, password: str, auth: HTTPAuthorizationCredentials = Depends(security)) -> uuid.UUID:
    try:
        api_key_or_password = auth.credentials
        if api_key_or_password == password:
            # user is admin so we just return the default uuid
            return server.authenticate_user()
        user_id = server.api_key_to_user(api_key=api_key_or_password)
        return user_id
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"Authentication error: {e}")
