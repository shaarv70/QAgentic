from constants.agent_names import AgentNames
from models.action_spec import ActionSpec
from models.automation_artifact import AutomationArtifact
from services.base_generator import BaseGenerator


class AutomationGenerator(BaseGenerator):

    action_spec = ActionSpec(
        name="automation",
        kind="tool",
        description="Generate automated test code from functional test cases.",
        requires=("test_cases",),
        produces=("automation_code",),
    )

    def __init__(self, ai_service, prompt_builder):
        super().__init__(
            ai_service,
            prompt_builder,
        )

    def generate(self, task, execution_context):
        dependency_artifacts = (
            execution_context.dependency_artifacts
        )

        prompt = self.prompt_builder.automation(
            task,
            execution_context.requirement,
            dependency_artifacts,
        )

        content = self.generate_text(
            AgentNames.AUTOMATION,
            prompt.system_prompt,
            prompt.user_prompt,
        )

        return AutomationArtifact.from_llm_content(content).to_json()

    def correct(
        self,
        task,
        execution_context,
        previous_content,
        feedback,
    ):
        dependency_artifacts = (
            execution_context.dependency_artifacts
        )

        contract_feedback = f"""
The previous automation artifact must remain a structured automation artifact.

Return the corrected project using the EXACT delimiter format shown below.
Do NOT use JSON. Do NOT use markdown fences inside file content.

--- BEGIN_FILE: relative/path/to/file ---
[complete file content here, exactly as it would appear on disk]
--- END_FILE ---

Repeat for every file. After all files, add:

--- BEGIN_METADATA ---
framework: <framework name>
language: <language>
build_tool: <build tool>
run_command: <exact command to compile and run the tests>
notes:
  - <note>
--- END_METADATA ---

Preserve correct files from the previous artifact. Change only what is
required by the reviewer feedback, while ensuring the final artifact is a
complete internally consistent project.

REVIEWER FEEDBACK:
{feedback}
""".strip()

        prompt = self.prompt_builder.correction(
            task,
            execution_context.requirement,
            previous_content,
            contract_feedback,
            dependency_artifacts,
        )

        content = self.generate_text(
            AgentNames.CORRECTION,
            prompt.system_prompt,
            prompt.user_prompt,
        )

        return AutomationArtifact.from_llm_content(content).to_json()
