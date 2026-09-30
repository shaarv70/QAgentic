from agents.base_agent import BaseAgent


class RepositoryAnalysisAgent(BaseAgent):
    def __init__(self, repository_analysis_service):
        super().__init__()
        self.repository_analysis_service = repository_analysis_service

    def execute(self, state):
        if not isinstance(state, dict):
            raise ValueError("Repository analysis state must be a dictionary")

        workspace_path = state.get("workspace_path")
        if not workspace_path:
            raise ValueError(
                "workspace_path is required for repository analysis"
            )

        requested_suite = state.get("requested_suite")

        return self.repository_analysis_service.analyze(
            workspace_path=workspace_path,
            requested_suite=requested_suite,
        )