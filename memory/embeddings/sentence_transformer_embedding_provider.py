from typing import List

from sentence_transformers import SentenceTransformer

from memory.embeddings.embedding_provider import EmbeddingProvider


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """
    Local, free embedding provider using Sentence Transformers.
    """

    def __init__(
        self,
        model: str = "all-MiniLM-L6-v2",
    ) -> None:
        self.model_name = model
        self.model = SentenceTransformer(model)

    def embed(self, text: str) -> List[float]:
        if not text or not text.strip():
            raise ValueError("Text cannot be empty.")

        embedding = self.model.encode(
            text,
            convert_to_numpy=True,
        )

        return embedding.tolist()

    def embed_batch(
        self,
        texts: List[str],
    ) -> List[List[float]]:

        if not texts:
            return []

        if any(
            not text or not text.strip()
            for text in texts
        ):
            raise ValueError(
                "Embedding input cannot contain empty text."
            )

        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
        )

        return embeddings.tolist()