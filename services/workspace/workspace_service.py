from abc import ABC, abstractmethod

from domain.repository.repository_source import RepositorySource
from domain.workspace.workspace_artifact import WorkspaceArtifact


class WorkspaceService(ABC):

    @abstractmethod
    async def prepare(
        self,
        source: RepositorySource,
    ) -> WorkspaceArtifact:
        raise NotImplementedError

    @abstractmethod
    async def cleanup(
        self,
        workspace: WorkspaceArtifact,
    ) -> None:
        raise NotImplementedError