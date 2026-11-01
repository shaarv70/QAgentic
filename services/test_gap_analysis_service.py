import os
from pathlib import Path
from typing import Any

from ai.builders.prompt_builder import PromptBuilder
from ai.models.llm_request import LLMRequest
from ai.services.ai_service import AIService
from constants.agent_names import AgentNames
from models.test_gap_report import TestGap, TestGapReport
from utils.logger import logger


class TestGapAnalysisService:
    """
    Reads test file contents from a workspace and asks the LLM to
    identify coverage gaps relative to the source / feature code.

    Unlike RepositoryAnalysisService (which reads only paths for
    structure discovery), this service reads the FULL content of
    test files so the LLM can understand what scenarios already exist.
    """

    MAX_TEST_FILE_CHARS = 3_000
    MAX_SOURCE_FILE_CHARS = 2_000
    MAX_TOTAL_TEST_CHARS = 20_000
    MAX_TOTAL_SOURCE_CHARS = 8_000
    MAX_SOURCE_FILES = 10

    # Source file extensions worth reading for feature hints.
    SOURCE_EXTENSIONS = {
        ".ts", ".js", ".tsx", ".jsx",
        ".py", ".java", ".cs", ".go", ".rb",
    }

    # Directories that contain application source (not tests/config/build).
    SOURCE_DIRS = {
        "src", "app", "lib", "pages", "components",
        "controllers", "services", "models", "api",
        "features",
    }

    IGNORED_DIRS = {
        ".git", "node_modules", "target", "build", "dist",
        "__pycache__", ".gradle", "test-results", "playwright-report",
        "allure-results", "coverage", ".nyc_output", "out", "bin",
        ".cache", ".npm",
    }

    def __init__(self, ai_service: AIService, prompt_builder: PromptBuilder) -> None:
        self.ai_service = ai_service
        self.prompt_builder = prompt_builder

    def analyze(
        self,
        workspace_path: str,
        profile: Any,               # RepositoryExecutionProfile
    ) -> TestGapReport:
        workspace = Path(workspace_path).resolve()
        framework = self._resolve_framework(profile)

        test_files_evidence = self._collect_test_evidence(workspace, profile)
        source_files_evidence = self._collect_source_evidence(workspace, profile)

        logger.info(
            "Test gap analysis evidence | workspace=%s | "
            "test_files=%d | source_files=%d",
            workspace,
            len(test_files_evidence),
            len(source_files_evidence),
        )

        prompt = self.prompt_builder.test_gap_analysis(
            workspace_path=str(workspace),
            framework=framework,
            test_files_evidence=test_files_evidence,
            source_files_evidence=source_files_evidence,
        )

        request = LLMRequest(
            system_prompt=prompt.system_prompt,
            user_prompt=prompt.user_prompt,
        )

        response = self.ai_service.generate_json(
            AgentNames.TEST_GAP_ANALYSIS,
            request,
        )

        return self._build_report(
            response=response,
            workspace_path=str(workspace),
            test_file_count=len(test_files_evidence),
            framework=framework,
        )

    # ------------------------------------------------------------------
    # Evidence collection
    # ------------------------------------------------------------------

    def _collect_test_evidence(self, workspace: Path, profile: Any) -> list[dict]:
        """Read actual test file contents from suite_candidates or test_locations."""
        evidence: list[dict] = []
        total_chars = 0
        seen: set[str] = set()

        # Prefer explicit suite candidates (have exact file paths).
        candidates = getattr(profile, "suite_candidates", []) or []
        test_paths: list[Path] = []

        for candidate in candidates:
            source = getattr(candidate, "source", None) or getattr(candidate, "selector", None)
            if isinstance(source, str) and source.strip():
                p = workspace / source.replace("\\", "/")
                if p.is_file():
                    test_paths.append(p)

        # Fall back to scanning test_locations directories.
        if not test_paths:
            for loc in getattr(profile, "test_locations", []) or []:
                loc_path = workspace / loc.replace("\\", "/")
                if loc_path.is_dir():
                    for p in sorted(loc_path.rglob("*")):
                        if p.is_file() and self._is_test_file(p.name):
                            test_paths.append(p)

        for path in test_paths:
            key = str(path).lower()
            if key in seen:
                continue
            seen.add(key)

            if total_chars >= self.MAX_TOTAL_TEST_CHARS:
                break

            content = self._read(path, self.MAX_TEST_FILE_CHARS)
            if content is None:
                continue

            rel = str(path.relative_to(workspace)).replace("\\", "/")
            evidence.append({"path": rel, "content": content})
            total_chars += len(content)

        return evidence

    def _collect_source_evidence(self, workspace: Path, profile: Any) -> list[dict]:
        """Read a sample of source / feature files for context."""
        evidence: list[dict] = []
        total_chars = 0
        seen: set[str] = set()

        for dirpath, dirnames, filenames in os.walk(workspace, followlinks=False):
            dirnames[:] = [
                d for d in dirnames
                if d.lower() not in self.IGNORED_DIRS
            ]
            dir_rel = Path(dirpath).relative_to(workspace)
            parts_lower = {p.lower() for p in dir_rel.parts}

            # Only enter source-like directories.
            if dir_rel.parts and not parts_lower & self.SOURCE_DIRS:
                continue

            for filename in sorted(filenames):
                if total_chars >= self.MAX_TOTAL_SOURCE_CHARS:
                    break
                if len(evidence) >= self.MAX_SOURCE_FILES:
                    break

                path = Path(dirpath) / filename
                if path.suffix.lower() not in self.SOURCE_EXTENSIONS:
                    continue
                if self._is_test_file(filename):
                    continue

                key = str(path).lower()
                if key in seen:
                    continue
                seen.add(key)

                content = self._read(path, self.MAX_SOURCE_FILE_CHARS)
                if content is None:
                    continue

                rel = str(path.relative_to(workspace)).replace("\\", "/")
                evidence.append({"path": rel, "content": content})
                total_chars += len(content)

            if total_chars >= self.MAX_TOTAL_SOURCE_CHARS:
                break
            if len(evidence) >= self.MAX_SOURCE_FILES:
                break

        return evidence

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_framework(profile: Any) -> str:
        frameworks = getattr(profile, "frameworks", []) or []
        if frameworks:
            return frameworks[0]
        runner = getattr(profile, "selected_runner", None) or ""
        return runner or "unknown"

    @staticmethod
    def _is_test_file(filename: str) -> bool:
        lower = filename.lower()
        return any(lower.endswith(s) for s in (
            ".spec.ts", ".spec.js", ".spec.mjs", ".spec.cjs",
            ".test.ts", ".test.js", ".test.mjs",
            "_test.py", "test_.py",
            ".feature",
        ))

    @staticmethod
    def _read(path: Path, max_chars: int) -> str | None:
        try:
            if path.stat().st_size > 500_000:
                return None
            text = path.read_text(encoding="utf-8", errors="replace")
            if len(text) > max_chars:
                text = text[:max_chars] + "\n...[truncated]"
            return text
        except OSError:
            return None

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _build_report(
        self,
        response: dict,
        workspace_path: str,
        test_file_count: int,
        framework: str,
    ) -> TestGapReport:
        if not isinstance(response, dict):
            response = {}

        gaps: list[TestGap] = []
        for raw in response.get("gaps", []) or []:
            if not isinstance(raw, dict):
                continue
            gaps.append(TestGap(
                area=str(raw.get("area", "Unknown")),
                severity=str(raw.get("severity", "medium")).lower(),
                description=str(raw.get("description", "")),
                suggested_test_title=str(raw.get("suggested_test_title", "")),
            ))

        tested = [
            str(s) for s in (response.get("tested_scenarios") or [])
            if isinstance(s, str)
        ]

        try:
            coverage = float(response.get("coverage_estimate", 0.0))
            coverage = max(0.0, min(1.0, coverage))
        except (TypeError, ValueError):
            coverage = 0.0

        return TestGapReport(
            framework=str(response.get("framework", framework)),
            test_file_count=test_file_count,
            tested_scenarios=tested,
            gaps=gaps,
            coverage_estimate=coverage,
            summary=str(response.get("summary", "")),
            workspace_path=workspace_path,
        )
