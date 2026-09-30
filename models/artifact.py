from typing import Any

from models.review import Review


class Artifact:

    """
    Represents a generated workflow artifact.

    Every task execution produces one Artifact.

    The artifact is progressively updated during
    execution and review.
    """

    task_id: str
    capability: str

    content: Any
    status: str

    review: Review | None

    approval_request: Any | None

    retry_count: int
    review_retry_count: int

    execution_time: float

    def __init__(
        self,
        task_id,
        capability,
    ):

        self.task_id = task_id
        self.capability = capability

        self.content = ""
        self.status = "PENDING"

        self.review = None

        # Approval metadata.
        self.approval_request = None

        # Technical generation retries.
        self.retry_count = 0

        # Quality correction retries.
        self.review_retry_count = 0

        self.execution_time = 0.00