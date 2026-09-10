"""
DreamTalk — Pipeline Metrics Collector
Prometheus-compatible metrics for monitoring.
"""
import time
import threading
from collections import defaultdict
from typing import Dict, Optional


class MetricsCollector:
    """Collects and exposes pipeline metrics for Prometheus."""
    
    def __init__(self):
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, list] = defaultdict(list)
        self._timers: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()
    
    def inc(self, name: str, value: float = 1.0):
        """Increment a counter."""
        with self._lock:
            self._counters[name] += value
    
    def set(self, name: str, value: float):
        """Set a gauge value."""
        with self._lock:
            self._gauges[name] = value
    
    def observe(self, name: str, value: float):
        """Observe a histogram value."""
        with self._lock:
            self._histograms[name].append(value)
            # Keep last 1000 observations
            if len(self._histograms[name]) > 1000:
                self._histograms[name] = self._histograms[name][-1000:]
    
    def timer(self, name: str):
        """Context manager for timing operations."""
        return _TimerContext(self, name)
    
    def request_counter(self, method: str, path: str, status: int):
        """Record an HTTP request."""
        self.inc(f"http_requests_total{{method={method},path={path},status={status}}}")
    
    def inference_time(self, model: str, duration_ms: float):
        """Record model inference time."""
        self.observe(f"model_inference_ms{{model={model}}}", duration_ms)
    
    def active_sessions(self, count: int):
        """Set active session count."""
        self.set("active_sessions", count)
    
    def gpu_memory_used(self, gb: float):
        """Set GPU memory usage."""
        self.set("gpu_memory_used_gb", gb)
    
    def emotion_event(self, emotion: str):
        """Record an emotion detection event."""
        self.inc(f"emotion_events_total{{emotion={emotion}}}")
    
    def brain_action(self, action: str):
        """Record a brain action selection."""
        self.inc(f"brain_actions_total{{action={action}}}")
    
    def tts_request(self, engine: str):
        """Record a TTS request."""
        self.inc(f"tts_requests_total{{engine={engine}}}")
    
    def to_prometheus(self) -> str:
        """Export all metrics in Prometheus text format."""
        lines = []
        
        for name, value in self._counters.items():
            lines.append(f"# TYPE {name.split('{')[0]} counter")
            lines.append(f"{name} {value}")
        
        for name, value in self._gauges.items():
            lines.append(f"# TYPE {name.split('{')[0]} gauge")
            lines.append(f"{name} {value}")
        
        for name, values in self._histograms.items():
            base = name.split("{")[0]
            lines.append(f"# TYPE {base} histogram")
            if values:
                lines.append(f'{name}_count {len(values)}')
                lines.append(f'{name}_sum {sum(values):.3f}')
                lines.append(f'{name}_bucket{{le="50"}} {sum(1 for v in values if v <= 50)}')
                lines.append(f'{name}_bucket{{le="100"}} {sum(1 for v in values if v <= 100)}')
                lines.append(f'{name}_bucket{{le="500"}} {sum(1 for v in values if v <= 500)}')
                lines.append(f'{name}_bucket{{le="1000"}} {sum(1 for v in values if v <= 1000)}')
                lines.append(f'{name}_bucket{{le="+Inf"}} {len(values)}')
        
        return "\n".join(lines)
    
    def to_json(self) -> dict:
        """Export metrics as JSON."""
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                k: {
                    "count": len(v),
                    "sum": sum(v),
                    "avg": sum(v) / len(v) if v else 0,
                    "p50": sorted(v)[len(v) // 2] if v else 0,
                    "p95": sorted(v)[int(len(v) * 0.95)] if v else 0,
                    "p99": sorted(v)[int(len(v) * 0.99)] if v else 0,
                }
                for k, v in self._histograms.items()
            },
        }


class _TimerContext:
    """Context manager for timing."""
    
    def __init__(self, collector: MetricsCollector, name: str):
        self._collector = collector
        self._name = name
        self._start = 0
    
    def __enter__(self):
        self._start = time.time()
        return self
    
    def __exit__(self, *args):
        elapsed_ms = (time.time() - self._start) * 1000
        self._collector.observe(f"{self._name}_ms", elapsed_ms)


# Singleton
_collector: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector
