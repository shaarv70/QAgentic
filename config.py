import os

from dotenv import load_dotenv

load_dotenv()

def get_required_env(key: str) -> str:
    value = os.getenv(key)

    if value is None:
        raise RuntimeError(f"{key} environment variable is missing.")

    return value


LLM_PROVIDER = "ollama"

OLLAMA_URL = get_required_env("OLLAMA_URL")

MODEL_NAME = get_required_env("MODEL_NAME")

LOG_LEVEL = os.getenv("LOG_LEVEL")

OUTPUT_FOLDER = os.getenv(
    "OUTPUT_FOLDER",
    "generated"
)

MAX_EXECUTION_RETRIES = 3
MAX_REVIEW_RETRIES = 2