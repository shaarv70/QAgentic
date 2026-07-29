from agents.base_agent import BaseAgent
from models.artifact import Artifact
from concurrent.futures import ThreadPoolExecutor
from models.execution_context import ExecutionContext
from config import MAX_EXECUTION_RETRIES
from utils.logger import logger
import time


class ExecutionAgent(BaseAgent):

    def __init__(self, tool_registry):

        super().__init__()
        self.tool_registry = tool_registry


    def execute(self, state):
        return state


    

    def execute_task(self, task, state):

        start = time.perf_counter()

        generator = self.tool_registry.get(
            task.capability
        )

        artifact = Artifact(
            task_id=task.task_id,
            capability=task.capability
        )

        logger.info(f"Started {task.task_id}: {task.description}")
        dependency_artifacts = {}
        for dependency_id in task.depends_on:
        
                        dependency_artifact = state.artifacts.get(
                            dependency_id
                        )
        
                        if dependency_artifact is None:
                            raise RuntimeError(
                                f"{task.task_id} requires "
                                f"{dependency_id}, but its artifact "
                                f"is unavailable."
                            )
        
                        dependency_artifacts[dependency_id] = dependency_artifact.content
                        
        execution_context = ExecutionContext(requirement=state.requirement,dependency_artifacts=dependency_artifacts)
        for attempt in range(MAX_EXECUTION_RETRIES):
           
            try:

                result = generator.generate(task,execution_context)

                artifact.content = result

                artifact.status = "COMPLETED"

                artifact.retry_count = attempt

                artifact.execution_time = (time.perf_counter() - start)

                logger.info(
                    f"{task.task_id} ({task.capability}) "
                    f"completed in "
                    f"{artifact.execution_time:.2f} sec"
                )

                return artifact

            except Exception as e:

                artifact.retry_count = attempt + 1

                logger.warning(
                    f"{task.task_id} failed: {e}"
                )

                logger.warning(
                    f"{task.task_id} Retry {attempt + 1}"
                )


        artifact.status = "FAILED"

        artifact.execution_time = (
            time.perf_counter() - start
        )

        raise RuntimeError(
            f"{task.task_id} failed after "
            f"{MAX_EXECUTION_RETRIES} retries"
        )
        
        
        
    def correct_task(self, task, state, artifact):

        start = time.perf_counter()

        generator = self.tool_registry.get(
            task.capability
        )

        logger.info(
            f"Correcting {task.task_id}: "
            f"{task.description}"
        )

        feedback = artifact.review.feedback

        # Build dependency context again for correction
        dependency_artifacts = {}

        for dependency_id in task.depends_on:

            dependency_artifact = state.artifacts.get(
                dependency_id
            )

            if dependency_artifact is None:
                raise RuntimeError(
                    f"{task.task_id} requires "
                    f"{dependency_id}, but its artifact "
                    f"is unavailable during correction."
                )

            dependency_artifacts[
                dependency_id
            ] = dependency_artifact.content

        execution_context = ExecutionContext(
            requirement=state.requirement,
            dependency_artifacts=dependency_artifacts
        )

        for attempt in range(MAX_EXECUTION_RETRIES):

            try:

                result = generator.correct(
                    task,
                    execution_context,
                    artifact.content,
                    feedback
                )

                artifact.content = result

                artifact.review_retry_count += 1

                artifact.execution_time += (
                    time.perf_counter() - start
                )

                # Review belongs to previous artifact version
                artifact.review = None

                logger.info(
                    f"{task.task_id} correction completed "
                    f"(quality retry "
                    f"{artifact.review_retry_count})"
                )

                return artifact

            except Exception as e:

                logger.warning(
                    f"{task.task_id} correction failed: {e}"
                )

                logger.warning(
                    f"{task.task_id} correction execution "
                    f"retry {attempt + 1}/"
                    f"{MAX_EXECUTION_RETRIES}"
                )

        raise RuntimeError(
            f"{task.task_id} correction failed after "
            f"{MAX_EXECUTION_RETRIES} execution retries"
        )
        
        
        
    
                    
    def get_ready_tasks(self, state):

        ready_tasks = []

        for task in state.plan.tasks:

            # Already completed and approved
            if task.task_id in state.artifacts:
                continue

            dependencies_ready = all(
                dependency_id in state.artifacts
                and state.artifacts[dependency_id].status == "COMPLETED"
                and state.artifacts[dependency_id].review is not None
                and state.artifacts[dependency_id].review.status == "PASS"
                for dependency_id in task.depends_on
            )

            if dependencies_ready:
                ready_tasks.append(task)

        return ready_tasks               
    
    
    
    def execute_tasks(self, tasks, state):

        artifacts = []

        if not tasks:
            return artifacts

        with ThreadPoolExecutor(
            max_workers=min(4, len(tasks))
        ) as executor:

            future_to_task = {
                executor.submit(
                    self.execute_task,
                    task,
                    state
                ): task
                for task in tasks
            }

            for future, task in future_to_task.items():

                try:

                    artifact = future.result()
                    artifacts.append(artifact)

                except Exception:

                    logger.exception(
                        f"{task.task_id} execution failed"
                    )

                    raise

        return artifacts                