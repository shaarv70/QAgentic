from agents.base_agent import BaseAgent
from models.artifact import Artifact
from concurrent.futures import ThreadPoolExecutor
from models.execution_context import ExecutionContext
from models.automation_artifact import AutomationArtifact
from config import MAX_EXECUTION_RETRIES
from utils.logger import logger
from models.capability_result import CapabilityResult

import time


class ExecutionAgent(BaseAgent):

    def __init__(
        self,
        tool_registry,
        capability_registry,
        episode_service,
    ):
        super().__init__()

        self.tool_registry = tool_registry
        self.capability_registry = capability_registry
        self.episode_service = episode_service

    def execute(self, state):
        return state

    def execute_task(self, task, state):

        last_error = None
        start = time.perf_counter()

        artifact = Artifact(
            task_id=task.task_id,
            capability=task.capability,
        )

        logger.info(
            f"Started {task.task_id}: "
            f"{task.description}"
        )

        dependency_artifacts = {}

        for dependency_id in task.depends_on:

            dependency_artifact = (
                state.artifacts.get(dependency_id)
            )

            if dependency_artifact is None:
                raise RuntimeError(
                    f"{task.task_id} requires "
                    f"{dependency_id}, but its artifact "
                    f"is unavailable."
                )

            dependency_artifacts[
                dependency_id
            ] = dependency_artifact.content

        execution_context = ExecutionContext(
            requirement=state.requirement,
            dependency_artifacts=dependency_artifacts,
            workflow_state=state,
        )

        # ==========================================================
        # CAPABILITY EXECUTION
        # ==========================================================
        capability = self._get_capability(
            task.capability
        )

        if capability is not None:

            failure_retryable = True

            for attempt in range(
                MAX_EXECUTION_RETRIES
            ):

                try:

                    result = capability.execute(
                        task,
                        execution_context,
                    )

                    if not isinstance(
                        result,
                        CapabilityResult,
                    ):
                        raise RuntimeError(
                            f"Capability "
                            f"'{task.capability}' "
                            f"returned an invalid "
                            f"result type."
                        )

                    # ==================================================
                    # APPROVAL PAUSE
                    # ==================================================

                    if result.status == (
                        "PENDING_APPROVAL"
                    ):

                        artifact.content = (
                            result.data
                        )

                        artifact.status = (
                            "PENDING_APPROVAL"
                        )

                        artifact.retry_count = attempt

                        artifact.execution_time = (
                            time.perf_counter()
                            - start
                        )

                        logger.info(
                            f"{task.task_id} "
                            f"({task.capability}) "
                            f"is waiting for approval."
                        )

                        # VERY IMPORTANT:
                        # Do NOT retry.
                        # Do NOT capture failure.
                        # Do NOT raise.
                        # Do NOT mark FAILED.

                        return artifact

                    # ==================================================
                    # NORMAL RESULTS
                    # ==================================================

                    if result.status not in (
                        "PASSED",
                        "FAILED",
                    ):
                        raise RuntimeError(
                            f"Capability "
                            f"'{task.capability}' "
                            f"returned unsupported "
                            f"status "
                            f"'{result.status}'."
                        )

                    artifact.content = result.data

                    artifact.status = (
                        "COMPLETED"
                        if result.status == "PASSED"
                        else "FAILED"
                    )

                    artifact.retry_count = attempt

                    artifact.execution_time = (
                        time.perf_counter()
                        - start
                    )

                    if result.error:
                        last_error = result.error

                    failure_retryable = (
                        result.retryable
                    )

                    if result.status == "PASSED":

                        logger.info(
                            f"{task.task_id} "
                            f"({task.capability}) "
                            f"completed in "
                            f"{artifact.execution_time:.2f} sec"
                        )

                        return artifact

                    logger.warning(
                        f"{task.task_id} "
                        f"({task.capability}) "
                        f"failed: "
                        f"{result.error or 'Capability execution failed'}"
                    )

                    if not result.retryable:

                        logger.warning(
                            f"{task.task_id} "
                            f"({task.capability}) "
                            f"failed with a "
                            f"non-retryable result: "
                            f"{result.error or 'Capability execution failed'}"
                        )

                        break

                except Exception as e:

                    last_error = str(e)

                    artifact.retry_count = attempt

                    logger.warning(
                        f"{task.task_id} capability "
                        f"execution failed: {e}"
                    )

                    logger.warning(
                        f"{task.task_id} Retry {attempt}"
                    )

            artifact.status = "FAILED"

            artifact.execution_time = (
                time.perf_counter() - start
            )

            failure_reason = (
                last_error
                or "Capability execution failed"
            )

            self.episode_service.capture_failure(
                state,
                task,
                artifact,
                failure_reason,
            )

            # Healable capabilities (e.g. test_execution with self-healing)
            # return the FAILED artifact so the review + correction cycle
            # can trigger self-healing instead of aborting the workflow.
            if getattr(capability, "healable", False):
                logger.info(
                    "%s failed but capability supports self-healing "
                    "— returning artifact for review/correction",
                    task.task_id,
                )
                return artifact

            if not failure_retryable:

                raise RuntimeError(
                    f"{task.task_id} failed: "
                    f"{failure_reason}"
                )

            raise RuntimeError(
                f"{task.task_id} failed after "
                f"{MAX_EXECUTION_RETRIES} "
                f"execution attempts"
            )

        # ==========================================================
        # EXISTING TOOL REGISTRY PATH
        # ==========================================================

        generator = self.tool_registry.get(
            task.capability
        )

        for attempt in range(
            MAX_EXECUTION_RETRIES
        ):

            try:

                result = generator.generate(
                    task,
                    execution_context,
                )

                artifact.content = result
                artifact.status = "COMPLETED"
                artifact.retry_count = attempt

                artifact.execution_time = (
                    time.perf_counter() - start
                )

                logger.info(
                    f"{task.task_id} "
                    f"({task.capability}) "
                    f"completed in "
                    f"{artifact.execution_time:.2f} sec"
                )

                return artifact

            except Exception as e:

                last_error = str(e)

                artifact.retry_count = attempt

                logger.warning(
                    f"{task.task_id} failed: {e}"
                )

                logger.warning(
                    f"{task.task_id} Retry "
                    f"{attempt + 1}"
                )

        artifact.status = "FAILED"

        artifact.execution_time = (
            time.perf_counter() - start
        )

        failure_reason = (
            last_error
            or (
                f"Task failed after "
                f"{MAX_EXECUTION_RETRIES} "
                f"execution retries"
            )
        )

        self.episode_service.capture_failure(
            state,
            task,
            artifact,
            failure_reason,
        )

        raise RuntimeError(
            f"{task.task_id} failed after "
            f"{MAX_EXECUTION_RETRIES} retries"
        )

    def _get_capability(
        self,
        capability_name,
    ):

        try:
            return self.capability_registry.get(
                capability_name
            )

        except ValueError:
            return None

    def correct_task(
        self,
        task,
        state,
        artifact,
    ):

        capability = self._get_capability(task.capability)

        if capability is not None:
            prior_retry_count = artifact.review_retry_count

            # Build execution context so the capability's correct() can access
            # dependency artifacts and the requirement — same as execute_task().
            dependency_artifacts = {}
            for dependency_id in task.depends_on:
                dep_artifact = state.artifacts.get(dependency_id)
                if dep_artifact is None:
                    raise RuntimeError(
                        f"{task.task_id} requires {dependency_id}, "
                        f"but its artifact is unavailable during correction."
                    )
                dependency_artifacts[dependency_id] = dep_artifact.content

            execution_context = ExecutionContext(
                requirement=state.requirement,
                dependency_artifacts=dependency_artifacts,
                workflow_state=state,
            )

            feedback = (
                artifact.review.feedback
                if artifact.review
                else "Review failed — no specific feedback available."
            )

            # Try the capability's self-healing correct() path first.
            # Fall back to plain re-execution when not implemented.
            try:
                result = capability.correct(
                    task,
                    execution_context,
                    artifact,
                    feedback,
                )

                if not isinstance(result, CapabilityResult):
                    raise RuntimeError(
                        f"Capability '{task.capability}' correct() returned "
                        f"an invalid result type."
                    )

                # When self-healing produced a patched AutomationArtifact,
                # propagate it to state so downstream tasks (e.g. code_push)
                # receive the fixed version rather than the original code.
                if (
                    isinstance(result.data, dict)
                    and "_healed_automation_artifact" in result.data
                ):
                    healed = result.data["_healed_automation_artifact"]
                    result.data = result.data.get("_execution_result")
                    for dep_id in task.depends_on:
                        dep_artifact = state.artifacts.get(dep_id)
                        if (
                            dep_artifact is not None
                            and isinstance(dep_artifact.content, AutomationArtifact)
                        ):
                            dep_artifact.content = healed
                            logger.info(
                                "Propagated healed AutomationArtifact to %s",
                                dep_id,
                            )
                            break

                artifact.content = result.data
                artifact.status = (
                    "COMPLETED" if result.status == "PASSED" else "FAILED"
                )
                artifact.review_retry_count = prior_retry_count + 1
                artifact.review = None

                logger.info(
                    f"{task.task_id} self-healing correction completed "
                    f"(quality retry {artifact.review_retry_count})"
                )
                return artifact

            except NotImplementedError:
                logger.info(
                    f"Capability '{task.capability}' has no correction mode — "
                    f"re-executing as correction attempt."
                )
                new_artifact = self.execute_task(task, state)
                new_artifact.review_retry_count = prior_retry_count + 1
                return new_artifact

        start = time.perf_counter()

        generator = self.tool_registry.get(
            task.capability
        )

        logger.info(
            f"Correcting {task.task_id}: "
            f"{task.description}"
        )

        feedback = artifact.review.feedback

        dependency_artifacts = {}

        for dependency_id in task.depends_on:

            dependency_artifact = (
                state.artifacts.get(
                    dependency_id
                )
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
            dependency_artifacts=dependency_artifacts,
            workflow_state=state,
        )

        for attempt in range(
            MAX_EXECUTION_RETRIES
        ):

            try:

                result = generator.correct(
                    task,
                    execution_context,
                    artifact.content,
                    feedback,
                )

                artifact.content = result
                artifact.review_retry_count += 1

                artifact.execution_time += (
                    time.perf_counter() - start
                )

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

            if task.task_id in state.artifacts:
                continue

            dependencies_ready = all(
                dependency_id in state.artifacts
                and (
                    state.artifacts[dependency_id].status == "FAILED"
                    or (
                        state.artifacts[dependency_id].status == "COMPLETED"
                        and state.artifacts[dependency_id].review is not None
                        and state.artifacts[dependency_id].review.status == "PASS"
                    )
                )
                for dependency_id in task.depends_on
            )

            if dependencies_ready:
                ready_tasks.append(task)

        return ready_tasks

    def execute_tasks(self, tasks, state):

        artifacts = []

        if not tasks:
            return artifacts

        # ----------------------------------------------------------
        # IMPORTANT:
        # Approval-sensitive capability execution must not allow
        # several repository mutations to race ahead concurrently.
        #
        # We execute the ready batch sequentially.
        # ----------------------------------------------------------

        for task in tasks:

            try:

                artifact = self.execute_task(
                    task,
                    state,
                )

                artifacts.append(artifact)

                # Stop immediately when human approval
                # is required.
                if artifact.status == (
                    "PENDING_APPROVAL"
                ):
                    break

            except Exception:

                logger.exception(
                    f"{task.task_id} execution failed"
                )

                raise

        return artifacts