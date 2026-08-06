from models.state import State
from models.workflow_state import WorkflowState
from utils.logger import logger



class SupervisorAgent:
    """
==========================================================
Class : SupervisorAgent
==========================================================

Purpose:
    Entry point of the AI QA Assistant.

Responsibilities:
    • Accept user requirements.
    • Create the initial workflow state.
    • Delegate execution to the WorkflowManager.
    • Display the final execution results.

This class NEVER:
    ❌ Executes workflow nodes.
    ❌ Contains business logic.
    ❌ Builds the workflow.
    ❌ Calls LLM providers directly.

Workflow:

    User Requirement
            │
            ▼
    Create WorkflowState
            │
            ▼
    WorkflowManager
            │
            ▼
    Display Generated Artifacts

==========================================================
"""
    def __init__(self, workflow_manager):

        self.workflow_manager = workflow_manager



    def start(self,requirement: str) -> State:

    # -----------------------------------------
    # Initialize workflow
    # -----------------------------------------
        workflow_state = WorkflowState(State())
        workflow_state.app_state.requirement = requirement
        phase="INITIAL_ANALYSIS"
        while True:
            logger.info("")
            logger.info("=" * 60)
            logger.info(
                f"Workflow Phase {phase} : "
                f"{'Initial Analysis' if phase == "INITIAL_ANALYSIS" else 'Requirement Re-analysis'}")
            logger.info("=" * 60)


            # -----------------------------------------
            # Execute workflow
            # -----------------------------------------

            workflow_state = (self.workflow_manager.execute(workflow_state))
            app_state = workflow_state.app_state
            intelligence = (app_state.requirement_intelligence)

            if intelligence is None:

                raise RuntimeError(
                    "Requirement Intelligence missing."
                )

            # -----------------------------------------
            # Requirement ready
            # -----------------------------------------

            if intelligence.status == "READY":

                return app_state

            # -----------------------------------------
            # Requirement needs clarification
            # -----------------------------------------

            if (intelligence.status== "NEEDS_CLARIFICATION"):

                self._collect_clarifications(workflow_state)

                phase="RE_ANALYSIS"

                logger.info("")
                logger.info("Clarification received.")
                logger.info("Restarting workflow analysis...\n")

                continue

            raise RuntimeError(
                 f"Unknown requirement status: {intelligence.status}")



    def _collect_clarifications(self,workflow_state: WorkflowState) -> None:
        """
    =====================================================
    Collect clarification answers from the user and
    update the current requirement.
    =====================================================
    """

        app_state = workflow_state.app_state

        intelligence = app_state.requirement_intelligence

        if intelligence is None:
            raise RuntimeError("Requirement Intelligence missing.")

        for question in intelligence.questions:

            answer = input(f"\n🤖 {question}\n> ")

            app_state.conversation.add_answer(question,answer)

        app_state.requirement += (
            "\n\nClarifications:\n"
            + app_state.conversation.get_clarification_text()
        )

        logger.info("\nUpdated Requirement:")
        logger.info("-" * 60)
        logger.info(app_state.requirement)
        logger.info("-" * 60)


