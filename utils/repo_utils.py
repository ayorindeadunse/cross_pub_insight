import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

def clone_if_remote(repo_input: str, base_clone_dir: str = "~/projects") -> str:
    """
    Clones a repo if it's a GitHub URL; otherwise returns the local path.
    Args:
        repo_input: Either a full URL or a local path.
        base_clone_dir: Where to clone if needed.

    Returns:
        Local path to the repo.
    """
    repo_input = repo_input.strip()
    if repo_input.startswith("http://") or repo_input.startswith("https://"):
        parsed = urlparse(repo_input)
        repo_name = Path(parsed.path).stem # e.g., 'gemini-cli-main' from URL
        clone_path = os.path.expanduser(f"{base_clone_dir}/{repo_name}")
        if Path(clone_path).exists():
            print(f"Repo already exists locally: {clone_path}")
            return clone_path
        
        print(f"Cloning repo from {repo_input} to {clone_path}...")
        subprocess.run(["git", "clone",repo_input,  clone_path], check=True)
        return clone_path
    else:
        # Assume it's already a local path
        return os.path.expanduser(repo_input)

