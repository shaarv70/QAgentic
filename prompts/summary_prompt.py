import json


def build_summary_prompt(task, requirement):

    context = json.dumps(
        task.context,
        indent=2
    )

    return f"""
You are a Senior QA Analyst.

Requirement:
{requirement}

Task:
{task.description}

Context:
{context}

Generate the summary requested by the task.

Base the summary on the requirement, task description, and available context.

Do not invent details that are not supported by the provided information.

Return the summary only.
"""