import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from utils.logger import logger


_META_FILENAME = ".qagentic-meta.json"


class WorkspaceRetentionService:
    """
    Prunes stale workspaces from the .qagentic/workspaces directory.

    Called once at application startup before any new workspace is allocated.

    Three configurable rules (all via env vars, see config.py):
      - TTL:        delete workspaces older than WORKSPACE_TTL_DAYS days
                    (0 = disabled)
      - Count cap:  keep only the WORKSPACE_MAX_COUNT most recent workspaces
                    (0 = disabled)
      - Size cap:   prune oldest workspaces when total size exceeds
                    WORKSPACE_MAX_SIZE_MB megabytes (0 = disabled)

    When multiple rules apply to the same workspace, it is only deleted once.
    Workspaces without a .qagentic-meta.json fall back to directory mtime.
    """

    def __init__(
        self,
        ttl_days: int,
        max_count: int,
        max_size_mb: int,
        base_directory: str = ".qagentic/workspaces",
    ) -> None:
        self.ttl_days = ttl_days
        self.max_count = max_count
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.base_directory = Path(base_directory)

    def prune(self) -> None:
        if not self.base_directory.exists():
            return

        workspaces = self._discover_workspaces()

        if not workspaces:
            return

        to_delete: set[Path] = set()

        # --------------------------------------------------
        # Rule 1: TTL
        # --------------------------------------------------
        if self.ttl_days > 0:
            cutoff = (
                datetime.now(timezone.utc).timestamp()
                - self.ttl_days * 86_400
            )
            for ws in workspaces:
                if ws["created_at"] < cutoff:
                    to_delete.add(ws["path"])
                    logger.info(
                        "Workspace queued for TTL pruning | "
                        "workspace=%s | repo=%s | age_days=%.1f",
                        ws["path"].name,
                        ws["repo_url"] or "unknown",
                        (
                            datetime.now(timezone.utc).timestamp()
                            - ws["created_at"]
                        ) / 86_400,
                    )

        # --------------------------------------------------
        # Rule 2: Max count
        # --------------------------------------------------
        if self.max_count > 0:
            surviving = [
                ws for ws in workspaces
                if ws["path"] not in to_delete
            ]
            if len(surviving) > self.max_count:
                oldest_first = sorted(
                    surviving,
                    key=lambda w: w["created_at"],
                )
                overflow = oldest_first[: len(surviving) - self.max_count]
                for ws in overflow:
                    to_delete.add(ws["path"])
                    logger.info(
                        "Workspace queued for count pruning | "
                        "workspace=%s | repo=%s",
                        ws["path"].name,
                        ws["repo_url"] or "unknown",
                    )

        # --------------------------------------------------
        # Rule 3: Size cap
        # --------------------------------------------------
        if self.max_size_bytes > 0:
            surviving = [
                ws for ws in workspaces
                if ws["path"] not in to_delete
            ]
            total_bytes = sum(ws["size_bytes"] for ws in surviving)
            if total_bytes > self.max_size_bytes:
                oldest_first = sorted(
                    surviving,
                    key=lambda w: w["created_at"],
                )
                for ws in oldest_first:
                    if total_bytes <= self.max_size_bytes:
                        break
                    to_delete.add(ws["path"])
                    total_bytes -= ws["size_bytes"]
                    logger.info(
                        "Workspace queued for size pruning | "
                        "workspace=%s | repo=%s | size_mb=%.1f",
                        ws["path"].name,
                        ws["repo_url"] or "unknown",
                        ws["size_bytes"] / (1024 * 1024),
                    )

        for path in to_delete:
            self._delete(path)

        if to_delete:
            logger.info(
                "Workspace pruning complete | deleted=%d | remaining=%d",
                len(to_delete),
                len(workspaces) - len(to_delete),
            )

    # --------------------------------------------------
    # Internal helpers
    # --------------------------------------------------

    def _discover_workspaces(self) -> list[dict]:
        workspaces = []

        try:
            entries = list(self.base_directory.iterdir())
        except OSError:
            return workspaces

        for entry in entries:
            if not entry.is_dir():
                continue

            meta = self._read_meta(entry)
            size = self._directory_size(entry)

            try:
                fallback_mtime = entry.stat().st_mtime
            except OSError:
                fallback_mtime = 0.0

            workspaces.append(
                {
                    "path": entry,
                    "repo_url": meta.get("repo_url"),
                    "created_at": meta.get("created_at") or fallback_mtime,
                    "size_bytes": size,
                }
            )

        return workspaces

    @staticmethod
    def _read_meta(workspace_path: Path) -> dict:
        meta_file = workspace_path / _META_FILENAME

        if not meta_file.exists():
            return {}

        try:
            data = json.loads(
                meta_file.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError):
            return {}

        if not isinstance(data, dict):
            return {}

        raw_ts = data.get("created_at")

        if isinstance(raw_ts, str):
            try:
                data["created_at"] = (
                    datetime.fromisoformat(raw_ts).timestamp()
                )
            except ValueError:
                data.pop("created_at", None)

        return data

    @staticmethod
    def _directory_size(path: Path) -> int:
        total = 0
        try:
            for f in path.rglob("*"):
                if f.is_file():
                    try:
                        total += f.stat().st_size
                    except OSError:
                        pass
        except OSError:
            pass
        return total

    @staticmethod
    def _delete(path: Path) -> None:
        try:
            shutil.rmtree(path)
            logger.info(
                "Workspace deleted | workspace=%s",
                path.name,
            )
        except OSError as exc:
            logger.warning(
                "Failed to delete workspace | path=%s | error=%s",
                path,
                exc,
            )
