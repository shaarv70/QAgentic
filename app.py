from registries.agent_registry import AgentRegistry
from agents.supervisor_agent import SupervisorAgent
from registries.provider_registry import ProviderRegistry
from registries.tool_registry import ToolRegistry
from services.llm_service import LLMService
from utils.logger import logger



print("=" * 60)
print("         AI QA Assistant")
print("=" * 60)
print("\nDescribe what you want the QA Assistant to do.")
print("Type 'exit' anytime to quit.")
print("=" * 60)


# -----------------------------------------------------
# Dependency Injection
# -----------------------------------------------------

provider_registry = ProviderRegistry()

llm_service = LLMService(provider_registry)

tool_registry = ToolRegistry(llm_service)

agent_registry = AgentRegistry(
    tool_registry,
    llm_service
)


# -----------------------------------------------------
# Chat Loop
# -----------------------------------------------------

while True:

    requirement = input("\nEnter Requirement: ").strip()

    if requirement.lower() == "exit":
        logger.info("\nGoodbye!")
        break

    if not requirement:
        print("\nRequirement cannot be empty.")
        continue

    supervisor = SupervisorAgent(agent_registry)

    supervisor.start(requirement)