import os
import re
from pathlib import Path
from typing import Dict, List, Any, Union

from utils.config_loader import load_config
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Load Configuration
CONFIG = load_config()
PARSER_CONFIG = CONFIG.get("repo_parser", {})

EXTENSION_LANGUAGE_MAP = PARSER_CONFIG.get("extension_language_map", {})
MAX_README_EXCERPT = PARSER_CONFIG.get("max_readme_excerpt_chars", 500)
MAX_LICENSE_EXCERPT = PARSER_CONFIG.get("max_license_excerpt_chars", 200)
NUM_KEYWORDS = PARSER_CONFIG.get("num_keywords", 10)

def extract_readme(repo_path: Path) -> str:
    """
    Looks for README.md or README in the root of the repo and returns its content.

    """
    for filename in ["README.md", "README"]:
        readme_path = repo_path / filename
        if readme_path.exists():
            logger.debug(f"README file found: {readme_path}")
            return readme_path.read_text(encoding='utf-8')  
    logger.warning(f"No README file found in {repo_path}")
    return "No README file found."

def extract_license(repo_path: Path) -> str:
    """
    Looks for LICENSE or LICENSE.txt in the root of the repo and returns its content.

    """
    for filename in ["LICENSE", "LICENSE.txt"]:
        license_path = repo_path / filename
        if license_path.exists():
            logger.debug(f"LICENSE file found: {license_path}")
            return license_path.read_text(encoding='utf-8')
    logger.warning(f"No LICENSE file found in {repo_path}")
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

def map_extensions_to_languages(extensions: Dict[str, int]) -> Dict[str, int]:
    """
    Maps file extensions to programming languages using EXTENSION_LANGUAGE_MAP.

    """
    language_count = {}
    for ext, count in extensions.items():
        language = EXTENSION_LANGUAGE_MAP.get(ext.lower(), "Other")
        language_count[language] = language_count.get(language, 0) + count
    return language_count

def extract_keywords(text: str) -> list:
    """
    Native keyword extraction: returns most frequent non-trivial words.
    """
    words = re.findall(r'\b\w+\b', text.lower())
    common_words = {"the", "and", "for", "with", "this", "that", "from", "are","of" 
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
        logger.error(f"Repository path does not exist: {repo_path}")
        return f"Repository path {repo_path} does not exist."
    
    logger.info(f"Parsing repository: {repo}")
    
    readme = extract_readme(repo)
    license_info = extract_license(repo)
    file_types = list_file_extensions(repo)
    languages_used = map_extensions_to_languages(file_types)
    keywords = extract_keywords(readme) if readme else []

    return {
        "repository_name": repo.name,
        "file_types": file_types,
        "languages_used": languages_used,
        "license_excerpt": license_info[:MAX_LICENSE_EXCERPT] + ("..." if len(license_info) > MAX_LICENSE_EXCERPT else ""),
        "keywords": keywords,
        "readme_excerpt": readme[:MAX_README_EXCERPT] + ("..." if len(readme) > MAX_README_EXCERPT else "")
    }
    