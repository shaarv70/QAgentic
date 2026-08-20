from memory.memory_manager import MemoryManager
from memory.models.memory_entry import MemoryEntry


class ProceduralMemory:

    def __init__(self, memory_manager: MemoryManager) -> None:
        self.memory_manager = memory_manager

    def seed(self, memory: MemoryEntry) -> None:

        if self._exists(memory.id):
            return

        self.memory_manager.remember(memory)

    def seed_many(self, memories: list[MemoryEntry]) -> None:

        for memory in memories:
            self.seed(memory)

    def _exists(self, memory_id: str) -> bool:
        return self.memory_manager.store.get(memory_id) is not None