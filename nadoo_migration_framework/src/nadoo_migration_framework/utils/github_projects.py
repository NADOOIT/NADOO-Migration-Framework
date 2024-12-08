from pathlib import Path
from functools import lru_cache

@lru_cache(maxsize=None)
def get_github_projects_folder() -> Path:
    """
    Determine the GitHub projects folder.

    Returns:
        Path: The path to the GitHub projects folder.

    Raises:
        FileNotFoundError: If the GitHub projects folder cannot be found.
    """
    # Common directories to search
    search_directories = [
        Path.home() / "Documents" / "GitHub",
        Path.home() / "GitHub",
        Path.home() / "Projects",
        Path.home() / "OneDrive" / "Dokumente" / "GitHub",
        Path.home() / "Dokumente" / "GitHub",
    ]

    for base_dir in search_directories:
        if base_dir.is_dir():
            return base_dir

    raise FileNotFoundError(f"GitHub projects folder could not be found. "
                            f"Searched in: {', '.join(str(d) for d in search_directories)}")

def get_list_of_github_projects() -> list[str]:
    """
    Returns a list of project names in the GitHub projects folder.

    Returns:
        list[str]: A list of project names.
    """
    github_folder = get_github_projects_folder()
    return [project.name for project in github_folder.iterdir() if project.is_dir()]
