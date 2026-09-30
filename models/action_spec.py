from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class ActionSpec:
    """
    Declarative contract for an executable QAgentic action.

    ActionSpec contains metadata used by planning/orchestration.
    It does not contain execution logic.
    """

    name: str
    kind: Literal["tool", "capability"]
    description: str = ""
    requires: tuple[str, ...] = field(default_factory=tuple)
    produces: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "description": self.description,
            "requires": list(self.requires),
            "produces": list(self.produces),
        }