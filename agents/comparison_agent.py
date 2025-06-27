from typing import Dict, List
from tools.comparison_tool import run_comparison_tool

def run(state: Dict) -> Dict:
    current_analysis = state.get("anaylsis_result", "")
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
    return state

