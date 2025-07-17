import os
os.environ["GGML_METAL_LOG_LEVEL"] = "0"

import sys
import json
import uuid

from tools.repo_parser import parse_repository, condense_repo_summary
from agents.project_analyzer import ProjectAnalyzerAgent
from orchestrator.orchestrator import CrossPublicationInsightOrchestrator
from agents.trend_aggregator import run as aggregate_trends
from utils.logger import get_logger
from utils.repo_utils import clone_if_remote
from utils.config_loader import load_config

logger = get_logger(__name__)

def run_orchestration(repo_path, comparison_repo_path,  user_query="", use_hitl=True):
    logger.info("Running Orchestrator...")

    thread_id = str(uuid.uuid4())
    config_override = {
        "configurable": {"thread_id":thread_id},
        "hitl_override": {"enabled":use_hitl}
    }

    # Analyze comparison repo
    comparison_analyzer = ProjectAnalyzerAgent(llm_type="local")
    comparison_analysis = comparison_analyzer.analyze_project(comparison_repo_path)

    # Aggregate trends for comparison. repo
    trend_input = {
        "repo_path": comparison_repo_path,
        "analysis_result": comparison_analysis
    }
    trend_result = aggregate_trends(trend_input)

    comparison_target_state = {
        "repo_path": comparison_repo_path,
        "analysis_result":comparison_analysis,
        "aggregated_trends": trend_result["aggregated_trends"]
    }

    # Build orchestration input
    initial_state = {
        "repo_path":repo_path,
        "comparison_target":comparison_target_state,
        "user_query":user_query.strip()
    }

    # Initialize orchestrator
    orchestrator = CrossPublicationInsightOrchestrator(user_query=user_query)
    result = orchestrator.run(initial_state, config=config_override)

    # Display results
    print("\n=====FACT CHECK RESULT =====\n")
    print(result.get("fact_check_result",  "No fact check result found."))

    if user_query:
        print("\n===== AGGREGATE QUERY RESULT ====== \n")
        print(result.get("aggregate_query_result", "No aggregate query generated."))
    
    print("\n===== FINAL PROJECT SUMMARY ======\n")
    print(result.get("final_summary", "No summary generated."))

def main():
    try:
        args = sys.argv[1:]

        if not args or len(args) < 2:
            print("Usage: python3 main.py <primary_repo> <comparison_repo1> [comparison_repo2...] [--query 'your question'] [--no-hitl]")
            sys.exit(1)
        
        use_hitl = True
        user_query = ""

        # Parse CLI flags
        if "--no-hitl" in args:
            use_hitl = False
            args.remove("--no-hitl")
        
        if "--query" in args:
            idx = args.index("--query")
            if idx + 1 < len(args):
                user_query = args[idx + 1]
                del args[idx:idx + 2]
            else:
                print("Error: --query flag. requires a string value.")
                sys.exit(1)
        
        # Resolve repositories
        local_repo_paths = [clone_if_remote(repo) for repo in args]
        repo_path = local_repo_paths[0]
        comparison_repo_paths = local_repo_paths[1:]

        # Display basic info
        logger.info(f"Starting analysis for primary repo: {repo_path}")
        primary_summary = parse_repository(repo_path)
        condensed = condense_repo_summary(primary_summary)

        print("\n===== CONDENSED (LLM) SUMMARY =====\n")
        print(condensed)

        # Compare with each secondary repo 
        for comparison_repo_path in comparison_repo_paths:
            print(f"\n=== Comparing PRIMARY: {repo_path} WITH: {comparison_repo_path} ===\n")
            run_orchestration(repo_path, comparison_repo_path, user_query=user_query, use_hitl=use_hitl)

    except Exception as e:
        logger.exception(f"An error occured during execution: {e}")


if __name__ == "__main__":
    main()