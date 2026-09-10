# Dreamtalk - Emotion Engine
# Migrated from Dreamtalk_Emotion_Engine

"""
FAISS-based emotional memory and knowledge base for semantic retrieval of
personality response patterns.
Merged from src/knowledge_base.py (NeuralKnowledgeBase).
"""

import logging
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from dreamtalk.emotion.models.emotion_states import KNOWLEDGE_CORPUS


class NeuralKnowledgeBase:
    """
    Embeds the knowledge corpus with a sentence-transformer model and
    indexes the vectors in FAISS for semantic retrieval.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.index = None
        self.corpus = KNOWLEDGE_CORPUS
        self.texts = []
        self.metadata = []
        self._trained = False

    def train(self):
        from sentence_transformers import SentenceTransformer
        import faiss

        logging.info(f"Loading neural model '{self.model_name}'...")
        self.model = SentenceTransformer(self.model_name)

        self.texts = [entry["text"] for entry in self.corpus]
        self.metadata = [
            {"category": entry["category"], "mood_context": entry["mood_context"]}
            for entry in self.corpus
        ]

        logging.info(f"Encoding {len(self.texts)} knowledge entries...")
        embeddings = self.model.encode(self.texts, show_progress_bar=False)
        embeddings = np.array(embeddings, dtype="float32")

        faiss.normalize_L2(embeddings)

        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings)

        self._trained = True
        logging.info(f"Knowledge base trained — {self.index.ntotal} vectors indexed.")

    def retrieve(self, query: str, current_mood: str = "", k: int = 5) -> list[dict]:
        if not self._trained:
            logging.warning("Knowledge base not trained yet. Returning empty.")
            return []

        import faiss

        augmented_query = f"[mood: {current_mood}] {query}" if current_mood else query
        query_vec = self.model.encode([augmented_query])
        query_vec = np.array(query_vec, dtype="float32")
        faiss.normalize_L2(query_vec)

        scores, indices = self.index.search(query_vec, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            results.append({
                "text": self.texts[idx],
                "category": self.metadata[idx]["category"],
                "mood_context": self.metadata[idx]["mood_context"],
                "score": float(score),
            })
        return results
