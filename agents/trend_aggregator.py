import os
os.environ["GGML_METAL_LOG_LEVEL"] = "0"

from tools.semantic_trend_detector import SemanticTrendDetector

detector = SemanticTrendDetector()

def run(state: dict) -> dict:
    analysis_text = state.get("analysis_result", "")

    if not analysis_text:
        return {**state, "aggregated_trends": "No project analysis result available"}
    
    
    # Detect semantic trends
    top_tags = detector.detect_trends(analysis_text)

    grouped_summary = SemanticTrendDetector.group_by_category(top_tags)
    trends_summary = f"Detected Trends:\n{grouped_summary}"
    
    return {**state, "aggregated_trends": trends_summary}
   
   