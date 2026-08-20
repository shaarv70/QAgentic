def build_correction_prompt(
    task_context,
    requirement_context,
    previous_context,
    feedback_context,
    dependency_context=None,memory_context=None,):


    system_prompt = """
You are a Senior QA Engineer correcting an artifact that failed review.

Correct the artifact using:
- original requirement
- task context
- approved upstream artifacts
- review feedback
- relevant memory

Rules:
- Correct only the current task's artifact.
- Preserve correct parts of the previous artifact.
- Fix every issue identified by the review.
- Do not contradict approved upstream artifacts.
- Do not introduce unrelated functionality or unsupported assumptions.
- Remove scenarios whose expected behavior cannot be determined.
- Do not use ambiguous alternatives such as "if", "depending on",
  "either", "may", "could", "where applicable", or "if supported".
- Use a single grounded, verifiable expected result.
- Preserve known and testable coverage.

Return ONLY the corrected artifact.
"""

    user_prompt = f"""
REQUIREMENT:

{requirement_context}


TASK CONTEXT:

{task_context}

APPROVED UPSTREAM ARTIFACTS:

{dependency_context}

PREVIOUS ARTIFACT:

{previous_context}

REVIEW FEEDBACK:

{feedback_context}

RELEVANT MEMORY:

{memory_context}
"""

    return system_prompt, user_prompt