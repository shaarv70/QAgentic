import logging
from pathlib import Path


log_folder = Path("logs")
log_folder.mkdir(exist_ok=True)

logger = logging.getLogger("QA_AGENT")
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s | %(threadName)s | %(levelname)s | %(message)s"
)

# File Handler
file_handler = logging.FileHandler(
    log_folder / "qa_agent.log",encoding="utf-8"
)
file_handler.setFormatter(formatter)

# Console Handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

logger.handlers.clear()

logger.addHandler(file_handler)
logger.addHandler(console_handler)