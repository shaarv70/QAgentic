from langgraph.graph import END, START, StateGraph
from workflow.constants import (
    INTELLIGENCE,
    PUBLISH,
    REQUIREMENT,
    PLANNER,
    EXECUTION,
)

from models.workflow_state import WorkflowState
from workflow.workflow_routers.requirement_router import requirement_router


class WorkflowBuilder:

    """
    ==========================================================
    Class : WorkflowBuilder
    ==========================================================

    Responsibility:

        • Register workflow nodes.
        • Connect workflow nodes.
        • Compile the graph.

    It does NOT execute the graph.
    """

    def __init__(self, node_registry):

        self.node_registry = node_registry

    def build(self, checkpointer=None):

        workflow_graph = StateGraph(
            WorkflowState
        )

        self.node_registry.register_all(
            workflow_graph
        )

        self.build_edges(
            workflow_graph
        )

        # ------------------------------------------------------
        # The checkpointer is supplied by LangGraphEngine.
        #
        # Keeping it injected means WorkflowBuilder does not
        # decide which persistence implementation is used.
        # ------------------------------------------------------

        return workflow_graph.compile(
            checkpointer=checkpointer
        )

    def build_edges(self, graph):

        graph.add_edge(
            START,
            REQUIREMENT
        )

        graph.add_edge(
            REQUIREMENT,
            INTELLIGENCE
        )

        graph.add_conditional_edges(
            INTELLIGENCE,
            requirement_router,
            {
                PLANNER: PLANNER,
                END: END,
            }
        )

        graph.add_edge(
            PLANNER,
            EXECUTION
        )

        graph.add_edge(
            EXECUTION,
            PUBLISH
        )

        graph.add_edge(
            PUBLISH,
            END
        )