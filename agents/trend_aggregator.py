from tools.semantic_trend_detector import SemanticTrendDetector

detector = SemanticTrendDetector()

def run(state: dict) -> dict:
    analysis_text = state.get("analysis_result", "")

    if not analysis_text:
        return {**state, "aggregated_trends": "No project analysis result available"}
    
    # Detect semantic trends
    top_tags = detector.detect_trends(analysis_text)

    # Format output
    trends_summary = "Detected Trends:\n" + "\n".join(f"- {tag}" for tag in top_tags)
    return {**state, "aggregated_trends": trends_summary}
   
   