from abc import ABC, abstractmethod

from domain.repository.repository_source import RepositorySource
from domain.workspace.workspace_artifact import WorkspaceArtifact


class RepositoryMaterializer(ABC):

    @abstractmethod
    async def materialize(
        self,
        source: RepositorySource,
        workspace: WorkspaceArtifact,
    ) -> WorkspaceArtifact:
        raise NotImplementedError