import requests

from memory.embeddings.embedding_provider import EmbeddingProvider


class OllamaEmbeddingProvider(EmbeddingProvider):
    """
    Ollama-backed embedding provider.
    """

    def __init__(self,base_url: str = "http://localhost:11434",model: str = "embeddinggemma",) -> None:

        self.base_url = base_url.rstrip("/")
        self.model = model



    def embed(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise ValueError("Text cannot be empty.")

        response = requests.post(f"{self.base_url}/api/embed",
            json={
                "model": self.model,
                "input": text,
            },
            timeout=60,
        )

        response.raise_for_status()

        data = response.json()

        embeddings = data.get("embeddings")

        if not embeddings:
            raise ValueError(
                "Ollama returned no embeddings."
            )

        return embeddings[0]




    def embed_batch(self,texts: list[str],) -> list[list[float]]:

        if not texts:
            return []

        if any(not text or not text.strip() for text in texts):
            raise ValueError("Embedding input cannot contain empty text.")


        response = requests.post(
            f"{self.base_url}/api/embed",
            json={
                "model": self.model,
                "input": texts,
            },
            timeout=60,
        )

        response.raise_for_status()

        data = response.json()

        embeddings = data.get("embeddings")

        if embeddings is None:
            raise ValueError("Ollama returned no embeddings.")

        return embeddings