def build_self_healing_prompt(
    execution_output: str,
    automation_files_context: str,
    requirement_context: str,
    task_context: str,
    memory_context: str,
    dom_context: str = "",
    diagnosis: dict | None = None,
) -> tuple[str, str]:
    system_prompt = """
You are a Senior Automation Test Engineer specialising in self-healing test suites.

Your job is to analyse a test execution failure and produce a corrected version
of the automation project that resolves the root cause.

Error taxonomy — identify which category applies:
  COMPILE   : Java / TypeScript compilation error (missing import, wrong type, undefined symbol).
  SELECTOR  : Element not found, NoSuchElementException, selector mismatch.
  ASSERTION : AssertionError, expected/actual value mismatch, wrong condition.
  TIMEOUT   : ElementNotInteractableException, TimeoutException, page load timeout.
  CONFIG    : Missing dependency in pom.xml / package.json, wrong run command.
  OTHER     : Any other failure.

Fix rules:
- Read the FAILURE OUTPUT carefully. Trace the error to the exact file and line.
- Fix only the code that caused the failure. Do not rewrite unrelated files.
- Preserve the intent of the original test — do not change what is being tested.
- For SELECTOR errors: inspect the requirement context for UI hints, choose a
  stable locator strategy (ID > name > CSS > XPath).
- For COMPILE errors: fix the import, type, or syntax. Do not change test logic.
- For ASSERTION errors: re-read the requirement; adjust the assertion to match the
  documented expected behaviour, not the broken actual output.
- For CONFIG errors: fix pom.xml / package.json / run_command only.
- Always return a complete, runnable project. Preserve every file that does not
  need changing.

OUTPUT FORMAT — identical to the original automation format:

--- BEGIN_FILE: relative/path/to/file ---
[complete file content, exactly as it should appear on disk]
--- END_FILE ---

Repeat for every file in the project (changed AND unchanged).

After all files:

--- BEGIN_METADATA ---
framework: <framework name>
language: <language>
build_tool: <build tool>
run_command: <exact command to compile and run the tests>
heal_summary: <one sentence: what root cause was identified and what was fixed>
--- END_METADATA ---
""".strip()

    diagnosis_block = ""
    if diagnosis:
        diagnosis_block = (
            f"\nDIAGNOSIS (pre-computed):\n"
            f"  category : {diagnosis.get('category', 'UNKNOWN')}\n"
            f"  summary  : {diagnosis.get('summary', '')}\n"
            f"  file     : {diagnosis.get('failing_file', '')}\n"
        )

    dom_block = (
        f"\nLIVE DOM (captured from the running application):\n{dom_context}\n"
        if dom_context
        else ""
    )

    user_prompt = f"""
REQUIREMENT:
{requirement_context}

TASK CONTEXT:
{task_context}
{diagnosis_block}
FAILURE OUTPUT:
{execution_output}
{dom_block}
CURRENT AUTOMATION CODE:
{automation_files_context}

{f"RELEVANT MEMORY:{chr(10)}{memory_context}" if memory_context else ""}

INSTRUCTIONS:
1. Identify the root cause category (COMPILE / SELECTOR / ASSERTION / TIMEOUT / CONFIG / OTHER).
2. Trace the error to the exact file and line number.
3. Apply the minimal fix that resolves the root cause.
   - If LIVE DOM is provided: use element ids/names/classes from the DOM to write the correct locator.
4. Return the complete project — every file — in the delimiter format shown above.
""".strip()

    return system_prompt, user_prompt
