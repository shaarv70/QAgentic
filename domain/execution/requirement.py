from dataclasses import dataclass


@dataclass(frozen=True)
class TestRequirement:
    """
    Represents a test requirement supplied by the user.

    This is intentionally execution-agnostic.
    """

    description: str

    repository_path: str | None = None
    repository_url: str | None = None
    branch: str | None = None

    framework: str | None = None
    test_path: str | None = None