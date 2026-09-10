"""
DreamTalk — Model Loading Manager

Manages ML model lifecycle:
- Lazy loading on first use
- Memory-efficient caching with LRU eviction
- GPU memory monitoring
- Warm-up on startup
- Health checks per model
"""

import time
import gc
import logging
import threading
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from collections import OrderedDict

logger = logging.getLogger("dreamtalk.pipeline.model_manager")


@dataclass
class ModelInfo:
    """Metadata about a loaded model."""
    name: str
    status: str = "unloaded"  # unloaded, loading, loaded, error
    load_time_ms: float = 0.0
    memory_mb: float = 0.0
    last_used: float = 0.0
    use_count: int = 0
    error: Optional[str] = None
    device: str = "cpu"
    priority: int = 0  # Higher = more important to keep loaded

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "status": self.status,
            "load_time_ms": round(self.load_time_ms, 2),
            "memory_mb": round(self.memory_mb, 2),
            "last_used": self.last_used,
            "use_count": self.use_count,
            "device": self.device,
            "error": self.error,
        }


class ModelManager:
    """Manages ML model loading, caching, and lifecycle.

    Features:
    - Lazy loading: models only loaded when first accessed
    - LRU eviction: least-recently-used models evicted when memory is tight
    - Priority: high-priority models resist eviction
    - Thread-safe loading with locks per model
    - Memory monitoring via torch.cuda if available
    """

    def __init__(self, max_memory_mb: float = 6000):
        self._models: Dict[str, Any] = {}
        self._info: Dict[str, ModelInfo] = {}
        self._loaders: Dict[str, Callable] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._max_memory_mb = max_memory_mb
        self._torch_available = False

        try:
            import torch
            self._torch_available = True
            self._torch = torch
        except ImportError:
            self._torch = None

    def register(
        self,
        name: str,
        loader: Callable,
        priority: int = 0,
        device: str = "auto",
    ):
        """Register a model loader for lazy loading."""
        self._info[name] = ModelInfo(name=name, priority=priority, device=device)
        self._loaders[name] = loader
        self._locks[name] = threading.Lock()
        logger.info(f"Registered model: {name} (priority={priority})")

    def get(self, name: str) -> Any:
        """Get a model, loading it lazily if needed."""
        if name in self._models:
            info = self._info.get(name)
            if info:
                info.last_used = time.time()
                info.use_count += 1
            return self._models[name]

        return self._load_model(name)

    def _load_model(self, name: str) -> Any:
        """Load a model with thread-safe locking."""
        if name not in self._loaders:
            raise ValueError(f"Model '{name}' not registered")

        lock = self._locks[name]
        with lock:
            # Double-check after acquiring lock
            if name in self._models:
                return self._models[name]

            info = self._info[name]
            info.status = "loading"

            # Check memory before loading
            self._check_memory()

            start = time.time()
            try:
                loader = self._loaders[name]
                model = loader()
                self._models[name] = model

                elapsed = (time.time() - start) * 1000
                info.status = "loaded"
                info.load_time_ms = elapsed
                info.last_used = time.time()
                info.use_count = 1
                info.memory_mb = self._estimate_memory(name)

                logger.info(f"Loaded model '{name}' in {elapsed:.1f}ms ({info.memory_mb:.1f}MB)")
                return model

            except Exception as e:
                info.status = "error"
                info.error = str(e)
                logger.error(f"Failed to load model '{name}': {e}")
                raise

    def _check_memory(self):
        """Evict models if memory is too high."""
        total = self._get_total_memory_mb()
        if total < self._max_memory_mb:
            return

        # Sort by priority (ascending) then last_used (ascending)
        candidates = sorted(
            self._info.items(),
            key=lambda x: (x[1].priority, x[1].last_used),
        )

        for name, info in candidates:
            if total < self._max_memory_mb * 0.8:
                break
            if info.priority > 5:  # Don't evict high-priority models
                continue
            if name in self._models:
                self._unload_model(name)
                total = self._get_total_memory_mb()

    def _unload_model(self, name: str):
        """Unload a model to free memory."""
        if name in self._models:
            del self._models[name]
            gc.collect()

            if self._torch and self._torch.cuda.is_available():
                self._torch.cuda.empty_cache()

            info = self._info.get(name)
            if info:
                info.status = "unloaded"
                info.memory_mb = 0
            logger.info(f"Unloaded model '{name}'")

    def _get_total_memory_mb(self) -> float:
        """Get total memory used by loaded models."""
        total = 0.0
        for name, info in self._info.items():
            if info.status == "loaded":
                total += info.memory_mb
        return total

    def _estimate_memory_mb(self, name: str) -> float:
        """Estimate memory of a loaded model."""
        model = self._models.get(name)
        if model is None:
            return 0

        if self._torch and hasattr(model, 'parameters'):
            try:
                total_params = sum(p.numel() * p.element_size() for p in model.parameters())
                return total_params / (1024 * 1024)
            except Exception:
                pass

        return 50  # Default estimate

    def warm_up(self, model_names: Optional[List[str]] = None):
        """Pre-load specified models (or all registered)."""
        names = model_names or list(self._loaders.keys())
        for name in names:
            try:
                self.get(name)
            except Exception as e:
                logger.warning(f"Warm-up failed for '{name}': {e}")

    def health_check(self) -> Dict[str, Any]:
        """Check status of all registered models."""
        return {
            "total_registered": len(self._info),
            "total_loaded": sum(1 for i in self._info.values() if i.status == "loaded"),
            "total_memory_mb": round(self._get_total_memory_mb(), 2),
            "max_memory_mb": self._max_memory_mb,
            "models": {name: info.to_dict() for name, info in self._info.items()},
            "gpu_available": self._torch.cuda.is_available() if self._torch else False,
        }

    def unload_all(self):
        """Unload all models."""
        names = list(self._models.keys())
        for name in names:
            self._unload_model(name)
        gc.collect()


# ── Singleton ──────────────────────────────────────────────────────────

_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """Get or create the default model manager singleton."""
    global _manager
    if _manager is None:
        _manager = ModelManager()
    return _manager
