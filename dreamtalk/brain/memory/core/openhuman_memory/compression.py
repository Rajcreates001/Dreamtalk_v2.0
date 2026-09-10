# Dreamtalk - Memory Module
# Extracted from OpenHuman (Rust -> Python port)

from __future__ import annotations

from typing import Any, Dict, List, Optional


class TokenJuice:
    def __init__(self, token_budget: int = 4096, compression_ratio: float = 0.5):
        self.token_budget = token_budget
        self.compression_ratio = compression_ratio

    def compress(self, texts: List[str], importance_scores: Optional[List[float]] = None) -> List[str]:
        if not texts:
            return []
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        if importance_scores is None:
            importance_scores = [1.0] * len(texts)
        scored = list(zip(texts, importance_scores, range(len(texts))))
        scored.sort(key=lambda x: x[1], reverse=True)
        result = []
        total_tokens = 0
        target_tokens = int(self.token_budget * self.compression_ratio)
        for text, score, _ in scored:
            tokens = len(enc.encode(text))
            if total_tokens + tokens > target_tokens:
                max_len = max(1, target_tokens - total_tokens)
                truncated = enc.decode(enc.encode(text)[:max_len])
                result.append(truncated)
                total_tokens += len(enc.encode(truncated))
                break
            result.append(text)
            total_tokens += tokens
        result.sort(key=lambda x: importance_scores[texts.index(x)] if x in texts else 0, reverse=True)
        return result

    def should_compress(self, total_tokens: int) -> bool:
        return total_tokens > self.token_budget


def compress_context(context: str, max_tokens: int = 4096, model: str = "gpt-4") -> str:
    import tiktoken
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(context)
    if len(tokens) <= max_tokens:
        return context
    ratio = max_tokens / len(tokens)
    keep_count = max(1, int(len(tokens) * ratio))
    import math
    head = tokens[:keep_count // 2]
    tail = tokens[-keep_count // 2:]
    paraphrased = head + tail
    return enc.decode(paraphrased) + "\n[...compressed...]"
