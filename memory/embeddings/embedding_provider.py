from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """
    Contract for generating text embeddings.
    """

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """
        Generate an embedding for a single text.
        """
        raise NotImplementedError

    

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.
        """
        raise NotImplementedError