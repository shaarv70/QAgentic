from langgraph.graph import START, END, StateGraph
from workflow.constants import (INTELLIGENCE, PUBLISH, REQUIREMENT,PLANNER,EXECUTION)
from models.workflow_state import WorkflowState
from workflow.workflow_routers.requirement_router import (requirement_router)
from workflow.constants import PLANNER



class WorkflowBuilder:
    """
==========================================================
Class : WorkflowBuilder
==========================================================

Purpose:
    Creates and compiles the LangGraph workflow.

Responsibility:
    - Register workflow nodes.
    - Connect nodes.
    - Compile the graph.

It NEVER:
    - Executes business logic.
    - Creates agents.
    - Calls LLM.
    - Reads user input.

Created By:
    app.py

Used By:
    LangGraphEngine
"""


    def __init__(self, node_registry):

        self.node_registry = node_registry




    def build(self):

        workflow_graph  = StateGraph(WorkflowState)
        self.node_registry.register_all(workflow_graph)
        self.build_edges(workflow_graph)
        return workflow_graph.compile()



    def build_edges(self,graph):
        """
    Connects workflow nodes.

    This method defines the workflow order.
    """
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
             END: END
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

