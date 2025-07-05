import os
os.environ["GGML_METAL_LOG_LEVEL"] = "0"

from pathlib import Path
from typing import Optional

from llm.client import get_llm_client
from tools.repo_parser import parse_repository, condense_repo_summary
from utils.logger import get_logger
from utils.config_loader import load_config

logger = get_logger(__name__)

class FactCheckerAgent:
    def __init__(self, llm_type: str = "local", model_name: Optional[str] = None, config_file: str = "config/config.yaml"):
        self.config = load_config(config_file)
        self.llm = get_llm_client(
            llm_type=llm_type,
            model_name=model_name or self.config.get("llm", {}).get("model_name")
        )
        self.prompt_template = self._load_prompt_template()
    def _load_prompt_template(self) -> str:
        prompt_rel_path = self.config.get("paths", {}).get("fact_checker_prompt", "config/prompts/fact_checker_prompt.txt")
        prompt_path = Path(prompt_rel_path)

        logger.debug("Loading fact checker prompt from: {prompt_path}")
        if not prompt_path.exists():
            logger.error(f"Prompt template not found at {prompt_path}")
            raise FileNotFoundError(f"Prompt template not found at {prompt_path}")
        
        try:
            return prompt_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.exception(f"Failed to read prompt: {e}")
            raise e
    
    def fact_check(self, analysis: str, repo_path: str) -> str:
        logger.info(f"Fact-checking analysis result for repo: {repo_path}")

        repo_summary = parse_repository(repo_path)
        if "error" in repo_summary:
            logger.error(f"Repo parsing failed during fact-check: {repo_summary['error']}")
            return "Error parsing repository during fact check."
        
        condensed_repo = condense_repo_summary(repo_summary)

        prompt = self.prompt_template.format(
            analysis_result=analysis,
            repo_summary=condensed_repo
        )

        logger.debug(f"Prompt sent to LLM:\n{prompt}")
        response = self.llm.generate(prompt)

        logger.info(f"LLM response (fact check result): {response}")
        assert isinstance(response, str), "Expected string response from LLM"
        
        return response

def run(state: dict) -> dict:
    print("Running fact_checker...")
    agent = FactCheckerAgent()
    analysis = state.get("analysis_result", "")
    repo_path = state.get("repo_path", "")
    result = agent.fact_check(analysis, repo_path)

    state["fact_check_result"] = result
    return state




        

