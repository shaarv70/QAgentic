from models.plan import Plan



class State:

    def __init__(self):

        self.requirement_analysis = None
        
        self.requirement = ""

        self.application_type = ""

        self.plan =Plan

        self.artifacts = {}

        self.logs = []

        self.status = "STARTED"