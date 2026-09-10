# Dreamtalk - Voice Engine
# Extracted from RVC (Retrieval-based Voice Conversion)

import numpy as np
import faiss
import traceback


class FeatureIndex:
    def __init__(self, index_path: str, index_rate: float = 0.5):
        self.index_path = index_path
        self.index_rate = index_rate
        self.index = None
        self.big_npy = None

        if index_rate != 0:
            self._load_index()

    def _load_index(self):
        try:
            self.index = faiss.read_index(self.index_path)
            self.big_npy = self.index.reconstruct_n(0, self.index.ntotal)
        except Exception:
            traceback.print_exc()
            self.index = None
            self.big_npy = None

    def search(self, features, k=8):
        if self.index is None or self.big_npy is None:
            return features

        npy = features.cpu().numpy().astype("float32")
        score, ix = self.index.search(npy, k=k)

        if (ix >= 0).all():
            weight = np.square(1 / score)
            weight /= weight.sum(axis=1, keepdims=True)
            npy = np.sum(self.big_npy[ix] * np.expand_dims(weight, axis=2), axis=1)
            return npy * self.index_rate + (1 - self.index_rate) * features.cpu().numpy()

        return features.cpu().numpy()

    def is_valid(self):
        return self.index is not None and self.big_npy is not None
