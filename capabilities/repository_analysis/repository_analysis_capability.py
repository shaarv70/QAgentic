import re
from pathlib import Path
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

            # Fail fast (non-retryable) when the workspace path doesn't exist.
            # This happens when the planner incorrectly adds repository_analysis
            # for a pure generate flow with no existing repository or directory.
            from pathlib import Path as _Path
            if not _Path(workspace_path).exists():
                return CapabilityResult(
                    status="FAILED",
                    error=(
                        f"Repository analysis skipped: workspace does not "
                        f"exist at '{workspace_path}'. This task should not "
                        f"be included in a pure generate flow."
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
                retryable=False,
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

            # Local path requirement — planner sets repository_path
            # when the user supplies a local directory instead of a URL.
            repository_path = task_context.get(
                "repository_path"
            )

            if repository_path:
                return self._extract_path(
                    repository_path
                )

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

        # Last resort: scan every string value in the task context
        # for a local filesystem path.  The requirement string always
        # contains exactly what the user typed, regardless of which
        # key name the LLM chose.
        if isinstance(task_context, dict):
            for value in task_context.values():
                if isinstance(value, str):
                    path = self._extract_local_path(value)
                    if path:
                        return path

        return None

    @staticmethod
    def _extract_local_path(text: str) -> str | None:
        """
        Find the first local filesystem path in a string and return it
        if it actually exists on disk.

        Handles single-backslash (C:\\dir) and double-backslash
        (C:\\\\dir, from JSON serialization) Windows paths, and Unix
        absolute paths (/...).
        """
        # Normalize double backslashes so JSON-serialized paths work correctly.
        normalized = text.replace("\\\\", "\\")
        patterns = [
            r"[A-Za-z]:\\(?:[^\s\\/:*?\"<>|]+\\)*[^\s\\/:*?\"<>|]*",
            r"/(?:[^\s/]+/)*[^\s/]+",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, normalized):
                candidate = match.group(0).rstrip(".,;)")
                if candidate and Path(candidate).exists():
                    return candidate
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

        for key in (
            "test_identifier",
            "test_name",
            "suite",
            "test_category",
            "test_file",
            "spec",
            "test",
        ):
            value = task_context.get(key)
            if value and isinstance(value, str):
                return value.strip()

        # Fallback: parse the requirement string.
        # Handles patterns like "Run <TestName> test(s) in C:\..."
        # where the planner did not explicitly store the suite name.
        requirement_str = task_context.get("requirement", "")
        if isinstance(requirement_str, str) and requirement_str.strip():
            match = re.search(
                r"\b([A-Z][A-Za-z0-9_]+)\s+tests?\b",
                requirement_str,
            )
            if match:
                return match.group(1).strip()

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