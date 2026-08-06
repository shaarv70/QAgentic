from config import MAX_REVIEW_RETRIES
from utils.logger import logger
from workflow.constants import EXECUTION, REVIEW
from workflow.nodes.base_workflow__node import BaseWorkflowNode
from models.workflow_state import WorkflowState


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

Receives:
    WorkflowState

Returns:
    Updated WorkflowState

Stores:
    ExecutionAgent
    ReviewAgent

Does NOT Know:
    Requirement
    Planner

Reason:
    Encapsulates the complete execution lifecycle
    (dependency execution + quality review).
"""


    def __init__(self, agent_registry):


        self.execution_agent = agent_registry.get(EXECUTION)
        self.review_agent = agent_registry.get(REVIEW)



    def execute(self,state: WorkflowState) -> WorkflowState:

        app_state = state.app_state

        if app_state.plan is None:
            raise RuntimeError(
            "ExecutionWorkflowNode cannot execute because no execution plan was found."
        )

        while not self._is_execution_complete(app_state):

            ready_tasks = self._fetch_ready_tasks(app_state)

            candidate_artifacts = self._execute_ready_tasks(
                ready_tasks,
                app_state
            )

            self._review_artifacts(
                ready_tasks,
                candidate_artifacts,
                app_state
            )

        return state



    def _fetch_ready_tasks(self, state):
        """
    Retrieves every task whose dependencies
    have already completed.

    Raises:
        RuntimeError:
            If no task can be executed,
            indicating a circular dependency
            or invalid execution plan.
    """
        ready_tasks = self.execution_agent.get_ready_tasks(state)

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



    def _execute_ready_tasks(self,ready_tasks,state):

        return self.execution_agent.execute_tasks(ready_tasks,state)



    def _review_artifacts(
        self,
        ready_tasks,
        candidate_artifacts,
        state
    ):

        for artifact in candidate_artifacts:

            task = next(
                task
                for task in ready_tasks
                if task.task_id == artifact.task_id
            )

            artifact = self._quality_check(
                task,
                artifact,state
            )

            if (
                not artifact.review
                or artifact.review.status != "PASS"):

                raise RuntimeError(
                    f"{artifact.task_id} failed quality review "
                    f"after {MAX_REVIEW_RETRIES} corrections."
                )

            state.artifacts[artifact.task_id] = artifact

            logger.info(
                f"{artifact.task_id} approved and "
                f"available to dependent tasks"
            )



    def _quality_check(self,task,artifact,state):

            artifact = self.review_agent.review_artifact(
                task,
                artifact
            )

            while (
                artifact.review
                and artifact.review.status == "FAIL"
                and artifact.review_retry_count < MAX_REVIEW_RETRIES):

                logger.info(
                    f"{artifact.task_id} failed review. "
                    f"Correction attempt "
                    f"{artifact.review_retry_count + 1}/"
                    f"{MAX_REVIEW_RETRIES}"
                )

                artifact = self.execution_agent.correct_task(
                    task,
                    state,
                    artifact
                )

                artifact =self.review_agent.review_artifact(
                    task,
                    artifact
                )

            return artifact


    def _is_execution_complete(self,state):

        return (len(state.artifacts)== len(state.plan.tasks)
    )




