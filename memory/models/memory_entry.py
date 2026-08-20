from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from memory.models.memory_category import MemoryCategory
from memory.models.memory_types import (
    MemoryImportance,
    MemoryScope,
    MemorySource,
    MemoryType,
)


@dataclass(slots=True)
class MemoryEntry:
    """
    Represents a single piece of information intentionally
    retained by the memory subsystem.
    """

    id: str
    content: str

    category:MemoryCategory
    memory_type: MemoryType
    scope: MemoryScope
    source: MemorySource

    importance: MemoryImportance
    confidence: float

    created_at: datetime
    updated_at: datetime

    expires_at: datetime | None = None

    metadata: dict[str, Any] = field(default_factory=dict)


    def __post_init__(self) -> None:
        """
        Validate the structural integrity of the memory.
        """

        if not self.id:
            raise ValueError("Memory id cannot be empty.")

        if not self.content or not self.content.strip():
            raise ValueError("Memory content cannot be empty.")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "Memory confidence must be between 0.0 and 1.0."
            )