import json


def build_correction_prompt(
    task,
    requirement,
    previous_content,
    feedback,
    dependency_artifacts=None
):

    context = json.dumps(
        task.context,
        indent=2
    )

    dependencies = json.dumps(
        dependency_artifacts or {},
        indent=2
    )

    return f"""
You are a Senior QA Engineer.

Requirement:
{requirement}

Task:
{task.description}

Capability:
{task.capability}

Context:
{context}

Approved Upstream Artifacts:
{dependencies}

Previous Artifact:
{previous_content}

Review Feedback:
{feedback}

The previous artifact failed quality review.

Correct the artifact so that it satisfies the original requirement,
task description, context, approved upstream artifacts, and review
feedback.

The approved upstream artifacts are source inputs for this task.
Do not contradict, replace, or ignore them.

Preserve correct parts of the previous artifact.

Fix the issues identified by the review.

Do not introduce unrelated functionality or unsupported assumptions.

REMOVAL OF UNSUPPORTED TEST CASES:

Not every test case from the previous artifact must be preserved.

If a test case depends on application behavior that is not defined
by the requirement, task context, approved upstream artifacts, or
review feedback, and no single deterministic expected result can be
established, REMOVE that test case.

Do not preserve an unsupported scenario by writing conditional
expected results.

Do not use alternatives such as:

- "if the system..."
- "depending on..."
- "either..."
- "may..."
- "could..."
- "where applicable..."
- "if supported..."

Do not invent a product rule merely to make the scenario deterministic.

Preserve correct test cases, correct fixable test cases, and remove
test cases whose expected behavior cannot be determined from the
available information.

Comprehensive coverage means comprehensive coverage of known and
testable behavior. It does not require speculative scenarios.

Return ONLY the corrected artifact.
"""