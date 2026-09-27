import os
from pathlib import Path
from typing import List

from src.core.config import settings


def _resolve_model_source() -> tuple[str, bool]:
    """Return (source, use_local_files_only) for the sentence-transformer model."""
    local_path = Path(settings.EMBEDDING_MODEL_PATH)
    if local_path.is_dir():
        return str(local_path), True
    return settings.EMBEDDING_MODEL_ID, False


def _apply_offline_flags(local_only: bool) -> None:
    if local_only:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"


class EmbeddingService:
    _instance = None
    _model = None

    def __new__(cls):
        # Only memoise after the model has actually loaded, otherwise a failed
        # load leaves a half-initialised singleton behind and every later call
        # silently reuses it instead of retrying.
        if cls._instance is not None:
            return cls._instance

        from sentence_transformers import SentenceTransformer

        source, local_only = _resolve_model_source()
        _apply_offline_flags(local_only)
        model = SentenceTransformer(source, local_files_only=local_only)

        instance = super().__new__(cls)
        instance._model = model
        cls._instance = instance
        return instance

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
