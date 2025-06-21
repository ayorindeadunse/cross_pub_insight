import os
from pathlib import Path
from typing import Dict,Any
from llm.client import get_llm_client
from tools.repo_parser import parse_repository 
from utils.logger import get_logger
from utils.config_loader import load_config

logger = get_logger()

class ProjectAnalyzerAgent:
    def __init__(self, llm_type:str = "local", model_name: str = None, config_file: str = "config/config.yaml"):
        self.config = load_config(config_file)
        self.llm = get_llm_client(llm_type=llm_type, model_name=model_name or self.config.get("llm", {}).get("model_name"))
        self.prompt_template = self.load_prompt_template()


def load_prompt_template(self) -> str:
    prompt_rel_path = self.config.get("paths", {}).get("analyzer_prompt","config/prompts/analyzer_prompt.txt")
    prompt_path = Path(prompt_rel_path)

    logger.debug(f"Attempting to load prompt template from: {prompt_path}")

    if not prompt_path.exists():
        logger.error(f"Prompt template not found at {prompt_path}")
        raise FileNotFoundError(f"Prompt template not found at {prompt_path}")
    
    try:
        content = prompt_path.read_text(encoding="utf-8")
        logger.info(f"Successfully loaded prompt template from: {prompt_path}")
        return content
    except Exception as e:
        logger.exception(f"Error reading prompt template from {prompt_path}: {e}")
        raise e

def analyze_project(self, repo_path: str) -> str:
    logger.info(f"Analyzing repository at: {repo_path}")
    
    repo_summary = parse_repository(repo_path)
    logger.debug(f"Repository summary extracted: {repo_summary}")

    full_prompt = self.prompt_template.format(repo_summary=repo_summary)

    response = self.llm.generate(full_prompt)
    logger.info(f"Generated analysis completed.")
    return response