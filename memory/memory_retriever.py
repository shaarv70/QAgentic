import math
from memory.embeddings.embedding_provider import EmbeddingProvider
from memory.models.memory_category import MemoryCategory
from memory.models.memory_entry import MemoryEntry
from memory.models.memory_query import MemoryQuery
from memory.stores.memory_store import MemoryStore
from typing import List, Tuple
from utils.logger import logger


class MemoryRetriever:
    """
    Retrieves relevant memories using semantic similarity.

    Retrieval flow:
        1. Retrieve candidate memories from the store.
        2. Generate an embedding for the query.
        3. Generate embeddings for candidate memories.
        4. Calculate cosine similarity.
        5. Apply relevance threshold.
        6. Sort by similarity.
        7. Return Top-K results.
    """

    def __init__(self,store: MemoryStore,embedding_provider: EmbeddingProvider, similarity_threshold: float = 0.5,candidate_limit: int = 100) -> None:
        self.store = store
        self.embedding_provider = embedding_provider
        self.similarity_threshold = similarity_threshold
        self.candidate_limit = candidate_limit



    def retrieve(self,query: MemoryQuery,) -> list[MemoryEntry]:
        logger.info(
            "MemoryQuery filters | capability=%s | category=%s | memory_type=%s | scope=%s",
            query.capability,
            query.category,
            query.memory_type,
            query.scope,
        )

        # --------------------------------------------------
        # 1. Retrieve candidate memories
        # --------------------------------------------------


        memories = self.store.list(
            MemoryQuery(
                query=query.query,
                scope=query.scope,
                memory_type=query.memory_type,
                category=query.category,
                capability=query.capability,
                minimum_confidence=query.minimum_confidence,
                limit=self.candidate_limit,
                include_expired=query.include_expired,
            )
        )

        if not memories:
            return []

        logger.info("Semantic memory retrieval | query=%s | candidates=%d",query.query,len(memories),)

        # --------------------------------------------------
        # 2. Generate query embedding
        # --------------------------------------------------

        query_embedding = self.embedding_provider.embed(query.query)



        # --------------------------------------------------
        # 3. Generate candidate embeddings
        # --------------------------------------------------

        memory_embeddings = (
            self.embedding_provider.embed_batch(
                [memory.content for memory in memories]
            )
        )

        # --------------------------------------------------
        # 4. Calculate similarity
        # 5. Apply relevance threshold
        # --------------------------------------------------


        scored_memories: List[Tuple[float, MemoryEntry]] = []
        threshold = self.similarity_threshold
        if query.category == MemoryCategory.PROCEDURAL:
            threshold = 0.25
        for memory, embedding in zip(memories,memory_embeddings,):
            score = self._cosine_similarity(query_embedding,embedding,)
            if score >= threshold:
                scored_memories.append((score, memory))
            logger.info("Semantic memory result | id=%s | score=%.4f",memory.id,score,)

        # --------------------------------------------------
        # 6. Rank by relevance
        # --------------------------------------------------


        scored_memories.sort(key=lambda item: item[0],reverse=True,)

        # --------------------------------------------------
        # 7. Return Top-K
        # --------------------------------------------------

        results = [
            memory for _, memory in scored_memories[:query.limit]]

        logger.info(
            "Semantic memory retrieval complete | ""candidates=%d | relevant=%d | returned=%d",
            len(memories),
            len(scored_memories),
            len(results),
        )

        return results



    @staticmethod
    def _cosine_similarity(vector_a: list[float],vector_b: list[float],) -> float:

        if len(vector_a) != len(vector_b):
            raise ValueError("Embedding dimensions do not match.")

        dot_product = sum(a * b for a, b in zip(vector_a, vector_b))

        magnitude_a = math.sqrt(sum(a * a for a in vector_a))

        magnitude_b = math.sqrt(sum(b * b for b in vector_b))

        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0

        return dot_product / (magnitude_a * magnitude_b)