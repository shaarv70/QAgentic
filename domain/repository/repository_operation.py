from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RepositoryOperationType(str, Enum):
    CLONE = "clone"
    INSPECT = "inspect"
    READ = "read"
    SEARCH = "search"
    MODIFY = "modify"
    VALIDATE = "validate"
    DIFF = "diff"
    BRANCH = "branch"
    COMMIT = "commit"
    PUSH = "push"
    PULL_REQUEST = "pull_request"


@dataclass(frozen=True, slots=True)
class RepositoryOperation:
    operation: RepositoryOperationType
    arguments: dict[str, Any] = field(default_factory=dict)

    @property
    def is_mutating(self) -> bool:
        return self.operation in {
            RepositoryOperationType.MODIFY,
            RepositoryOperationType.BRANCH,
            RepositoryOperationType.COMMIT,
            RepositoryOperationType.PUSH,
            RepositoryOperationType.PULL_REQUEST,
        }

    @property
    def requires_approval(self) -> bool:
        return self.is_mutating