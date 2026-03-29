import logging
from typing import Dict, Tuple

import numpy as np
from openai import OpenAI

from config import OPENAI_EMBEDDING_MODEL
from tools.vocabulary import CATEGORY_PROTOTYPES

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, model_name: str = OPENAI_EMBEDDING_MODEL) -> None:
        self.client = OpenAI()
        self.model_name = model_name
        logger.info(f"Precomputing category embeddings with model={model_name}")
        self.category_embeddings = self._precompute_category_embeddings()
        logger.info(f"EmbeddingService ready: {len(self.category_embeddings)} categories")

    def _embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        try:
            response = self.client.embeddings.create(
                model=self.model_name,
                input=texts,
            )
        except Exception as e:
            logger.error(f"Embedding API call failed for {len(texts)} text(s): {e}")
            raise
        return [np.array(item.embedding, dtype=np.float32) for item in response.data]

    def _normalize(self, vector: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector
        return vector / norm

    def _precompute_category_embeddings(self) -> Dict[str, np.ndarray]:
        categories = list(CATEGORY_PROTOTYPES.keys())
        texts = [CATEGORY_PROTOTYPES[c] for c in categories]
        vectors = self._embed_batch(texts)
        return {
            category: self._normalize(vector)
            for category, vector in zip(categories, vectors)
        }

    def embed_text(self, text: str) -> np.ndarray:
        vector = self._embed_batch([text])[0]
        return self._normalize(vector)

    def compute_category_score(self, text: str) -> Tuple[float, str]:
        article_vector = self.embed_text(text)

        best_category = ""
        best_cosine = -1.0

        for category, category_vector in self.category_embeddings.items():
            cosine = float(np.dot(article_vector, category_vector))
            if cosine > best_cosine:
                best_cosine = cosine
                best_category = category

        semantic_score = (best_cosine + 1.0) / 2.0
        return semantic_score, best_category
