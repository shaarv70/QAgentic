def build_requirement_prompt(application_type,requirement):

    prompt = f"""
You are a Senior QA Engineer.

Analyze the following requirement.

Application Type:
{application_type}

Requirement:
{requirement}

Return ONLY valid JSON.

Example:

{{
    "status":"COMPLETE",
    "questions":[]
}}

OR

{{
    "status":"INCOMPLETE",
    "questions":[
        "...",
        "...",
        "..."
    ]
}}

Do not return markdown.

Do not explain.

Only JSON.
"""

    return prompt