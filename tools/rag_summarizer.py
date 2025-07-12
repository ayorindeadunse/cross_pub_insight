import os
import re
from pathlib import Path
from typing import List, Optional

from llm.client import get_llm_client
from utils.logger import get_logger
from utils.config_loader import load_config

logger = get_logger(__name__)

CODE_EXTENSIONS = {
    # Programming languages
    ".py", ".js", ".ts", ".tsx", ".jsx",".json",".html",".xml",".jsp",".jspx",".asp",".aspx"
    ".go", ".rs", ".java", ".cpp", ".c",".mbt",".wsdl",".vb",
    ".cs", ".kt", ".kts", ".swift", ".m", ".mm",
    ".rb", ".php", ".scala", ".sh", ".bat", ".ps1",
    ".r", ".jl", ".lua", ".dart", ".clj", ".cljs",
    ".groovy", ".v", ".sv", ".vhd",
    ".sol", ".vy", ".nim", ".ml", ".mli",
    ".fs", ".fsi", ".asm", ".s",
    ".hx", ".ex", ".exs", ".erl",
    ".ada", ".d", ".tcl", ".pl", ".pm",
    ".cr", ".zig", ".cob", ".for", ".f90",
    ".lisp", ".scm", ".purs", ".re", ".reml",
    ".bas", ".cu", ".metal", ".glsl", ".wgsl",

    # Markup languages
    ".html", ".htm",               # HTML
    ".xml",                        # XML
    ".xhtml",                      # XHTML
    ".svg",                        # Scalable Vector Graphics
    ".xaml",                       # Used in .NET UI
    ".qml",                        # Qt Quick Markup Language
    ".md", ".markdown",            # Markdown
    ".rst",                        # reStructuredText
    ".tex", ".ltx",                # LaTeX
    ".yaml", ".yml",               # YAML (config)
    ".toml",                       # TOML (Rust, crypto)
    ".ini",                        # INI files
    ".cfg", ".conf",               # General configs
}

IGNORE_DIRS = {"tests", "__pycache__", "venv", "env", "node_modules", ".git", "build", "dist"}
MAX_SNIPPETS = 10
MAX_CONTEXT_CHARS = 5000

_config = load_config("config/config.yaml")
_llm = get_llm_client(
    llm_type=_config.get("llm", {}).get("type", "local"),
    model_name=_config.get("llm", {}).get("model_name")
)
    
def _load_prompt_template() -> str:
    prompt_rel_path = _config.get("paths", {}).get("rag_summarizer_prompt", "config/prompts/rag_summarizer_prompt.txt")
    prompt_path = Path(prompt_rel_path)

    logger.debug(f"Loading RAG summarizer prompt from: {prompt_path}")
    if not prompt_path.exists():
        logger.error(f"Prompt template not found at {prompt_path}")
        raise FileNotFoundError(f"Prompt template not found at {prompt_path}")
    
    return prompt_path.read_text(encoding="utf-8")

    
def summarize_readme(repo_path: str) -> str:
    """
    Attempts to generate a RAG-style summary of a repository when the README is missing or malformed.
    """
    logger.info(f"Generating RAG-style summary for repo: {repo_path}")
    repo = Path(repo_path)
    if not repo.exists() or not repo.is_dir():
        return "Invalid repository path."

    max_files = _config.get("rag_summarizer", {}).get("max_files", 10)
    max_chars_per_file = _config.get("rag_summarizer", {}).get("max_file_chars", 5000)

    selected_files = _rank_and_select_files(repo, max_files=max_files)

    if not selected_files:
        logger.warning("No informative source files found.")
        return "No informative source files found to summarize the project."

    sources = []
    logger.info(f"Reading through selected files...")
    for filepath in selected_files:
        try:
            content = filepath.read_text(encoding="utf-8")[:max_chars_per_file]
            sources.append(f"\n### File: {filepath.relative_to(repo)}\n{content}")
        except Exception as e:
            logger.warning(f"Failed to read {filepath}: {e}")

    combined_context = "\n".join(sources)
    prompt_template = _load_prompt_template()
    prompt = prompt_template.format(repo_name=repo.name, file_context=combined_context)
    logger.info(f"RAG prompt being sent to LLM: {prompt}")

    logger.debug("Sending RAG prompt to LLM...")
    response = _llm.generate(prompt)

    if not isinstance(response, str):
        logger.error("LLM returned non-string response.")
        return "Failed to generate summary."

    return response.strip()
    
def _rank_and_select_files(repo: Path, max_files: int = 10, max_size: int = 100_000) -> List[Path]:
    candidates = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for fname in files:
            filepath = Path(root) / fname
            if filepath.suffix.lower() not in CODE_EXTENSIONS:
                continue
            if filepath.name.endswith('.min.js') or filepath.stat().st_size > max_size:
                continue
            try:
                content = filepath.read_text(encoding="utf-8")
                score = _informativeness_score(content, filepath)
                candidates.append((score, filepath))
            except Exception as e:
                logger.debug(f"Skipping unreadable file {filepath}: {e}")
                continue

    candidates.sort(reverse=True, key=lambda x: x[0])
    return [path for _, path in candidates[:max_files]]
    
def _informativeness_score(content: str, filepath: Path) -> int:
    lines = content.splitlines()
    if len(lines) < 5:
        return 0

    indent_lines = sum(1 for line in lines if line.startswith((" ", "\t")))
    comment_lines = sum(1 for line in lines if re.match(r'^\s*(#|//|/\*|\*|<!--)', line))
    symbols = len(re.findall(r'[{}()\[\];:=>]', content))
    keywords = len(re.findall(r'\b(def|class|func|fn|impl|interface|struct|module|export|import|async|await|const|var|let)\b', content, re.IGNORECASE))

    score = (
        (len(lines) // 10) +
        (indent_lines // 5) +
        (comment_lines * 2) +
        (symbols // 15) +
        (keywords * 3)
    )
    return score



