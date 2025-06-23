import os
import json
from tools.repo_parser import parse_repository, condense_repo_summary
from agents.project_analyzer import ProjectAnalyzerAgent
from utils.logger import get_logger

logger = get_logger()

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

        # Run Project Analyzer Agent (LLM-based analysis)
        agent = ProjectAnalyzerAgent(llm_type="local")
        analysis = agent.analyze_project(repo_path)
        
        print("\n===== PROJECT ANALYSIS =====\n")
        print(analysis)

    except Exception as e:
        logger.exception(f"An error occurred during repository parsing test: {e}")

if __name__ == "__main__":
    main()
