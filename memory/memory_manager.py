from memory.models.memory_entry import MemoryEntry
from memory.models.memory_query import MemoryQuery
from memory.memory_policy import MemoryPolicy
from memory.memory_retriever import MemoryRetriever
from memory.stores.memory_store import MemoryStore
from utils.logger import logger


class MemoryManager:
    """
    Coordinates memory operations between agents,
    memory policy, and the underlying memory store.
    """

    def __init__(self,store: MemoryStore,policy: MemoryPolicy,retriever: MemoryRetriever,) -> None:
        self.store = store
        self.policy = policy
        self.retriever = retriever



    def remember(self, memory: MemoryEntry) -> bool:
        """
        Persist the memory if it satisfies the memory policy.

        Returns:
            True if the memory was persisted.
            False if the policy rejected it.
        """

        if not self.policy.should_remember(memory):
            return False

        self.store.save(memory)
        return True



    def retrieve(self, query: MemoryQuery) -> list[MemoryEntry]:
        """
        Retrieve memories relevant to the supplied query.
        """
        memories = self.retriever.retrieve(query)
        logger.info("Memory retrieval | query=%s | results=%d",query.query,len(memories),)
        for memory in memories:
            logger.info("Retrieved memory | id=%s | type=%s | importance=%s",memory.id,memory.memory_type.value,memory.importance.value,)

        return memories



    def update(self, memory: MemoryEntry) -> None:
        """
        Update an existing memory after policy validation.
        """

        if not self.policy.should_remember(memory):
            raise ValueError(
                f"Memory does not satisfy policy: {memory.id}"
            )

        self.store.update(memory)



    def forget(self, memory_id: str) -> None:
        """
        Remove a memory.
        """
        self.store.delete(memory_id)