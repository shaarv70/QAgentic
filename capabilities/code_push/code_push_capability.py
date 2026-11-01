import asyncio
import json

from capabilities.base_capability import BaseCapability
from models.capability_result import CapabilityResult
from models.approval_model import ApprovalRequest, ApprovalStatus
from models.automation_artifact import AutomationArtifact
from domain.workspace.workspace_artifact import WorkspaceArtifact
from utils.logger import logger


class CodePushCapability(BaseCapability):
    """
    Writes generated (or self-healed) test automation files to the source
    repository, creates a branch, commits, pushes, and optionally opens a PR.

    A guardrail approval pause is always inserted before any git mutation.

    Phase 1 — prepare:
        Gather the automation files and workspace path, compute a branch name
        and commit message, then surface an ApprovalRequest for the user.

    Phase 2 — push (after approval):
        Write files, git checkout -b, git add, git commit, git push, gh pr create.
    """

    review_required = False

    def __init__(self, approval_service, code_push_service) -> None:
        super().__init__()
        self.approval_service = approval_service
        self.code_push_service = code_push_service

    @property
    def name(self) -> str:
        return "code_push"

    def execute(self, task, context=None) -> CapabilityResult:
        request_id = f"code_push_{task.task_id}"

        approval = asyncio.run(self._get_approval(request_id))

        # Phase 2: already approved — execute push
        if approval is not None and approval.status == ApprovalStatus.APPROVED:
            return self._execute_push(task, context, approval.details)

        # Rejected
        if approval is not None and approval.status == ApprovalStatus.REJECTED:
            return CapabilityResult(
                status="FAILED",
                data=None,
                error="Code push was rejected by the user.",
                retryable=False,
            )

        # Phase 1: prepare and request approval
        try:
            automation_artifact = self._find_automation_artifact(context)
            workspace_artifact = self._find_workspace_artifact(context)

            if automation_artifact is None:
                return CapabilityResult(
                    status="FAILED",
                    data=None,
                    error=(
                        "code_push requires an AutomationArtifact dependency. "
                        "Ensure the plan includes an 'automation' task."
                    ),
                    retryable=False,
                )

            if workspace_artifact is None:
                return CapabilityResult(
                    status="FAILED",
                    data=None,
                    error=(
                        "code_push requires a repository_workspace dependency. "
                        "Ensure the plan includes a 'repository_workspace' task."
                    ),
                    retryable=False,
                )

            plan = self.code_push_service.prepare(
                task=task,
                context=context,
                automation_artifact=automation_artifact,
                workspace_artifact=workspace_artifact,
            )

            approval_request = ApprovalRequest(
                request_id=request_id,
                action="code_push",
                description=(
                    f"Push {plan['file_count']} file(s) to new branch "
                    f"'{plan['branch_name']}' and open a PR"
                ),
                details=plan,
            )

            asyncio.run(self.approval_service.create_request(approval_request))

            logger.info(
                "code_push: approval requested | branch=%s | files=%d",
                plan["branch_name"],
                plan["file_count"],
            )

            return CapabilityResult(
                status="PENDING_APPROVAL",
                data={"approval_request": approval_request},
                retryable=False,
            )

        except Exception as exc:
            logger.exception("code_push: prepare failed: %s", exc)
            return CapabilityResult(
                status="FAILED",
                data=None,
                error=str(exc),
                retryable=True,
            )

    def _execute_push(self, task, context, plan: dict) -> CapabilityResult:
        try:
            automation_artifact = self._find_automation_artifact(context)

            if automation_artifact is None:
                return CapabilityResult(
                    status="FAILED",
                    data=None,
                    error="Automation artifact not available during push execution.",
                    retryable=False,
                )

            result = self.code_push_service.push(
                plan=plan,
                automation_artifact=automation_artifact,
            )

            logger.info(
                "code_push: completed | branch=%s | files=%d | pr=%s",
                result.get("branch"),
                result.get("files_committed"),
                result.get("pr_url") or "n/a",
            )

            return CapabilityResult(
                status="PASSED",
                data=result,
                error=None,
            )

        except Exception as exc:
            logger.exception("code_push: push failed: %s", exc)
            return CapabilityResult(
                status="FAILED",
                data=None,
                error=str(exc),
                retryable=True,
            )

    # ==========================================================
    # Artifact helpers
    # ==========================================================

    @staticmethod
    def _find_automation_artifact(context) -> AutomationArtifact | None:
        dependency_artifacts = (
            getattr(context, "dependency_artifacts", None) or {}
        )
        if not isinstance(dependency_artifacts, dict):
            return None

        for artifact in dependency_artifacts.values():
            if isinstance(artifact, AutomationArtifact):
                return artifact

            if isinstance(artifact, str):
                try:
                    return AutomationArtifact.from_llm_content(artifact)
                except (ValueError, TypeError, json.JSONDecodeError):
                    continue

            if isinstance(artifact, dict):
                try:
                    return AutomationArtifact.from_dict(artifact)
                except (ValueError, TypeError):
                    continue

        return None

    @staticmethod
    def _find_workspace_artifact(context) -> WorkspaceArtifact | None:
        dependency_artifacts = (
            getattr(context, "dependency_artifacts", None) or {}
        )
        if not isinstance(dependency_artifacts, dict):
            return None

        for artifact in dependency_artifacts.values():
            if isinstance(artifact, WorkspaceArtifact):
                return artifact

        return None

    async def _get_approval(self, request_id: str):
        try:
            return await self.approval_service.get_request(request_id)
        except KeyError:
            return None
