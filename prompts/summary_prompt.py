def build_summary_prompt(task_context, requirement_context):


    system_prompt = """
You are a Senior QA Analyst.

Generate the summary requested by the task.

Base the summary on the requirement, task description, and
available context.

Do not invent details that are not supported by the provided
information.

Return the summary only.
"""

    user_prompt = f"""
REQUIREMENT:

{requirement_context}


TASK CONTEXT:

{task_context}
"""

    return system_prompt, user_prompt