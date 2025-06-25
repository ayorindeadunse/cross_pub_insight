import os
import json
import uuid 
from tools.repo_parser import parse_repository, condense_repo_summary
from agents.project_analyzer import ProjectAnalyzerAgent
from orchestrator.orchestrator import CrossPublicationInsightOrchestrator
from utils.logger import get_logger

logger = get_logger()

def run_project_analyzer_test(repo_path):
    logger.info("Running Project Analyzer Agent test...")
    agent = ProjectAnalyzerAgent(llm_type="local")
    analysis = agent.analyze_project(repo_path)

    print("\n===== PROJECT ANALYSIS =====\n")
    print(analysis)

def run_orchestrator_test(repo_path):
    logger.info("Running Orchestrator test...")
    orchestrator = CrossPublicationInsightOrchestrator()
   # initial_state = {"repository_path": repo_path}
    thread_id = str(uuid.uuid4())
    initial_state = {
        "repo_path": repo_path
    }

    config = {"configurable": {"thread_id": thread_id}}
    result = orchestrator.run(initial_state, config=config)

    print("\n===== ORCHESTRATION RESULT =====\n")
    print(json.dumps(result, indent=2))

def main():
    try:
        repo_name = "LangGraphBotDocIngestor"
        repo_path = os.path.expanduser(f"~/projects/{repo_name}")

        logger.info(f"Starting repository parsing test for: {repo_path}")

        # Parse Repository
        repo_summary = parse_repository(repo_path)
        print("\n===== REPOSITORY SUMMARY =====\n")
        print(json.dumps(repo_summary, indent=2))

        # Condense summary for LLM input
        condensed = condense_repo_summary(repo_summary)

        print("\n===== CONDENSED REPOSITORY SUMMARY (LLM INPUT) =====\n")
        print(condensed)

        # Run Project Analyser and Orchestration Tests)
        run_project_analyzer_test(repo_path)
        run_orchestrator_test(repo_path)

    except Exception as e:
        logger.exception(f"An error occurred during the test: {e}")

if __name__ == "__main__":
    main()
