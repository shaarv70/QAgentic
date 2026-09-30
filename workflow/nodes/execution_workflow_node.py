


from dataclasses import asdict
import asyncio

from config import MAX_REVIEW_RETRIES
from models.workflow_state import WorkflowState
from utils.logger import logger
from workflow.constants import EXECUTION, REVIEW
from workflow.nodes.base_workflow__node import BaseWorkflowNode


from langgraph.types import interrupt

from models.approval_model import ApprovalStatus


class ExecutionWorkflowNode(BaseWorkflowNode):
    """
=====================================================
Class : ExecutionWorkflowNode
=====================================================

Purpose:
    Execute the complete artifact generation workflow.

Created By:
    NodeRegistry

Called By:
    LangGraph Runtime

Calls:
    ExecutionAgent
    ReviewAgent
    ApprovalService

Receives:
    WorkflowState

Returns:
    Updated WorkflowState

Stores:
    ExecutionAgent
    ReviewAgent
    EpisodeService
    ApprovalService

Does NOT Know:
    Requirement
    Planner

Reason:
    Encapsulates the complete execution lifecycle
    (dependency execution + quality review).

Approval:
    Repository mutations can return PENDING_APPROVAL.
    LangGraph interrupt() pauses the workflow at that
    exact point. The workflow is resumed using the same
    checkpoint/thread, so completed operations are not
    executed again.
"""

    def __init__(
        self,
        agent_registry,
        episode_service,
        approval_service,
    ):
        self.execution_agent = agent_registry.get(EXECUTION)
        self.review_agent = agent_registry.get(REVIEW)
        self.episode_service = episode_service
        self.approval_service = approval_service

    def execute(
        self,
        state: WorkflowState,
    ) -> WorkflowState:

        app_state = state.app_state

        if app_state.plan is None:
            raise RuntimeError(
                "ExecutionWorkflowNode cannot execute "
                "because no execution plan was found."
            )

        # ----------------------------------------------------------
        # Resume an approval interruption.
        # ----------------------------------------------------------

        if app_state.pending_approval is not None:

            self._handle_pending_approval(
                app_state
            )

            checkpoint = (
                app_state.repository_execution_checkpoint
            )

            if (
                checkpoint is not None
                and checkpoint.rejected
            ):

                app_state.status = "FAILED"
                state.app_state = app_state

                return state

        # ----------------------------------------------------------
        # Execute until complete or interrupted.
        # ----------------------------------------------------------

        while not self._is_execution_complete(
            app_state
        ):

            ready_tasks = (
                self._fetch_ready_tasks(
                    app_state
                )
            )

            candidate_artifacts = (
                self._execute_ready_tasks(
                    ready_tasks,
                    app_state,
                )
            )

            pending_artifact = (
                self._find_pending_approval(
                    candidate_artifacts
                )
            )

            if pending_artifact is not None:

                self._pause_for_approval(
                    pending_artifact,
                    app_state,
                )

                # IMPORTANT:
                # On the first execution interrupt() raises and the
                # workflow is checkpointed here.
                #
                # On resume, interrupt() returns the human decision
                # and _process_approval_decision() updates the
                # approval service/checkpoint.
                #
                # We MUST NOT review the stale PENDING_APPROVAL
                # artifact. Continue the execution loop so the
                # capability calls the repository provider again.
                #
                # The repository checkpoint guarantees that the
                # same operation resumes and that already successful
                # operations are not repeated.

                checkpoint = (
                    app_state.repository_execution_checkpoint
                )

                if (
                    checkpoint is not None
                    and checkpoint.rejected
                ):
                    app_state.status = "FAILED"
                    state.app_state = app_state
                    return state

                continue

            self._review_artifacts(
                ready_tasks,
                candidate_artifacts,
                app_state,
            )

        state.app_state = app_state

        return state


    # ==========================================================
    # TASK EXECUTION
    # ==========================================================

    def _fetch_ready_tasks(self, state):

        ready_tasks = self.execution_agent.get_ready_tasks(
            state
        )

        if not ready_tasks:
            raise RuntimeError(
                "Workflow cannot progress. "
                "Possible circular dependency, "
                "invalid dependency, or failed upstream task."
            )

        logger.info(
            "Ready tasks: "
            f"{[task.task_id for task in ready_tasks]}"
        )

        return ready_tasks

    def _execute_ready_tasks(
        self,
        ready_tasks,
        state,
    ):

        return self.execution_agent.execute_tasks(
            ready_tasks,
            state,
        )

    # ==========================================================
    # APPROVAL
    # ==========================================================

    def _find_pending_approval(
        self,
        candidate_artifacts,
    ):
        """
        Find the artifact whose capability execution is waiting
        for human approval.

        Only one approval boundary should be active at a time.
        """

        for artifact in candidate_artifacts:

            if artifact.status == "PENDING_APPROVAL":
                return artifact

        return None

    def _pause_for_approval(
        self,
        artifact,
        state,
    ):
        """
        Pause workflow execution immediately before the
        repository mutation.

        The approval request is stored in application state so
        the caller can display it to the user.
        """

        if not isinstance(artifact.content, dict):
            raise RuntimeError(
                "Pending approval artifact must contain "
                "a dictionary payload."
            )

        approval_request = artifact.content.get(
            "approval_request"
        )

        if approval_request is None:
            raise RuntimeError(
                "Repository operation requires approval, "
                "but no approval request was returned."
            )

        # --------------------------------------------------
        # Convert dataclass approval request into a normal
        # dictionary for LangGraph interrupt payload.
        # --------------------------------------------------

        if hasattr(approval_request, "__dataclass_fields__"):
            request_payload = asdict(
                approval_request
            )
        elif isinstance(approval_request, dict):
            request_payload = approval_request
        else:
            raise RuntimeError(
                "Unsupported approval request format."
            )

        # --------------------------------------------------
        # Store the request in application state.
        # --------------------------------------------------

        state.pending_approval = request_payload

        logger.info(
            "Repository operation requires approval | "
            f"request_id={request_payload.get('request_id')} | "
            f"action={request_payload.get('action')}"
        )

        # --------------------------------------------------
        # LangGraph checkpoint/interrupt.
        #
        # The workflow pauses here.
        #
        # IMPORTANT:
        # No repository mutation has happened yet.
        # --------------------------------------------------

        decision = interrupt(
            request_payload
        )

        # --------------------------------------------------
        # The workflow reaches this point only after resume.
        # --------------------------------------------------

        self._process_approval_decision(
            decision,
            state,
        )

    def _process_approval_decision(
        self,
        decision,
        state,
    ):
        """
        Process the human decision received when the
        interrupted workflow resumes.
        """

        request_id = state.pending_approval.get(
            "request_id"
        )

        if not request_id:
            raise RuntimeError(
                "Pending approval does not contain "
                "a request_id."
            )

        normalized_decision = str(
            decision
        ).strip().lower()

        if normalized_decision in {
            "approve",
            "approved",
            "yes",
            "y",
        }:

            asyncio.run(
                self.approval_service.approve(
                    request_id
                )
            )

            logger.info(
                "Repository operation approved | "
                f"request_id={request_id}"
            )

            state.pending_approval = None
            return

        if normalized_decision in {
            "reject",
            "rejected",
            "no",
            "n",
        }:

            asyncio.run(
                self.approval_service.reject(
                    request_id
                )
            )

            logger.info(
                "Repository operation rejected | "
                f"request_id={request_id}"
            )

            state.pending_approval = None

            checkpoint = (
                state.repository_execution_checkpoint
            )

            if checkpoint is not None:
                checkpoint.rejected = True
                checkpoint.rejection_reason = (
                    "Repository operation was rejected "
                    "by the user."
                )

            return

        raise ValueError(
            "Invalid approval decision. "
            "Expected approve or reject."
        )


     # ==========================================================
    # RESUME CHECK
    # ==========================================================



    # ==========================================================
    # REVIEW
    # ==========================================================

    def _review_artifacts(
        self,
        ready_tasks,
        candidate_artifacts,
        state,
    ):

        for artifact in candidate_artifacts:

            task = next(
                task
                for task in ready_tasks
                if task.task_id == artifact.task_id
            )

            artifact = self._quality_check(
                task,
                artifact,
                state,
            )

            if (
                not artifact.review
                or artifact.review.status != "PASS"
            ):
                raise RuntimeError(
                    f"{artifact.task_id} failed quality review "
                    f"after {MAX_REVIEW_RETRIES} corrections."
                )

            state.artifacts[
                artifact.task_id
            ] = artifact

            logger.info(
                f"{artifact.task_id} approved and "
                f"available to dependent tasks"
            )

    def _quality_check(
        self,
        task,
        artifact,
        state,
    ):
        dependency_artifacts = {
        dependency_id: state.artifacts[dependency_id]
        for dependency_id in task.depends_on
        if dependency_id in state.artifacts
    }
        artifact = self.review_agent.review_artifact(
            task,
            artifact,
            dependency_artifacts
        )

        self.episode_service.capture_review(
            state,
            task,
            artifact,
        )

        while (
            artifact.review
            and artifact.review.status == "FAIL"
            and artifact.review_retry_count
            < MAX_REVIEW_RETRIES
        ):

            logger.info(
                f"{artifact.task_id} failed review. "
                f"Correction attempt "
                f"{artifact.review_retry_count + 1}/"
                f"{MAX_REVIEW_RETRIES}"
            )

            self.episode_service.capture_correction(
                state,
                task,
                artifact,
            )

            artifact = self.execution_agent.correct_task(
                task,
                state,
                artifact,
            )

            artifact = (
                self.review_agent.review_artifact(
                    task,
                    artifact,
                    dependency_artifacts,
                )
            )

        return artifact

    # ==========================================================
    # COMPLETION
    # ==========================================================

    def _is_execution_complete(
        self,
        state,
    ):

        return (
            len(state.artifacts)
            == len(state.plan.tasks)
        )

    # ==========================================================
    # PENDING APPROVAL CONTINUATION
    # ==========================================================

    def _handle_pending_approval(
        self,
        state,
    ):
        """
        Handle an approval that was previously interrupted.

        The actual repository provider owns the repository
        execution checkpoint. This node only processes the
        human decision and then allows the capability to
        continue from that checkpoint.
        """

        pending_approval = state.pending_approval

        if not pending_approval:
            return

        logger.info(
            "Resuming workflow after repository approval | "
            f"request_id="
            f"{pending_approval.get('request_id')}"
        )

        # The approval decision itself is supplied by the
        # LangGraph resume() call.
        #
        # Therefore there is intentionally no automatic
        # approval here.