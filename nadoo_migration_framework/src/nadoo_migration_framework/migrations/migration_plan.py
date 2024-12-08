from typing import List, Dict, Any

class MigrationPlan:
    """Represents a plan for migrating a project."""

    def __init__(self, steps: List[Dict[str, Any]], estimated_time: float):
        """Initialize the migration plan.

        Args:
            steps: A list of migration steps, each represented as a dictionary.
            estimated_time: Estimated time to complete the migration in minutes.
        """
        self.steps = steps
        self.estimated_time = estimated_time

    def get_steps(self) -> List[Dict[str, Any]]:
        """Get the list of migration steps.

        Returns:
            List[Dict[str, Any]]: The migration steps.
        """
        return self.steps

    def get_estimated_time(self) -> float:
        """Get the estimated time for the migration.

        Returns:
            float: Estimated time in minutes.
        """
        return self.estimated_time
