from artifacts.artifact_manager import ArtifactManager
from models.conversation import Conversation
from models.state import State
from utils.logger import logger


class SupervisorAgent:

    def __init__(self, registry):

        self.registry = registry
        self.state = State()
        self.conversation = Conversation()
        self.artifact_manager = ArtifactManager()

    def start(self, application_type, requirement):

        requirement_completed = False

        requirement_agent = self.registry.get("requirement")
        planner_agent = self.registry.get("planner")
        execution_agent = self.registry.get("execution")
        review_agent = self.registry.get("review")

        self.state.requirement = requirement
        self.state.application_type = application_type

        while not requirement_completed:

            self.state = requirement_agent.run(self.state)

            response = self.state.requirement_analysis      #return response in form of dict

            if response["status"] == "COMPLETE":

                self.state = planner_agent.run(self.state)
                self.state = execution_agent.run(self.state)
                self.state = review_agent.run(self.state)

                requirement_completed = True

            else:

                clarification = ""

                for question in response["questions"]:

                    answer = input(f"\n🤖 {question}\n>")

                    clarification += (
                        question + " : " + answer + "\n"
                    )

                    self.conversation.add_answer(question, answer)

                requirement += (
                    "\n\nClarifications:\n" + clarification
                )

                self.state.requirement = requirement

                logger.info("\nUpdated Requirement:")
                logger.info("-" * 60)
                logger.info(requirement)
                logger.info("-" * 60)
                logger.info("\nRe-analyzing requirement...\n")