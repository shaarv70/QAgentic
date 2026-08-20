from dataclasses import dataclass
from typing import Optional

from memory.models.memory_category import MemoryCategory
from memory.models.memory_types import (
    MemoryImportance,
    MemoryScope,
    MemoryType,
)


@dataclass(slots=True)
class MemoryQuery:
    """
    Defines criteria used to retrieve relevant memories.
    """

    query: str

    scope: Optional[MemoryScope] = None
    memory_type: Optional[MemoryType] = None
    category: Optional[MemoryCategory] = None
    capability: Optional[str] = None
    minimum_importance: Optional[MemoryImportance] = None
    minimum_confidence: Optional[float] = None

    limit: int = 5
    include_expired: bool = False

    def __post_init__(self) -> None:
        if not self.query or not self.query.strip():
            raise ValueError("Memory query cannot be empty.")

        if self.limit <= 0:
            raise ValueError("Memory query limit must be greater than zero.")

        if self.minimum_confidence is not None:
            if not 0.0 <= self.minimum_confidence <= 1.0:
                raise ValueError(
                    "minimum_confidence must be between 0.0 and 1.0."
                )