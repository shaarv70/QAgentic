from typing import Any

from capabilities.base_capability import BaseCapability
from models.capability_result import CapabilityResult
from models.repository_execution_profile import RepositoryExecutionProfile
from utils.logger import logger


class TestGapAnalysisCapability(BaseCapability):
    """
    Analyses test coverage gaps for a repository workspace.

    Depends on a completed repository_analysis task that produced a
    RepositoryExecutionProfile.  Reads the actual test file contents
    (not just paths) and asks the LLM to identify untested scenarios.
    """

    def __init__(self, test_gap_analysis_service) -> None:
        super().__init__()
        self.test_gap_analysis_service = test_gap_analysis_service

    @property
    def name(self) -> str:
        return "test_gap_analysis"

    def execute(self, task: Any, context: Any = None) -> CapabilityResult:
        try:
            workspace_path, profile = self._resolve_inputs(task, context)

            if not workspace_path:
                return CapabilityResult(
                    status="FAILED",
                    error="test_gap_analysis requires a workspace path.",
                    retryable=False,
                )

            report = self.test_gap_analysis_service.analyze(
                workspace_path=workspace_path,
                profile=profile,
            )

            logger.info(
                "Test gap analysis complete | workspace=%s | "
                "gaps=%d | coverage=%.0f%%",
                workspace_path,
                len(report.gaps),
                report.coverage_estimate * 100,
            )

            return CapabilityResult(
                status="PASSED",
                data=report,
                retryable=False,
            )

        except Exception as exc:
            return CapabilityResult(
                status="FAILED",
                error=f"Test gap analysis failed: {exc}",
                retryable=False,
            )

    # ------------------------------------------------------------------

    def _resolve_inputs(
        self, task: Any, context: Any
    ) -> tuple[str | None, Any]:
        """Return (workspace_path, profile) from dependency artifacts."""

        dependency_artifacts = getattr(context, "dependency_artifacts", {}) or {}
        profile = None
        workspace_path = None

        for artifact in dependency_artifacts.values():
            if isinstance(artifact, RepositoryExecutionProfile):
                profile = artifact
                workspace_path = getattr(artifact, "working_directory", None)
                break
            # Artifact may be wrapped in a dict or dataclass
            if isinstance(artifact, dict):
                inner = artifact.get("data") or artifact.get("profile")
                if isinstance(inner, RepositoryExecutionProfile):
                    profile = inner
                    workspace_path = getattr(inner, "working_directory", None)
                    break

        # Fall back to task context
        if not workspace_path:
            task_context = getattr(task, "context", None) or {}
            if isinstance(task_context, dict):
                workspace_path = (
                    task_context.get("workspace_path")
                    or task_context.get("repository_path")
                )

        return workspace_path, profile
