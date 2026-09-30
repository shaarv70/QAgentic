from agents.base_agent import BaseAgent
from utils.logger import logger


class ReviewAgent(BaseAgent):

    def __init__(self, review_service):
        super().__init__()
        self.review_service = review_service

    def execute(self, state):

        for artifact in state.artifacts.values():

            task = next(
                task
                for task in state.plan.tasks
                if task.task_id == artifact.task_id
            )

            dependency_artifacts = {
                dependency_id: state.artifacts[dependency_id]
                for dependency_id in task.depends_on
                if dependency_id in state.artifacts
            }

            self.review_artifact(
                task,
                artifact,
                dependency_artifacts,
            )

        return state

    def review_artifact(
        self,
        task,
        artifact,
        dependency_artifacts=None,
    ):

        review = self.review_service.review(
            task,
            artifact,
            dependency_artifacts or {},
        )

        artifact.review = review

        logger.info(
            f"{artifact.task_id} Review: "
            f"{review.status}"
        )

        if artifact.review.status == "FAIL":

            logger.info(
                f"{artifact.task_id} Feedback: "
                f"{review.feedback}"
            )

        return artifact