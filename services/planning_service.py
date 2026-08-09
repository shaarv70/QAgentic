from ai.builders.prompt_builder import PromptBuilder
from ai.models.llm_request import LLMRequest
from constants.agent_names import AgentNames
from models.task import Task
from prompts.planning_prompt import build_planning_prompt
from models.plan import Plan


class PlanningService:

    def __init__(self,ai_service,available_capabilities,prompt_builder:PromptBuilder):

        self.ai_service=ai_service
        self.available_capabilities = available_capabilities
        self.prompt_builder=prompt_builder


    def create_plan(self, requirement, intelligence):

        system_prompt, user_prompt = self.prompt_builder.planner(requirement,intelligence,self.available_capabilities,)

        request = LLMRequest(system_prompt=system_prompt,user_prompt=user_prompt)

        response = self.ai_service.generate_json(AgentNames.PLANNER,request)

        plan = Plan()

        for index, task_data in enumerate(response["tasks"], start=1):

            capability = task_data["capability"]
            if capability not in self.available_capabilities:
                raise ValueError(f"Planner returned unsupported capability: "f"{capability}")
            task = Task(
                task_id=f"task_{index}",
                capability=task_data["capability"],
                description=task_data["description"],
                context=task_data.get("context", {}),
                depends_on=task_data.get("depends_on", []))

            plan.tasks.append(task)

        plan.priority = response.get("priority", "MEDIUM")
        plan.parallel = response.get("parallel", True)

        return plan