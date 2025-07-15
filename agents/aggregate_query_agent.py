import os
os.environ["GGML_METAL_LOG_LEVEL"] = "0"

from pathlib import Path
from typing import List, Optional, Dict, Any
from llm.client import get_llm_client
from utils.config_loader import load_config
from utils.logger import get_logger
from jinja2 import Template

logger = get_logger(__name__)

class AggregateQueryAgent:
    def __init__(self, llm_type: str = "local", model_name: Optional[str] = None, config_file: str = "config/config.yaml"):
        self.config = load_config(config_file)
        self.llm = get_llm_client(
            llm_type=llm_type,
            model_name=model_name or self.config.get("llm", {}).get("model_name")
        )
        self.prompt_template = self._load_prompt_template()
    
    def _load_prompt_template(self) -> Template:
        prompt_path = Path(self.config["paths"].get("aggregate_prompt", "config/prompts/aggregate_query.txt"))
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt not found at {prompt_path}")
        content = prompt_path.read_text(encoding="utf-8")
        return Template(content)
    
    def run(self, query: str, analyses: List[str]) -> str:
        logger.info("Running aggregate query: {query}")
        prompt = self.prompt_template.render(query=query, analyses=analyses)
        logger.debug(f"Prompt for aggregation:\n{prompt}")
        response = self.llm.generate(prompt, temperature=0.2, max_tokens=600)
        return response.strip()

def run(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Running AggregateQueryAgent...")
    query = state.get("user_query", "").strip()
    comparison = state.get("comparison_target", {})
    analyses = [state.get("analysis_result", "")]
    
    if comparison:
        comp_analysis = comparison.get("analysis_result", "")
        if comp_analysis:
            analyses.append(comp_analysis)
        
    if not query:
        logger.warning("No user_query provided. Skipping aggregation.")
        state["aggregate_query_result"] = "No aggregate query provided"
        return state
        
    agent = AggregateQueryAgent()
    result = agent.run(query = query, analyses = analyses)
    state["aggregate_query_result"] = result
    return state
    
    



     