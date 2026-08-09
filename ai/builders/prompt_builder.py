from ai.builders.context_builder import ContextBuilder
from ai.prompts.prompt_result import PromptResult
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

    def __init__(self,context_builder: ContextBuilder,):

        self.context_builder = context_builder



    # ======================================================
    # Agent Prompts
    # ======================================================

    def requirement_intelligence(self,requirement,)->PromptResult:

        requirement_context = (self.context_builder.requirement(requirement))
        system_prompt, user_prompt = (build_requirement_intelligence_prompt(requirement_context))
        return PromptResult(system_prompt=system_prompt,user_prompt=user_prompt,)



    def planner(self,requirement,intelligence,available_capabilities,)->PromptResult:

        requirement_context = (self.context_builder.requirement(requirement))
        intelligence_context = intelligence
        capabilities_context = (self.context_builder.requirement(available_capabilities))
        system_prompt, user_prompt = build_planning_prompt(requirement_context,intelligence_context,capabilities_context,)
        return PromptResult(system_prompt=system_prompt,user_prompt=user_prompt,)


    def review(self,task,artifact,):

        task_context = self.context_builder.task(task)
        artifact_context = (self.context_builder.artifact(artifact))
        system_prompt, user_prompt = build_review_prompt(task_context,artifact_context,)
        return PromptResult(system_prompt=system_prompt,user_prompt=user_prompt,)


    # ======================================================
    # Generator Prompts
    # ======================================================


    def testcase(self,task,requirement,)-> PromptResult:

        task_context = self.context_builder.task(task)
        requirement_context = self.context_builder.requirement(requirement)
        system_prompt, user_prompt=build_testcase_prompt(task_context,requirement_context,)
        return PromptResult(system_prompt=system_prompt,user_prompt=user_prompt,)



    def automation(self,task,requirement,dependency_artifacts,)-> PromptResult:

        task_context = self.context_builder.task(task)
        requirement_context = self.context_builder.requirement(requirement)
        dependency_context = (self.context_builder.artifacts(dependency_artifacts))
        system_prompt, user_prompt =build_automation_prompt(requirement_context,task_context,dependency_context,)
        return PromptResult(system_prompt=system_prompt,user_prompt=user_prompt,)




    def database(self,task,requirement,)-> PromptResult:

        task_context = self.context_builder.task(task)
        requirement_context = self.context_builder.requirement(requirement)
        system_prompt, user_prompt = build_database_prompt(task_context,requirement_context,)
        return PromptResult(system_prompt=system_prompt,user_prompt=user_prompt,)



    def summary(self,task,requirement,)-> PromptResult:

        task_context = self.context_builder.task(task)
        requirement_context = self.context_builder.requirement(requirement)
        system_prompt, user_prompt = build_summary_prompt(task_context,requirement_context,)
        return PromptResult(system_prompt=system_prompt,user_prompt=user_prompt,)


    def correction(self,task,requirement,previous_content,feedback,dependency_artifacts,)-> PromptResult:

        task_context = self.context_builder.task(task)
        requirement_context = self.context_builder.requirement(requirement)
        previous_context = (self.context_builder.requirement(previous_content))
        feedback_context = (self.context_builder.requirement(feedback))
        dependency_context = (self.context_builder.artifacts(dependency_artifacts))
        system_prompt, user_prompt = build_correction_prompt(
            task_context,
            requirement_context,
            previous_context,
            feedback_context,
            dependency_context,)
        return PromptResult(system_prompt=system_prompt,user_prompt=user_prompt,)