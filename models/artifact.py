from models.review import Review


class Artifact:

    """
    ==========================================================
    Class : Artifact
    ==========================================================

    Represents a generated workflow artifact.

    Every task execution produces exactly one Artifact.

    The artifact is progressively updated during the
    execution and review lifecycle.
    ==========================================================
    """

    task_id: str
    capability: str

    content: str
    status: str

    review: Review | None

    # Technical generation retries
    retry_count: int

    # Quality correction retries
    review_retry_count: int

    execution_time: float







    def __init__(self,  task_id, capability):

        self.task_id = task_id
        self.capability = capability

        self.content = ""
        self.status = "PENDING"
        self.review = None

        # Technical generation retries
        self.retry_count = 0

        # Quality correction attempts
        self.review_retry_count = 0

        self.execution_time = 0.00