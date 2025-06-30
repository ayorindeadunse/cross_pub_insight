import os
import json
import uuid 
from tools.repo_parser import parse_repository, condense_repo_summary
from agents.project_analyzer import ProjectAnalyzerAgent
from orchestrator.orchestrator import CrossPublicationInsightOrchestrator
from agents.trend_aggregator import run as aggregate_trends
from agents.summarize_agent import SummarizeAgent
from utils.logger import get_logger

logger = get_logger()

def run_project_analyzer_test(repo_path):
    logger.info("Running Project Analyzer Agent test...")
    agent = ProjectAnalyzerAgent(llm_type="local")
    analysis = agent.analyze_project(repo_path)

    print("\n===== PROJECT ANALYSIS =====\n")
    print(analysis)

def run_aggregate_trends_and_comparison_test(repo_path, comparison_repo_path):
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

    print("\n===== AGGREGATE TRENDS AND REPO COMPARISON RESULT =====\n")
    print(json.dumps(result, indent=2))

def generate_project_summary(repo_path, comparison_repo_path):
    logger.info("Running Summarize Agent test...")

    # Step 1: Analyze target repo
    analyzer = ProjectAnalyzerAgent(llm_type="local")
    analysis_result = analyzer.analyze_project(repo_path)

    # Step 2: Aggregate trends
    trend_result = aggregate_trends({
        "repo_path": repo_path,
        "analysis_result": analysis_result
    })

    # Step 3: Analyze comparison project
    comparison_analysis = analyzer.analyze_project(comparison_repo_path)

    # Step 4: Assemble state
    state = {
        "repo_path": repo_path,
        "analysis_result": analysis_result,
        "aggregated_trends": trend_result["aggregated_trends"],
        "comparison_result": comparison_analysis
    }

    # Step 5: Run summarization
    agent = SummarizeAgent(llm_type="local")
    updated_state = agent.run(state)

    # Step 6: Output summary
    print("\n===== FINAL PROJECT SUMMARY =====\n")
    print(updated_state["final_summary"])

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

        # Run tests: The first two are run in generate_project_summary, so unless you still want to debug those two function, comment these out for now
       # run_project_analyzer_test(repo_path)
      #  run_aggregate_trends_and_comparison_test(repo_path, comparison_repo_path)
        generate_project_summary(repo_path, comparison_repo_path)

    except Exception as e:
        logger.exception(f"An error occurred during the test: {e}")

if __name__ == "__main__":
    main()
