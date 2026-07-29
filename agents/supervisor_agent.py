from artifacts.artifact_manager import ArtifactManager
from models.conversation import Conversation
from models.state import State
from utils.logger import logger
from datetime import datetime
from config import MAX_REVIEW_RETRIES


class SupervisorAgent:

    def __init__(self, registry):

        self.registry = registry
        self.state = State()
        self.conversation = Conversation()
        self.artifact_manager = ArtifactManager()
        
        
    def _quality_check(self,task,artifact,execution_agent,review_agent):

        artifact = review_agent.review_artifact(
            task,
            artifact
        )

        while (
            artifact.review
            and artifact.review.status == "FAIL"
            and artifact.review_retry_count < MAX_REVIEW_RETRIES
        ):

            logger.info(
                f"{artifact.task_id} failed review. "
                f"Correction attempt "
                f"{artifact.review_retry_count + 1}/"
                f"{MAX_REVIEW_RETRIES}"
            )

            artifact = execution_agent.correct_task(
                task,
                self.state,
                artifact
            )

            artifact = review_agent.review_artifact(
                task,
                artifact
            )

        return artifact    

    def start(self,requirement): 

        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        requirement_agent = self.registry.get("requirement")
        intelligence_agent = self.registry.get("intelligence")
        planner_agent = self.registry.get("planner")
        execution_agent = self.registry.get("execution")
        review_agent = self.registry.get("review")

        self.state.requirement = requirement

        # Requirement enters the workflow once
        self.state = requirement_agent.run(self.state)
        while True:

            # Analyze current requirement
            self.state = intelligence_agent.run(self.state)

            intelligence = self.state.requirement_intelligence

            if intelligence.status == "READY":

                self.state = planner_agent.run(self.state)

                for task in self.state.plan.tasks:
                    logger.info(
                        f"{task.task_id} | "
                        f"{task.capability} | "
                        f"depends_on={task.depends_on}"
                    )

                # ---------------------------------------------
                # Execute dependency graph in waves
                # ---------------------------------------------

                while len(self.state.artifacts) < len(self.state.plan.tasks):

                    ready_tasks = execution_agent.get_ready_tasks(
                        self.state
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

                    # Generate all currently-ready tasks in parallel
                    candidate_artifacts = (
                        execution_agent.execute_tasks(
                            ready_tasks,
                            self.state
                        )
                    )

                    # Review/correct each candidate
                    for artifact in candidate_artifacts:

                        task = next(
                            task
                            for task in ready_tasks
                            if task.task_id == artifact.task_id
                        )

                        artifact = self._quality_check(
                            task,
                            artifact,
                            execution_agent,
                            review_agent
                        )

                        if (
                            not artifact.review
                            or artifact.review.status != "PASS"
                        ):
                            raise RuntimeError(
                                f"{artifact.task_id} failed quality review "
                                f"after {MAX_REVIEW_RETRIES} corrections."
                            )

                        # IMPORTANT:
                        # Only approved artifacts enter State.
                        self.state.artifacts[
                            artifact.task_id
                        ] = artifact

                        logger.info(
                            f"{artifact.task_id} approved and "
                            f"available to dependent tasks"
                        )

                # ---------------------------------------------
                # Publish approved artifacts
                # ---------------------------------------------

                for artifact in self.state.artifacts.values():

                    print("\n" + "=" * 60)
                    print(
                        f"Generated Artifact: "
                        f"{artifact.capability}"
                    )
                    print("=" * 60)

                    print(artifact.content)

                    self.artifact_manager.save(
                        artifact,
                        run_id
                    )

                break
                                    
                                    
                
                
                
            if intelligence.status not in { "READY","NEEDS_CLARIFICATION"}:
                raise ValueError(f"Unknown requirement intelligence status: "f"{intelligence.status}")


            if not intelligence.questions:
                raise RuntimeError(
                "Requirement requires clarification but no clarification questions were provided.")

            clarification = ""

            for question in intelligence.questions:

                answer = input(
                    f"\n🤖 {question}\n>"
                )

                clarification += (
                    question + " : " + answer + "\n"
                )

                self.conversation.add_answer(
                    question,
                    answer
                )

            requirement += (
                "\n\nClarifications:\n"
                + clarification
            )

            self.state.requirement = requirement

            logger.info("\nUpdated Requirement:")
            logger.info("-" * 60)
            logger.info(requirement)
            logger.info("-" * 60)

            logger.info(
                "\nRe-analyzing requirement...\n"
            )

        return self.state