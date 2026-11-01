import os

from dotenv import load_dotenv

load_dotenv()


def get_required_env(key: str) -> str:
    value = os.getenv(key)

    if value is None:
        raise RuntimeError(
            f"{key} environment variable is missing."
        )

    return value


LLM_PROVIDER = os.getenv(
    "LLM_PROVIDER",
    "groq"
)

OLLAMA_URL = os.getenv(
    "OLLAMA_URL"
)

MODEL_NAME = os.getenv(
    "MODEL_NAME"
)

LOG_LEVEL = os.getenv("LOG_LEVEL")

OUTPUT_FOLDER = os.getenv(
    "OUTPUT_FOLDER",
    "generated"
)

MAX_EXECUTION_RETRIES = 3
MAX_REVIEW_RETRIES = 2

WORKSPACE_BASE_DIR = os.getenv(
    "WORKSPACE_BASE_DIR",
    ".qagentic/workspaces",
)

WORKSPACE_TTL_DAYS = int(os.getenv("WORKSPACE_TTL_DAYS", "7"))
WORKSPACE_MAX_COUNT = int(os.getenv("WORKSPACE_MAX_COUNT", "20"))
WORKSPACE_MAX_SIZE_MB = int(os.getenv("WORKSPACE_MAX_SIZE_MB", "500"))

EXECUTION_TIMEOUT_SECONDS = int(os.getenv("EXECUTION_TIMEOUT_SECONDS", "1800"))

# --- Playwright MCP ---
PLAYWRIGHT_MCP_ENABLED = os.getenv("PLAYWRIGHT_MCP_ENABLED", "true").lower() != "false"
PLAYWRIGHT_MCP_HEADLESS = os.getenv("PLAYWRIGHT_MCP_HEADLESS", "true").lower() != "false"

# --- GitHub MCP ---
# GITHUB_MCP_TRANSPORT: "stdio" (default, uses PAT) or "streamable-http" (Copilot)
GITHUB_MCP_TRANSPORT = os.getenv("GITHUB_MCP_TRANSPORT", "stdio")
GITHUB_PERSONAL_ACCESS_TOKEN = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")