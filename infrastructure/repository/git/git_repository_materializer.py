from pathlib import Path
import subprocess

from capabilities.repository.ports.repository_materializer import RepositoryMaterializer
from domain.repository.repository_source import RepositorySource
from domain.workspace.workspace_artifact import WorkspaceArtifact
from utils.logger import logger


class GitRepositoryMaterializer(RepositoryMaterializer):
    """
    Materializes a remote Git repository into an execution-ready workspace.

    The materializer is responsible for proving that the clone produced a
    usable repository workspace before returning a WorkspaceArtifact.
    """

    async def materialize(
        self,
        source: RepositorySource,
        workspace: WorkspaceArtifact,
    ) -> WorkspaceArtifact:
        if not source.repository_url:
            raise ValueError(
                "repository_url is required for remote Git materialization."
            )

        workspace_path = Path(workspace.path).expanduser().resolve()

        logger.info(
            "Git materializer runtime | module=%s | cwd=%s | workspace=%s",
            __file__,
            Path.cwd(),
            workspace_path,
        )

        workspace_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        command = ["git", "clone"]

        if source.branch:
            command.extend(["--branch", source.branch])

        command.extend(
            [
                "--single-branch",
                source.repository_url,
                str(workspace_path),
            ]
        )

        try:
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )

            logger.info(
                "Git clone completed | workspace=%s | return_code=%s | stdout=%s | stderr=%s",
                workspace_path,
                result.returncode,
                result.stdout.strip(),
                result.stderr.strip(),
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "Git executable was not found. "
                "Make sure Git is installed and available on PATH."
            ) from exc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                "Failed to clone repository.\n"
                f"Repository: {source.repository_url}\n"
                f"Branch: {source.branch}\n"
                f"Error: {exc.stderr.strip()}"
            ) from exc

        self._validate_materialized_workspace(
            workspace_path=workspace_path,
            repository_url=source.repository_url,
        )

        entries = sorted(
            entry.name
            for entry in workspace_path.iterdir()
        )

        logger.info(
            "Git materializer validation passed | workspace=%s | entries=%s",
            workspace_path,
            entries,
        )

        return WorkspaceArtifact(
            path=str(workspace_path),
            repository={
                "url": source.repository_url,
                "path": str(workspace_path),
                "branch": source.branch,
                "commit": None,
            },
        )

    @staticmethod
    def _validate_materialized_workspace(
        workspace_path: Path,
        repository_url: str,
    ) -> None:
        if not workspace_path.exists():
            raise RuntimeError(
                "Git clone completed but the workspace was not created. "
                f"Repository: {repository_url} "
                f"Workspace: {workspace_path}"
            )

        if not workspace_path.is_dir():
            raise RuntimeError(
                "Git clone completed but the workspace path is not a directory. "
                f"Repository: {repository_url} "
                f"Workspace: {workspace_path}"
            )

        git_metadata = workspace_path / ".git"

        if not git_metadata.exists():
            raise RuntimeError(
                "Git clone completed but the workspace does not contain "
                f"Git metadata. Repository: {repository_url} "
                f"Workspace: {workspace_path}"
            )

        repository_entries = [
            entry
            for entry in workspace_path.iterdir()
            if entry.name != ".git"
        ]

        logger.info(
            "Git materializer validation | workspace=%s | exists=%s | is_dir=%s | git_metadata=%s | repository_entries=%s",
            workspace_path,
            workspace_path.exists(),
            workspace_path.is_dir(),
            git_metadata.exists(),
            sorted(entry.name for entry in repository_entries),
        )

        if not repository_entries:
            raise RuntimeError(
                "Git clone completed but the workspace contains no repository "
                f"content. Repository: {repository_url} "
                f"Workspace: {workspace_path}"
            )
