import os
from typing import List

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from sentence_transformers import SentenceTransformer


class EmbeddingService:
    _instance = None
    _model: SentenceTransformer

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            cls._model = SentenceTransformer("all-MiniLM-L6-v2")
        return cls._instance

    def get_embeddings(self, text: str) -> List[float]:
        vector = self._model.encode(text, convert_to_numpy=True)
        return vector.tolist()

    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        vectors = self._model.encode(
            texts, batch_size=32, show_progress_bar=False, convert_to_numpy=True
        )
        return vectors.tolist()
