from dataclasses import dataclass, field


@dataclass(frozen=True)
class  ExecutionPolicy:
    """
    Security policy governing test-command execution.

    This policy is independent of MCP transport and server
    configuration.
    """

    allowed_commands: frozenset[str] = field(default_factory=frozenset)

    timeout_seconds: int = 300

    max_output_bytes: int = 1_000_000

    allow_environment: bool = False

    allow_shell: bool = False


    def is_command_allowed(self,command: str,) -> bool:
        """
        Determine whether the executable in a command
        is permitted by this policy.
        """

        executable = command.strip().split(maxsplit=1)[0]

        return executable in self.allowed_commands