from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from uuid import uuid4
from typing import List, Optional, Dict
import asyncio

from utils.logger import get_logger
from orchestrator.orchestrator import CrossPublicationInsightOrchestrator
from agents.project_analyzer import ProjectAnalyzerAgent
from agents.trend_aggregator import run as aggregate_trends
from tools.repo_parser import parse_repository, condense_repo_summary
from utils.repo_utils import clone_if_remote

logger = get_logger(__name__)

session_store: Dict[str, Dict] = {}

app = FastAPI()

class RepoRequest(BaseModel):
    primary_repo: str
    comparison_repos: List[str]
    user_query: Optional[str] = ""
    use_hitl: Optional[bool] = True

def run_orchestration(session_id, repo_path, comparison_repo_paths, user_query="", use_hitl=True):
    logger.info("Running Orchestrator...")


    thread_id = str(uuid4())
    config_override = {
        "configurable": {"thread_id": thread_id},
        "hitl_override": {"enabled": use_hitl}
    }

    local_repo_paths = [clone_if_remote(repo) for repo in [repo_path] + comparison_repo_paths]
    repo_path = local_repo_paths[0]
    comparison_repo_paths = local_repo_paths[1:]

    comparison_target_states = []
    for comparison_repo_path in comparison_repo_paths:
        comparison_analyzer = ProjectAnalyzerAgent(llm_type="local")
        comparison_analysis = comparison_analyzer.analyze_project(comparison_repo_path)
        trend_input = {
            "repo_path": comparison_repo_path,
            "analysis_result": comparison_analysis
        }
        trend_result = aggregate_trends(trend_input)
        comparison_target_states.append({
            "repo_path": comparison_repo_path,
            "analysis_result": comparison_analysis,
            "aggregated_trends": trend_result["aggregated_trends"]
        })

    orchestrator = CrossPublicationInsightOrchestrator(user_query=user_query)

    results = []
    for comparison_target in comparison_target_states:
        initial_state = {
            "repo_path": repo_path,
            "comparison_target": comparison_target,
            "user_query": user_query.strip()
        }
        result = orchestrator.run(initial_state, config=config_override)
        results.append({
            "comparison_repo": comparison_target["repo_path"],
            "analysis_result": result.get("analysis_result","No analysis result found"),
            "fact_check_result": result.get("fact_check_result", "No fact check result found."),
            "aggregate_query_result": result.get("aggregate_query_result", "No aggregate query generated."),
            "final_summary": result.get("final_summary", "No summary generated.")
        })

    logger.info(f"Complete Analysis result: {results}")
    session_store[session_id] = {
        "status": "completed",
        "results": results
    }

@app.post("/run-analysis/")
async def run_analysis(request: RepoRequest, background_tasks: BackgroundTasks):
    session_id = str(uuid4())
    session_store[session_id] = {"status": "processing", "results": []}
    background_tasks.add_task(run_orchestration, session_id, request.primary_repo, request.comparison_repos, request.user_query, request.use_hitl)
    return {"session_id": session_id, "status": "processing"}

@app.get("/results/{session_id}")
async def get_results(session_id: str):
    return session_store.get(session_id, {"status": "not_found"})
