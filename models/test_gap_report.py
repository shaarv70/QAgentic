from dataclasses import dataclass, field


@dataclass
class TestGap:
    area: str
    severity: str          # "high" | "medium" | "low"
    description: str
    suggested_test_title: str


@dataclass
class TestGapReport:
    framework: str
    test_file_count: int
    tested_scenarios: list[str]
    gaps: list[TestGap]
    coverage_estimate: float       # 0.0 – 1.0
    summary: str
    workspace_path: str = ""
    metadata: dict = field(default_factory=dict)
