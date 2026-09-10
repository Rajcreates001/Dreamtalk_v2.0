# Dreamtalk - Memory Module
# Extracted from MemoryOS

from __future__ import annotations

from typing import Any, Dict, List, Optional

from dreamtalk.brain.memory.hierarchical.memoryos.memoryos import MemoryOS, MemoryRecord


class PromotionPipeline:
    def __init__(self, memoryos: MemoryOS):
        self.memoryos = memoryos

    def run(self):
        records = self.memoryos.short_term.get_all()
        if not records:
            return
        for record in records:
            self.memoryos.mid_term.add(
                record.text,
                embedding=record.embedding,
                metadata={**record.metadata, "source": "short_term"},
            )
        self.memoryos.short_term.clear()
        promotable = self.memoryos.mid_term.get_promotable()
        for record in promotable:
            self.memoryos.long_term.add_knowledge(
                record.text,
                embedding=record.embedding,
                metadata={**record.metadata, "source": "mid_term"},
            )
            self.memoryos.mid_term.remove(record.id)

    def promote_single(self, record: MemoryRecord, from_tier: str = "short_term"):
        if from_tier == "short_term":
            self.memoryos.mid_term.add(
                record.text,
                embedding=record.embedding,
                metadata={**record.metadata, "source": "promotion_pipeline"},
            )
        elif from_tier == "mid_term":
            self.memoryos.long_term.add_knowledge(
                record.text,
                embedding=record.embedding,
                metadata={**record.metadata, "source": "promotion_pipeline"},
            )

    def get_stats(self) -> Dict[str, Any]:
        return {
            "short_term_size": len(self.memoryos.short_term),
            "mid_term_size": len(self.memoryos.mid_term),
            "long_term_size": len(self.memoryos.long_term.get_all_knowledge()),
            "promotable_mid_term": len(self.memoryos.mid_term.get_promotable()),
            "short_term_capacity": self.memoryos.short_term.capacity,
        }
