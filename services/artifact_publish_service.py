

class ArtifactPublisher:

    """
=====================================================
Class : ArtifactPublisher
=====================================================

Purpose:
    Publish generated artifacts.

Responsibilities:

    • Display generated artifacts.
    • Save artifacts.
    • Future:
        - HTML
        - PDF
        - Dashboard
        - Email

Called By:
    PublishNode
"""

    def __init__(self,artifact_manager):

        self.artifact_manager = artifact_manager


    def publish(self,state):

        for artifact in state.artifacts.values():

            print("\n" + "=" * 60)
            print(f"Generated Artifact : " f"{artifact.capability}")
            print("=" * 60)
            print(artifact.content)

            self.artifact_manager.save(artifact,state.run_id)
