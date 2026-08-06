from models.conversation import Conversation
from models.plan import Plan
from models.requirement_intelligence import RequirementIntelligence
from models.artifact import Artifact


class State:

    requirement: str
    requirement_intelligence: RequirementIntelligence | None
    conversation: Conversation
    plan: Plan | None
    artifacts: dict[str, Artifact]
    logs: list[str]
    status: str
    run_id: str

    def __init__(self):

        self.requirement = ""

        self.requirement_intelligence = None

        self.conversation = Conversation()

        self.plan = None

        self.artifacts = {}

        self.logs = []

        self.status = "STARTED"

        self.run_id = ""