class Artifact:

    def __init__(self, name):

        self.name = name

        self.content = ""

        self.status = "PENDING"

        self.review = None

        self.retry_count = 0

        self.execution_time = 0