import json
import re
from datetime import datetime, timezone
from pathlib import Path
import subprocess

from capabilities.repository.ports.repository_materializer import RepositoryMaterializer
from domain.repository.repository_source import RepositorySource
from domain.workspace.workspace_artifact import WorkspaceArtifact
from utils.logger import logger


_META_FILENAME = ".qagentic-meta.json"

# Planner-supplied values that mean "use whatever the remote default is".
_SENTINEL_BRANCHES = {"default", "none", "null", "n/a", "head"}

# Pattern that git emits when the requested branch is absent on the remote.
_BRANCH_NOT_FOUND_PATTERN = re.compile(
    r"remote branch .+ not found", re.IGNORECASE
)


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

        effective_branch = (source.branch or "").strip().lower()
        requested_branch = (
            source.branch
            if source.branch and effective_branch not in _SENTINEL_BRANCHES
            else None
        )

        resolved_branch = self._clone_with_fallback(
            repository_url=source.repository_url,
            workspace_path=workspace_path,
            requested_branch=requested_branch,
        )

        self._validate_materialized_workspace(
            workspace_path=workspace_path,
            repository_url=source.repository_url,
        )

        self._write_meta(
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
                "branch": resolved_branch,
                "commit": None,
            },
        )

    @staticmethod
    def _build_clone_command(
        repository_url: str,
        workspace_path: Path,
        branch: str | None,
    ) -> list[str]:
        command = ["git", "clone"]
        if branch:
            command.extend(["--branch", branch])
        command.extend(["--single-branch", repository_url, str(workspace_path)])
        return command

    def _clone_with_fallback(
        self,
        repository_url: str,
        workspace_path: Path,
        requested_branch: str | None,
    ) -> str | None:
        """
        Attempt to clone, falling back to the remote's actual default branch
        when the requested branch is not found.

        Returns the branch name that was ultimately used (None means the
        remote's default was used without an explicit --branch flag).
        """
        command = self._build_clone_command(
            repository_url=repository_url,
            workspace_path=workspace_path,
            branch=requested_branch,
        )

        try:
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(
                "Git clone completed | workspace=%s | branch=%s | stderr=%s",
                workspace_path,
                requested_branch or "<remote-default>",
                result.stderr.strip(),
            )
            return requested_branch

        except FileNotFoundError as exc:
            raise RuntimeError(
                "Git executable was not found. "
                "Make sure Git is installed and available on PATH."
            ) from exc

        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip()

            # Only attempt fallback when the error is a missing branch, not a
            # network error or auth failure.
            if requested_branch and _BRANCH_NOT_FOUND_PATTERN.search(stderr):
                return self._clone_via_default_branch(
                    repository_url=repository_url,
                    workspace_path=workspace_path,
                    requested_branch=requested_branch,
                    original_error=stderr,
                )

            raise RuntimeError(
                "Failed to clone repository.\n"
                f"Repository: {repository_url}\n"
                f"Branch: {requested_branch or '<remote-default>'}\n"
                f"Error: {stderr}"
            ) from exc

    def _clone_via_default_branch(
        self,
        repository_url: str,
        workspace_path: Path,
        requested_branch: str,
        original_error: str,
    ) -> str | None:
        """
        Resolve the remote's actual default branch and re-attempt the clone.
        Falls back to a no-branch clone if resolution fails.
        """
        default_branch = self._resolve_default_branch(repository_url)

        if default_branch and default_branch != requested_branch:
            logger.warning(
                "Branch '%s' not found on remote; retrying with detected default '%s' | repo=%s",
                requested_branch,
                default_branch,
                repository_url,
            )
            fallback_branch: str | None = default_branch
        else:
            logger.warning(
                "Branch '%s' not found and default branch resolution failed; "
                "retrying without --branch flag | repo=%s",
                requested_branch,
                repository_url,
            )
            fallback_branch = None

        command = self._build_clone_command(
            repository_url=repository_url,
            workspace_path=workspace_path,
            branch=fallback_branch,
        )

        try:
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(
                "Git clone (fallback) completed | workspace=%s | branch=%s | stderr=%s",
                workspace_path,
                fallback_branch or "<remote-default>",
                result.stderr.strip(),
            )
            return fallback_branch

        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                "Failed to clone repository.\n"
                f"Repository: {repository_url}\n"
                f"Requested branch: {requested_branch}\n"
                f"Fallback branch: {fallback_branch or '<remote-default>'}\n"
                f"Original error: {original_error}\n"
                f"Fallback error: {exc.stderr.strip()}"
            ) from exc

    @staticmethod
    def _resolve_default_branch(repository_url: str) -> str | None:
        """
        Query the remote's HEAD symref to determine its default branch name.

        Uses `git ls-remote --symref` which requires no authentication beyond
        what is already needed for cloning and produces no local side-effects.
        """
        try:
            result = subprocess.run(
                ["git", "ls-remote", "--symref", repository_url, "HEAD"],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            # Output line: "ref: refs/heads/<branch>\tHEAD"
            for line in result.stdout.splitlines():
                match = re.match(r"^ref:\s+refs/heads/(\S+)\s+HEAD$", line)
                if match:
                    return match.group(1)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Could not resolve default branch for %s: %s",
                repository_url,
                exc,
            )
        return None

    @staticmethod
    def _write_meta(
        workspace_path: Path,
        repository_url: str,
    ) -> None:
        meta = {
            "repo_url": repository_url,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            (workspace_path / _META_FILENAME).write_text(
                json.dumps(meta, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning(
                "Could not write workspace meta file | path=%s | error=%s",
                workspace_path,
                exc,
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
