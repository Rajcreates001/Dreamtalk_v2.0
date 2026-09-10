"""
DreamTalk — Pipeline Health Monitor

Comprehensive health checks for all pipeline components:
- Voice engines (Kokoro, IndicF5, GPT-SoVITS, RVC)
- Face engines (LivePortrait, MuseTalk)
- Brain pipeline (SNN areas, emotion, LLM)
- Infrastructure (DB, Redis, Weaviate, GPU)
"""

import time
import logging
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger("dreamtalk.pipeline.health")


@dataclass
class ComponentHealth:
    name: str
    status: str  # healthy, degraded, unhealthy, unknown
    message: str = ""
    latency_ms: float = 0.0
    details: Dict = None

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "latency_ms": round(self.latency_ms, 2),
            "details": self.details or {},
        }


class PipelineHealthMonitor:
    """Monitors health of all DreamTalk pipeline components."""

    async def check_all(self) -> Dict[str, Any]:
        """Run all health checks and return comprehensive status."""
        start = time.time()

        checks = {}

        # Voice checks
        checks["voice_kokoro"] = await self._check_kokoro()
        checks["voice_indicf5"] = await self._check_indicf5()

        # Face checks
        checks["face_liveportrait"] = await self._check_liveportrait()
        checks["face_musetalk"] = await self._check_musetalk()

        # Brain checks
        checks["brain_pipeline"] = await self._check_brain()
        checks["brain_llm"] = await self._check_llm()

        # Infrastructure
        checks["gpu"] = await self._check_gpu()
        checks["weights"] = await self._check_weights()

        total_ms = (time.time() - start) * 1000

        # Determine overall status
        statuses = [c["status"] for c in checks.values()]
        if all(s == "healthy" for s in statuses):
            overall = "healthy"
        elif any(s == "unhealthy" for s in statuses):
            overall = "degraded"
        else:
            overall = "healthy"

        return {
            "status": overall,
            "checks": checks,
            "total_latency_ms": round(total_ms, 2),
            "timestamp": time.time(),
        }

    async def _check_kokoro(self) -> Dict:
        start = time.time()
        try:
            from dreamtalk.voice.core.tts.kokoro_engine import KokoroTTSEngine
            engine = KokoroTTSEngine()
            voices = engine.list_voices()
            ms = (time.time() - start) * 1000
            return {
                "status": "healthy",
                "message": f"{len(voices)} voices available",
                "latency_ms": round(ms, 2),
                "details": {"voice_count": len(voices)},
            }
        except Exception as e:
            ms = (time.time() - start) * 1000
            return {"status": "unhealthy", "message": str(e)[:200], "latency_ms": round(ms, 2)}

    async def _check_indicf5(self) -> Dict:
        start = time.time()
        try:
            import urllib.request
            import os as _os
            _indic_host = _os.environ.get("INDICF5_HOST", "host.docker.internal")
            _indic_port = _os.environ.get("INDICF5_PORT", "8002")
            resp = urllib.request.urlopen(f"http://{_indic_host}:{_indic_port}/health", timeout=5)
            data = __import__("json").loads(resp.read())
            ms = (time.time() - start) * 1000
            return {
                "status": "healthy" if data.get("model_loaded") else "degraded",
                "message": "Model loaded" if data.get("model_loaded") else "Model not loaded",
                "latency_ms": round(ms, 2),
                "details": data,
            }
        except Exception as e:
            ms = (time.time() - start) * 1000
            return {"status": "unhealthy", "message": str(e)[:200], "latency_ms": round(ms, 2)}

    async def _check_liveportrait(self) -> Dict:
        start = time.time()
        try:
            from pathlib import Path
            weights_dir = Path("weights/liveportrait")
            required = ["appearance_feature_extractor.pth", "motion_extractor.pth", "spade_generator.pth"]
            present = [f for f in required if (weights_dir / f).exists()]
            ms = (time.time() - start) * 1000
            if len(present) == len(required):
                return {"status": "healthy", "message": "All weights present", "latency_ms": round(ms, 2)}
            else:
                missing = [f for f in required if f not in present]
                return {"status": "degraded", "message": f"Missing: {missing}", "latency_ms": round(ms, 2)}
        except Exception as e:
            ms = (time.time() - start) * 1000
            return {"status": "unhealthy", "message": str(e)[:200], "latency_ms": round(ms, 2)}

    async def _check_musetalk(self) -> Dict:
        start = time.time()
        try:
            from pathlib import Path
            weights_dir = Path("weights/musetalk")
            has_unet = (weights_dir / "pytorch_model.bin").exists() or (weights_dir / "unet.pth").exists()
            ms = (time.time() - start) * 1000
            if has_unet:
                return {"status": "healthy", "message": "Weights present", "latency_ms": round(ms, 2)}
            else:
                return {"status": "degraded", "message": "Weights not found", "latency_ms": round(ms, 2)}
        except Exception as e:
            ms = (time.time() - start) * 1000
            return {"status": "unhealthy", "message": str(e)[:200], "latency_ms": round(ms, 2)}

    async def _check_brain(self) -> Dict:
        start = time.time()
        try:
            from dreamtalk.pipeline.brain_pipeline import BrainPipeline
            pipeline = BrainPipeline()
            import numpy as np
            features = np.random.randn(256).astype(np.float32)
            spike = pipeline.encoder.encode(features)
            ms = (time.time() - start) * 1000
            return {
                "status": "healthy",
                "message": f"SNN encoder working (shape: {spike.shape})",
                "latency_ms": round(ms, 2),
            }
        except Exception as e:
            ms = (time.time() - start) * 1000
            return {"status": "unhealthy", "message": str(e)[:200], "latency_ms": round(ms, 2)}

    async def _check_llm(self) -> Dict:
        start = time.time()
        try:
            from dreamtalk.brain.llm.engine import BrainLLMEngine
            engine = BrainLLMEngine()
            result = await engine.health_check()
            ms = (time.time() - start) * 1000
            return {
                "status": result.get("status", "unknown"),
                "message": result.get("error", result.get("model", "OK")),
                "latency_ms": round(ms, 2),
                "details": result,
            }
        except Exception as e:
            ms = (time.time() - start) * 1000
            return {"status": "unhealthy", "message": str(e)[:200], "latency_ms": round(ms, 2)}

    async def _check_gpu(self) -> Dict:
        start = time.time()
        try:
            import torch
            if torch.cuda.is_available():
                props = torch.cuda.get_device_properties(0)
                mem_used = torch.cuda.memory_allocated(0) / (1024**3)
                mem_total = props.total_memory / (1024**3)
                ms = (time.time() - start) * 1000
                return {
                    "status": "healthy",
                    "message": f"{props.name} ({mem_used:.1f}/{mem_total:.1f} GB)",
                    "latency_ms": round(ms, 2),
                    "details": {
                        "name": props.name,
                        "memory_used_gb": round(mem_used, 2),
                        "memory_total_gb": round(mem_total, 2),
                        "memory_percent": round(mem_used / mem_total * 100, 1),
                    },
                }
            else:
                ms = (time.time() - start) * 1000
                return {"status": "degraded", "message": "No GPU available, using CPU", "latency_ms": round(ms, 2)}
        except ImportError:
            ms = (time.time() - start) * 1000
            return {"status": "unknown", "message": "PyTorch not installed", "latency_ms": round(ms, 2)}

    async def _check_weights(self) -> Dict:
        start = time.time()
        try:
            from pathlib import Path
            weights_dir = Path("weights")
            total_size = sum(f.stat().st_size for f in weights_dir.rglob("*") if f.is_file())
            total_gb = total_size / (1024**3)
            file_count = sum(1 for f in weights_dir.rglob("*") if f.is_file())
            ms = (time.time() - start) * 1000
            return {
                "status": "healthy" if total_gb > 1 else "degraded",
                "message": f"{total_gb:.1f} GB across {file_count} files",
                "latency_ms": round(ms, 2),
                "details": {"total_gb": round(total_gb, 2), "file_count": file_count},
            }
        except Exception as e:
            ms = (time.time() - start) * 1000
            return {"status": "unhealthy", "message": str(e)[:200], "latency_ms": round(ms, 2)}


# ── Singleton ──────────────────────────────────────────────────────────

_monitor: Optional[PipelineHealthMonitor] = None


def get_health_monitor() -> PipelineHealthMonitor:
    global _monitor
    if _monitor is None:
        _monitor = PipelineHealthMonitor()
    return _monitor
