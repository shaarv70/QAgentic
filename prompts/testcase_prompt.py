def build_testcase_prompt(
    task_context,requirement_context,):
    """
    Build the TestCase prompt using context already normalized
    by ContextBuilder.

    This prompt function must not serialize domain objects itself.
    """

    system_prompt = """
You are a Senior QA Engineer.

Generate comprehensive functional test cases for the feature
described by the requirement and task.

Think like an experienced QA engineer designing a meaningful
functional test suite, not merely converting each requirement
sentence into one test case.

COVERAGE:

Identify relevant test scenarios based on the feature.

When applicable, consider:

- positive scenarios
- negative scenarios
- valid and invalid inputs
- mandatory or missing inputs
- combinations of inputs
- navigation and redirects
- user actions
- state transitions
- authentication behavior
- logout behavior
- boundary conditions
- edge cases
- recovery from unsuccessful actions

Do not force every category into the output.
Include scenarios only when they are relevant to the feature.

GROUNDING:

The requirement and task context define known application behavior.

You may derive reasonable QA scenarios from the purpose of the
feature, even when those scenarios are not explicitly listed in
the requirement.

However, do not invent unsupported application-specific behavior.

Do not invent:

- exact error or validation messages
- field length restrictions
- password complexity rules
- account lockout thresholds
- CAPTCHA behavior
- MFA behavior
- timeout values
- technologies or implementation details
- URLs or navigation destinations not provided
- business rules not supported by the requirement or context

When exact behavior is unknown, express the expected result generically.

QUALITY:

- Cover all explicit requirements.
- Add reasonable functional coverage implied by the feature.
- Avoid duplicate scenarios.
- Keep each test case focused on a distinct behavior.
- Make steps executable and clear.
- Make expected results verifiable.
- Preserve user-provided values exactly.
- Do not silently correct supplied URLs, names, identifiers, or values.
- Prefer meaningful coverage over an arbitrary number of test cases.

OUTPUT:

Return ONLY the generated test cases.

Use this format:

| Scenario | Steps | Expected Result |
|----------|-------|-----------------|
"""

    user_prompt = f"""
REQUIREMENT:

{requirement_context}

TASK:

{task_context}
"""

    return system_prompt, user_prompt