from pathlib import Path
from typing import Optional
from llm.client import get_llm_client
from utils.config_loader import load_config
from utils.logger import get_logger
from jinja2 import Template

logger = get_logger(__name__)

class SummarizeAgent:
    def __init__(self, llm_type: str = "local", model_name: Optional[str]= None, config_file: str = "config/config.yaml"):
        """
        Initializes the SummarizeAgent.
        
        Args:
            llm_type (str): Type of LLM backend ("local", "openai", etc.)
            model_name (Optional[str]): Specific model to use; falls back to config default if None.
            config_file (str): Path to the configuration YAML file.
        """
        self.config = get_llm_client(
            llm_type=llm_type,
            model_name=model_name or self.config.get("llm", {}).get("model_name")
        )
        self.prompt_template = self._load_prompt_template()
   
    def _load_prompt_template(self) -> Template:
       """
       Loads the Jinja2 prompt template for summarization from path in config.

       Returns:
         Template: Compiled Jinja2 template object
        """
       prompt_rel_path = self.config.get("paths", {}).get("summarize_prompt", "config/prompts/summarize_project.txt")
       prompt_path = Path(prompt_rel_path)

       logger.debug(f"Attempting to load summarization prompt from: {prompt_path}")

       if not prompt_path.exists():
           logger.error(f"Summarization prompt not found at {prompt_path}")
           raise FileNotFoundError(f"Summarization prompt not found at {prompt_path}")
       
       try:
           content = prompt_path.read_text(encoding="utf-8")
           logger.info(f"Successfully loaded summarization prompt from: {prompt_path}")
           return Template(content)
       except Exception as e:
           logger.exception(f"Error reading summarization prompt from {prompt_path}: {e}")
           raise e
       
    def run(self, state: dict) -> dict:
        """
        Runs summarization process using input state dictionary.

        Args:
        state (dict): Must include 'analysis_result', 'aggregated_trends', and optionally 'comparison_result'.

        Returns:
            dict: Updated state with 'final_summary'
        """
        logger.info("Generating final project summary...")

        prompt = self.prompt_template.render(
            analysis=state.get("analysis_result", ""),
            trends=state.get("aggregated_trends", ""),
            comparison=state.get("comparison_result", "")
        )

        logger.debug(f"Generated prompt for LLM:\n: + {prompt}")

        response = self.llm.generate(
            prompt = prompt,
            temperature = 0.3,
            max_tokens = 800
        )

        logger.info("Final summary generation complete.")

        state["final_summary"] = response
        return state


       
       

       
        
