def build_requirement_intelligence_prompt(requirement,memory_context,clarification_context=""):

    system_prompt = """
You are a Senior QA Requirement Analyst.

Analyze the requirement and return ONLY valid JSON:

{
  "status": "READY|NEEDS_CLARIFICATION",
  "intent": "",
  "context": {},
  "assumptions": [],
  "unknowns": [],
  "questions": [
    {
      "key": "",
      "question": ""
    }
  ]
}

Rules:
- Use only the requirement, clarification state, and relevant memory.
- Preserve the user's scope and supplied values.
- Do not invent product-specific behavior.
- Do not fill missing details using typical or standard behavior.
- Put relevant unavailable information in unknowns.
- Ask only when missing information materially blocks the requested QA work.
- Every question must have a stable semantic key representing its
  information need.
- Reuse an existing key for the same information need.
- Never ask a clarification key already present in the clarification state.
- If the available information is sufficient, return READY.

Return only the JSON object.
"""

    user_prompt = f"""
Analyze the following requirement.

Requirement:

{requirement}


PREVIOUS CLARIFICATION HISTORY:

{clarification_context if clarification_context else "None"}


RELEVANT MEMORY:

{memory_context}
"""

    return system_prompt, user_prompt