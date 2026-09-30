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
        • Delegate execution to WorkflowManager.
        • Handle human approval requests.
        • Handle requirement clarification.
        • Display the final execution results.

    This class NEVER:
        ❌ Executes workflow nodes.
        ❌ Executes repository operations.
        ❌ Calls MCP tools.
        ❌ Calls LLM providers directly.
        ❌ Builds the workflow.

    Supervisor is only the human interaction boundary.

    Approval flow:

        WorkflowManager
              │
              ▼
        LangGraph execution
              │
              ▼
          interrupt()
              │
              ▼
        SupervisorAgent
              │
        user decision
              │
              ▼
        WorkflowManager
              │
              ▼
        LangGraph resume
    ==========================================================
    """

    def __init__(
        self,
        workflow_manager,
        episode_service,
    ):

        self.workflow_manager = workflow_manager
        self.episode_service = episode_service

    def start(
        self,
        requirement: str,
    ) -> State:

        # ------------------------------------------------------
        # Initialize workflow state.
        # ------------------------------------------------------

        workflow_state = WorkflowState(
            State()
        )

        workflow_state.app_state.requirement = requirement

        phase = "INITIAL_ANALYSIS"

        while True:

            logger.info("")
            logger.info("=" * 60)

            logger.info(
                f"Workflow Phase {phase} : "
                f"{'Initial Analysis' if phase == 'INITIAL_ANALYSIS' else 'Requirement Re-analysis'}"
            )

            logger.info("=" * 60)

            # --------------------------------------------------
            # Execute the workflow.
            #
            # If LangGraph reaches an interrupt(), the call
            # returns with pending_approval populated.
            # --------------------------------------------------

            workflow_state = (
                self.workflow_manager.execute(
                    workflow_state
                )
            )

            app_state = workflow_state.app_state

            # --------------------------------------------------
            # Handle one or more approval requests.
            #
            # There can be multiple repository mutations in
            # one plan, therefore approval must be checked in
            # a loop.
            # --------------------------------------------------

            while app_state.pending_approval is not None:

                approval_request = (
                    app_state.pending_approval
                )

                logger.info("")
                logger.info(
                    "=" * 60
                )
                logger.info(
                    "REPOSITORY APPROVAL REQUIRED"
                )
                logger.info(
                    "=" * 60
                )

                logger.info(
                    f"Action: "
                    f"{approval_request.get('action')}"
                )

                logger.info(
                    f"Description: "
                    f"{approval_request.get('description')}"
                )

                logger.info(
                    f"Details: "
                    f"{approval_request.get('details', {})}"
                )

                # --------------------------------------------------
                # Human approval.
                #
                # Supervisor only collects the decision.
                # It does NOT execute the repository operation.
                # --------------------------------------------------

                decision = input(
                    "\nApprove this operation? "
                    "[approve/reject]: "
                ).strip().lower()

                # --------------------------------------------------
                # Resume the SAME LangGraph thread.
                #
                # workflow_state still contains the same run_id.
                # --------------------------------------------------

                workflow_state = (
                    self.workflow_manager.execute(
                        workflow_state,
                        resume={
                            "decision": decision
                        },
                    )
                )

                app_state = workflow_state.app_state

            # --------------------------------------------------
            # Requirement intelligence should now be available.
            # --------------------------------------------------

            intelligence = (
                app_state.requirement_intelligence
            )

            if intelligence is None:

                raise RuntimeError(
                    "Requirement Intelligence missing."
                )

            # --------------------------------------------------
            # Requirement is ready.
            # --------------------------------------------------

            if intelligence.status == "READY":

                self.episode_service.capture_execution(
                    app_state
                )

                return app_state

            # --------------------------------------------------
            # Requirement needs clarification.
            # --------------------------------------------------

            if (
                intelligence.status
                == "NEEDS_CLARIFICATION"
            ):

                self._collect_clarifications(
                    workflow_state
                )

                phase = "RE_ANALYSIS"

                logger.info("")
                logger.info(
                    "Clarification received."
                )

                logger.info(
                    "Restarting workflow analysis...\n"
                )

                continue

            raise RuntimeError(
                f"Unknown requirement status: "
                f"{intelligence.status}"
            )

    def _collect_clarifications(
        self,
        workflow_state: WorkflowState,
    ) -> None:

        """
        =====================================================
        Collect clarification answers from the user and
        update the current requirement.
        =====================================================
        """

        app_state = workflow_state.app_state

        intelligence = (
            app_state.requirement_intelligence
        )

        if intelligence is None:

            raise RuntimeError(
                "Requirement Intelligence missing."
            )

        conversation = app_state.conversation

        if conversation is None:

            raise RuntimeError(
                "Conversation state missing."
            )

        for clarification in intelligence.questions:

            key = clarification["key"]

            question = clarification["question"]

            # --------------------------------------------------
            # Do not ask the same clarification twice.
            # --------------------------------------------------

            if conversation.has_key(key):

                logger.warning(
                    "Skipping previously resolved "
                    f"clarification | key={key}"
                )

                continue

            answer = input(
                f"\n🤖 {question}\n> "
            )

            conversation.add_answer(
                key=key,
                question=question,
                answer=answer,
            )

