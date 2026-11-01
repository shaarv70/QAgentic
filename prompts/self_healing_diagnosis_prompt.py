def build_self_healing_diagnosis_prompt(
    execution_output: str,
    files_context: str,
    requirement_context: str,
) -> tuple[str, str]:
    system_prompt = """
You are a test-failure triage expert.

Analyse the failure output and the test source files provided, then return a
JSON object with exactly these fields:

{
  "category": "<COMPILE|SELECTOR|ASSERTION|TIMEOUT|CONFIG|OTHER>",
  "url_hint": "<the URL the failing test navigates to, or empty string if unknown>",
  "failing_file": "<relative path of the primary source file that caused the failure, or empty string>",
  "summary": "<one sentence: what went wrong>"
}

Category definitions:
  COMPILE   — Java/TypeScript compilation error (missing import, undefined symbol, wrong type).
  SELECTOR  — Element not found at runtime: NoSuchElementException, StaleElementReferenceException,
              selector/locator mismatch, XPath/CSS not matching any element.
  ASSERTION — Test assertion failed: expected vs actual value mismatch.
  TIMEOUT   — ElementNotInteractableException, TimeoutException, page load timeout.
  CONFIG    — Missing dependency in pom.xml/package.json, wrong run command, missing env var.
  OTHER     — Anything else.

For url_hint: scan the source files for driver.get("..."), navigate().to("..."),
baseUrl fields, or @Value("${app.url}") patterns and extract the URL.
Return empty string if no URL is found.

Return ONLY the JSON object. No explanation, no markdown.
""".strip()

    user_prompt = f"""
FAILURE OUTPUT:
{execution_output[:3000]}

SOURCE FILES (excerpt):
{files_context}

REQUIREMENT:
{requirement_context}
""".strip()

    return system_prompt, user_prompt
