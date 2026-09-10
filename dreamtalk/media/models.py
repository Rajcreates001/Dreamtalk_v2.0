from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import uuid


@dataclass
class AssetMetadata:
    original_name: str
    mime_type: str
    file_size: int
    checksum: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[float] = None
    processing_status: str = "raw"
    processing_log: list = field(default_factory=list)


@dataclass
class MediaAsset:
    asset_id: str
    twin_id: str
    category: str
    sub_category: str
    filename: str
    file_path: str
    metadata: AssetMetadata
    is_original: bool = True
    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class MediaCollection:
    twin_id: str
    category: str
    sub_category: str
    assets: list = field(default_factory=list)
    total_size: int = 0
    asset_count: int = 0


@dataclass
class TwinMediaPaths:
    twin_id: str
    role: str
    base_path: str = ""

    appearance: str = ""
    voice: str = ""
    memory: str = ""
    personality: str = ""
    knowledge: str = ""
    generated: str = ""
    temp: str = ""

    # Role-specific
    relationship: str = ""
    conversation: str = ""
    analytics: str = ""
    appointments: str = ""
    reports: str = ""
    transcripts: str = ""
    meetings: str = ""

    def __post_init__(self):
        self.base_path = f"dreamtalk/media/{self.role}/{self.twin_id}"
        self.appearance = f"{self.base_path}/appearance"
        self.voice = f"{self.base_path}/voice"
        self.memory = f"{self.base_path}/memory"
        self.personality = f"{self.base_path}/personality"
        self.knowledge = f"{self.base_path}/knowledge"
        self.generated = f"{self.base_path}/generated"
        self.temp = f"{self.base_path}/temp"

        if self.role == "normal_user":
            self.relationship = f"{self.base_path}/relationship"
            self.conversation = f"{self.base_path}/conversation"
            self.analytics = f"{self.base_path}/analytics"
        elif self.role == "healthcare":
            self.appointments = f"{self.base_path}/appointments"
            self.reports = f"{self.base_path}/reports"
            self.transcripts = f"{self.base_path}/transcripts"
        elif self.role == "business":
            self.meetings = f"{self.base_path}/meetings"
            self.reports = f"{self.base_path}/reports"
            self.transcripts = f"{self.base_path}/transcripts"

    @property
    def all_paths(self) -> dict:
        paths = {
            "appearance": self.appearance,
            "voice": self.voice,
            "memory": self.memory,
            "personality": self.personality,
            "knowledge": self.knowledge,
            "generated": self.generated,
            "temp": self.temp,
        }
        if self.relationship:
            paths["relationship"] = self.relationship
        if self.conversation:
            paths["conversation"] = self.conversation
        if self.analytics:
            paths["analytics"] = self.analytics
        if self.appointments:
            paths["appointments"] = self.appointments
        if self.reports:
            paths["reports"] = self.reports
        if self.transcripts:
            paths["transcripts"] = self.transcripts
        if self.meetings:
            paths["meetings"] = self.meetings
        return paths

    def sub_path(self, sub_dir: str, filename: str = "") -> str:
        base = getattr(self, sub_dir, None) or f"{self.base_path}/{sub_dir}"
        return f"{base}/{filename}" if filename else base
