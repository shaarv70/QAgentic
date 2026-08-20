from ai.builders.context_builder import ContextBuilder
from ai.prompts.prompt_result import PromptResult
from constants.agent_names import AgentNames
from memory.memory_context_service import MemoryContextService
from prompts.requirement_intelligence_prompt import (
    build_requirement_intelligence_prompt,
)
from prompts.planning_prompt import build_planning_prompt
from prompts.review_prompt import build_review_prompt
from prompts.testcase_prompt import build_testcase_prompt
from prompts.automation_prompt import build_automation_prompt
from prompts.database_prompt import build_database_prompt
from prompts.summary_prompt import build_summary_prompt
from prompts.correction_prompt import build_correction_prompt


class PromptBuilder:
    """
    ==========================================================
    Prompt Builder
    ==========================================================

    Central entry point for prompt construction.

    Responsibilities:
        - Obtain normalized runtime context from ContextBuilder.
        - Pass prepared context to prompt implementations.
        - Return a consistent PromptResult.

    Prompt implementations are responsible only for defining
    LLM instructions and prompt structure.

    They should not perform JSON serialization.
    ==========================================================
    """

    def __init__(self,context_builder: ContextBuilder,memory_context_service: MemoryContextService,):

        self.context_builder = context_builder
        self.memory_context_service = memory_context_service


    def _memory(self,agent_name: str,query_text: str,capability: str | None = None,) -> str:

        return self.memory_context_service.build(
        agent_name=agent_name,
        query_text=query_text,
        capability=capability,
    )

    # ======================================================
    # Agent Prompts
    # ======================================================

    def requirement_intelligence(self,requirement, clarification_context="",)->PromptResult:

        requirement_context = (self.context_builder.requirement(requirement))
        memory_text = self._memory(AgentNames.REQUIREMENT_INTELLIGENCE,requirement,)
        system_prompt, user_prompt = build_requirement_intelligence_prompt(requirement_context,memory_text,clarification_context,)
        return PromptResult(system_prompt=system_prompt,user_prompt=user_prompt,)



    def planner(self,requirement,intelligence,available_capabilities,)->PromptResult:

        requirement_context = (self.context_builder.requirement(requirement))
        intelligence_context = self.context_builder.requirement(
        {
        "intent": intelligence.intent,
        "context": intelligence.context,
        "assumptions": intelligence.assumptions,
        "unknowns": intelligence.unknowns,})
        capabilities_context = (self.context_builder.requirement(available_capabilities))
        planner_memory_query = (f"{requirement} "f"{intelligence.intent}")
        memory_text = self._memory(AgentNames.PLANNER,planner_memory_query)
        system_prompt, user_prompt = build_planning_prompt(requirement_context,intelligence_context,capabilities_context,memory_text,)
        return PromptResult(system_prompt=system_prompt,user_prompt=user_prompt,)


    def review(self,task,artifact,):

        task_context = self.context_builder.task(task)
        artifact_context = (self.context_builder.artifact(artifact))
        review_memory_query = (f"{task.description} "f"{task.capability}")
        memory_text = self._memory(AgentNames.REVIEW,review_memory_query,capability=task.capability,)
        system_prompt, user_prompt = build_review_prompt(task_context,artifact_context,memory_text,)
        return PromptResult(system_prompt=system_prompt,user_prompt=user_prompt,)


    # ======================================================
    # Generator Prompts
    # ======================================================


    def testcase(self,task,requirement,)-> PromptResult:

        task_context = self.context_builder.task(task)
        requirement_context = self.context_builder.requirement(requirement)
        memory_text = self._memory(AgentNames.TESTCASE,task.description,capability=task.capability,)
        system_prompt, user_prompt=build_testcase_prompt(task_context,requirement_context,memory_text)
        return PromptResult(system_prompt=system_prompt,user_prompt=user_prompt,)



    def automation(self,task,requirement,dependency_artifacts,)-> PromptResult:

        task_context = self.context_builder.task(task)
        requirement_context = self.context_builder.requirement(requirement)
        dependency_context = (self.context_builder.artifacts(dependency_artifacts))
        memory_text = self._memory(AgentNames.AUTOMATION,task.description,capability=task.capability,)
        system_prompt, user_prompt =build_automation_prompt(requirement_context,task_context,dependency_context, memory_text,)
        return PromptResult(system_prompt=system_prompt,user_prompt=user_prompt,)




    def database(self,task,requirement,)-> PromptResult:

        task_context = self.context_builder.task(task)
        requirement_context = self.context_builder.requirement(requirement)
        memory_text = self._memory(AgentNames.DATABASE,task.description,capability=task.capability,)
        system_prompt, user_prompt = build_database_prompt(task_context,requirement_context,memory_text,)
        return PromptResult(system_prompt=system_prompt,user_prompt=user_prompt,)



    def summary(self,task,requirement,)-> PromptResult:

        task_context = self.context_builder.task(task)
        requirement_context = self.context_builder.requirement(requirement)
        memory_text =  self._memory(AgentNames.SUMMARY,task.description,capability=task.capability,)
        system_prompt, user_prompt = build_summary_prompt(task_context,requirement_context,memory_text,)
        return PromptResult(system_prompt=system_prompt,user_prompt=user_prompt,)


    def correction(self,task,requirement,previous_content,feedback,dependency_artifacts,)-> PromptResult:

        task_context = self.context_builder.task(task)
        requirement_context = self.context_builder.requirement(requirement)
        previous_context = (self.context_builder.requirement(previous_content))
        feedback_context = (self.context_builder.requirement(feedback))
        dependency_context = (self.context_builder.artifacts(dependency_artifacts))
        correction_memory_query = (f"{task.description} "f"{task.capability} "f"{feedback}")
        memory_text = self._memory(AgentNames.CORRECTION,correction_memory_query,capability=task.capability,)
        system_prompt, user_prompt = build_correction_prompt(
            task_context,
            requirement_context,
            previous_context,
            feedback_context,
            dependency_context,memory_text,)
        return PromptResult(system_prompt=system_prompt,user_prompt=user_prompt,)