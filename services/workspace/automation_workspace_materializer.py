from __future__ import annotations

from pathlib import Path
from typing import Any

from domain.workspace.workspace_artifact import WorkspaceArtifact
from models.automation_artifact import AutomationArtifact



class AutomationWorkspaceMaterializer:
    """Materializes a generated AutomationArtifact into an execution workspace."""

    def materialize(
        self,
        artifact: AutomationArtifact,
        workspace_path: str | Path,
    ) -> WorkspaceArtifact:
        if not isinstance(artifact, AutomationArtifact):
            raise TypeError(
                "artifact must be an AutomationArtifact."
            )

        root = Path(workspace_path).resolve()
        root.mkdir(parents=True, exist_ok=True)

        for automation_file in artifact.files:
            relative_path = Path(automation_file.path)

            if relative_path.is_absolute():
                raise ValueError(
                    f"Automation artifact path must be relative: "
                    f"{automation_file.path}"
                )

            if ".." in relative_path.parts:
                raise ValueError(
                    f"Automation artifact path cannot contain '..': "
                    f"{automation_file.path}"
                )

            target = (root / relative_path).resolve()

            try:
                target.relative_to(root)
            except ValueError as exc:
                raise ValueError(
                    f"Automation artifact path escapes workspace: "
                    f"{automation_file.path}"
                ) from exc

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                automation_file.content,
                encoding="utf-8",
            )

        metadata: dict[str, Any] = dict(artifact.metadata or {})

        repository = metadata.get("repository")
        if not isinstance(repository, dict):
            repository = None

        return WorkspaceArtifact(
            path=str(root),
            repository=repository,
        )
