from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AutomationFile:
    """One generated source/configuration file."""

    path: str
    content: str

    def __post_init__(self) -> None:
        path = self.path.strip()
        if not path:
            raise ValueError("Automation file path cannot be empty.")

        normalized = path.replace("\\", "/").lstrip("/")
        if normalized in {".", ".."} or any(
            part == ".." for part in normalized.split("/")
        ):
            raise ValueError(
                f"Automation file path must stay inside the workspace: {self.path!r}"
            )

        if not isinstance(self.content, str):
            raise TypeError(
                f"Automation file content must be a string: {self.path!r}"
            )

        object.__setattr__(self, "path", normalized)


@dataclass(frozen=True, slots=True)
class AutomationArtifact:
    """
    Structured automation project produced by the Automation Agent.

    The artifact is deliberately framework-agnostic. A generated project
    can contain Java, TypeScript, Python, configuration, build files, etc.
    """

    files: tuple[AutomationFile, ...]
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.files:
            raise ValueError("Automation artifact must contain at least one file.")

        paths = [item.path for item in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("Automation artifact contains duplicate file paths.")

        object.__setattr__(
            self,
            "metadata",
            dict(self.metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "files": [
                {
                    "path": item.path,
                    "content": item.content,
                }
                for item in self.files
            ],
            "metadata": dict(self.metadata or {}),
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            indent=2,
        )

    @classmethod
    def from_dict(cls, value: Any) -> "AutomationArtifact":
        if not isinstance(value, dict):
            raise ValueError("Automation artifact must be a JSON object.")

        raw_files = value.get("files")
        if not isinstance(raw_files, list):
            raise ValueError(
                "Automation artifact must contain a 'files' array."
            )

        files: list[AutomationFile] = []

        for index, raw_file in enumerate(raw_files):
            if not isinstance(raw_file, dict):
                raise ValueError(
                    f"Automation file at index {index} must be an object."
                )

            path = raw_file.get("path")
            content = raw_file.get("content")

            if not isinstance(path, str):
                raise ValueError(
                    f"Automation file at index {index} is missing a string 'path'."
                )

            if not isinstance(content, str):
                raise ValueError(
                    f"Automation file at {path!r} is missing string 'content'."
                )

            files.append(
                AutomationFile(
                    path=path,
                    content=content,
                )
            )

        metadata = value.get("metadata", {})
        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise ValueError("'metadata' must be an object when provided.")

        return cls(
            files=tuple(files),
            metadata=metadata,
        )

    @classmethod
    def from_delimiter_content(cls, content: str) -> "AutomationArtifact":
        """
        Parse the delimiter-based format produced by the automation prompt.

        Expected format:
            --- BEGIN_FILE: relative/path/to/file ---
            [file content]
            --- END_FILE ---

            --- BEGIN_METADATA ---
            framework: ...
            language: ...
            --- END_METADATA ---

        The BEGIN_FILE / END_FILE delimiters are matched case-insensitively
        and tolerate minor spacing variations in the dashes.
        """
        file_pattern = re.compile(
            r"-{2,}\s*BEGIN_FILE\s*:\s*(.+?)\s*-{2,}\n"
            r"(.*?)"
            r"-{2,}\s*END_FILE\s*-{2,}",
            re.DOTALL | re.IGNORECASE,
        )

        files: list[AutomationFile] = []
        for match in file_pattern.finditer(content):
            path = match.group(1).strip().strip("`")
            # Skip spurious matches: delimiter syntax or markdown table content
            # leaking into the captured path (e.g. `--- END_FILE ---`) | ✅ |)
            if not path or "---" in path or "|" in path or "\n" in path:
                continue
            file_content = match.group(2)
            if file_content.startswith("\n"):
                file_content = file_content[1:]
            file_content = file_content.rstrip()
            files.append(AutomationFile(path=path, content=file_content))

        if not files:
            raise ValueError(
                "No BEGIN_FILE / END_FILE blocks found in delimiter format."
            )

        meta_pattern = re.compile(
            r"-{2,}\s*BEGIN_METADATA\s*-{2,}\n"
            r"(.*?)"
            r"-{2,}\s*END_METADATA\s*-{2,}",
            re.DOTALL | re.IGNORECASE,
        )
        metadata: dict[str, Any] = {}
        meta_match = meta_pattern.search(content)
        if meta_match:
            meta_text = meta_match.group(1).strip()
            try:
                parsed_meta = json.loads(meta_text)
                if isinstance(parsed_meta, dict):
                    metadata = parsed_meta
            except (json.JSONDecodeError, ValueError):
                for line in meta_text.splitlines():
                    line = line.strip()
                    if ":" in line and not line.startswith("-"):
                        key, _, val = line.partition(":")
                        metadata[key.strip()] = val.strip()

        return cls(files=tuple(files), metadata=metadata)

    @classmethod
    def from_llm_content(cls, content: Any) -> "AutomationArtifact":
        """
        Parse the structured artifact returned by an LLM.

        Parsing order:
        1. Delimiter format  (--- BEGIN_FILE: path --- ... --- END_FILE ---)
        2. Raw JSON / fenced JSON  ({"files": [...]})

        The delimiter format is tried first because it is the primary output
        format requested by the automation prompt and is immune to
        JSON-escaping failures in large Java/TypeScript source files.
        """
        if isinstance(content, cls):
            return content

        if not isinstance(content, str):
            raise ValueError(
                "Automation generator returned unsupported content type."
            )

        text = content.strip()
        if not text:
            raise ValueError("Automation generator returned empty content.")

        try:
            return cls.from_delimiter_content(text)
        except ValueError:
            pass

        candidates = [text]

        fenced = re.findall(
            r"```(?:json|JSON)?\s*(.*?)```",
            text,
            flags=re.DOTALL,
        )
        candidates.extend(item.strip() for item in fenced if item.strip())

        parsed: Any = None
        last_error: Exception | None = None

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
                break
            except (TypeError, json.JSONDecodeError) as exc:
                last_error = exc

        if parsed is None:
            raise ValueError(
                "Automation generator must return either the delimiter format "
                "(--- BEGIN_FILE: path --- ... --- END_FILE ---) "
                "or a JSON automation artifact with a 'files' array."
            ) from last_error

        return cls.from_dict(parsed)
