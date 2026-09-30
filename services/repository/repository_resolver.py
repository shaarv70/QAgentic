from pathlib import Path

from capabilities.repository.ports.repository_materializer import (
    RepositoryMaterializer,
)
from domain.repository.repository_source import RepositorySource
from domain.workspace.workspace_artifact import WorkspaceArtifact
from services.workspace.workspace_service import WorkspaceService


class RepositoryResolver:
    """
    Resolves a repository source into an execution-ready workspace.

    This class coordinates workspace allocation and repository
    materialization. It does not execute tests.
    """

    def __init__(
        self,
        workspace_service: WorkspaceService,
        repository_materializer: RepositoryMaterializer,
    ) -> None:
        self.workspace_service = workspace_service
        self.repository_materializer = repository_materializer

    async def resolve(
        self,
        source: RepositorySource,
    ) -> WorkspaceArtifact:

        if source.is_local:
            return self._resolve_local(source)

        if source.is_remote:
            return await self._resolve_remote(source)

        raise ValueError(
            "Unsupported repository source."
        )

    def _resolve_local(
    self,
    source: RepositorySource,
) -> WorkspaceArtifact:
        if not source.repository_path:
            raise ValueError(
                "repository_path is required for local repository resolution."
            )

        path = Path(source.repository_path)

        if not path.exists():
            raise ValueError(
                f"Repository path does not exist: {path}"
            )

        if not path.is_dir():
            raise ValueError(
                f"Repository path is not a directory: {path}"
            )

        return WorkspaceArtifact(
            path=str(path),
            repository={
                "url": source.repository_url,
                "path": str(path),
                "branch": source.branch,
                "commit": None,
            },
        )

    async def _resolve_remote(
        self,
        source: RepositorySource,
    ) -> WorkspaceArtifact:

        workspace = await self.workspace_service.prepare(
            source
        )

        try:
            return await self.repository_materializer.materialize(
                source=source,
                workspace=workspace,
            )

        except Exception:
            await self.workspace_service.cleanup(
                workspace
            )
            raise