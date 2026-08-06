from datetime import datetime


class RunService:

    """
    Creates execution metadata
    for every workflow run.
    """

    @staticmethod
    def create_run_id():

        return datetime.now().strftime("%Y%m%d_%H%M%S")