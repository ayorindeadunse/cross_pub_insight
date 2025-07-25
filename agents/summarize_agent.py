import os
os.environ["GGML_METAL_LOG_LEVEL"] = "0"

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
        self.config = load_config(config_file)
        self.llm = get_llm_client(
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
    
    def _assess_confidence(self, analysis: str, fact_check: str, trends: str, comparison: str) -> str:
        """
        Heuristically. assess confidence based on analysis, completeness and fact-check feedback.
        Returns one of: 'High', 'Medium', 'Low'

        These are basic heuristics and will be finetuned
        
        """
        if not analysis or len(analysis.strip()) < 100:
            return "Low"
        
        if "not specify" in fact_check.lower() or "missing" in fact_check.lower():
            return "Medium"
        if not trends or "None" in trends:
            return "Medium"
        if comparison and analysis.strip() == comparison.strip():
            return "Medium"
        
        return "High"

       
    def run(self, state: dict) -> dict:
        """
        Runs summarization process using input state dictionary.

        Args:
        state (dict): Must include 'analysis_result', 'aggregated_trends', and optionally 'comparison_result'.

        Returns:
            dict: Updated state with 'final_summary'
        """
        logger.info("Generating final project summary...")

        primary_analysis = state.get("analysis_result", "").strip()
        comparison_analysis = state.get("comparison_target", {}).get("analysis_result", "").strip()

        # Check for self-comparison
        if primary_analysis and comparison_analysis and primary_analysis == comparison_analysis:
              logger.warning("Comparison analysis matches primary analysis. Skipping comparison section.")
              comparison_section = ""
        else:
            #comparison_section = state.get("comparison_result", "")
            comparison_section = comparison_analysis

        prompt = self.prompt_template.render(
            analysis=state.get("analysis_result", ""),
            trends=state.get("aggregated_trends", ""),
            comparison=comparison_section
        )
        
        logger.debug(f"Generated prompt for LLM:\n: + {prompt}")

        response = self.llm.generate(
            prompt = prompt,
            temperature = 0.3,
            max_tokens = 800
        )

        confidence = self._assess_confidence(
            analysis=primary_analysis,
            fact_check=state.get("fact_check_result", ""),
            trends=state.get("aggregated_trends", ""),
            comparison=comparison_section
        )

        # Prepend confidence block
        confidence_block = f"\n Confidence Rating: **{confidence}**\n\n"
        # response = confidence_block + response

        # Attach to state
        state["confidence_rating"] = confidence
        state["final_summary"] = response

        logger.info("Final summary generation complete.")

        

        # Append results of fact-checking if available
        fact_check_result = state.get("fact_check_result", "")
        if fact_check_result:
            logger.info("Preparing fact check feedback to summary.")
            fact_check_block = (
                "\n"
                "##################################################\n"
                "#                 🧪 FACT CHECK RESULT            #\n"
                "##################################################\n"
                f"{fact_check_result}\n"
                "--------------------------------------------------\n\n"
            )
            response = confidence_block + fact_check_block + response
            logger.info(f"FINAL SUMMARY :\n: + {response}")
            state["final_summary"] = response

        return state
    
def run(state: dict) -> dict:
    agent = SummarizeAgent(llm_type="local")
    return agent.run(state)


       
       

       
        
