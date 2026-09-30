import uuid
from pathlib import Path

from domain.repository.repository_source import RepositorySource
from domain.workspace.workspace_artifact import WorkspaceArtifact
from services.workspace.workspace_service import WorkspaceService


class LocalWorkspaceService(WorkspaceService):

    def __init__(
        self,
        base_directory: str = ".qagentic/workspaces",
    ) -> None:
        self.base_directory = Path(base_directory)




    async def prepare(
        self,
        source: RepositorySource,
    ) -> WorkspaceArtifact:

        self.base_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        workspace_path = (
            self.base_directory / str(uuid.uuid4())
        )

        # IMPORTANT:
        # Do not create the final directory here.
        # git clone needs to create/populate it.
        return WorkspaceArtifact(
                    path=str(workspace_path),
                    repository={
                        "url": source.repository_url,
                        "path": str(workspace_path),
                        "branch": source.branch,
                        "commit": None,
                    },
                )




    async def cleanup(
        self,
        workspace: WorkspaceArtifact,
    ) -> None:

        path = Path(workspace.path)

        if not path.exists():
            return

        if not path.is_dir():
            raise ValueError(
                f"Workspace path is not a directory: {workspace.path}"
            )

        import shutil

        shutil.rmtree(path)