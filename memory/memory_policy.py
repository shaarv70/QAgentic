from datetime import datetime, timezone

from memory.models.memory_entry import MemoryEntry
from memory.models.memory_types import MemoryImportance


class MemoryPolicy:
    """
    Determines whether a MemoryEntry is eligible for persistence.
    """



    def __init__(self, minimum_confidence: float = 0.7) -> None:
        if not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError(
                "minimum_confidence must be between 0.0 and 1.0."
            )

        self.minimum_confidence = minimum_confidence




    def should_remember(self, memory: MemoryEntry) -> bool:
        """
        Determine whether the supplied memory should be persisted.
        """

        if not memory.content.strip():
            return False

        if memory.importance == MemoryImportance.LOW:
            return False

        if memory.confidence < self.minimum_confidence:
            return False

        if self._is_expired(memory):
            return False

        return True



    @staticmethod
    def _is_expired(memory: MemoryEntry) -> bool:
        
        if memory.expires_at is None:
            return False

        now = datetime.now(timezone.utc)

        expires_at = memory.expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        return expires_at <= now