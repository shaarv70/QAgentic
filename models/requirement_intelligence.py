class RequirementIntelligence:

    status: str
    intent: str
    context: dict[str, str]
    assumptions: list[str]
    unknowns: list[str]
    questions: list[dict]

    def __init__(
        self,
        status,
        intent,
        context=None,
        assumptions=None,
        unknowns=None,
        questions=None,
    ):
        self.status = status
        self.intent = intent
        self.context = context or {}
        self.assumptions = assumptions or []
        self.unknowns = unknowns or []
        self.questions = questions or []