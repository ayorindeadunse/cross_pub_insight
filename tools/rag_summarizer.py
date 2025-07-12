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
MAX_CONTEXT_CHARS = 3000

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

def _is_valid_source_file(path: Path, max_size: int = 100_100) -> bool:
    ignored_exts = {".sh", ".bat", ".psi", ".bash", ".zsh"}
    return (
        path.suffix.lower() in CODE_EXTENSIONS
        and path.suffix.lower() not in ignored_exts
        and not path.name.endswith(".min.js")
        and path.stat().st_size <= max_size
    )
    
def summarize_readme(repo_path: str) -> str:
    """
    Attempts to generate a RAG-style summary of a repository when the README is missing or malformed.
    """
    logger.info(f"Generating RAG-style summary for repo: {repo_path}")
    repo = Path(repo_path)
    if not repo.exists() or not repo.is_dir():
        logger.error(f"Invalid repository path: {repo_path}")
        return "Invalid repository path."
    
    selected_files = _rank_and_select_files(repo)
    if not selected_files:
        logger.warning("No informative source files found.")
        return "No informative source files found to summarize the project."
    
    sources = []
    total_chars = 0
    logger.info("Extracting informative snippets from selected files...")

    for filepath in selected_files:
        try:
            content = filepath.read_text(encoding="utf-8")
            snippet_text = _extract_snippet_lines(content, max_lines=12)
            if not snippet_text:
                continue
            if total_chars + len(snippet_text) > MAX_CONTEXT_CHARS:
                break
            total_chars += len(snippet_text)
            sources.append(f"\n### File: {filepath.relative_to(repo)}\n{snippet_text}")
        except Exception as e:
            logger.warning(f"Skipping problematic file {filepath}: {e}")
    
    if not sources:
        logger.warning("No usable content extracted for prompt.")
        return "unable to generate summary from source files."
    
    combined_context = "\n".join(sources)
    prompt_template = _load_prompt_template()
    prompt = prompt_template.format(repo_name = repo.name, file_context=combined_context)

    logger.info("Sending RAG prompt to LLM...")
    logger.info(f"RAG prompt being sent to LLM:\n{prompt}")

    response = _llm.generate(prompt)
    logger.info(f"RAG response coming back from LLM:\n{response}")

    if not isinstance(response, str):
        logger.error("LLM returned non-string response for RAG summary.")
        return "Failed to generate a summary."
    
    return response.strip()


    
def _rank_and_select_files(repo: Path, max_files: int = 10, max_size: int = 100_000) -> List[Path]:
    candidates = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for fname in files:
            filepath = Path(root) / fname
            if not _is_valid_source_file(filepath, max_size):
                continue
            try:
                content = filepath.read_text(encoding="utf-8")
                score = _informativeness_score(content, filepath)
                candidates.append((score, filepath))
            except Exception as e:
                logger.debug(f"Skipping unreadable file {filepath}: {e}")
                continue

    candidates.sort(reverse=True, key=lambda x: x[0])
    logger.info(f"Selected top files for summarization: {[f.name for _, f in candidates[:max_files]]}")
    return [path for _, path in candidates[:max_files]]


def _extract_snippet_lines(content: str, max_lines: int = 12) -> str:
    snippet = []
    for line in content.splitlines():
        line = line.strip()
        if not line or len(line) < 4:
            continue
        if re.match(r"^\s*(#|//|/\*|\*|<!--)", line):
            snippet.append(line)
        elif re.match(r"^\s*(def|class|func|fn|public|private|interface|module|package|export|using|import)\b", line, re.IGNORECASE):
            snippet.append(line)
        elif re.match(r"^\s*(if|for|while|switch|case)\b", line):
            snippet.append(line)
        if len(snippet) >= max_lines:
            break
    return "\n".join(snippet)

    
def _informativeness_score(content: str, filepath: Path) -> int:
    lines = content.splitlines()
    if len(lines) < 5:
        return 0

    # Common tokens used to identify boilerplate bash scripts
    repetitive_patterns = ["export ", "PYTHONPATH", "echo", "bash", "job", "cluster"]

    # Compute line-based metrics
    indent_lines = sum(1 for line in lines if line.startswith((" ", "\t")))
    comment_lines = sum(1 for line in lines if re.match(r'^\s*(#|//|/\*|\*|<!--)', line))
    symbols = len(re.findall(r'[{}()\[\];:=>]', content))
    keywords = len(re.findall(r'\b(def|class|func|fn|impl|interface|struct|module|export|import|async|await|const|var|let|main)\b', content, re.IGNORECASE))

    score = (
        (len(lines) // 10) +
        (indent_lines // 5) +
        (comment_lines * 2) +
        (symbols // 15) +
        (keywords * 3)
    )

    # Penalize shell scripts with low variety
    if filepath.suffix == ".sh":
        lower_content = content.lower()
        repetition_penalty = sum(lower_content.count(p) for p in repetitive_patterns)
        if repetition_penalty > 15 or score < 10:
            return 0  # Skip low-signal shell scripts

    return score




