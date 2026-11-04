import json
import re

from agents.base_agent import BaseAgent
from constants.agent_names import AgentNames
from models.automation_artifact import AutomationArtifact, AutomationFile
from ai.models.llm_request import LLMRequest
from utils.logger import logger

# Token-budget limits for the fix-generation call.
# Keep total context well under 8k (input + max_output_tokens) so the call
# works on models with small context windows (e.g. openai/gpt-oss-120b on Groq).
_EXECUTION_OUTPUT_MAX_CHARS = 1_500   # last N chars of the failure log
_FILES_CONTEXT_MAX_CHARS    = 3_500   # total across all files sent to the LLM
_FILE_MAX_CHARS             = 2_000   # single file cap

# Build-descriptor filenames that are always useful for CONFIG / COMPILE fixes.
_BUILD_DESCRIPTORS = frozenset({
    "pom.xml", "package.json", "build.gradle", "build.gradle.kts",
    "requirements.txt", "Gemfile", "go.mod", "*.csproj",
})


class SelfHealingAgent(BaseAgent):
    """
    Universal self-healing agent for test pipeline failures.

    Replaces the single-shot SelfHealingService with a three-step
    reasoning loop that adapts its investigation strategy to the
    failure category:

    Step 1 — Diagnose  (fast JSON LLM call)
        Classifies the failure as one of:
        COMPILE | SELECTOR | ASSERTION | TIMEOUT | CONFIG | OTHER

    Step 2 — Investigate  (category-specific, no LLM)
        SELECTOR / TIMEOUT  → launch headless browser, capture live DOM
                               so the LLM gets real element attributes
                               instead of guessing from test code alone.
        COMPILE             → scan workspace for ALL files referenced in
                               the compiler error output and add them to
                               the artifact so no file is missing from context.
        ASSERTION           → parse expected vs actual values from the
                               failure output; surface them clearly so the
                               LLM can fix the assertion logic precisely.
        CONFIG              → collect all project config files (pom.xml,
                               testng.xml, *.properties, *.yaml) from the
                               workspace so the LLM has full dependency context.
        OTHER               → no extra investigation; proceed with what is known.

    Step 3 — Generate fix  (full LLM call with all gathered context)
        Receives: failure output + source files + diagnosis summary
                  + category-specific context (DOM / assertion detail /
                  config files / extra source files).
        Returns a corrected AutomationArtifact in the standard delimiter format.

    The agent responds to the same `.heal()` interface as SelfHealingService
    so it is a transparent drop-in replacement in TestExecutionCapability.
    """

    def __init__(self, ai_service, prompt_builder, dom_capture_service=None):
        super().__init__()
        self.ai_service = ai_service
        self.prompt_builder = prompt_builder
        self.dom_capture_service = dom_capture_service

    # ------------------------------------------------------------------
    # BaseAgent contract
    # ------------------------------------------------------------------

    def execute(self, state):
        return state

    # ------------------------------------------------------------------
    # Public heal() interface — drop-in for SelfHealingService.heal()
    # ------------------------------------------------------------------

    def heal(
        self,
        execution_output: str,
        automation_artifact: AutomationArtifact,
        requirement: str,
        task,
        workspace_path: str = "",
    ) -> AutomationArtifact:
        """
        Diagnose the failure, run category-specific investigation,
        then generate and return a patched AutomationArtifact.

        workspace_path is optional — when provided the agent can read
        additional source / config files from the cloned repository.
        """

        # ----------------------------------------------------------------
        # Step 1: Diagnose — classify and extract key metadata
        # ----------------------------------------------------------------
        diagnosis = self._diagnose(
            execution_output=execution_output,
            automation_artifact=automation_artifact,
            requirement=requirement,
        )

        category = diagnosis.get("category", "OTHER")
        logger.info(
            "SelfHealingAgent | category=%s | url=%s | file=%s | summary=%s",
            category,
            diagnosis.get("url_hint") or "(none)",
            diagnosis.get("failing_file") or "(none)",
            diagnosis.get("summary"),
        )

        # ----------------------------------------------------------------
        # Step 2: Category-specific investigation
        # ----------------------------------------------------------------
        extra_context: dict = {}

        if category in {"SELECTOR", "TIMEOUT"}:
            extra_context = self._investigate_selector(diagnosis)

        elif category == "COMPILE":
            extra_context = self._investigate_compile(
                execution_output, automation_artifact, workspace_path
            )
            # Merge any extra files into the artifact so _generate_fix sees them
            automation_artifact = self._merge_extra_files(
                automation_artifact,
                extra_context.pop("extra_files", []),
            )

        elif category == "ASSERTION":
            extra_context = self._investigate_assertion(execution_output)

        elif category == "CONFIG":
            extra_context = self._investigate_config(
                automation_artifact, workspace_path
            )
            automation_artifact = self._merge_extra_files(
                automation_artifact,
                extra_context.pop("extra_files", []),
            )

        # OTHER: no investigation needed — failure output + files are sufficient

        # ----------------------------------------------------------------
        # Step 3: Generate fix with all available context
        # ----------------------------------------------------------------
        return self._generate_fix(
            execution_output=execution_output,
            automation_artifact=automation_artifact,
            requirement=requirement,
            task=task,
            diagnosis=diagnosis,
            extra_context=extra_context,
        )

    # ------------------------------------------------------------------
    # Step 1 — Diagnose
    # ------------------------------------------------------------------

    def _diagnose(
        self,
        execution_output: str,
        automation_artifact: AutomationArtifact,
        requirement: str,
    ) -> dict:
        """
        Fast LLM call — classifies the failure and extracts key metadata.

        Returns:
            category     : COMPILE | SELECTOR | ASSERTION | TIMEOUT | CONFIG | OTHER
            url_hint     : URL the test navigates to, or ""
            failing_file : relative path of the primary source file, or ""
            summary      : one-sentence root cause
        """
        files_context = self._format_files_brief(automation_artifact)

        prompt = self.prompt_builder.self_healing_diagnosis(
            execution_output=execution_output,
            files_context=files_context,
            requirement=requirement,
        )

        response = self.ai_service.generate(
            AgentNames.SELF_HEALING_DIAGNOSIS,
            LLMRequest(
                system_prompt=prompt.system_prompt,
                user_prompt=prompt.user_prompt,
            ),
        )

        try:
            result = json.loads(response.content)
        except (json.JSONDecodeError, TypeError, AttributeError):
            result = {}

        return {
            "category":     result.get("category", "OTHER"),
            "url_hint":     result.get("url_hint", ""),
            "failing_file": result.get("failing_file", ""),
            "summary":      result.get("summary", ""),
        }

    # ------------------------------------------------------------------
    # Step 2 — Category-specific investigation
    # ------------------------------------------------------------------

    def _investigate_selector(self, diagnosis: dict) -> dict:
        """
        SELECTOR / TIMEOUT: launch headless browser → capture live DOM.
        """
        if self.dom_capture_service is None:
            logger.info("SelfHealingAgent | DOM capture skipped (service not wired)")
            return {}

        url_hint = (diagnosis.get("url_hint") or "").strip()
        if not url_hint:
            logger.info(
                "SelfHealingAgent | SELECTOR/TIMEOUT — no URL found in test code, "
                "skipping DOM capture"
            )
            return {}

        logger.info(
            "SelfHealingAgent | launching headless browser | url=%s", url_hint
        )
        dom = self.dom_capture_service.capture(url_hint)

        if dom:
            logger.info(
                "SelfHealingAgent | live DOM captured | chars=%d", len(dom)
            )
            return {"dom_context": dom}

        logger.warning(
            "SelfHealingAgent | DOM capture returned nothing "
            "(app may not be running) — proceeding without live DOM"
        )
        return {}

    def _investigate_compile(
        self,
        execution_output: str,
        automation_artifact: AutomationArtifact,
        workspace_path: str,
    ) -> dict:
        """
        COMPILE: find additional source files referenced in the compiler
        error output that are not yet in the artifact, and load them.

        Maven compiler errors name every file and line that failed — scanning
        those references ensures the LLM has ALL relevant files rather than
        just the subset extracted from the stack trace.
        """
        if not workspace_path:
            return {}

        from pathlib import Path

        workspace = Path(workspace_path).resolve()
        existing_paths = {f.path for f in automation_artifact.files}

        # Match any .java file mentioned anywhere in the error output
        referenced = re.findall(
            r"([\w$/]+\.java)",
            execution_output,
            re.IGNORECASE,
        )

        extra_files: list[AutomationFile] = []
        seen_names: set = set()

        for filename in referenced:
            if filename in seen_names:
                continue
            seen_names.add(filename)

            for java_file in (workspace / "src").rglob(filename):
                abs_path = java_file.resolve()
                try:
                    rel = str(abs_path.relative_to(workspace)).replace("\\", "/")
                except ValueError:
                    continue
                if rel in existing_paths:
                    continue
                existing_paths.add(rel)
                try:
                    extra_files.append(AutomationFile(
                        path=rel,
                        content=abs_path.read_text(encoding="utf-8", errors="replace"),
                    ))
                except OSError:
                    pass

        if extra_files:
            logger.info(
                "SelfHealingAgent | COMPILE — loaded %d additional source file(s)",
                len(extra_files),
            )

        return {"extra_files": extra_files}

    @staticmethod
    def _investigate_assertion(execution_output: str) -> dict:
        """
        ASSERTION: extract expected and actual values from the failure output
        and surface them as a structured string so the LLM can fix the
        assertion precisely.

        Handles TestNG, JUnit, and AssertJ patterns.
        """
        patterns = [
            # AssertJ / JUnit 5:  expected: <X> but was: <Y>
            r"expected:\s*[<\"]?(.+?)[>\"]?\s+but was:\s*[<\"]?(.+?)[>\"]?(?:\n|$)",
            # TestNG:  expected [X] but found [Y]
            r"expected\s*\[(.+?)\]\s*but found\s*\[(.+?)\]",
            # JUnit 4:  expected:<X> but was:<Y>
            r"expected:<(.+?)> but was:<(.+?)>",
            # AssertionError: X != Y
            r"AssertionError:\s*(.+?)\s*!=\s*(.+?)(?:\n|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, execution_output, re.IGNORECASE)
            if match:
                expected, actual = match.group(1).strip(), match.group(2).strip()
                detail = (
                    f"ASSERTION DETAIL:\n"
                    f"  expected : {expected}\n"
                    f"  actual   : {actual}\n"
                    f"  Fix the assertion or the code so the actual value matches "
                    f"the documented expected behaviour."
                )
                logger.info(
                    "SelfHealingAgent | ASSERTION — expected=%r | actual=%r",
                    expected[:80],
                    actual[:80],
                )
                return {"assertion_detail": detail}

        return {}

    def _investigate_config(
        self,
        automation_artifact: AutomationArtifact,
        workspace_path: str,
    ) -> dict:
        """
        CONFIG: collect project configuration files (testng.xml, *.properties,
        *.yaml, *.yml) so the LLM has complete dependency and runner context.

        Skips test-output / build directories and caps file size + total
        context to stay within model token limits.
        """
        if not workspace_path:
            return {}

        from pathlib import Path

        workspace = Path(workspace_path).resolve()
        existing_paths = {f.path for f in automation_artifact.files}

        _SKIP_DIRS = {
            "target", ".git", "node_modules",
            # Test result / report directories — not project config
            "test-output", "test-results", "surefire-reports",
            "build", "out", "dist", ".gradle", "reports", "html-report",
        }
        _MAX_FILE_CHARS = 6_000   # single file cap — skip oversized result XML
        _MAX_TOTAL_CHARS = 20_000  # total cap across all config files

        config_globs = ["testng*.xml", "*.properties", "*.yaml", "*.yml"]

        extra_files: list[AutomationFile] = []
        total_chars = 0

        for pattern in config_globs:
            for cfg_file in workspace.rglob(pattern):
                if total_chars >= _MAX_TOTAL_CHARS:
                    break
                parts = cfg_file.parts
                if any(p in _SKIP_DIRS for p in parts):
                    continue
                try:
                    rel = str(cfg_file.resolve().relative_to(workspace)).replace("\\", "/")
                except ValueError:
                    continue
                if rel in existing_paths:
                    continue
                existing_paths.add(rel)
                try:
                    content = cfg_file.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if len(content) > _MAX_FILE_CHARS:
                    logger.debug(
                        "SelfHealingAgent | CONFIG — skipping large file %s (%d chars)",
                        rel, len(content),
                    )
                    continue
                extra_files.append(AutomationFile(path=rel, content=content))
                total_chars += len(content)

        if extra_files:
            logger.info(
                "SelfHealingAgent | CONFIG — loaded %d additional config file(s): %s",
                len(extra_files),
                [f.path for f in extra_files],
            )

        return {"extra_files": extra_files}

    # ------------------------------------------------------------------
    # Step 3 — Generate fix
    # ------------------------------------------------------------------

    def _generate_fix(
        self,
        execution_output: str,
        automation_artifact: AutomationArtifact,
        requirement: str,
        task,
        diagnosis: dict,
        extra_context: dict,
    ) -> AutomationArtifact:
        """
        Fix-generation LLM call with trimmed context.

        Keeps only the files most relevant to the failure (failing file +
        build descriptor) and caps execution_output to reduce token usage
        so the call fits within small model context windows (e.g. 8k).

        The LLM is instructed to return ONLY changed files; we merge the
        result back with the original artifact so unchanged files survive.
        """
        failing_file = diagnosis.get("failing_file") or ""
        files_context = self._format_files_for_healing(
            automation_artifact, failing_file
        )

        # Cap execution output — errors are always at the tail.
        trimmed_output = execution_output[-_EXECUTION_OUTPUT_MAX_CHARS:]
        if len(trimmed_output) < len(execution_output):
            trimmed_output = "...(truncated)...\n" + trimmed_output

        investigation_parts = []
        if extra_context.get("dom_context"):
            investigation_parts.append(extra_context["dom_context"])
        if extra_context.get("assertion_detail"):
            investigation_parts.append(extra_context["assertion_detail"])
        dom_context = "\n\n".join(investigation_parts)

        prompt = self.prompt_builder.self_healing(
            execution_output=trimmed_output,
            automation_files_context=files_context,
            requirement=requirement,
            task=task,
            dom_context=dom_context,
            diagnosis=diagnosis,
        )

        response = self.ai_service.generate(
            AgentNames.SELF_HEALING_AGENT,
            LLMRequest(
                system_prompt=prompt.system_prompt,
                user_prompt=prompt.user_prompt,
            ),
        )

        # LLM returns only the changed files — merge back with the original
        # so that unchanged files are preserved in the returned artifact.
        healed = AutomationArtifact.from_llm_content(response.content)
        return self._merge_healed(automation_artifact, healed)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_extra_files(
        artifact: AutomationArtifact,
        extra_files: list,
    ) -> AutomationArtifact:
        """Return a new artifact with extra_files appended."""
        if not extra_files:
            return artifact
        return AutomationArtifact(files=tuple(list(artifact.files) + extra_files))

    @staticmethod
    def _merge_healed(
        original: AutomationArtifact,
        healed: AutomationArtifact,
    ) -> AutomationArtifact:
        """
        Overlay healed files on top of the original artifact.
        Files present in healed replace their counterparts in original;
        files NOT in healed are carried through unchanged.
        """
        if not healed.files:
            return original
        healed_paths = {f.path for f in healed.files}
        kept = [f for f in original.files if f.path not in healed_paths]
        return AutomationArtifact(files=tuple(kept + list(healed.files)))

    @staticmethod
    def _format_files_for_healing(
        artifact: AutomationArtifact,
        failing_file: str,
    ) -> str:
        """
        Build a compact files context for the fix-generation call.

        Priority order:
          1. The failing file (most important — always included if present)
          2. Build descriptor (pom.xml / package.json / etc.)
          3. Remaining files up to the token budget

        Each file is capped at _FILE_MAX_CHARS; total is capped at
        _FILES_CONTEXT_MAX_CHARS so the call fits within small context windows.
        """
        import os

        def _is_build_descriptor(path: str) -> bool:
            name = os.path.basename(path).lower()
            return name in _BUILD_DESCRIPTORS

        def _truncate(content: str) -> str:
            if len(content) <= _FILE_MAX_CHARS:
                return content
            return content[:_FILE_MAX_CHARS] + "\n...(truncated)"

        def _block(f: AutomationFile) -> str:
            return (
                f"--- BEGIN_FILE: {f.path} ---\n"
                f"{_truncate(f.content)}\n"
                f"--- END_FILE ---"
            )

        # Sort: failing file first, build descriptors second, rest last.
        failing_lower = failing_file.lower()

        def _priority(f: AutomationFile) -> int:
            if failing_lower and f.path.lower().endswith(failing_lower):
                return 0
            if _is_build_descriptor(f.path):
                return 1
            return 2

        sorted_files = sorted(artifact.files, key=_priority)

        parts: list[str] = []
        total = 0
        for f in sorted_files:
            block = _block(f)
            if total + len(block) > _FILES_CONTEXT_MAX_CHARS and parts:
                break
            parts.append(block)
            total += len(block)

        return "\n\n".join(parts)

    @staticmethod
    def _format_files(artifact: AutomationArtifact) -> str:
        parts = []
        for f in artifact.files:
            parts.append(
                f"--- BEGIN_FILE: {f.path} ---\n{f.content}\n--- END_FILE ---"
            )
        return "\n\n".join(parts)

    @staticmethod
    def _format_files_brief(artifact: AutomationArtifact) -> str:
        """Compact format for the cheap diagnosis call — filename + first 15 lines."""
        parts = []
        for f in artifact.files:
            lines = f.content.split("\n")[:15]
            parts.append(f"[{f.path}]\n" + "\n".join(lines) + "\n...")
        return "\n\n".join(parts)
