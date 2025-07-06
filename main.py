import os
import json
from unittest import result
import uuid 
from tools.repo_parser import parse_repository, condense_repo_summary
from agents.project_analyzer import ProjectAnalyzerAgent
from orchestrator.orchestrator import CrossPublicationInsightOrchestrator
from agents.trend_aggregator import run as aggregate_trends
from agents.summarize_agent import SummarizeAgent
from utils.logger import get_logger

logger = get_logger()

def run_orchestration(repo_path, comparison_repo_path):
    logger.info("Running Orchestrator test...")

    orchestrator = CrossPublicationInsightOrchestrator()
    thread_id = str(uuid.uuid4())

    # Analyze main repo
    initial_state = {"repo_path": repo_path}
    config = {"configurable": {"thread_id": thread_id}}

    # Analyze comparison repo
    comparison_analyzer = ProjectAnalyzerAgent(llm_type="local")
    comparison_analysis = comparison_analyzer.analyze_project(comparison_repo_path)

    # Aggregate trends for comparison repo
    trend_input = {
        "repo_path": comparison_repo_path,
        "analysis_result": comparison_analysis
    }
    trend_result = aggregate_trends(trend_input)

    # Build comparison state
    comparison_target_state = {
        "repo_path": comparison_repo_path,
        "analysis_result": comparison_analysis,
        "aggregated_trends": trend_result["aggregated_trends"]
    }

    # Add comparison_target into orchestrator's initial state
    initial_state["comparison_target"] = comparison_target_state

    # Run orchestrator
    result = orchestrator.run(initial_state, config=config)

    # 🔍 FACT CHECK RESULT LOGGING
    print("\n===== 🧪 FACT CHECK RESULT =====\n")
    print(result.get("fact_check_result", "No fact check result found."))

    print("\n===== CPIA ORCHESTRATION OUTPUT (Raw JSON) =====\n")
    print(json.dumps(result, indent=2))  # keep if you still want raw log

    print("\n===== 📘 FINAL PROJECT SUMMARY =====\n")
    print(result.get("final_summary", "No summary generated."))

def main():
    try:
        # Target repo
        repo_name = "LangGraphBotDocIngestor"
        repo_path = os.path.expanduser(f"~/projects/{repo_name}")

        # Comparison repo
        comparison_repo_name = "gemini-cli-main"
        comparison_repo_path = os.path.expanduser(f"~/projects/{comparison_repo_name}")

        logger.info(f"Starting repository parsing test for: {repo_path}")

        # Parse Repository
        repo_summary = parse_repository(repo_path)
        print("\n===== REPOSITORY SUMMARY =====\n")
        print(json.dumps(repo_summary, indent=2))

        # Condense summary for LLM input
        condensed = condense_repo_summary(repo_summary)

        print("\n===== CONDENSED REPOSITORY SUMMARY (LLM INPUT) =====\n")
        print(condensed)

        run_orchestration(repo_path, comparison_repo_path)

    except Exception as e:
        logger.exception(f"An error occurred during the test: {e}")

if __name__ == "__main__":
    main()
