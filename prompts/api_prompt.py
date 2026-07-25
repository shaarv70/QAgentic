def build_api_prompt(application_type, requirement):

    prompt = f"""
You are a Senior QA Engineer.

Application Type:
{application_type}

Requirement:
{requirement}

Generate comprehensive API test cases.

Include:

1. Positive Test Cases
2. Negative Test Cases
3. Boundary Test Cases
4. Validation Test Cases
5. HTTP Status Code Validation
6. Request Header Validation
7. Response Body Validation

Return the answer in Markdown table format.
"""

    return prompt