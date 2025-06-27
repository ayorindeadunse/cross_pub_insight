from typing import Dict
from utils.comparison import compare_trends, summarize_difference

def run_comparison_tool(
    current_analysis: str,
    current_trends: str,
    comparison_analysis: str,
    comparison_trends: str
) -> str:
    analysis_diff = summarize_difference(current_analysis, comparison_analysis)
    trend_diff = compare_trends(current_trends, comparison_trends)
    shared = ', '.join(trend_diff["shared"]) or "None"
    only_current = ', '.join(trend_diff["only_in_a"]) or "None"
    only_comparison = ', '.join(trend_diff["only_in_b"]) or "None"

    return (
        f"{analysis_diff}\n\n"
        f"**Trend Comparison**:\n"
        f"- Shared trends: {shared}\n"
        f"- Unique to current project: {only_current}\n"
        f"- Unique to comparison project: {only_comparison}\n"
    )