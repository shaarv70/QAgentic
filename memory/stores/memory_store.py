from abc import ABC, abstractmethod

from memory.models.memory_entry import MemoryEntry
from memory.models.memory_query import MemoryQuery


class MemoryStore(ABC):
    """
    Abstract contract for memory persistence and retrieval.

    Implementations are responsible for storing and retrieving
    MemoryEntry objects.
    """

    @abstractmethod
    def save(self, memory: MemoryEntry) -> None:
        """
        Persist a new memory.
        """
        raise NotImplementedError


    @abstractmethod
    def get(self, memory_id: str) -> MemoryEntry | None:
        """
        Retrieve a memory by its identifier.
        """
        raise NotImplementedError


    @abstractmethod
    def search(self, query: MemoryQuery) -> list[MemoryEntry]:
        """
        Search memories using the supplied query.
        """
        raise NotImplementedError


    @abstractmethod
    def update(self, memory: MemoryEntry) -> None:
        """
        Update an existing memory.
        """
        raise NotImplementedError


    @abstractmethod
    def delete(self, memory_id: str) -> None:
        """
        Delete a memory by its identifier.
        """
        raise NotImplementedError



    @abstractmethod
    def list(self,query: MemoryQuery,) -> list[MemoryEntry]:
        """
    Return memories matching structural filters,
    without semantic/text matching.
    """
        raise NotImplementedError