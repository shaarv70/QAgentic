from typing import Any

from capabilities.base_capability import BaseCapability
from models.capability_result import CapabilityResult


class RepositoryAnalysisCapability(BaseCapability):
    """
    Capability for analyzing an acquired repository workspace.

    This capability does not perform repository discovery itself and
    does not execute tests.

    Its responsibility is to invoke the specialized
    RepositoryAnalysisAgent and return a structured
    RepositoryExecutionProfile.
    """



    def __init__(self, repository_analysis_agent):
        super().__init__()
        self.repository_analysis_agent = repository_analysis_agent

    @property
    def name(self) -> str:
        return "repository_analysis"

    def execute(
        self,
        task: Any,
        context: Any = None,
    ) -> CapabilityResult:

        try:
            workspace_path = self._resolve_workspace_path(
                task,
                context,
            )

            if not workspace_path:
                return CapabilityResult(
                    status="FAILED",
                    error=(
                        "Repository analysis requires "
                        "a workspace path."
                    ),
                    retryable=False,
                )

            requested_suite = self._resolve_requested_suite(task)

            analysis_context = {
                "workspace_path": workspace_path,
                "requested_suite": requested_suite,
            }

            profile = self.repository_analysis_agent.execute(
                analysis_context
            )

            return CapabilityResult(
                status="PASSED",
                data=profile,
                retryable=False,
            )

        except ValueError as exc:
            return CapabilityResult(
                status="FAILED",
                error=str(exc),
                retryable=False,
            )

        except Exception as exc:
            return CapabilityResult(
                status="FAILED",
                error=f"Repository analysis failed: {exc}",
                retryable=True,
            )

    def _resolve_workspace_path(
    self,
    task,
    context,
) -> str | None:

        # Direct workspace path from execution context
        if isinstance(context, dict):
            workspace_path = context.get("workspace_path")

            if workspace_path:
                return self._extract_path(workspace_path)

        # ExecutionContext exposes dependency artifacts
        dependency_artifacts = getattr(
            context,
            "dependency_artifacts",
            None,
        )

        if isinstance(dependency_artifacts, dict):
            for artifact in dependency_artifacts.values():
                path = self._extract_path(artifact)

                if path:
                    return path

        # Direct workspace information from task context
        task_context = getattr(
            task,
            "context",
            None,
        )

        if isinstance(task_context, dict):

            workspace_path = task_context.get(
                "workspace_path"
            )

            if workspace_path:
                return self._extract_path(
                    workspace_path
                )

            workspace = task_context.get(
                "workspace"
            )

            if workspace:
                path = self._extract_path(
                    workspace
                )

                if path:
                    return path

        # Legacy/direct dependency information
        dependencies = getattr(
            task,
            "dependencies",
            None,
        )

        if dependencies:

            for dependency in dependencies:

                path = self._extract_path(
                    dependency
                )

                if path:
                    return path

        return None

    @staticmethod
    def _resolve_requested_suite(task) -> str | None:

        task_context = getattr(
            task,
            "context",
            None,
        )

        if not isinstance(task_context, dict):
            return None

        requested_suite = task_context.get(
            "test_category"
        )

        if requested_suite:
            return str(requested_suite)

        requested_suite = task_context.get(
            "suite"
        )

        if requested_suite:
            return str(requested_suite)

        return None

    @staticmethod
    def _extract_path(value) -> str | None:

        if isinstance(value, str):
            return value

        if isinstance(value, dict):

            path = value.get("path")

            if path:
                return str(path)

            data = value.get("data")

            if isinstance(data, dict):

                path = data.get("path")

                if path:
                    return str(path)

        path = getattr(
            value,
            "path",
            None,
        )

        if path:
            return str(path)

        data = getattr(
            value,
            "data",
            None,
        )

        if isinstance(data, dict):

            path = data.get("path")

            if path:
                return str(path)

        return None