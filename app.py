from registries.agent_registry import AgentRegistry
from agents.supervisor_agent import SupervisorAgent
from registries.provider_registry import ProviderRegistry
from registries.tool_registry import ToolRegistry
from services.llm_service import LLMService
from utils.logger import logger

# -----------------------------------------------------
# Welcome Message
# -----------------------------------------------------

print("=" * 60)
print("         AI QA Assistant")
print("=" * 60)
print("\nSelect Application Type")
print("1. Web")
print("2. API")
print("3. Mobile\n")

print("Type 'exit' anytime to quit.")
print("=" * 60)

# -----------------------------------------------------
# Dependency Injection (Composition Root)
# -----------------------------------------------------

applications = ["Web", "API", "Mobile"]

provider_registry = ProviderRegistry()

llm_service = LLMService(provider_registry)

tool_registry = ToolRegistry(llm_service)

agent_registry = AgentRegistry(
    tool_registry,
    llm_service
)

supervisor = SupervisorAgent(agent_registry)

# -----------------------------------------------------
# Chat Loop
# -----------------------------------------------------

while True:

    choice = input("Enter your choice: ")

    if choice not in ["1", "2", "3"]:
        print("\nInvalid Choice")
        continue

    application_type = applications[int(choice) - 1]

    requirement = input("\nEnter Requirement : ")
    
    choice = input("Enter your choice: ")

    if choice.lower() == "exit":
        logger.info("\nGoodbye!")
        break

    if requirement.lower() == "exit":
        logger.info("\nGoodbye!")
        break

    supervisor.start(application_type, requirement)