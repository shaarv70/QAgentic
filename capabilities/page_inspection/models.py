from dataclasses import dataclass, field


@dataclass
class PageInspectionResult:
    url: str
    title: str = ""
    dom_snapshot: str = ""
    screenshot_available: bool = False
    error: str | None = None

    def has_content(self) -> bool:
        return bool(self.dom_snapshot and not self.error)

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "dom_snapshot": self.dom_snapshot,
            "screenshot_available": self.screenshot_available,
            "page_inspection": True,
            "error": self.error,
        }
