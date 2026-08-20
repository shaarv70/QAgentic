def build_testcase_prompt(
    task_context,requirement_context, memory_context,):
    """
    Build the TestCase prompt using context already normalized
    by ContextBuilder.

    This prompt function must not serialize domain objects itself.
    """

    system_prompt = """
You are a Senior QA Engineer.

Generate functional test cases for the requested requirement.

Rules:
- Cover explicit requirements with relevant positive, negative,
  validation, boundary, state, and recovery scenarios.
- Do not duplicate scenarios or force irrelevant coverage.
- Base expected results only on behavior supported by the requirement,
  task context, and relevant memory.
- Do not invent exact error messages, limits, policies, security behavior,
  URLs, technologies, or business rules.
- When behavior is unknown, use a generic verifiable invariant or omit
  the scenario.
- Keep steps executable and expected results clear and verifiable.
- Preserve supplied values exactly.

Return only a Markdown table:

| Scenario | Steps | Expected Result |
|----------|-------|-----------------|
"""

    user_prompt = f"""
REQUIREMENT:

{requirement_context}

TASK:

{task_context}


RELEVANT MEMORY:

{memory_context}
"""

    return system_prompt, user_prompt