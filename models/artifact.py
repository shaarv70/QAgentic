class Artifact:

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