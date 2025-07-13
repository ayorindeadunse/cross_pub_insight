import os
os.environ["GGML_METAL_LOG_LEVEL"] = "0"

import re
from pathlib import Path
from typing import Dict, List, Any
from bs4 import BeautifulSoup

from utils.config_loader import load_config
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Load Configuration
CONFIG = load_config()
PARSER_CONFIG = CONFIG.get("repo_parser", {})

EXTENSION_LANGUAGE_MAP = PARSER_CONFIG.get("extension_language_map", {})
MAX_README_EXCERPT = PARSER_CONFIG.get("max_readme_excerpt_chars", 2000)
MAX_LICENSE_EXCERPT = PARSER_CONFIG.get("max_license_excerpt_chars", 2000)
NUM_KEYWORDS = PARSER_CONFIG.get("num_keywords", 10)

COMMON_WORDS = {
    "the", "and", "for", "with", "this", "that", "from", "are", "of",
    "to", "in", "is", "it", "on", "as", "by", "an", "be", "at", "or"
}

def extract_readme(repo_path: Path) -> str:
    """Extracts the README content from a repository directory."""
    for filename in ["README.md", "README"]:
        readme_path = repo_path / filename
        if readme_path.exists():
            logger.debug(f"README file found: {readme_path}")
            raw = readme_path.read_text(encoding='utf-8')
        
            #Clean HTML if necessary
            soup = BeautifulSoup(raw, "html.parser")
            text = soup.get_text(separator="\n")

            # Remove empty lines or markdown clutter
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            cleaned = "\n".join(lines)

            logger.info(f"Extracted and cleaned README content ({len(cleaned)}) chars)")
            return cleaned
        
    logger.warning(f"No README file found in {repo_path}")
    return "No README file found."

def extract_license(repo_path: Path) -> str:
    """Extracts the LICENSE content from a repository directory."""
    for filename in ["LICENSE", "LICENSE.txt"]:
        license_path = repo_path / filename
        if license_path.exists():
            logger.debug(f"LICENSE file found: {license_path}")
            return license_path.read_text(encoding='utf-8')
    logger.warning(f"No LICENSE file found in {repo_path}")
    return "No LICENSE file found."

def list_file_extensions(repo_path: Path) -> Dict[str, int]:
    """Lists all file extensions in the repository and their counts."""
    extensions = {}
    for root, _, files in os.walk(repo_path):
        for file in files:
            ext = Path(file).suffix
            if ext:
                extensions[ext] = extensions.get(ext, 0) + 1
    logger.debug(f"File extensions found: {extensions}")
    return extensions

def map_extensions_to_languages(extensions: Dict[str, int]) -> Dict[str, int]:
    """Maps file extensions to programming languages with usage counts."""
    language_count = {}
    for ext, count in extensions.items():
        language = EXTENSION_LANGUAGE_MAP.get(ext.lower(), "Other")
        language_count[language] = language_count.get(language, 0) + count
    logger.debug(f"Languages used in repository: {language_count}")
    return language_count

def extract_keywords(text: str) -> List[str]:
    """Extracts the most common keywords from the given text."""
    words = re.findall(r'\b\w+\b', text.lower())
    keywords = [word for word in words if word not in COMMON_WORDS and len(word) > 3]
    
    freq = {}
    for word in keywords:
        freq[word] = freq.get(word, 0) + 1

    sorted_keywords = sorted(freq.items(), key=lambda item: item[1], reverse=True)
    top_keywords = [word for word, _ in sorted_keywords[:NUM_KEYWORDS]]

    logger.debug(f"Extracted keywords: {top_keywords}")
    return top_keywords

def parse_repository(repo_path: str) -> Dict[str, Any]:
    """Parses the repository and returns a structured summary."""
    repo = Path(repo_path)
    if not repo.exists():
        logger.error(f"Repository path does not exist: {repo_path}")
        return {"error": f"Repository path {repo_path} does not exist."}
    
    logger.info(f"Parsing repository: {repo}")

    readme = extract_readme(repo)
    license_info = extract_license(repo)
    file_types = list_file_extensions(repo)
    languages_used = map_extensions_to_languages(file_types)
    keywords = extract_keywords(readme) if readme else []

    summary = {
        "repository_name": repo.name,
        "file_types": file_types,
        "languages_used": languages_used,
        "license_excerpt": license_info[:MAX_LICENSE_EXCERPT] + ("..." if len(license_info) > MAX_LICENSE_EXCERPT else ""),
        "keywords": keywords,
        "readme_excerpt": readme[:MAX_README_EXCERPT] + ("..." if len(readme) > MAX_README_EXCERPT else "")
    }

    logger.debug(f"Repository summary generated: {summary}")
    return summary

def format_repo_summary(summary: Dict[str, Any]) -> str:
    """Formats the repository summary into a human-readable string."""
    languages = ', '.join([f"{lang} ({count})" for lang, count in summary.get("languages_used", {}).items()])
    keywords = ', '.join(summary.get("keywords", []))
    file_types = ', '.join([f"{ext} ({count})" for ext, count in summary.get("file_types", {}).items()])

    formatted = (
        f"Repository Name: {summary.get('repository_name', 'N/A')}\n"
        f"Languages Used: {languages or 'None detected'}\n"
        f"File Types: {file_types or 'None detected'}\n"
        f"Top Keywords: {keywords or 'None found'}\n\n"
        f"README Excerpt:\n{summary.get('readme_excerpt', '')}\n\n"
        f"License Excerpt:\n{summary.get('license_excerpt', '')}\n"
    )
    return formatted

def condense_repo_summary(summary: Dict[str, Any]) -> str:
    """
    Generates a condensed semantic summary of the repository for LLM input.
    """
    repo_name = summary.get("repository_name", "Unknown Project")
    languages = ', '.join(list(summary.get("languages_used", {}).keys())[:3]) or "Unknown Languages"
    file_types = ', '.join(list(summary.get("file_types", {}).keys())[:3]) or "Unknown File Types"
    keywords = ', '.join(summary.get("keywords", [])[:5]) or "No Keywords"

    # Improve project summary extraction
    readme_excerpt = summary.get("readme_excerpt", "")
    project_summary = ""
    if readme_excerpt:
        paragraph_lines = []
        # Try to find the first meaningful paragraph (skip headings/empty lines)
        for line in readme_excerpt.splitlines():
            line = line.strip()

            # Skip markdown images, badges, empty lines or headings
            if not line:
                if paragraph_lines:
                    break
                continue
            if re.match(r"^!\[.*\]\(.*\)", line):  # markdown image
                continue
            if re.match(r"^\[!\[.*\]\(.*\)\]", line):  # markdown badge
                continue
            if line.startswith("#"):
                continue 

            paragraph_lines.append(line)
            if len(paragraph_lines) >= 3: # Limit paragraph length
                break

            # Accept the first "normal" line
            project_summary = " ".join(paragraph_lines).strip()
            
    if not project_summary:
        project_summary = "No project description available."

    condensed = (
        f"Project: {repo_name}\n"
        f"Main Languages: {languages}\n"
        f"File Types: {file_types}\n"
        f"Top Keywords: {keywords}\n"
        f"Project Summary: {project_summary}"
    )
    return condensed
