def build_summary_prompt(task_context, requirement_context, memory_context):


    system_prompt = """
You are a Senior QA Analyst.

Generate the summary requested by the task.

Base the summary only on the provided context.
Do not invent unsupported details.

Return the summary only.
"""

    user_prompt = f"""
REQUIREMENT:

{requirement_context}


TASK CONTEXT:

{task_context}


RELEVANT MEMORY:

{memory_context}
"""

    return system_prompt, user_prompt