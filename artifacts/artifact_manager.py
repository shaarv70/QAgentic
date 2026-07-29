from utils.file_utils import save_to_file
from utils.logger import logger


class ArtifactManager:

    def save(self, artifact, run_id):

        filename = (
            f"{artifact.task_id}_"
            f"{artifact.capability}.md"
        )

        path = save_to_file(
            run_id,
            filename,
            artifact.content
        )

        logger.info(
            f"Saved artifact: {path}"
        )

        return path