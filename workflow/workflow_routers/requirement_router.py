from langgraph.graph import END

from models.workflow_state import WorkflowState
from workflow.constants import (
    READY,
    NEEDS_CLARIFICATION,
    PLANNER
)


def requirement_router(state: WorkflowState) -> str:
    """
    ==========================================================
    Requirement Router
    ==========================================================

    Determines the next workflow node based on the
    Requirement Intelligence result.

    READY
        -> Planner

    NEEDS_CLARIFICATION
        -> END
    ==========================================================
    """

    app_state = state.app_state

    intelligence = app_state.requirement_intelligence

    if intelligence is None:
        raise RuntimeError(
            "Requirement Intelligence not available."
        )

    if intelligence.status == READY:
        return PLANNER

    if intelligence.status == NEEDS_CLARIFICATION:
        return END

    raise RuntimeError(
        f"Unknown Requirement Intelligence Status : "
        f"{intelligence.status}"
    )