# Dreamtalk - 3D Avatar Module
# Extracted from MHR
# Copyright (c) Meta Platforms, Inc. and affiliates.
# Licensed under Apache License, Version 2.0

from pathlib import Path
from typing import Dict, Optional

from dreamtalk.avatar.core.body.mhr.config import LOD


class LODManager:
    """Manages LOD (Level of Detail) levels 0-6 for MHR body model.

    Higher LOD = more vertices, higher quality, more computation.
    LOD 0 is the lowest resolution, LOD 6 is the highest.
    """

    LOD_VERTEX_COUNTS: Dict[LOD, int] = {
        0: 1000,
        1: 5000,
        2: 10000,
        3: 20000,
        4: 40000,
        5: 70000,
        6: 100000,
    }

    LOD_DESCRIPTIONS: Dict[LOD, str] = {
        0: "Lowest resolution, fastest",
        1: "Low resolution for preview",
        2: "Medium-low",
        3: "Medium (default balance)",
        4: "Medium-high quality",
        5: "High quality",
        6: "Highest quality, slowest",
    }

    def __init__(self, asset_folder: Path):
        self.asset_folder = asset_folder
        self._available_lods: Dict[LOD, bool] = {}
        self._scan_available_lods()

    def _scan_available_lods(self) -> None:
        """Check which LOD FBX files are available on disk."""
        for lod in range(7):
            fbx_path = self.asset_folder / f"lod{lod}.fbx"
            self._available_lods[LOD(lod)] = fbx_path.exists()

    def get_available_lods(self) -> Dict[LOD, bool]:
        """Get map of LOD level to availability."""
        return dict(self._available_lods)

    def get_highest_available(self) -> Optional[LOD]:
        """Get the highest available LOD level."""
        for lod in reversed(range(7)):
            if self._available_lods.get(LOD(lod), False):
                return LOD(lod)
        return None

    def get_lowest_available(self) -> Optional[LOD]:
        """Get the lowest available LOD level."""
        for lod in range(7):
            if self._available_lods.get(LOD(lod), False):
                return LOD(lod)
        return None

    def get_recommended_lod(self, performance_target: str = "balanced") -> LOD:
        """Get recommended LOD based on performance target.

        Args:
            performance_target: "fast", "balanced", or "quality"
        Returns:
            Recommended LOD level
        """
        mapping = {"fast": 0, "balanced": 3, "quality": 6}
        target = mapping.get(performance_target, 3)

        # Find closest available LOD
        for lod in [target, target - 1, target + 1, target - 2, target + 2]:
            if 0 <= lod <= 6 and self._available_lods.get(LOD(lod), False):
                return LOD(lod)

        return self.get_lowest_available() or LOD(1)

    def get_fbx_path(self, lod: LOD) -> str:
        """Get FBX path for a given LOD level."""
        return str(self.asset_folder / f"lod{lod}.fbx")

    def get_blendshapes_path(self, lod: LOD) -> str:
        """Get corrective blendshapes path for a given LOD."""
        return str(self.asset_folder / f"corrective_blendshapes_lod{lod}.npz")

    @staticmethod
    def get_vertex_count_estimate(lod: LOD) -> int:
        """Get approximate vertex count for a given LOD."""
        return LODManager.LOD_VERTEX_COUNTS.get(lod, 5000)

    @staticmethod
    def get_description(lod: LOD) -> str:
        """Get human-readable description of a LOD level."""
        return LODManager.LOD_DESCRIPTIONS.get(lod, "Unknown")
