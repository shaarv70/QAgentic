def build_testcase_prompt(
    task_context,
    requirement_context,
    memory_context,
    dependency_context="",
    dom_snapshot="",
):
    system_prompt = """
You are a Senior QA Engineer.

Generate functional test cases for the requested requirement.

Rules:
- Generate EXACTLY 8 test cases — no more, no fewer. Hard limit: 8.
- Choose only the highest-priority scenarios: critical positive paths,
  the most impactful negative paths, and one boundary case.
  Do NOT list every permutation.
- Do not duplicate scenarios or force irrelevant coverage.
- If a LIVE PAGE DOM SNAPSHOT is provided in the context below, use the
  real element names, labels, and structure from the snapshot to write
  accurate, grounded test cases. Do NOT invent selectors or page structure
  when real data is available.
- If no DOM snapshot is provided, base expected results only on behavior
  supported by the requirement, task context, and relevant memory.
- Do not invent exact error messages, limits, policies, security behavior,
  URLs, technologies, or business rules unless present in the DOM snapshot.
- When behavior is unknown, use a generic verifiable invariant or omit
  the scenario.
- Keep steps concise: 2–4 bullets per test case, not paragraphs.
- Keep expected results to a single sentence.
- Preserve supplied values exactly.

Return ONLY a Markdown table with exactly 8 rows:

| Scenario | Steps | Expected Result |
|----------|-------|-----------------|
"""

    dom_section = ""
    if dom_snapshot and dom_snapshot.strip():
        dom_section = f"""
LIVE PAGE DOM SNAPSHOT (use this for accurate selectors and page structure):

{dom_snapshot}
"""

    user_prompt = f"""
REQUIREMENT:

{requirement_context}

TASK:

{task_context}
{dom_section}
RELEVANT MEMORY:

{memory_context}
"""

    return system_prompt.strip(), user_prompt.strip()
