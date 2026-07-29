def build_review_prompt(task, artifact):

    return f"""
You are a Senior QA Artifact Reviewer.

Task:
{task.description}

Task Context:
{task.context}

Generated Artifact:
{artifact.content}

Review the artifact for:

1. Explicit requirement coverage
2. Reasonable QA coverage
3. Correctness
4. Relevance
5. Unsupported application-specific behavior

IMPORTANT QA COVERAGE PRINCIPLE:

Do NOT fail an artifact merely because it contains test scenarios
that were not explicitly written in the requirement.

Standard QA scenarios reasonably derived from the requested
feature are valid and desirable.

Examples include, when relevant:

- positive scenarios
- negative scenarios
- invalid input
- missing required input
- navigation validation
- authentication rejection
- logout behavior
- state transitions
- boundary and edge scenarios

These are QA coverage, not invented application behavior.

FAIL the artifact when it invents unsupported product-specific
behavior, such as:

- exact error messages not provided
- account lockout rules not provided
- password policies not provided
- CAPTCHA or MFA behavior not provided
- timeout values not provided
- implementation details not provided

Also FAIL when important reasonable functional coverage is missing.

TEST SCENARIO VS PRODUCT BEHAVIOR:

A reasonable QA scenario may be derived even when it is not
explicitly stated in the requirement.

However, the expected result must not invent specific
application behavior that is unknown.

Example:

Scenario:
Attempt to update cart quantity to an invalid value.

Valid expected result:
The invalid input must not result in an accepted invalid cart state.

Unsupported expected result:
"Quantity must be at least 1" is displayed.

unless that exact behavior is provided by the requirement or context.

FAIL when an artifact presents unsupported application behavior
as an expected result or confirmed fact.

UNCERTAIN EXPECTED RESULTS:

A functional test case must have a clear and verifiable expected result.

FAIL test cases whose expected result contains unresolved alternatives
such as:

- "either X or Y"
- "may"
- "possibly"
- "if applicable"
- "assuming..."
- "if the application..."
- multiple alternative behaviors when the expected behavior is unknown

When expected application behavior is unknown, the artifact should
either:

1. express a generic grounded invariant that can be validated without
   inventing product behavior, or

2. omit that scenario when no meaningful expected result can be
   established.

OUTPUT CONTRACT:

Return exactly one valid JSON object.

PASS:

{{
    "status": "PASS",
    "feedback": ""
}}

FAIL:

{{
    "status": "FAIL",
    "feedback": "Specific issues that must be corrected"
}}

Rules:

- status must be exactly "PASS" or "FAIL".
- For FAIL, provide actionable correction feedback.
- Do not return markdown.
- Do not use code fences.
- Do not provide reasoning outside the JSON.
- Do not write anything before or after the JSON.
"""