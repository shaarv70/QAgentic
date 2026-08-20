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
    def __init__(self, workflow_manager ,episode_service,):

        self.workflow_manager = workflow_manager
        self.episode_service = episode_service


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

                self.episode_service.capture_execution(app_state)
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

            raise RuntimeError(f"Unknown requirement status: {intelligence.status}")



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

        conversation = app_state.conversation

        if conversation is None:
            raise RuntimeError("Conversation state missing.")

        for clarification in intelligence.questions:

            key = clarification["key"]
            question = clarification["question"]

            if conversation.has_key(key):

                logger.warning("Skipping previously resolved clarification | "f"key={key}")

                continue

            answer = input(f"\n🤖 {question}\n> ")

            conversation.add_answer( key=key,question=question,answer=answer,)


