class ExecutionPrerequisiteError(RuntimeError):
    """
    Raised when a required execution prerequisite cannot be satisfied
    before a command is run.

    Examples:
        - JDK not found for a Maven/Gradle build
        - Required runtime not on PATH

    This error is never retryable — the same command will fail on
    every attempt until the environment is corrected.
    """
