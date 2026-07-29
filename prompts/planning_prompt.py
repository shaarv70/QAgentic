import json


def build_planning_prompt(
    requirement,
    intelligence,
    available_capabilities
):

    intelligence_data = {
        "intent": intelligence.intent,
        "context": intelligence.context,
        "assumptions": intelligence.assumptions
    }

    intelligence_json = json.dumps(
        intelligence_data,
        indent=2
    )

    capabilities_json = json.dumps(
        available_capabilities,
        indent=2
    )

    return f"""
You are a Senior QA Architect.

Requirement:
{requirement}

Requirement Analysis:
{intelligence_json}

Currently Available Capabilities:
{capabilities_json}

Create an execution plan for the requirement.

Break the work into tasks that can be executed using the currently
available capabilities.

Each task must contain:

- capability: The capability that will execute this task.
- description: The specific work that must be performed.
- context: Information needed to execute the task.

Return ONLY valid JSON.

{{
    "tasks": [
        {{
            "capability": "testcase",
            "description": "Generate functional test cases for login",
            "context": {{}}
            "depends_on": []
        }}
    ],
    "priority": "MEDIUM",
    "parallel": true
}}
TASK DEPENDENCIES:

Each task must contain a "depends_on" field.

"depends_on" is a list of task IDs whose generated artifacts are
required before the current task can execute.

Use an empty list when the task can execute independently.

Example:

If the user requests:

"Generate functional test cases and automate the generated test cases"

create:

task_1:
capability = testcase
depends_on = []

task_2:
capability = automation
depends_on = ["task_1"]

because automation must use the test cases produced by task_1.

Do NOT create dependencies merely because tasks are related.

A dependency exists only when a task requires the OUTPUT of another
task to perform its work.

Independent tasks should have depends_on = [].

Rules:

- Use only capabilities listed under Currently Available Capabilities.
- Create only tasks required to satisfy the user's request.
- Do not create unnecessary tasks.
- Use the analyzed intent to understand the requested outcome.
- Use grounded requirement context when creating task context.
- Preserve user-provided values exactly.
- Do not convert assumptions into confirmed facts.
- Include only context relevant to executing that specific task.
- Do not invent technologies, business rules, URLs, validation behavior,
  implementation details, or application behavior.
- Keep each task focused on one executable unit of work.
- priority must be HIGH, MEDIUM, or LOW.
- parallel must be true only when all planned tasks can execute independently.
"""