# Dreamtalk - Cognition Module
# Extracted from Aura (https://github.com/anomalyco/aura)
# License: MIT
#
# Contrastive Activation Addition (CAA) - steering vector control

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger("Dreamtalk.CAA")


class CollapseSeverity(Enum):
    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


@dataclass
class CollapseSignal:
    severity: CollapseSeverity = CollapseSeverity.NONE
    repetition_ratio: float = 0.0
    entropy_drop: float = 0.0
    score: float = 0.0
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity.value,
            "repetition_ratio": self.repetition_ratio,
            "entropy_drop": self.entropy_drop,
            "score": self.score,
            "detail": self.detail,
        }


@dataclass
class AlphaState:
    current: float = 5.0
    base: float = 5.0
    min_val: float = 1.0
    max_val: float = 20.0

    def to_dict(self) -> dict[str, float]:
        return {
            "current": self.current,
            "base": self.base,
            "min": self.min_val,
            "max": self.max_val,
        }


@dataclass
class VectorProvenance:
    source: str = "bootstrap"
    layer: int = 0
    key: str = ""
    extracted_from: str = ""
    created_at: float = 0.0


@dataclass
class RegisteredVector:
    vector: np.ndarray
    provenance: VectorProvenance = field(default_factory=VectorProvenance)


@dataclass
class VectorQualityReport:
    mean_magnitude: float = 0.0
    consistency: float = 0.0
    n_vectors: int = 0
    is_valid: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "mean_magnitude": self.mean_magnitude,
            "consistency": self.consistency,
            "n_vectors": self.n_vectors,
            "is_valid": self.is_valid,
        }


class ReadinessLevel(Enum):
    BOOTSTRAP = "bootstrap"
    PRODUCTION = "production"


class ReadinessGate:
    def __init__(
        self,
        vectors_dir: str | Path = "vectors",
        behavioral_results_path: str | Path | None = None,
    ):
        self.vectors_dir = Path(vectors_dir)
        self.behavioral_results_path = (
            Path(behavioral_results_path)
            if behavioral_results_path
            else None
        )

    def evaluate(
        self,
        registry_status: dict[str, Any],
        model_path: str = "",
    ) -> dict[str, Any]:
        return {
            "level": "bootstrap",
            "detail": "gate_check",
            "coverage_ratio": registry_status.get("coverage", 0.0),
        }


class AlphaController:
    def __init__(self, base_alpha: float = 5.0):
        self.state = AlphaState(base=base_alpha, current=base_alpha)

    def update(
        self,
        readiness_level: str = "bootstrap",
        exact_match_ratio: float = 0.0,
        extracted_ratio: float = 0.0,
        collapse_signal: CollapseSignal | None = None,
        generation_health: float | None = None,
        cross_entropy: float | None = None,
    ):
        if collapse_signal and collapse_signal.score > 0.5:
            self.state.current = max(
                self.state.min_val, self.state.current - 2.0
            )
        elif readiness_level == "production" and extracted_ratio > 0.5:
            self.state.current = min(
                self.state.max_val, self.state.current + 0.5
            )

    def get_alpha(self) -> float:
        return self.state.current


class ModeCollapseDetector:
    def __init__(self):
        self._last_signal = CollapseSignal()

    def observe(
        self,
        text: str,
    ) -> CollapseSignal:
        if not text:
            return CollapseSignal()
        words = text.split()
        if len(words) < 5:
            return CollapseSignal()
        unique_ratio = len(set(words)) / max(len(words), 1)
        if unique_ratio < 0.3:
            return CollapseSignal(
                severity=CollapseSeverity.MODERATE,
                repetition_ratio=1.0 - unique_ratio,
                score=1.0 - unique_ratio,
                detail=f"Repetition detected: {unique_ratio:.0%} unique",
            )
        return CollapseSignal(
            severity=CollapseSeverity.NONE,
            repetition_ratio=1.0 - unique_ratio,
            score=0.0,
        )

    def status(self) -> dict[str, Any]:
        return {"last_signal": self._last_signal.to_dict()}


