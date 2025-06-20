import os
from pathlib import Path
from typing import Dict,Any
from llm.client import get_llm_client
from tools.repo_parser import parse_repository 
from utils.logger import get_logger

logger = get_logger()

class ProjectAnalyzerAgent:
    def __init__(self, llm_type="local", model_name=None):
        self.llm = get_llm_client(llm_type=llm_type, model_name=model_name)
        self.prompt_template = self.load_prompt_template()

@staticmethod
def load_prompt_template() -> str:
    prompt_path = Path(__file__).parent / "config" / "prompts" / "analyzer_prompt.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt template not found at {prompt_path}")
    return prompt_path.read_text();

def analyze_project(self, repo_path: str) -> str:
    logger.info(f"Analyzing repository at: {repo_path}")
    
    repo_summary = parse_repository(repo_path)
    logger.debug(f"Repository summary extracted: {repo_summary}")

    full_prompt = self.prompt_template.format(repo_summary=repo_summary)

    response = self.llm.generate(full_prompt)
    logger.info(f"Generated analysis completed.")
    return response