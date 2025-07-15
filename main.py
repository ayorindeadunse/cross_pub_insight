import os
os.environ["GGML_METAL_LOG_LEVEL"] = "0"

import sys
import json
from unittest import result
import uuid 
from tools.repo_parser import parse_repository, condense_repo_summary
from agents.project_analyzer import ProjectAnalyzerAgent
from orchestrator.orchestrator import CrossPublicationInsightOrchestrator
from agents.trend_aggregator import run as aggregate_trends
from agents.summarize_agent import SummarizeAgent
from utils.logger import get_logger
from utils.repo_utils import clone_if_remote 
from utils.config_loader import load_config

logger = get_logger(__name__)

def run_orchestration(repo_path, comparison_repo_path, config_override=None):
    logger.info("Running Orchestrator test...")

    orchestrator = CrossPublicationInsightOrchestrator()
    thread_id = str(uuid.uuid4())

    # Analyze main repo
    initial_state = {"repo_path": repo_path}
    config = config_override or {"configurable": {"thread_id": thread_id}}

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

    cfg = load_config()
    if cfg.get("hitl", {}).get("enabled", False):
        logger.info("⚠️  HITL intervention is enabled — you may be prompted to review before final summary.")

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
        args = sys.argv[1:]

        if not args or len(args) < 2:
            print(" Please provide at least one primary and one comparison repo.")
            print(" Usage: python3 main.py <primary_repo> <comparison_repo1> [comparison_repo2] ...")
            sys.exit(1)
        
        # Detect and remove --no-hitl flag
        use_hitl = True
        if "--no-hitl" in args:
            use_hitl = False
            args.remove("==no-hitl")
        
        # Clone or resolve all input repos 
        local_repo_paths = [clone_if_remote(repo) for repo in args]

        repo_path = local_repo_paths[0] #primary repo
        comparison_repo_paths = local_repo_paths[1:] #seconday repo

        logger.info(f"Starting analysis for primary repo: {repo_path}")
        primary_summary = parse_repository(repo_path)
        condensed = condense_repo_summary(primary_summary)

       # print("\n===== PRIMARY REPOSITORY SUMMARY =====\n")
       # print(json.dumps(primary_summary, indent=2))
        print("\n===== CONDENSED (LLM) SUMMARY =====\n")
        print(condensed)

        # Loop over comparison repos
        for comparison_repo_path in comparison_repo_paths:
            print(f"\n=== 🔄 Comparing PRIMARY: {repo_path} WITH: {comparison_repo_path} ===\n")

            config_override = {
                "configurable": {"thread_id": str(uuid.uuid4())},
                "hitl_override": {"enabled": use_hitl}
            }

            run_orchestration(repo_path, comparison_repo_path, config_override)
    except Exception as e:
        logger.exception(f"An error occurred during execution: {e}")

if __name__ == "__main__":
    main()
