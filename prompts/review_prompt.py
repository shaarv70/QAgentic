def build_review_prompt(content):

    return f"""
Review this artifact.{content}

Return ONLY JSON.

{{
    "status":"PASS",
    "feedback":""
}}

OR

{{
    "status":"FAIL",
    "feedback":"Missing Boundary Test Cases"
}}

"""