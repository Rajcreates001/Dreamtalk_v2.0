# Dreamtalk - Avatar Module
# Migrated from Dreamtalk-Avatar-Module

try:
    from dreamtalk.avatar.core.pipeline import settings as _settings
    settings = _settings
except Exception:
    settings = None

try:
    from dreamtalk.avatar.services.avatar_service import AvatarService as _AvatarService
    AvatarService = _AvatarService
except Exception:
    AvatarService = None

try:
    from dreamtalk.avatar.integrations.did_api import DIDService as _DIDService
    DIDService = _DIDService
except Exception:
    DIDService = None

try:
    from dreamtalk.avatar.api.avatar_router import router as _router
    router = _router
except Exception:
    router = None

__all__ = [
    "settings",
    "AvatarService",
    "DIDService",
    "router",
]
