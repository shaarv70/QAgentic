class RequirementIntelligenceAgent:

    def decide(self, response):

        if response["status"] == "COMPLETE":
            return "PLAN"

        return "ASK_USER"