class VectorRegistry:
    def __init__(self):
        self._vectors: dict[int, dict[str, RegisteredVector]] = {}

    def register(
        self,
        layer: int,
        key: str,
        vector: np.ndarray,
        source: str = "bootstrap",
    ):
        if layer not in self._vectors:
            self._vectors[layer] = {}
        self._vectors[layer][key] = RegisteredVector(
            vector=vector.copy(),
            provenance=VectorProvenance(
                source=source, layer=layer, key=key
            ),
        )

    def get(
        self, layer: int, key: str
    ) -> RegisteredVector | None:
        return self._vectors.get(layer, {}).get(key)

    def layers(self) -> dict[int, dict[str, RegisteredVector]]:
        return dict(self._vectors)

    def status(
        self,
        expected_layers: list[int] | None = None,
        expected_keys: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "n_layers": len(self._vectors),
            "n_vectors": sum(
                len(v) for v in self._vectors.values()
            ),
            "layers": list(self._vectors.keys()),
        }


def compute_vector_quality(
    vectors: dict[str, RegisteredVector],
    layer_idx: int = 0,
) -> VectorQualityReport:
    if not vectors:
        return VectorQualityReport(is_valid=False)
    magnitudes = []
    for v in vectors.values():
        mag = float(np.linalg.norm(v.vector))
        magnitudes.append(mag)
    return VectorQualityReport(
        mean_magnitude=float(np.mean(magnitudes)),
        consistency=(
            float(np.std(magnitudes)) if len(magnitudes) > 1 else 0.0
        ),
        n_vectors=len(vectors),
        is_valid=True,
    )


class ProductionCAA:
    def __init__(
        self,
        base_alpha: float = 5.0,
        vectors_dir: str | Path = "vectors",
        behavioral_results_path: str | Path | None = None,
        registry: VectorRegistry | None = None,
    ):
        self.registry = registry or VectorRegistry()
        self.readiness_gate = ReadinessGate(
            vectors_dir=vectors_dir,
            behavioral_results_path=behavioral_results_path,
        )
        self.alpha_controller = AlphaController(base_alpha=base_alpha)
        self.collapse_detector = ModeCollapseDetector()
        self.vector_quality_by_layer: dict[int, dict[str, Any]] = {}
        self.readiness: dict[str, Any] = {
            "level": "bootstrap",
            "detail": "uninitialized",
            "coverage_ratio": 0.0,
        }
        self.last_collapse: dict[str, Any] = (
            self.collapse_detector.status()["last_signal"]
        )

    def ingest_registry(
        self,
        registry: VectorRegistry,
        expected_layers: list[int] | None = None,
        expected_keys: list[str] | None = None,
        model_path: str = "",
    ) -> dict[str, Any]:
        self.registry = registry
        self.vector_quality_by_layer = {
            layer: compute_vector_quality(vectors, layer_idx=layer).to_dict()
            for layer, vectors in registry.layers().items()
        }
        registry_status = registry.status(
            expected_layers=expected_layers,
            expected_keys=expected_keys,
        )
        self.readiness = self.readiness_gate.evaluate(
            registry_status, model_path=model_path
        )
        self.alpha_controller.update(
            readiness_level=self.readiness["level"],
            exact_match_ratio=float(
                self.readiness.get("exact_match_ratio", 0.0) or 0.0
            ),
            extracted_ratio=float(
                self.readiness.get("extracted_ratio", 0.0) or 0.0
            ),
        )
        return self.status()

    def observe_generation(
        self,
        text: str,
        generation_health: float | None = None,
        cross_entropy: float | None = None,
    ) -> dict[str, Any]:
        signal: CollapseSignal = self.collapse_detector.observe(text)
        self.last_collapse = signal.to_dict()
        self.alpha_controller.update(
            readiness_level=self.readiness["level"],
            exact_match_ratio=float(
                self.readiness.get("exact_match_ratio", 0.0) or 0.0
            ),
            extracted_ratio=float(
                self.readiness.get("extracted_ratio", 0.0) or 0.0
            ),
            collapse_signal=signal,
            generation_health=generation_health,
            cross_entropy=cross_entropy,
        )
        return {
            "collapse": self.last_collapse,
            "alpha_state": self.alpha_controller.state.to_dict(),
        }

    def status(self) -> dict[str, Any]:
        return {
            "readiness": self.readiness,
            "alpha_state": self.alpha_controller.state.to_dict(),
            "collapse": self.collapse_detector.status(),
            "registry": self.registry.status(),
            "vector_quality_by_layer": self.vector_quality_by_layer,
        }

    def get_steer_layer_range(self) -> tuple[float, float]:
        return (0.45, 0.60)
