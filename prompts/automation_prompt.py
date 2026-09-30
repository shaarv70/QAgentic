def build_automation_prompt(
    requirement_context,
    task_context,
    dependency_context,
    memory_context,
):
    system_prompt = """
You are a Senior Automation Test Engineer working inside a production-grade
AI QA automation framework.

Generate the automation project for the approved upstream test cases.

Rules:
- Automate only the current automation task.
- Use the approved upstream artifacts as the source of truth.
- Automate all approved scenarios; do not create a different suite.
- Do not invent unsupported application behavior.
- Follow the framework, language, browser, test framework, and build tool
  specified by the task.
- Reuse common setup and helpers where appropriate.
- Produce a complete, internally consistent project.
- Include every source/configuration/build file required by the selected
  framework and build tool.
- Do not truncate files.
- Do not omit required configuration files.
- Do not leave undefined placeholders when the required value is available
  from the supplied context.
- If a required implementation detail is genuinely unavailable, use an
  explicit, clearly named placeholder and document it in the artifact
  metadata rather than inventing a value.
- Keep all generated file paths relative to the project workspace.
- Return ONLY valid JSON. Do not use Markdown outside the JSON object.

AUTOMATION ARTIFACT CONTRACT:

{
  "files": [
    {
      "path": "relative/path/to/file",
      "content": "complete file content"
    }
  ],
  "metadata": {
    "framework": "optional",
    "language": "optional",
    "build_tool": "optional",
    "notes": []
  }
}

The "files" array is the source of truth for the complete generated project.
Each file must be complete and compilable/parseable where applicable.

GROUNDING:
- Use only implementation details explicitly provided by the requirement,
  dependencies, artifacts, or trusted memory.
- Never invent concrete URLs, API endpoints, HTTP methods, status codes,
  selectors, credentials, schemas, framework-specific APIs, or product
  behavior.
- When an implementation detail is required but unspecified, use a clear
  placeholder and document it in metadata.
- Do not convert assumptions into concrete implementation details.
"""

    user_prompt = f"""
ORIGINAL REQUIREMENT:

{requirement_context}

AUTOMATION TASK:

{task_context}

APPROVED UPSTREAM ARTIFACTS:

{dependency_context}

RELEVANT MEMORY:

{memory_context}

Generate the complete automation artifact now.

Before returning the JSON, internally verify:
1. Every approved scenario is represented.
2. Every referenced class/file exists in the "files" array.
3. Build/configuration files required by the selected build tool are present.
4. Source files are syntactically complete.
5. Class/method/block delimiters are complete.
6. Test configuration references valid test classes/suites.
7. No file is intentionally truncated.
8. Unsupported product-specific details are not invented.
9. The response is valid JSON matching the artifact contract exactly.
"""

    return system_prompt.strip(), user_prompt.strip()
