import os

def parse_repository(repo_path: str) -> str:
    """

    Dummy repo parser for now 

    """

    if not os.path.exists(repo_path):
        return "Repository path does not exist."
    files = [f for f in os.listdir(repo_path) if os.path.isfile(os.path.join(repo_path, f))]
    return f"files in repository: {', '.join(files)}"