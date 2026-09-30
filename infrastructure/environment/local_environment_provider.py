import asyncio
from pathlib import Path

from capabilities.environment.ports.environment_provider import EnvironmentProvider


class LocalEnvironmentProvider(EnvironmentProvider):

    async def execute_command(
        self,
        command: str,
        working_directory: str,
        timeout_seconds: int = 300,
    ):
        if not command or not command.strip():
            raise ValueError("Environment command cannot be empty.")

        if not working_directory:
            raise ValueError("Working directory cannot be empty.")

        process = await asyncio.create_subprocess_shell(
            command,
            cwd=working_directory,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise TimeoutError(
                f"Command timed out after {timeout_seconds} seconds."
            )

        return {
            "return_code": process.returncode,
            "stdout": stdout.decode(errors="replace"),
            "stderr": stderr.decode(errors="replace"),
        }

    async def create_directory(self, path: str) -> None:
        if not path:
            raise ValueError("Directory path cannot be empty.")

        Path(path).mkdir(parents=True, exist_ok=True)

    async def read_file(self, path: str) -> str:
        if not path:
            raise ValueError("File path cannot be empty.")

        return Path(path).read_text(encoding="utf-8")

    async def write_file(
        self,
        path: str,
        content: str,
    ) -> None:
        if not path:
            raise ValueError("File path cannot be empty.")

        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    async def delete_path(self, path: str) -> None:
        if not path:
            raise ValueError("Path cannot be empty.")

        target = Path(path)

        if not target.exists():
            return

        if target.is_dir():
            import shutil
            shutil.rmtree(target)
        else:
            target.unlink()