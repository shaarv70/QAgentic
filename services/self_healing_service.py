from constants.agent_names import AgentNames
from models.automation_artifact import AutomationArtifact
from services.base_generator import BaseGenerator


class SelfHealingService(BaseGenerator):
    """
    Analyses a test execution failure and produces a patched AutomationArtifact.

    Called by TestExecutionCapability.correct() when a test run fails review.
    The service passes the raw failure output (stdout/stderr) together with
    the current automation source files to the LLM, which returns a corrected
    project in the standard delimiter format.
    """

    def __init__(self, ai_service, prompt_builder):
        super().__init__(ai_service, prompt_builder)

    def heal(
        self,
        execution_output: str,
        automation_artifact: AutomationArtifact,
        requirement: str,
        task,
    ) -> AutomationArtifact:
        """
        Return a fixed AutomationArtifact based on the execution failure.

        Parameters
        ----------
        execution_output:
            Raw stdout / stderr captured during the failed test run.
        automation_artifact:
            The automation project that was executed and failed.
        requirement:
            The original user requirement (for context).
        task:
            The test_execution task (for context builder).
        """
        automation_files_context = self._format_files(automation_artifact)

        prompt = self.prompt_builder.self_healing(
            execution_output=execution_output,
            automation_files_context=automation_files_context,
            requirement=requirement,
            task=task,
        )

        content = self.generate_text(
            AgentNames.SELF_HEALING,
            prompt.system_prompt,
            prompt.user_prompt,
        )

        return AutomationArtifact.from_llm_content(content)

    def generate(self, task, execution_context) -> str:
        raise NotImplementedError(
            "SelfHealingService.generate() is not used — call heal() instead."
        )

    def correct(self, task, execution_context, previous_content, feedback) -> str:
        raise NotImplementedError(
            "SelfHealingService.correct() is not used — call heal() instead."
        )

    @staticmethod
    def _format_files(artifact: AutomationArtifact) -> str:
        """Render the automation artifact as delimiter-formatted text for the prompt."""
        parts = []
        for f in artifact.files:
            parts.append(f"--- BEGIN_FILE: {f.path} ---\n{f.content}\n--- END_FILE ---")
        if artifact.metadata:
            import json
            parts.append(
                f"--- BEGIN_METADATA ---\n"
                f"{json.dumps(artifact.metadata, indent=2)}\n"
                f"--- END_METADATA ---"
            )
        return "\n\n".join(parts)
