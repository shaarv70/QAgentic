from dataclasses import dataclass, field
from typing import Any

from domain.repository.repository_execution_plan import (
    RepositoryExecutionPlan,
)


@dataclass(slots=True)
class RepositoryExecutionCheckpoint:
    """
    Persistent execution state for one repository execution plan.

    This checkpoint allows repository execution to pause before a
    mutating operation and resume later without regenerating the
    execution plan.

    Example:

        plan:
            0 -> read_file
            1 -> modify_file
            2 -> commit

        current_operation_index:
            1

        pending_approval_request_id:
            "approval-123"

    After approval:

        current_operation_index:
            remains 1

    The provider then executes operation 1 and advances to 2.
    """

    plan_id: str

    # --------------------------------------------------------------
    # The generated plan is stored here.
    #
    # This is important because on resume we must NOT ask the LLM
    # to create another plan.
    # --------------------------------------------------------------
    plan: RepositoryExecutionPlan | None = None

    # --------------------------------------------------------------
    # Index of the operation currently being processed.
    # --------------------------------------------------------------
    current_operation_index: int = 0

    # --------------------------------------------------------------
    # Results from operations already executed.
    #
    # These are required for resolving references such as:
    #
    # "$result.search_file.path"
    # --------------------------------------------------------------
    results: list[dict[str, Any]] = field(
        default_factory=list
    )

    # --------------------------------------------------------------
    # Approval request associated with the operation currently
    # waiting for authorization.
    # --------------------------------------------------------------
    pending_approval_request_id: str | None = None

    # --------------------------------------------------------------
    # Final execution state.
    # --------------------------------------------------------------
    completed: bool = False
    rejected: bool = False
    rejection_reason: str | None = None

    @property
    def has_pending_approval(self) -> bool:
        return (
            self.pending_approval_request_id
            is not None
        )