import asyncio

from capabilities.base_capability import BaseCapability
from domain.repository.repository_source import RepositorySource
from models.capability_result import CapabilityResult


class RepositoryWorkspaceCapability(BaseCapability):
    """
    Acquires a repository as an execution-ready workspace.

    This capability is responsible only for repository/workspace
    acquisition.

    It does NOT:
        - execute tests
        - execute repository MCP operations
        - communicate directly with MCP
        - decide test commands

    Flow:

        RepositoryWorkspaceCapability
                    ↓
            RepositoryResolver
                    ↓
        WorkspaceService / Materializer
                    ↓
             WorkspaceArtifact
    """

    def __init__(
        self,
        repository_resolver,
    ) -> None:
        self.repository_resolver = repository_resolver

    @property
    def name(self) -> str:
        return "repository_workspace"

    def execute(
        self,
        task,
        context=None,
    ) -> CapabilityResult:

        try:
            repository = self._build_repository_source(task)

            workspace = asyncio.run(
                self.repository_resolver.resolve(
                    repository
                )
            )

            return CapabilityResult(
                status="PASSED",
                data=workspace,
                error=None,
                retryable=False,
            )

        except (
            TypeError,
            ValueError,
            FileNotFoundError,
            NotADirectoryError,
        ) as exc:

            return CapabilityResult(
                status="FAILED",
                data=None,
                error=str(exc),
                retryable=False,
            )

        except Exception as exc:

            return CapabilityResult(
                status="FAILED",
                data=None,
                error=str(exc),
                retryable=True,
            )

    @staticmethod
    def _build_repository_source(
        task,
    ) -> RepositorySource:

        context = task.context or {}

        repository = context.get(
            "repository"
        )

        if repository is None:
            raise ValueError(
                "Repository workspace task requires "
                "'repository' context."
            )

        if not isinstance(repository, dict):
            raise TypeError(
                "Repository workspace task 'repository' "
                "must be a dictionary."
            )

        repository_url = repository.get(
            "url"
        )

        repository_path = repository.get(
            "path"
        )

        branch = repository.get(
            "branch"
        )

        if not repository_url and not repository_path:
            raise ValueError(
                "Repository workspace task requires "
                "either repository 'url' or 'path'."
            )

        return RepositorySource(
            repository_url=repository_url,
            repository_path=repository_path,
            branch=branch,
        )