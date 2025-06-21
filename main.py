from agents.project_analyzer import ProjectAnalyzerAgent
from utils.logger import get_logger

logger = get_logger()

def main():
    try:
        agent = ProjectAnalyzerAgent(llm_type="local")
        repo_path = "path/to/repository"  # <- Update this with your actual repository path
        logger.info(f"Starting analysis for repository at: {repo_path}")

        analysis = agent.analyze_project(repo_path)
        print("\n===== PROJECT ANALYSIS =====\n")
        print(analysis)

    except Exception as e:
        logger.exception(f"An error occurred during project analysis: {e}")

if __name__ == "__main__":
    main()