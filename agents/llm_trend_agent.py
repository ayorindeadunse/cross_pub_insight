import os
os.environ["GGML_METAL_LOG_LEVEL"] = "0"

from pathlib import Path
from typing import Optional, Dict, Any
from jinja2 import Template
from llm.client import get_llm_client
from utils.logger import get_logger
from utils.config_loader import load_config

from tools.semantic_trend_detector import SemanticTrendDetector


logger = get_logger(__name__)

class LLMTrendInsightAgent:
    def __init__(self, llm_type="local", model_name=None, config_file="config/config.yaml"):
        self.config = load_config(config_file)
        self.llm = get_llm_client(
            llm_type=llm_type,
            model_name=model_name or self.config.get("llm", {}).get("model_name")
        )
        self.prompt_template = self._load_prompt_template()
    
    def _load_prompt_template(self) -> Template:
        prompt_path = Path(self.config["paths"].get("llm_trend_prompt", "config/prompts/llm_trend_extractor.txt"))
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt not found at {prompt_path}")
        content = prompt_path.read_text(encoding="utf-8")
        return Template(content)
    
    def extract_trends(self, analysis: str) -> str:
        logger.info("Extracting trends using LLM...")
        prompt = self.prompt_template.render(analysis=analysis)
        logger.info(f"Prompt to LLM:\n{prompt}")
        response = self.llm.generate(prompt)
        logger.info(f"Trends respons from LLM:\n{response}")
        return response.strip()
    
def run(state: Dict[str, Any]) -> Dict[str, Any]:
    analysis = state.get("analysis_result", "")
    if not analysis:
        logger.warning("No analysis provided for trend extraction.")
        return {**state, "aggregated_trends": "No analysis to extract trends from."}
    
    try:
        agent = LLMTrendInsightAgent()
        trends = agent.extract_trends(analysis)
    except Exception as e:
        logger.warning(f"LLM trend extraction failed. Falling back to semantic method: {e}")
        # Fallback using semantic trend detector
        detector = SemanticTrendDetector()
        top_tags = detector.detect_trends(analysis)
        grouped_summary = SemanticTrendDetector.group_by_category(top_tags)
        trends = f"[Fallback] Semantic Trend Detection:\n{grouped_summary}"

    logger.info(f"Extracted trends:\n{trends}")
    return {**state, "aggregated_trends": trends}


