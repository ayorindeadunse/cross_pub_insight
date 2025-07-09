import os
import re
from pathlib import Path
from typing import List, Optional

from llm.client import get_llm_client
from utils.logger import get_logger
from utils.config_loader import load_config

logger = get_logger(__name__)
CONFIG = load_config()

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
    def __init__(self, llm_type: str = "local", model_name: Optional[str] = None):
        self.config = CONFIG
        self.llm = get_llm_client(
            llm_type=llm_type,
            model_name=model_name or self.config.get("llm", {}).get("model_name")
        )
        self.prompt_template = self._load_prompt_template()
    
    def _load_prompt_template(self) -> str:
        prompt_rel_path = self.config.get("paths", {}).get("rag_summarizer_prompt", "config/prompts/rag_summarizer_prompt.txt")
        prompt_path = Path(prompt_rel_path)

        logger.debug(f"Loading RAG summarizer prompt from: {prompt_path}")
        if not prompt_path.exists():
            logger.error(f"Prompt template not fouund at {prompt_path}")
            raise FileNotFoundError(f"Prompt template not found at: {prompt_path}")
        
        try:
            return prompt_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read prompt template: {e}")
            raise e
    
    def summarize_readme(self, repo_path: str) -> str:
        """
        Summarizes a project by analyzing source files when the README is malformed or missing.       
        """
        logger.info(f"Generating fallback RAG summary for repo: {repo_path}")
        repo = Path(repo_path)
        if not repo.exists():
            return "Repository does not exist."
        
        candidate_files = self._collect_source_files(repo)
        top_files = self._rank_and_select_files(candidate_files, repo)

        code_context = self._extract_context(top_files, repo)
        if not code_context.strip():
            return "Project source code could not be summarized."
        
        prompt = self.prompt_template.format(code_context=code_context)
        logger.debug(f"RAG prompt sent to LLM:\n{prompt}")
        response = self.llm.generate(prompt)

        logger.info("LLM RAG summary received.")
        return response.strip()

    
    def _collect_source_files(self, repo: Path) -> List[Path]:
        files = []
        for root, dirs, filenames in os.walk(repo):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for fname in filenames:
                if Path(fname).suffix in CODE_EXTENSIONS:
                    files.append(Path(root) / fname)
        return files
    
    def _rank_and_select_files(self, files: List[Path], repo: Path) -> List[Path]:
        def score(path: Path):
            name = path.name.lower()
            s = -len(str(path.relative_to(repo)))
            if "main" in name or "init" in name:
                s += 10
            if "test" in name:
                s -= 5
            return s
    
        return sorted(files, key=score, reverse=True)[:MAX_SNIPPETS]
    
    def _extract_context(self, files: List[Path], repo: Path) -> str:
        snippets = []
        total_chars = 0

        for f in files:
            try:
                content = f.read_text(encoding='utf-8')
                snippet = extract_comments_and_definitions(content)
                label = f"File: {f.relative_to(repo)}\n{snippet}"
                snippets.append(label)
                total_chars += len(label)
                if total_chars >= MAX_CONTEXT_CHARS:
                    break
            except Exception as e:
                logger.warning(f"Failed to read {f}: {e}")
                continue

        return "\n\n".join(snippets)[:MAX_CONTEXT_CHARS]
    
def extract_comments_and_definitions(code: str) -> str:
    comments = re.findall(r"(\"\"\".*?\"\"\"|'''.*?'''|#.*?$)", code, re.DOTALL | re.MULTILINE)
    definitions = re.findall(r"^\s*(def|class|function)\s+[a-zA-Z0-9_]+\s*\(?.*?\)?:?", code, re.MULTILINE)
    return "\n".join(comments + definitions)[:1000]
        
        
