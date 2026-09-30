from domain.repository.repository_detector import RepositoryDetector


class RepositoryDetectorRegistry:
    """
    Registry of repository discovery extensions.
    """

    def __init__(
        self,
        detectors: list[RepositoryDetector] | None = None,
    ) -> None:

        self._detectors: dict[
            str,
            RepositoryDetector,
        ] = {}

        for detector in detectors or []:
            self.register(detector)

    def register(
        self,
        detector: RepositoryDetector,
    ) -> None:

        if detector is None:
            raise ValueError(
                "Repository detector cannot be None."
            )

        name = detector.name.strip()

        if not name:
            raise ValueError(
                "Repository detector name cannot be empty."
            )

        if name in self._detectors:
            raise ValueError(
                f"Repository detector already registered: {name}"
            )

        self._detectors[name] = detector

    def get(
        self,
        name: str,
    ) -> RepositoryDetector:

        try:
            return self._detectors[name]
        except KeyError as exc:
            raise KeyError(
                f"Repository detector not registered: {name}"
            ) from exc

    def get_all(
        self,
    ) -> list[RepositoryDetector]:

        return list(
            self._detectors.values()
        )

    def get_registered_names(
        self,
    ) -> list[str]:

        return list(
            self._detectors.keys()
        )