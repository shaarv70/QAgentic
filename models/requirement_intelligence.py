class RequirementIntelligence:

    status: str
    intent: str
    context: dict[str, str]
    assumptions: list[str]
    questions: list[str]


    def __init__(
        self,
        status,
        intent,
        context=None,
        assumptions=None,
        questions=None):

        self.status = status
        self.intent = intent
        self.context = context or {}
        self.assumptions = assumptions or []
        self.questions = questions or []