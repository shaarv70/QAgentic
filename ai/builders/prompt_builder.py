from ai.builders.context_builder import ContextBuilder
from ai.prompts.prompt_result import PromptResult
from constants.agent_names import AgentNames
from memory.memory_context_service import MemoryContextService
from prompts.mcp_execution_prompt import build_mcp_execution_prompt

from prompts.planning_prompt import build_planning_prompt
from prompts.repository_analysis_prompt import build_repository_analysis_prompt
from prompts.repository_execution_prompt import build_repository_execution_prompt
from prompts.requirement_intelligence_prompt import (
    build_requirement_intelligence_prompt,
)

from prompts.review_prompt import build_review_prompt
from prompts.testcase_prompt import build_testcase_prompt
from prompts.automation_prompt import build_automation_prompt
from prompts.database_prompt import build_database_prompt
from prompts.summary_prompt import build_summary_prompt
from prompts.correction_prompt import build_correction_prompt
from prompts.self_healing_prompt import build_self_healing_prompt
from prompts.test_gap_analysis_prompt import build_test_gap_analysis_prompt


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


    # Maximum characters of memory context injected into any prompt.
    # Prevents large episodic memories (e.g. full prior test-case tables)
    # from bloating the LLM input and causing timeout on generation.
    _MEMORY_CONTEXT_MAX_CHARS = 4000

    def _memory(self,agent_name: str,query_text: str,capability: str | None = None, context: dict[str, str] | None = None,) -> str:

        raw = self.memory_context_service.build(
            agent_name=agent_name,
            query_text=query_text,
            capability=capability,
            context=context,
        )
        if len(raw) > self._MEMORY_CONTEXT_MAX_CHARS:
            raw = raw[: self._MEMORY_CONTEXT_MAX_CHARS] + "\n... [memory truncated]"
        return raw

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


    def review(
    self,
    task,
    artifact,
    dependency_artifacts=None,
) -> PromptResult:

        task_context = self.context_builder.task(task)

        artifact_context = (
            self.context_builder.artifact(artifact)
        )

        dependency_context = (
            self.context_builder.artifacts(
                dependency_artifacts or {}
            )
        )

        review_memory_query = (
            f"{task.description} "
            f"{task.capability}"
        )

        execution_context = (
            self._extract_execution_context(artifact)
        )

        memory_text = self._memory(
            AgentNames.REVIEW,
            review_memory_query,
            capability=task.capability,
            context=execution_context,
        )

        system_prompt, user_prompt = build_review_prompt(
            task_context,
            artifact_context,
            dependency_context,
            memory_text,
        )

        return PromptResult(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

    # ======================================================
    # Generator Prompts
    # ======================================================


    def testcase(self, task, requirement, dependency_artifacts=None) -> PromptResult:

        task_context = self.context_builder.task(task)
        requirement_context = self.context_builder.requirement(requirement)
        dependency_context = self.context_builder.artifacts(dependency_artifacts or {})
        dom_snapshot = self._extract_dom_snapshot(dependency_artifacts or {})
        memory_text = self._memory(AgentNames.TESTCASE, task.description, capability=task.capability)
        system_prompt, user_prompt = build_testcase_prompt(
            task_context, requirement_context, memory_text, dependency_context, dom_snapshot
        )
        return PromptResult(system_prompt=system_prompt, user_prompt=user_prompt)

    @staticmethod
    def _extract_dom_snapshot(dependency_artifacts: dict) -> str:
        for artifact_content in dependency_artifacts.values():
            if isinstance(artifact_content, dict) and artifact_content.get("page_inspection"):
                snapshot = artifact_content.get("dom_snapshot", "")
                if snapshot:
                    return snapshot
        return ""



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



    def self_healing(
        self,
        execution_output: str,
        automation_files_context: str,
        requirement: str,
        task,
        dom_context: str = "",
        diagnosis: dict | None = None,
    ) -> PromptResult:
        requirement_context = self.context_builder.requirement(requirement)
        task_context = self.context_builder.task(task)
        memory_text = self._memory(
            AgentNames.SELF_HEALING,
            task.description,
            capability="test_execution",
        )
        system_prompt, user_prompt = build_self_healing_prompt(
            execution_output=execution_output,
            automation_files_context=automation_files_context,
            requirement_context=requirement_context,
            task_context=task_context,
            memory_context=memory_text,
            dom_context=dom_context,
            diagnosis=diagnosis,
        )
        return PromptResult(system_prompt=system_prompt, user_prompt=user_prompt)

    def self_healing_diagnosis(
        self,
        execution_output: str,
        files_context: str,
        requirement: str,
    ) -> PromptResult:
        from prompts.self_healing_diagnosis_prompt import build_self_healing_diagnosis_prompt
        requirement_context = self.context_builder.requirement(requirement)
        system_prompt, user_prompt = build_self_healing_diagnosis_prompt(
            execution_output=execution_output,
            files_context=files_context,
            requirement_context=requirement_context,
        )
        return PromptResult(system_prompt=system_prompt, user_prompt=user_prompt)

    def mcp_execution(
    self,
    execution_context,
    available_tools,
) -> PromptResult:

        execution_context = self.context_builder.requirement(
            execution_context
        )

        tools_context = self.context_builder.requirement(
            available_tools
        )

        memory_text = self._memory(
            AgentNames.MCP_EXECUTION,
            execution_context,
            capability="test_execution",
        )

        system_prompt, user_prompt = (
            build_mcp_execution_prompt(
                execution_context,
                tools_context,
                memory_text,
            )
        )

        return PromptResult(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )


    def repository_execution(
        self,
        repository_context,
        available_tools,
    ) -> PromptResult:
        """Build the repository execution planning prompt.

        Repository execution participates in the same RAG architecture as
        the other agent prompts. Memory is advisory context only; the trusted
        repository operation and available MCP tools remain the execution
        boundary.
        """

        memory_query = (
            f"{repository_context} "
            f"{available_tools}"
        )

        memory_text = self._memory(
            AgentNames.REPOSITORY_EXECUTION,
            memory_query,
            capability="repository_execution",
        )

        system_prompt, user_prompt = build_repository_execution_prompt(
            repository_context=repository_context,
            available_tools=available_tools,
            memory_context=memory_text,
        )

        return PromptResult(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )




    @staticmethod
    def _extract_execution_context(
        artifact,
    ) -> dict[str, str]:

        if not isinstance(artifact.content, dict):
            return {}

        metadata = artifact.content.get("metadata", {})

        if not isinstance(metadata, dict):
            return {}

        context = {}

        for key in (
            "repository_url",
            "framework",
            "command",
            "branch",
            "test_path",
        ):
            value = metadata.get(key)

            if value is None:
                # command is stored at the artifact-content root
                # for TestExecutionResult.
                value = artifact.content.get(key)

            if value is not None:
                context[key] = str(value)

        return context



    def test_gap_analysis(
        self,
        workspace_path: str,
        framework: str,
        test_files_evidence: list,
        source_files_evidence: list,
    ) -> PromptResult:
        memory_text = self._memory(
            AgentNames.TEST_GAP_ANALYSIS,
            f"{workspace_path} {framework} test gap analysis",
            capability="test_gap_analysis",
        )
        system_prompt, user_prompt = build_test_gap_analysis_prompt(
            workspace_path=workspace_path,
            framework=framework,
            test_files_evidence=test_files_evidence,
            source_files_evidence=source_files_evidence,
            memory_context=memory_text,
        )
        return PromptResult(system_prompt=system_prompt, user_prompt=user_prompt)

    def repository_analysis(
    self,
    workspace_path,
    repository_evidence,
    requested_suite=None,
) -> PromptResult:

        memory_text = self._memory(
            AgentNames.REPOSITORY_ANALYSIS,
            (
                f"{workspace_path} "
                f"{requested_suite or ''}"
            ),
            capability="repository_analysis",
        )

        system_prompt, user_prompt = (
            build_repository_analysis_prompt(
                workspace_path=workspace_path,
                repository_evidence=repository_evidence,
                requested_suite=requested_suite,
                memory_context=memory_text,
            )
        )

        return PromptResult(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )