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

            self.review_artifact(
                task,
                artifact
            )

        return state


    def review_artifact(self, task, artifact):

        review = self.review_service.review(
            task,
            artifact
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