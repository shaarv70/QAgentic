from bootstrap.application_container import ApplicationContainer
from utils.logger import logger






def main():

    """
==========================================================
Module : app.py
==========================================================

Purpose:
    Entry point of the AI QA Assistant.

Responsibilities:
    • Create the application.
    • Display the welcome banner.
    • Accept user requirements.
    • Delegate execution to the SupervisorAgent.
    • Keep the application running until the user exits.

This module NEVER:
    ❌ Creates framework components manually.
    ❌ Contains workflow logic.
    ❌ Executes workflow nodes.
    ❌ Calls LLM providers directly.

Execution Flow:

    Application Start
            │
            ▼
    Create ApplicationContainer
            │
            ▼
    Create SupervisorAgent
            │
            ▼
    Display Welcome Banner
            │
            ▼
    Accept User Requirement
            │
            ▼
    SupervisorAgent.start()
            │
            ▼
    Wait For Next Requirement

==========================================================
"""

    # -----------------------------------------------------
    # Build the complete AI QA application.
    # -----------------------------------------------------
    container = ApplicationContainer()
    supervisor = container.create_supervisor()


    # -----------------------------------------------------
    # Display application banner.
    # -----------------------------------------------------
    print("=" * 60)
    print("         AI QA Assistant")
    print("=" * 60)
    print("\nDescribe what you want the QA Assistant to do.")
    print("Type 'exit' anytime to quit.")
    print("=" * 60)


    # -----------------------------------------------------
    # Main interaction loop.
    # Continuously accepts requirements until the user exits.
    # -----------------------------------------------------
    while True:

        # Read the user's requirement.
        requirement = input("\nEnter Requirement: ").strip()

        # Gracefully terminate the application.
        if requirement.lower() == "exit":
            logger.info("\nGoodbye!")
            break

        # Prevent empty requirements.
        if not requirement:
            print("\nRequirement cannot be empty.")
            continue

        # Delegate the complete workflow execution to the supervisor.
        supervisor.start(requirement)



if __name__ == "__main__":
    main()