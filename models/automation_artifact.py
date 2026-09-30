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
    def from_llm_content(cls, content: Any) -> "AutomationArtifact":
        """
        Parse the structured artifact returned by an LLM.

        The LLM is instructed to return JSON only, but this parser also
        tolerates a fenced JSON response so provider/model formatting does
        not become an execution dependency.
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
                "Automation generator must return a JSON automation artifact "
                "with a 'files' array."
            ) from last_error

        return cls.from_dict(parsed)
