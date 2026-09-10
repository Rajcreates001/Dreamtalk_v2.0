# Dreamtalk - Emotion Engine
# Migrated from Dreamtalk_Emotion_Engine

"""
3-layer memory system (STM/LTM/Emotional Memory) and RelationshipLedger.
Merged from backend/memory/system.py and server/relationship_ledger.py.
"""

import os
import json
import faiss
import numpy as np
from typing import List, Dict, Optional
from collections import defaultdict, deque


class MemorySystem:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.stm: List[Dict] = []
        self.stm_limit = 20

        # Lazy-load SentenceTransformer to avoid import failures on startup
        self._model_name = model_name
        self._ltm_model = None
        self.ltm_dim = 384
        self.ltm_index = faiss.IndexFlatIP(self.ltm_dim)
        self.ltm_corpus: List[Dict] = []

        self.emotional_history: List[Dict] = []

        self.base_path = "data/memory"
        os.makedirs(self.base_path, exist_ok=True)

    @property
    def ltm_model(self):
        if self._ltm_model is None:
            from sentence_transformers import SentenceTransformer
            self._ltm_model = SentenceTransformer(self._model_name)
        return self._ltm_model

    @ltm_model.setter
    def ltm_model(self, value):
        self._ltm_model = value
        self.ltm_dim = 384
        self.ltm_index = faiss.IndexFlatIP(self.ltm_dim)
        self.ltm_corpus: List[Dict] = []

        self.emotional_history: List[Dict] = []

        self.base_path = "data/memory"
        os.makedirs(self.base_path, exist_ok=True)

    def add_interaction(self, user_input: str, response: str, emotion: Dict):
        interaction = {
            "user": user_input,
            "assistant": response,
            "emotion": emotion,
            "timestamp": np.datetime64('now').astype(str)
        }

        self.stm.append(interaction)
        if len(self.stm) > self.stm_limit:
            oldest = self.stm.pop(0)
            self._add_to_ltm(oldest)

        self.emotional_history.append({
            "emotion": emotion["name"],
            "vad": emotion["vad"],
            "timestamp": interaction["timestamp"]
        })

    def _add_to_ltm(self, interaction: Dict):
        text = f"User said: {interaction['user']}\nDreamTalk responded: {interaction['assistant']}"
        embedding = self.ltm_model.encode([text])[0]
        embedding = np.array(embedding, dtype="float32")
        faiss.normalize_L2(embedding.reshape(1, -1))

        self.ltm_index.add(embedding.reshape(1, -1))
        self.ltm_corpus.append(interaction)

    def retrieve_context(self, query: str, k: int = 5) -> Dict:
        stm_context = self.stm[-5:] if self.stm else []

        ltm_results = []
        if self.ltm_index.ntotal > 0:
            query_vec = self.ltm_model.encode([query])
            query_vec = np.array(query_vec, dtype="float32")
            faiss.normalize_L2(query_vec)

            scores, indices = self.ltm_index.search(query_vec, k)
            for i in range(len(indices[0])):
                idx = indices[0][i]
                if idx != -1:
                    ltm_results.append(self.ltm_corpus[idx])

        recent_emotions = [e["emotion"] for e in self.emotional_history[-10:]]

        return {
            "stm": stm_context,
            "ltm": ltm_results,
            "emotional_profile": recent_emotions
        }

    def save(self):
        faiss.write_index(self.ltm_index, os.path.join(self.base_path, "ltm_index.faiss"))
        with open(os.path.join(self.base_path, "ltm_corpus.json"), "w") as f:
            json.dump(self.ltm_corpus, f)
        with open(os.path.join(self.base_path, "emotional_history.json"), "w") as f:
            json.dump(self.emotional_history, f)

    def load(self):
        idx_path = os.path.join(self.base_path, "ltm_index.faiss")
        if os.path.exists(idx_path):
            self.ltm_index = faiss.read_index(idx_path)

        corpus_path = os.path.join(self.base_path, "ltm_corpus.json")
        if os.path.exists(corpus_path):
            with open(corpus_path, "r") as f:
                self.ltm_corpus = json.load(f)

        eh_path = os.path.join(self.base_path, "emotional_history.json")
        if os.path.exists(eh_path):
            with open(eh_path, "r") as f:
                self.emotional_history = json.load(f)


class RelationshipLedger:
    def __init__(self):
        self._ledger: dict = defaultdict(self._default_entry)

    @staticmethod
    def _default_entry():
        return {
            "relationship_score": 0.5,
            "emotion_history":    deque(maxlen=20),
            "flag_count":         0,
            "miss_count":         0,
            "total_turns":        0,
            "cumulative_reward":  0.0,
        }

    def init_user(self, user_id: str):
        if user_id not in self._ledger:
            self._ledger[user_id] = self._default_entry()

    def record(
        self,
        user_id: str,
        pad_chosen: dict,
        emotion_label: str,
        reward: float,
        user_sentiment: dict,
    ):
        entry = self._ledger[user_id]
        entry["total_turns"]       += 1
        entry["cumulative_reward"] += reward
        entry["emotion_history"].append({
            "emotion":   emotion_label,
            "pad":       pad_chosen,
            "reward":    reward,
            "sentiment": user_sentiment,
        })
        if reward <= -2.0:
            entry["miss_count"]  += 1
        elif reward <= -0.9:
            entry["flag_count"]  += 1

    def query(self, user_id: str, query_type: str) -> dict:
        entry = self._ledger.get(user_id, self._default_entry())

        if query_type == "CHECK_RELATIONSHIP_SCORE":
            return {
                "relationship_score": round(entry["relationship_score"], 3),
                "total_turns":        entry["total_turns"],
                "miss_count":         entry["miss_count"],
                "flag_count":         entry["flag_count"],
                "avg_reward":         round(
                    entry["cumulative_reward"] / max(1, entry["total_turns"]), 3
                ),
            }

        if query_type == "QUERY_EMOTIONAL_HISTORY":
            history = list(entry["emotion_history"])[-5:]
            summary = []
            for h in history:
                summary.append({
                    "emotion": h["emotion"],
                    "reward":  round(h["reward"], 3),
                    "user_pleasure": round(h["sentiment"].get("pleasure", 0), 2),
                    "user_arousal":  round(h["sentiment"].get("arousal", 0), 2),
                })
            return {
                "last_5_turns": summary,
                "pattern_hint": self._detect_pattern(entry),
            }

        return {"error": f"Unknown query type: {query_type}"}

    def _detect_pattern(self, entry: dict) -> str:
        history = list(entry["emotion_history"])
        if not history:
            return "no history yet"

        recent_rewards  = [h["reward"] for h in history[-3:]]
        avg_recent      = sum(recent_rewards) / len(recent_rewards)
        miss_rate       = entry["miss_count"] / max(1, entry["total_turns"])

        if miss_rate > 0.4:
            return "WARNING: high emotional mismatch rate — try lower intensity responses"
        if avg_recent >= 1.0:
            return "GOOD: recent turns are well-calibrated — continue current strategy"
        if avg_recent < 0.0:
            return "DECLINING: recent turns performing poorly — reconsider PAD targets"
        return "STABLE: moderate performance — small adjustments may help"
