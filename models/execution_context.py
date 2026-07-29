class ExecutionContext:

    def __init__(
        self,
        requirement,
        dependency_artifacts=None
    ):
        self.requirement = requirement
        self.dependency_artifacts = (
            dependency_artifacts or {}
        )