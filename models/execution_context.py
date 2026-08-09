from models.artifact import Artifact


class ExecutionContext:


    requirement: str
    dependency_artifacts: dict[str,Artifact]


    def __init__(self,requirement,dependency_artifacts=None):
        self.requirement = requirement
        self.dependency_artifacts = (dependency_artifacts or {})