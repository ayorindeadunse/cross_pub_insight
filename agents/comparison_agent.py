import os
os.environ["GGML_METAL_LOG_LEVEL"] = "0"

from typing import Dict, List
from utils.logger import get_logger
from tools.comparison_tool import run_comparison_tool

logger = get_logger(__name__)

def run(state: Dict) -> Dict:
    current_analysis = state.get("analysis_result", "")
    current_trends = state.get("aggregated_trends", "")
    comparison = state.get("comparison_target", "")

    if not comparison:
        state["comparison_result"] = "No comparison target provided"
        return state
    
    comparison_analysis = comparison.get("analysis_result", "")
    comparison_trends = comparison.get("aggregated_trends", "")

    result = run_comparison_tool(
        current_analysis=current_analysis,
        current_trends=current_trends,
        comparison_analysis=comparison_analysis,
        comparison_trends=comparison_trends
    )

    state["comparison_result"] = result
    logger.info(f"Comparison result:\n: + {result}")
    return state

