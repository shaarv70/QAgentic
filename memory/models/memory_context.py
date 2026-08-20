from dataclasses import dataclass, field

from memory.models.memory_entry import MemoryEntry


@dataclass(slots=True)
class MemoryContext:
    """
    Represents memory retrieved for the current AI execution context.
    """

    memories: list[MemoryEntry] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.memories