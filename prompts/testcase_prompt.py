
def build_testcase_prompt(application_type,prompt):
    
    final_prompt = f"""
    Generate comprehensive software test cases.

    Application Type: {application_type}
    
    Requirement:{prompt}

    Include:

    1. Positive Test Cases

    2. Negative Test Cases

    3. Boundary Test Cases

    4. Validation Test Cases

    Return the answer in a clean table.
    """ 
    return final_prompt 