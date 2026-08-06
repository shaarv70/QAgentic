from models.task import Task
from prompts.planning_prompt import build_planning_prompt
from models.plan import Plan


class PlanningService:

    def __init__(self,llm_service,available_capabilities):

        self.llm_service=llm_service
        self.available_capabilities = available_capabilities


    def create_plan(self, requirement, intelligence):

        prompt = build_planning_prompt(requirement,intelligence,self.available_capabilities)

        response = self.llm_service.ask_llm_json(prompt)

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