"""Constant-memory streaming pipeline — ports and pure orchestration.

A producer (StreamSource) feeds a bounded queue feeding batch consumers
(BatchSink) with adaptive batch sizing (AdaptiveBatchController). Peak RAM
is provably (queue_cap + concurrency + 1) batches — independent of the total
number of rows — so the same code streams thousands or trillions of rows.

Pure business logic only. Infrastructure provides the adapters; handlers wire
them. See ~/.claude/plans/sharded-popping-harbor.md for the design and the
genius-review findings the contracts encode.
"""
# Adapted from Cortex (MIT License)

from __future__ import annotations

from .adaptive_controller import AdaptiveBatchController
from .backpressure_pipeline import (
    BackpressurePipeline,
    PipelineResult,
    compute_queue_cap,
)
from .ports import BatchSink, StreamSource

__all__ = [
    "AdaptiveBatchController",
    "BackpressurePipeline",
    "PipelineResult",
    "compute_queue_cap",
    "BatchSink",
    "StreamSource",
]
