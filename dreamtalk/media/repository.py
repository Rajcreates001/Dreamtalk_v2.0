import os
import shutil
import uuid
import hashlib
import json
import aiofiles
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from dreamtalk.media.models import MediaAsset, AssetMetadata, TwinMediaPaths, MediaCollection


MEDIA_ROOT = Path("dreamtalk/media")


class MediaRepository:
    """Central storage for every Digital Twin asset.

    Principle: Never mix assets. Each Digital Twin owns its own isolated folder.
    Never overwrite uploaded files. Store originals and processed versions separately.
    """

    def __init__(self):
        self._ensure_root()

    def _ensure_root(self):
        MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

    # ─── Path Resolution ───────────────────────────────────────────────────

    def get_twin_paths(self, twin_id: str, role: str = "normal_user") -> TwinMediaPaths:
        return TwinMediaPaths(twin_id=twin_id, role=role)

    def twin_dir_exists(self, twin_id: str, role: str = "normal_user") -> bool:
        paths = self.get_twin_paths(twin_id, role)
        return Path(paths.base_path).exists()

    # ─── Folder Creation ───────────────────────────────────────────────────

    def create_twin_folders(self, twin_id: str, role: str = "normal_user") -> TwinMediaPaths:
        paths = self.get_twin_paths(twin_id, role)
        for name, dir_path in paths.all_paths.items():
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        return paths

    def remove_twin_folders(self, twin_id: str, role: str = "normal_user"):
        paths = self.get_twin_paths(twin_id, role)
        base = Path(paths.base_path)
        if base.exists():
            shutil.rmtree(str(base))

    # ─── File Storage ──────────────────────────────────────────────────────

    async def store_file(
        self,
        twin_id: str,
        role: str,
        category: str,
        filename: str,
        content: bytes,
        metadata: Optional[dict] = None,
        version: int = 1,
    ) -> MediaAsset:
        paths = self.get_twin_paths(twin_id, role)
        sub_dir = category
        # If category doesn't exist in paths, use it directly under base
        dest_dir = Path(paths.sub_path(sub_dir))
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename to avoid overwrites
        stem, ext = os.path.splitext(filename)
        unique_name = f"{stem}_{uuid.uuid4().hex[:8]}{ext}"
        dest_path = dest_dir / unique_name

        # Write file
        async with aiofiles.open(str(dest_path), "wb") as f:
            await f.write(content)

        # Compute checksum
        checksum = hashlib.sha256(content).hexdigest()[:16]

        asset_meta = AssetMetadata(
            original_name=filename,
            mime_type=metadata.get("mime_type", "application/octet-stream") if metadata else "application/octet-stream",
            file_size=len(content),
            checksum=checksum,
            width=metadata.get("width") if metadata else None,
            height=metadata.get("height") if metadata else None,
            duration_seconds=metadata.get("duration") if metadata else None,
            processing_status="stored",
        )

        asset = MediaAsset(
            asset_id=uuid.uuid4().hex,
            twin_id=twin_id,
            category=role,
            sub_category=category,
            filename=unique_name,
            file_path=str(dest_path),
            metadata=asset_meta,
            is_original=True,
            version=version,
        )
        return asset

    async def store_processed(
        self,
        twin_id: str,
        role: str,
        category: str,
        filename: str,
        content: bytes,
        source_asset: MediaAsset,
        processing_step: str = "",
        metadata: Optional[dict] = None,
    ) -> MediaAsset:
        paths = self.get_twin_paths(twin_id, role)
        sub_dir = f"{category}/processed"
        dest_dir = Path(paths.sub_path(sub_dir))
        dest_dir.mkdir(parents=True, exist_ok=True)

        stem, ext = os.path.splitext(filename)
        step_tag = f"_{processing_step}" if processing_step else ""
        unique_name = f"{stem}{step_tag}_{uuid.uuid4().hex[:8]}{ext}"
        dest_path = dest_dir / unique_name

        async with aiofiles.open(str(dest_path), "wb") as f:
            await f.write(content)

        checksum = hashlib.sha256(content).hexdigest()[:16]

        meta = AssetMetadata(
            original_name=filename,
            mime_type=metadata.get("mime_type", "application/octet-stream") if metadata else "application/octet-stream",
            file_size=len(content),
            checksum=checksum,
            width=metadata.get("width") if metadata else None,
            height=metadata.get("height") if metadata else None,
            processing_status=f"processed_{processing_step}" if processing_step else "processed",
        )

        asset = MediaAsset(
            asset_id=uuid.uuid4().hex,
            twin_id=twin_id,
            category=role,
            sub_category=category,
            filename=unique_name,
            file_path=str(dest_path),
            metadata=meta,
            is_original=False,
            version=source_asset.version + 1,
        )
        return asset

    async def read_file(self, twin_id: str, role: str, category: str, filename: str) -> Optional[bytes]:
        paths = self.get_twin_paths(twin_id, role)
        file_path = Path(paths.sub_path(category, filename))
        if not file_path.exists():
            return None
        async with aiofiles.open(str(file_path), "rb") as f:
            return await f.read()

    def list_assets(self, twin_id: str, role: str, category: str) -> List[MediaAsset]:
        paths = self.get_twin_paths(twin_id, role)
        dir_path = Path(paths.sub_path(category))
        if not dir_path.exists():
            return []

        assets = []
        for fpath in dir_path.iterdir():
            if fpath.is_file():
                stat = fpath.stat()
                meta = AssetMetadata(
                    original_name=fpath.name,
                    mime_type=self._guess_mime(fpath.suffix),
                    file_size=stat.st_size,
                    processing_status="stored",
                )
                asset = MediaAsset(
                    asset_id=uuid.uuid4().hex,
                    twin_id=twin_id,
                    category=role,
                    sub_category=category,
                    filename=fpath.name,
                    file_path=str(fpath),
                    metadata=meta,
                )
                assets.append(asset)
        return sorted(assets, key=lambda a: a.filename)

    def get_collection(self, twin_id: str, role: str, category: str) -> MediaCollection:
        assets = self.list_assets(twin_id, role, category)
        total_size = sum(a.metadata.file_size for a in assets)
        return MediaCollection(
            twin_id=twin_id,
            category=role,
            sub_category=category,
            assets=assets,
            total_size=total_size,
            asset_count=len(assets),
        )

    # ─── Temp File Management ──────────────────────────────────────────────

    async def store_temp(self, twin_id: str, role: str, filename: str, content: bytes) -> MediaAsset:
        return await self.store_file(twin_id, role, "temp", filename, content)

    def clean_temp(self, twin_id: str, role: str, max_age_hours: int = 24):
        paths = self.get_twin_paths(twin_id, role)
        temp_dir = Path(paths.temp)
        if not temp_dir.exists():
            return
        now = datetime.utcnow().timestamp()
        for fpath in temp_dir.iterdir():
            if fpath.is_file():
                age_hours = (now - fpath.stat().st_mtime) / 3600
                if age_hours > max_age_hours:
                    fpath.unlink()

    # ─── Helpers ───────────────────────────────────────────────────────────

    def twin_storage_report(self, twin_id: str, role: str) -> dict:
        paths = self.get_twin_paths(twin_id, role)
        report = {"twin_id": twin_id, "role": role, "categories": {}}
        total_size = 0
        for name, dir_path in paths.all_paths.items():
            p = Path(dir_path)
            if p.exists():
                size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                count = len(list(p.rglob("*")))
                report["categories"][name] = {"path": dir_path, "file_count": count, "size_bytes": size}
                total_size += size
            else:
                report["categories"][name] = {"path": dir_path, "file_count": 0, "size_bytes": 0}
        report["total_size_bytes"] = total_size
        return report

    def _guess_mime(self, suffix: str) -> str:
        mapping = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
            ".gif": "image/gif", ".webp": "image/webp", ".mp4": "video/mp4",
            ".webm": "video/webm", ".wav": "audio/wav", ".mp3": "audio/mpeg",
            ".m4a": "audio/mp4", ".aac": "audio/aac", ".flac": "audio/flac",
            ".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain", ".csv": "text/csv", ".json": "application/json",
        }
        return mapping.get(suffix.lower(), "application/octet-stream")
