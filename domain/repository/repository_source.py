from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RepositorySource:
    """
    Describes the source repository used for test execution.

    A repository can be:
        - local
        - remote Git repository

    Exactly one of repository_path or repository_url should normally
    be provided.
    """

    repository_path: Optional[str] = None
    repository_url: Optional[str] = None
    branch: Optional[str] = None

    def __post_init__(self) -> None:

        if not self.repository_path and not self.repository_url:
            raise ValueError(
                "Either repository_path or repository_url "
                "must be provided."
            )

        if self.repository_path and self.repository_url:
            raise ValueError(
                "repository_path and repository_url cannot "
                "both be provided."
            )

    @property
    def is_local(self) -> bool:
        return self.repository_path is not None

    @property
    def is_remote(self) -> bool:
        return self.repository_url is not None