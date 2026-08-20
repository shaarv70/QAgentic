from ai.profiles.agent_profile import AgentProfile
from constants.agent_names import AgentNames
from registries.base_registry import BaseRegistry



class AgentProfileRegistry(BaseRegistry[AgentProfile]):
    """
    ==========================================================
    Class : AgentProfileRegistry

    Purpose:
        Maintains all Agent Profiles.

    Responsibilities:
        • Register profiles.
        • Retrieve profiles.
    ==========================================================
    """

    def __init__(self):

        super().__init__()

        self._register_default_profiles()




    def _register_default_profiles(self):

        self.register(
        AgentNames.REQUIREMENT_INTELLIGENCE,
        AgentProfile(
            agent_name=AgentNames.REQUIREMENT_INTELLIGENCE,
            model="openai/gpt-oss-120b",
            temperature=0.1,
            response_format="json",
            max_output_tokens=2000
        ))

        self.register(
        AgentNames.PLANNER,
        AgentProfile(
            agent_name=AgentNames.PLANNER,
            model="openai/gpt-oss-120b",
            temperature=0.2,
            response_format="json",
            max_output_tokens=1200
        ))


        self.register(
        AgentNames.EXECUTION,
        AgentProfile(
            agent_name=AgentNames.EXECUTION,
            model="openai/gpt-oss-120b",
            temperature=0.2,
            max_output_tokens=2000
        ))


        self.register(
        AgentNames.REVIEW,
        AgentProfile(
            agent_name=AgentNames.REVIEW,
            model="openai/gpt-oss-120b",
            temperature=0.1,
            response_format="json",
            max_output_tokens=800
        ))

        self.register(
        AgentNames.CORRECTION,
        AgentProfile(
            agent_name=AgentNames.CORRECTION,
            model="openai/gpt-oss-120b",
            temperature=0.2,
            max_output_tokens=2500
        ))


        self.register(
        AgentNames.SUMMARY,
        AgentProfile(
            agent_name=AgentNames.SUMMARY,
            model="openai/gpt-oss-120b",
            temperature=0.2,
            max_output_tokens=1000
        ))

        self.register(
        AgentNames.TESTCASE,
        AgentProfile(
            agent_name=AgentNames.TESTCASE,
            model="openai/gpt-oss-120b",
            temperature=0.2,
            max_output_tokens=2500
        ))


        self.register(
        AgentNames.AUTOMATION,
        AgentProfile(
            agent_name=AgentNames.AUTOMATION,
            model="openai/gpt-oss-120b",
            temperature=0.2,
            max_output_tokens=4000
        ))



        self.register(
        AgentNames.DATABASE,
        AgentProfile(
            agent_name=AgentNames.DATABASE,
            model="openai/gpt-oss-120b",
            temperature=0.2,
            max_output_tokens=2500
        ))
