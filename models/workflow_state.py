from dataclasses import dataclass
from typing import Any
from models.state import State


@dataclass
class WorkflowState:
    """
    ==========================================================
    Class : WorkflowState
    ==========================================================

    Purpose:
        Wrapper around the application State.

    LangGraph exchanges WorkflowState between nodes,
    while business logic continues to work with State.

    Attribute delegation allows workflow nodes to access
    State attributes directly without writing
    state.app_state everywhere.

    Example:

        state.requirement
        state.plan
        state.artifacts

    instead of

        state.app_state.requirement
        state.app_state.plan
        state.app_state.artifacts
    ==========================================================
    """
    app_state: State

    def update(self, app_state: State) -> None:
        """
        Replace the current application state.
        """
        self.app_state = app_state





