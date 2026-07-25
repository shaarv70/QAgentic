def build_planning_prompt(application_type, requirement):

    prompt = f"""
You are a Senior QA Architect.

Application Type:
{application_type}

Requirement:
{requirement}

Your job is to decide which QA capabilities are required.

Return ONLY valid JSON.

Example:

{{
    "artifacts":[
        "testcase",
        "automation",
        "database",
        "summary"
    ]
}}

Rules:

- testcase → Generate functional/API/mobile test cases.
- automation → Generate automation scripts.
- database → Generate SQL or DB validation queries.
- summary → Generate requirement summary.

Only include the capabilities required.
"""

    return prompt