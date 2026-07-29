from models.plan import Plan



class State:

    def __init__(self):

        self.requirement = ""

        self.requirement_intelligence = None

        self.plan = None

        self.artifacts = {}

        self.logs = []

        self.status = "STARTED"
        
        self.run_id = ""