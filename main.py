import os
from agents.project_analyzer import ProjectAnalyzerAgent
from utils.logger import get_logger

logger = get_logger()

def main():
    try:
        repo_name = "LangGraphBotDocIngestor"
        repo_path = os.path.expanduser(f"~/projects/{repo_name}")

        logger.info(f"Starting analysis for repository at: {repo_path}")

        agent = ProjectAnalyzerAgent(llm_type="local")
        analysis = agent.analyze_project(repo_path)
        print("\n===== PROJECT ANALYSIS =====\n")
        print(analysis)

    except Exception as e:
        logger.exception(f"An error occurred during project analysis: {e}")

if __name__ == "__main__":
    main()