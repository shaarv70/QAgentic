from datetime import datetime, timezone
from uuid import uuid4
from models.state import State
from memory.memory_manager import MemoryManager
from memory.models.memory_category import MemoryCategory
from memory.models.memory_entry import MemoryEntry
from memory.models.memory_types import (
    MemoryImportance,
    MemoryScope,
    MemorySource,
    MemoryType,)
from utils.logger import logger


class EpisodeService:

    def __init__(self, memory_manager: MemoryManager) -> None:
        self.memory_manager = memory_manager



    def capture_execution(self, state: State) -> bool:
        """
        Capture one completed workflow execution
        as episodic memory.
        """

        now = datetime.now(timezone.utc)

        memory = MemoryEntry(
            id=f"episode_{uuid4().hex}",
            content=self._build_summary(state),
            category=MemoryCategory.EPISODIC,
            memory_type=MemoryType.EXECUTION,
            scope=MemoryScope.WORKFLOW,
            source=MemorySource.WORKFLOW,
            importance=MemoryImportance.MEDIUM,
            confidence=1.0,
            created_at=now,
            updated_at=now,
            metadata=self._build_metadata(state),
        )

        saved = self.memory_manager.remember(memory)

        if saved:
            logger.info(
                "Episodic memory captured | id=%s | type=%s",
                memory.id,
                memory.memory_type.value,
            )

        return saved




    def _build_summary(self, state: State) -> str:

        lines = [f"Requirement: {state.requirement}",]

        if state.run_id:
            lines.append(f"Run ID: {state.run_id}")

        if state.plan:
            lines.append(
                f"Tasks planned: {len(state.plan.tasks)}")

        if not state.artifacts:
            lines.append("No artifacts were generated.")
            lines.append("Outcome: UNKNOWN")
            return "\n".join(lines)

        completed = 0
        failed = 0
        approved = 0
        review_pending = 0

        for artifact in state.artifacts.values():

            if artifact.status == "COMPLETED":
                completed += 1

            elif artifact.status == "FAILED":
                failed += 1

            if artifact.review is not None:

                if artifact.review.status == "PASS":
                    approved += 1

                else:
                    review_pending += 1

            lines.append(
                f"Artifact {artifact.task_id}: "
                f"capability={artifact.capability}, "
                f"status={artifact.status}, "
                f"retry_count={artifact.retry_count}, "
                f"review_retry_count="
                f"{artifact.review_retry_count}, "
                f"execution_time="
                f"{artifact.execution_time:.2f}s")

            if artifact.review is not None:
                lines.append(
                    f"Review for {artifact.task_id}: "
                    f"status={artifact.review.status}")

        if failed > 0:
            outcome = "FAILED"

        elif (
            completed == len(state.artifacts)
            and approved == len(state.artifacts)):
            outcome = "COMPLETED_AND_APPROVED"

        elif completed == len(state.artifacts):
            outcome = "COMPLETED_REQUIRES_REVIEW"

        else:
            outcome = "UNKNOWN"

        lines.append(f"Outcome: {outcome}")

        return "\n".join(lines)




    def _build_metadata(self, state: State) -> dict:

        completed = 0
        failed = 0
        review_passed = 0
        corrections = 0

        for artifact in state.artifacts.values():

            if artifact.status == "COMPLETED":
                completed += 1

            elif artifact.status == "FAILED":
                failed += 1

            if artifact.review is not None:
                if artifact.review.status == "PASS":
                    review_passed += 1

            corrections += artifact.review_retry_count

        return {
            "run_id": state.run_id,
            "requirement": state.requirement,
            "artifact_count": len(state.artifacts),
            "completed_artifacts": completed,
            "failed_artifacts": failed,
            "review_passed": review_passed,
            "corrections": corrections,
        }




    def capture_correction(self,state,task,artifact,) -> bool:

        review = artifact.review

        if review is None:
            return False

        if review.status != "FAIL":
            return False

        now = datetime.now(timezone.utc)

        correction_attempt = artifact.review_retry_count + 1

        content = (
            f"Requirement: {state.requirement}\n"
            f"Run ID: {state.run_id}\n"
            f"Task: {task.task_id}\n"
            f"Capability: {artifact.capability}\n"
            f"Correction attempt: {correction_attempt}\n"
            f"Review status before correction: {review.status}\n"
            f"Review feedback: {review.feedback}"
        )

        memory = MemoryEntry(
            id=f"correction_{uuid4().hex}",
            content=content,
            category=MemoryCategory.EPISODIC,
            memory_type=MemoryType.CORRECTION,
            scope=MemoryScope.WORKFLOW,
            source=MemorySource.WORKFLOW,
            importance=MemoryImportance.MEDIUM,
            confidence=1.0,
            created_at=now,
            updated_at=now,
            metadata={
                "run_id": state.run_id,
                "task_id": task.task_id,
                "capability": artifact.capability,
                "correction_attempt": correction_attempt,
                "review_feedback": review.feedback,
            },
        )

        return self.memory_manager.remember(memory)



    def capture_review(self,state,task,artifact,) -> bool:

        review = artifact.review

        if review is None:
            return False

        now = datetime.now(timezone.utc)

        content = (
            f"Requirement: {state.requirement}\n"
            f"Run ID: {state.run_id}\n"
            f"Task: {task.task_id}\n"
            f"Capability: {artifact.capability}\n"
            f"Review status: {review.status}\n"
            f"Review feedback: {review.feedback}"
        )

        memory = MemoryEntry(
            id=f"review_{uuid4().hex}",
            content=content,
            category=MemoryCategory.EPISODIC,
            memory_type=MemoryType.REVIEW,
            scope=MemoryScope.WORKFLOW,
            source=MemorySource.WORKFLOW,
            importance=MemoryImportance.MEDIUM,
            confidence=1.0,
            created_at=now,
            updated_at=now,
            metadata={
                "run_id": state.run_id,
                "task_id": task.task_id,
                "capability": artifact.capability,
                "review_status": review.status,
                "review_feedback": review.feedback,
            },
        )

        return self.memory_manager.remember(memory)




    def capture_failure(self,state,task,artifact,failure_reason: str,) -> bool:

        now = datetime.now(timezone.utc)

        content = (
            f"Requirement: {state.requirement}\n"
            f"Run ID: {state.run_id}\n"
            f"Task: {task.task_id}\n"
            f"Capability: {artifact.capability}\n"
            f"Failure type: EXECUTION\n"
            f"Retry count: {artifact.retry_count}\n"
            f"Failure reason: {failure_reason}")

        memory = MemoryEntry(
            id=f"failure_{uuid4().hex}",
            content=content,
            category=MemoryCategory.EPISODIC,
            memory_type=MemoryType.FAILURE,
            scope=MemoryScope.WORKFLOW,
            source=MemorySource.WORKFLOW,
            importance=MemoryImportance.HIGH,
            confidence=1.0,
            created_at=now,
            updated_at=now,
            metadata={
                "run_id": state.run_id,
                "task_id": task.task_id,
                "capability": artifact.capability,
                "failure_type": "EXECUTION",
                "retry_count": artifact.retry_count,
                "failure_reason": failure_reason,
            },
        )

        return self.memory_manager.remember(memory)

