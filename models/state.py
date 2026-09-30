
from domain.repository.repository_execution_checkpoint import (
    RepositoryExecutionCheckpoint,
)
from models.artifact import Artifact
from models.conversation import Conversation
from models.plan import Plan
from models.requirement_intelligence import RequirementIntelligence


class State:

    requirement: str

    requirement_intelligence: RequirementIntelligence | None

    conversation: Conversation

    plan: Plan | None

    artifacts: dict[str, Artifact]

    logs: list[str]

    status: str

    run_id: str

    repository_execution_checkpoint: (
        RepositoryExecutionCheckpoint | None
    )

    pending_approval: dict | None

    def __init__(self):

        self.requirement = ""

        self.requirement_intelligence = None

        self.conversation = Conversation()

        self.plan = None

        self.artifacts = {}

        self.logs = []

        self.status = "STARTED"

        self.run_id = ""

        self.repository_execution_checkpoint = None

        self.pending_approval = None