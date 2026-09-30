from typing import Any


class ExecutionContext:
    """
    Runtime context supplied to capabilities during execution.

    The context contains:
        - the original workflow requirement
        - outputs produced by dependency tasks

    Dependency artifacts are intentionally represented as Any
    because capabilities may produce different artifact types,
    for example:

        - strings
        - dictionaries
        - execution results
        - WorkspaceArtifact
        - provider-specific results
    """

    requirement: str
    dependency_artifacts: dict[str, Any]
    workflow_state: Any | None


    def __init__(
        self,
        requirement: str,
        dependency_artifacts: dict[str, Any] | None = None,
        workflow_state: Any | None = None,
    ) -> None:

        self.requirement = requirement

        self.dependency_artifacts = dependency_artifacts or {}

        self.workflow_state = workflow_state