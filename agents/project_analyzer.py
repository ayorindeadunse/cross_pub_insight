import os
os.environ["GGML_METAL_LOG_LEVEL"] = "0"

from pathlib import Path
from typing import Dict, Any, Optional

from llm.client import get_llm_client
from tools.repo_parser import parse_repository, format_repo_summary,condense_repo_summary
from utils.logger import get_logger
from utils.config_loader import load_config

logger = get_logger(__name__)

class ProjectAnalyzerAgent:
    def __init__(self, llm_type: str = "local", model_name: Optional[str] = None, config_file: str = "config/config.yaml"):
        """
        Initializes the ProjectAnalyzerAgent.

        Args:
            llm_type (str): Type of LLM backend ("local", "openai", etc.)
            model_name (Optional[str]): Specific model to use; falls back to config default if None.
            config_file (str): Path to the configuration YAML file.
        """
        self.config = load_config(config_file)
        self.llm = get_llm_client(
            llm_type=llm_type,
            model_name=model_name or self.config.get("llm", {}).get("model_name")
        )
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """
        Loads the LLM prompt template from file specified in configuration.

        Returns:
            str: The loaded prompt template as a string.
        """
        prompt_rel_path = self.config.get("paths", {}).get("analyzer_prompt", "config/prompts/analyzer_prompt.txt")
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
        """
        Analyzes a project repository using the LLM and returns the analysis.

        Args:
            repo_path (str): Path to the local repository directory.

        Returns:
            str: Generated analysis from the LLM.
        """
        logger.info(f"Analyzing repository at: {repo_path}")

        repo_summary = parse_repository(repo_path)
        logger.debug(f"Repository summary extracted: {repo_summary}")

        if "error" in repo_summary:
            logger.error(f"Repository parsing failed: {repo_summary['error']}")
            return repo_summary["error"]

        # formatted_summary = format_repo_summary(repo_summary)
        condensed_summary = condense_repo_summary(repo_summary)
        full_prompt = self.prompt_template.format(repo_summary=condensed_summary)

        logger.debug("Condensed repo summary going into prompt:\n" + condensed_summary)
        logger.debug("Full prompt being sent to LLM:\n" + full_prompt)

        response = self.llm.generate(full_prompt)

        logger.debug(f"Raw LLM response: {response}")
        logger.debug(f"LLM response type: {type(response)}")

        assert isinstance(response, str), f"LLM response was not a string! Got {type(response)}"
        
        logger.info(f"Generated analysis completed.")
        return response
    
def run(state: dict) -> dict:
    print("Running project_analyzer...")
    agent = ProjectAnalyzerAgent()

    repo_path = state.get("repo_path","")
    analysis_result = agent.analyze_project(repo_path)

    state["analysis_result"] = analysis_result
    return state
