import os
import re
from pathlib import Path
from typing import Dict

def extract_readme(repo_path: Path) -> str:
    """
    Looks for README.md or README in the root of the repo and returns its content.

    """
    for filename in ["README.md", "README"]:
        readme_path = repo_path / filename
        if readme_path.exists():
            return readme_path.read_text(encoding='utf-8')  
    return "No README file found."

def extract_license(repo_path: Path) -> str:
    """
    Looks for LICENSE or LICENSE.txt in the root of the repo and returns its content.

    """
    for filename in ["LICENSE", "LICENSE.txt"]:
        license_path = repo_path / filename
        if license_path.exists():
            return license_path.read_text(encoding='utf-8')
    return "No LICENSE file found."

def list_file_extensions(repo_path: Path) -> Dict[str, int]:
    """
    Lists file extensions in the repository and counts their occurrences.

    """
    extensions = {}
    for root, _, files in os.walk(repo_path):
        for file in files:
            ext = Path(file).suffix
            if ext:
                extensions[ext] = extensions.get(ext, 0) + 1
    return extensions

def extract_keywords(text: str) -> list:
    """
    Native keyword extraction: returns most frequent non-trivial words.
    """
    words = re.findall(r'\b\w+\b', text.lower())
    common_words = {"the", "and", "for", "with", "this", "that", "from", "are" "of" 
                    "to", "in", "is", "it", "on", "as", "by", "an", "be", "at", "or"}
    keywords = [word for word in words if word not in common_words and len(word) > 3]
    freq = {}
    for word in keywords:
        freq[word] = freq.get(word, 0) + 1
        for word in keywords:
            freq[word] = freq.get(word, 0) + 1
        sorted_keywords = sorted(freq.items(), key=lambda item: item[1], reverse=True)
        return [word for word, _ in sorted_keywords[:10]]  # Return top 10 keywords
    
def parse_repository(repo_path: str) -> Dict[str, int]:
    """
    Parses the repository to extract a structured summary.
    """
    repo = Path(repo_path)
    if not repo.exists():
        return f"Repository path {repo_path} does not exist."
    
    readme = extract_readme(repo)
    file_types = list_file_extensions(repo)
    license_info = extract_license(repo)
    keywords = extract_keywords(readme) if readme else []

    return (
        f"Repository {repo.name}\n"
        f"Files by Type: {file_types}\n"
        f"License: {license_info}\n"
        f"Keywords: {keywords}\n"
        f"README Excerpt:\n{readme[:500]}{'...' if len(readme) > 500 else ''}"
    )
    