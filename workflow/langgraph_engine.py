from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.types import Command

from models.workflow_state import WorkflowState
from workflow.workflow_engine import WorkflowEngine


class LangGraphEngine(WorkflowEngine):

    """
    ==========================================================
    Class : LangGraphEngine
    ==========================================================

    Purpose:
        Executes the compiled LangGraph workflow.

    Responsibilities:
        • Compile the workflow.
        • Maintain workflow checkpoints.
        • Start new workflow executions.
        • Resume interrupted executions.
        • Return WorkflowState to the application layer.

    Important:
        run_id is used as LangGraph's thread_id.

        The same thread_id MUST be reused when a workflow
        is resumed after an interrupt.
    ==========================================================
    """

    def __init__(self, workflow_builder):

        # ------------------------------------------------------
        # Checkpointer
        #
        # QAgentic workflow state contains application-domain
        # Python objects such as Plan, Artifact, Conversation,
        # RequirementIntelligence, etc.
        #
        # The default LangGraph serializer uses msgpack and
        # cannot serialize the WorkflowState wrapper directly.
        #
        # pickle_fallback allows JsonPlusSerializer to handle
        # these existing Python objects without changing the
        # QAgentic state model.
        # ------------------------------------------------------

        serializer = JsonPlusSerializer(
            pickle_fallback=True
        )

        self.checkpointer = MemorySaver(
            serde=serializer
        )

        # ------------------------------------------------------
        # Compile the graph once.
        # ------------------------------------------------------

        self.compiled_graph = workflow_builder.build(
            checkpointer=self.checkpointer
        )

    def execute(
        self,
        workflow_state: WorkflowState,
        resume=None,
    ) -> WorkflowState:

        """
        Execute a new workflow or resume an interrupted workflow.

        Parameters
        ----------
        workflow_state:
            Current QAgentic workflow state.

        resume:
            None when starting a workflow.

            A value such as:
                {"decision": "approve"}

            when resuming an interrupted workflow.
        """

        app_state = workflow_state.app_state

        # ------------------------------------------------------
        # Generate a run ID only for a new workflow.
        #
        # On resume the existing ID MUST be reused.
        # ------------------------------------------------------

        if not app_state.run_id:

            from uuid import uuid4

            app_state.run_id = str(uuid4())

        config = {
            "configurable": {
                "thread_id": app_state.run_id
            }
        }

        # ------------------------------------------------------
        # NEW WORKFLOW
        # ------------------------------------------------------

        if resume is None:

            result = self.compiled_graph.invoke(
                workflow_state,
                config=config,
            )

        # ------------------------------------------------------
        # RESUME INTERRUPTED WORKFLOW
        # ------------------------------------------------------

        else:

            result = self.compiled_graph.invoke(
                Command(resume=resume),
                config=config,
            )

        # ------------------------------------------------------
        # LangGraph returns the graph state.
        #
        # Convert it back to QAgentic's WorkflowState.
        # ------------------------------------------------------

        if isinstance(result, dict):

            app_state = result.get(
                "app_state"
            )

            if app_state is None:

                raise RuntimeError(
                    "LangGraph returned a state without "
                    "'app_state'."
                )

            # --------------------------------------------------
            # When interrupt() pauses the graph, LangGraph puts
            # the interrupt payload into __interrupt__.
            # --------------------------------------------------

            interrupts = result.get(
                "__interrupt__"
            )

            if interrupts:

                interrupt_value = getattr(
                    interrupts[0],
                    "value",
                    interrupts[0],
                )

                app_state.pending_approval = (
                    interrupt_value
                )

            else:

                app_state.pending_approval = None

            return WorkflowState(
                app_state=app_state
            )

        return result