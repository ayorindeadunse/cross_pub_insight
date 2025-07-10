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

class RAGSummarizer:
    def __init__(self, llm_type: str = "local", model_name: Optional[str] = None, config_file: str = "config/config.yaml"):
        self.config = load_config(config_file)
        self.llm = get_llm_client(
            llm_type=llm_type,
            model_name=model_name or self.config.get("llm", {}).get("model_name")
        )
        self.prompt_template = self._load_prompt_template()
        self.max_files = self.config.get("rag_summarizer", {}).get("max_files", 10)
        self.max_file_chars = self.config.get("rag_summarizer", {}).get("max_file_chars", 5000)
    
    def _load_prompt_template(self) -> str:
        prompt_rel_path = self.config.get("paths", {}).get("rag_summarizer_prompt", "config/prompts/rag_summarizer_prompt.txt")
        prompt_path = Path(prompt_rel_path)

        logger.debug(f"Loading RAG summarizer prompt template from: {prompt_path}")
        if not prompt_path.exists():
            logger.error(f"Prompt template not found at {prompt_path}")
            raise FileNotFoundError(f"Prompt template not found at {prompt_path}")
        try:
            return prompt_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.exception(f"Error reading prompt template from {prompt_path}: {e}")
            raise e
    
    def summarize_readme(self, repo_path: str) -> str:
        logger.info(f"Generating RAG-style summary for repo: {repo_path}")
        repo = Path(repo_path)
        if not repo.exists() or not repo.is_dir():
            logger.error(f"invalid repository path: {repo_path}")
            return "Invalid repository path."
        
        selected_files = self._rank_and_select_files(repo)

        if not selected_files:
            logger.warning("No informative source files found.")
            return "No informative source files found to summarize the project."
        
        sources = []
        for filepath in selected_files:
            try:
                content = filepath.read_text(encoding="utf-8")[:self.max_file_chars]
                sources.append(f"\n### File: {filepath.relative_to(repo)}\n{content}")
            except Exception as e:
                logger.warning(f"Failed to read {filepath}: {e}")
        
        combined_context = "\n".join(sources)

        prompt = self.prompt_template.format(
            repo_name=repo.name,
            file_context=combined_context
        )

        logger.debug("Sending RAG summarization prompt to LLM...")
        response = self.llm.generate(prompt)

        if not isinstance(response, str):
            logger.error("LLM returned non-string response for RAG summary.")
            return "Failed to generate summary."
        
        return response.strip()
    
    def _rank_and_select_files(self, repo: Path) -> List[Path]:
        """
        Scans all source files and selects the most informative ones based on language-agnostic structure scoring.
        """
        candidates = []
        for root, _, files in os.walk(repo):
            for fname in files:
                filepath = Path(root) / fname
                if not filepath.suffix or filepath.suffix.lower() in {'md', '.txt', '.json', '.yml', '.yaml', '.toml'}:
                    continue
                if filepath.name.endswith('.min.js') or filepath.stat().st_size > 100_000:
                    continue
                try:
                    content = filepath.read_text(encoding="utf-8")
                    score = self._informativeness_score(content, filepath)
                    candidates.append((score, filepath))
                except Exception as e:
                    logger.debug(f"Skipping unreadable file {filepath}: {e}")
                    continue
        
        candidates.sort(reverse=True, key=lambda x: x[0])
        return [path for _, path in candidates[:self.max_files]]
    
    def _informativeness_score(self, content:str, filepath: Path) -> int:
        """
        Scores content by general informativeness signals: indentation, comments, length, symbols and code-like patterns.
        """
        lines = content.splitlines()
        if len(lines) < 5:
            return 0
        
        indent_lines = sum(1 for line in lines if line.startswith(" ") or line.startswith("\t"))
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



