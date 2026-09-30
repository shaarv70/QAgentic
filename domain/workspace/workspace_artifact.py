from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class WorkspaceArtifact:
    """
    Execution-ready repository workspace.

    `path` remains a first-class property because execution
    capabilities need the physical workspace location.

    Repository metadata is grouped under `repository` so the
    artifact has a stable, generic contract for downstream
    capabilities, review, reporting, and serialization.
    """

    path: str
    repository: dict[str, Any] | None = None

    @property
    def repository_url(self) -> str | None:
        if not self.repository:
            return None

        return self.repository.get("url")

    @property
    def branch(self) -> str | None:
        if not self.repository:
            return None

        return self.repository.get("branch")

    @property
    def commit(self) -> str | None:
        if not self.repository:
            return None

        return self.repository.get("commit")