from utils.logger import logger
from workflow.constants import PLANNER
from workflow.nodes.base_workflow__node import BaseWorkflowNode
from models.workflow_state import WorkflowState


class PlannerNode(BaseWorkflowNode):



    def __init__(self, agent_registry):

        self.planner_agent = agent_registry.get(PLANNER)



    def execute(self,state: WorkflowState) -> WorkflowState:

        app_state = state.app_state
        state.update(self.planner_agent.run(app_state))

        if app_state.plan is None:

          raise RuntimeError("PlannerAgent did not generate an execution plan.")

        for task in app_state.plan.tasks:

            logger.info(
            f"{task.task_id} | "
            f"{task.capability} | "
            f"depends_on={task.depends_on}")

        return state