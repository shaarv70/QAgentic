from dataclasses import dataclass, field

from domain.repository.repository_operation import RepositoryOperationType


@dataclass(slots=True)
class RepositoryExecutionOperation:

    operation: RepositoryOperationType

    tool_name: str

    arguments: dict = field(
        default_factory=dict
    )

    depends_on: list[str] = field(
        default_factory=list
    )

    @property
    def requires_approval(self) -> bool:
        return self.operation in {
            RepositoryOperationType.MODIFY,
            RepositoryOperationType.BRANCH,
            RepositoryOperationType.COMMIT,
            RepositoryOperationType.PUSH,
            RepositoryOperationType.PULL_REQUEST,
        }


@dataclass(slots=True)
class RepositoryExecutionPlan:

    plan_id: str

    executable: bool = True

    reason: str | None = None

    requires_approval: bool = False

    operations: list[RepositoryExecutionOperation] = field(
        default_factory=list
    )