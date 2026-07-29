import json


def build_automation_prompt(
    task,
    requirement,
    dependency_artifacts
):

    context = json.dumps(
        task.context,
        indent=2
    )

    dependencies = json.dumps(
        dependency_artifacts,
        indent=2
    )

    return f"""
You are a Senior Automation Test Engineer.

Original Requirement:
{requirement}

Automation Task:
{task.description}

Task Context:
{context}

Approved Upstream Artifacts:
{dependencies}

Generate automation for the approved upstream test cases.

IMPORTANT:

The upstream artifacts are outputs of tasks that this automation
task depends on and have already passed quality review.

Use those artifacts as the source of truth for which test scenarios
must be automated.

Do not independently create a different test suite.

Do not omit approved test cases merely to simplify the automation.

Do not invent application behavior that is not supported by the
requirement, task context, or upstream artifacts.

Follow the requested programming language, automation framework,
and test framework when provided in the task context.

Reuse common setup and helper methods where appropriate instead
of duplicating code unnecessarily.

Return ONLY the automation artifact.
"""