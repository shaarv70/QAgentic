import json


def build_database_prompt(task, requirement):

    context = json.dumps(
        task.context,
        indent=2
    )

    return f"""
You are a Senior Database QA Engineer.

Requirement:
{requirement}

Task:
{task.description}

Context:
{context}

Generate the database validation or SQL required for this task.

Use the database type, schema information, table information, expected
behavior, and other technical details when they are available in the context.

Do not invent database structures that are not provided.

When exact schema information is unavailable, clearly use placeholders
rather than assuming table or column names.

Return the required database validation or SQL with only the explanation
necessary to understand or use it.
"""