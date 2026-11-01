def build_test_gap_analysis_prompt(
    workspace_path: str,
    framework: str,
    test_files_evidence: list[dict],   # [{"path": ..., "content": ...}]
    source_files_evidence: list[dict], # [{"path": ..., "content": ...}]
    memory_context: str = "",
) -> tuple[str, str]:

    system_prompt = (
        "You are a senior QA analyst specialised in test coverage analysis.\n"
        "Your task is to examine the provided test files and source code, "
        "then produce a structured gap report identifying what is tested and what is missing.\n\n"
        "Return ONLY a JSON object matching this schema:\n"
        "{\n"
        '  "framework": "<detected test framework>",\n'
        '  "tested_scenarios": ["<short scenario description>", ...],\n'
        '  "gaps": [\n'
        '    {\n'
        '      "area": "<functional area>",\n'
        '      "severity": "high|medium|low",\n'
        '      "description": "<why this gap matters>",\n'
        '      "suggested_test_title": "<short name for the missing test>"\n'
        '    }\n'
        '  ],\n'
        '  "coverage_estimate": <0.0-1.0>,\n'
        '  "summary": "<one paragraph narrative>"\n'
        "}\n\n"
        "Severity guide:\n"
        "  high   — core user journey or data-integrity path is untested\n"
        "  medium — important but non-critical path is untested\n"
        "  low    — edge case or cosmetic scenario is untested\n\n"
        "Be precise. List only real gaps you can infer from the evidence."
    )

    sections: list[str] = []

    sections.append(f"Workspace: {workspace_path}")
    sections.append(f"Framework: {framework or 'unknown'}")
    sections.append(f"Test files analysed: {len(test_files_evidence)}")

    if memory_context:
        sections.append(f"\n--- Prior context ---\n{memory_context}")

    if test_files_evidence:
        sections.append("\n--- Test files ---")
        for item in test_files_evidence:
            sections.append(f"\n[file: {item['path']}]\n{item['content']}")
    else:
        sections.append("\n(No test files found — all scenarios are untested.)")

    if source_files_evidence:
        sections.append("\n--- Source / feature files ---")
        for item in source_files_evidence:
            sections.append(f"\n[file: {item['path']}]\n{item['content']}")

    sections.append(
        "\n\nAnalyse the above and return the JSON gap report."
    )

    user_prompt = "\n".join(sections)

    return system_prompt, user_prompt
