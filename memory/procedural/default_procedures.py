from datetime import datetime, timezone

from memory.models.memory_category import MemoryCategory
from memory.models.memory_entry import MemoryEntry
from memory.models.memory_types import (
    MemoryImportance,
    MemoryScope,
    MemorySource,
    MemoryType,
)


def get_default_procedures() -> list[MemoryEntry]:

    now = datetime.now(timezone.utc)

    return [

        MemoryEntry(
            id="proc_common_requirement_grounding_v1",
            content=(
                "When generating QA artifacts from a requirement, "
                "base the generated content on information supported "
                "by the requirement and available project knowledge. "
                "Do not invent undocumented product-specific behavior."
            ),
            category=MemoryCategory.PROCEDURAL,
            memory_type=MemoryType.DECISION,
            scope=MemoryScope.WORKFLOW,
            source=MemorySource.SYSTEM,
            importance=MemoryImportance.HIGH,
            confidence=1.0,
            created_at=now,
            updated_at=now,
            metadata={
                "capability": "common",
                "rule": "requirement_grounding",
                "version": "1.0",
            },
        ),

        MemoryEntry(
            id="proc_common_review_correction_v1",
            content=(
                "When a generated QA artifact fails quality review, "
                "use the reviewer feedback to correct the artifact "
                "and review the corrected artifact again until it "
                "passes review or the configured retry limit is reached."
            ),
            category=MemoryCategory.PROCEDURAL,
            memory_type=MemoryType.WORKFLOW_PATTERN,
            scope=MemoryScope.WORKFLOW,
            source=MemorySource.SYSTEM,
            importance=MemoryImportance.HIGH,
            confidence=1.0,
            created_at=now,
            updated_at=now,
            metadata={
                "capability": "common",
                "rule": "review_correction_cycle",
                "version": "1.0",
            },
        ),

    ]