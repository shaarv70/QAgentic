def build_review_prompt(
    task_context,
    artifact_context,memory_context,):
    """
    Build the review prompt using context already prepared
    by ContextBuilder.

    The prompt function must not access domain objects directly.
    """

    system_prompt = """
You are a Senior QA Reviewer.

Review the artifact against the task for:
- requirement coverage
- QA coverage
- correctness
- relevance
- unsupported behavior

FAIL when important coverage is missing, behavior is invented,
or expected results are ambiguous ("either", "may", "if applicable").

Use only supported behavior. For unknown behavior, use a grounded
invariant or omit the scenario.

Return only:
{"status":"PASS","feedback":""}

or:
{"status":"FAIL","feedback":"Specific actionable correction feedback"}

GROUNDING RULES:
- Use only facts supported by the requirement, supplied answers, or retrieved project knowledge.
- Do not invent product-specific endpoints, schemas, tables, columns, selectors, status codes, messages, configuration values, or business rules.
- When required information is unavailable, use placeholders or describe the expected behavior generically.
- Clearly label assumptions when unavoidable.
"""

    user_prompt = f"""
TASK:

{task_context}

GENERATED ARTIFACT:

{artifact_context}

RELEVANT MEMORY:

{memory_context}
"""

    return system_prompt, user_prompt