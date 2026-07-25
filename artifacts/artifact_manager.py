from utils.file_utils import save_to_file
from utils.logger import logger


class ArtifactManager:

    def save(self, name, content):

        save_to_file(name, content)

        logger.info(f"✅ Saved {name}")