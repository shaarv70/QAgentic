from models.task import Task




class Plan:


    tasks: list[Task]
    priority: str
    parallel: bool



    def __init__(self):

        self.tasks = []

        self.priority = "MEDIUM"

        self.parallel = True