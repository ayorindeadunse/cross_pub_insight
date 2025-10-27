from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from uuid import uuid4
from typing import List, Optional, Dict
import asyncio
from datetime import datetime
import traceback

from utils.logger import get_logger
from orchestrator.orchestrator import CrossPublicationInsightOrchestrator
from agents.project_analyzer import ProjectAnalyzerAgent
from agents.trend_aggregator import run as aggregate_trends
from tools.repo_parser import parse_repository, condense_repo_summary
from utils.repo_utils import clone_if_remote

# Import our enhanced models and security
from api.models import RepoRequest, AnalysisResponse, AnalysisResult, HealthCheckResponse
from api.security import setup_security_middleware

logger = get_logger(__name__)

session_store: Dict[str, Dict] = {}

# Initialize FastAPI app with enhanced configuration
app = FastAPI(
    title="Cross Publication Insight Assistant API",
    description="Multi-agent system for analyzing and comparing AI/ML repositories",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Setup security middleware
setup_security_middleware(app, rate_limit_requests=100, rate_limit_window=3600)

# Remove the old RepoRequest class as it's now in models.py

def run_orchestration(session_id, repo_path, comparison_repo_paths, user_query="", use_hitl=False):
    """Enhanced orchestration with proper error handling and logging"""
    logger.info(f"Running Orchestrator for session {session_id}...")
    
    try:
        # Update session status
        session_store[session_id]["status"] = "processing"
        session_store[session_id]["timestamp"] = datetime.now().isoformat()
        
        thread_id = str(uuid4())
        config_override = {
            "configurable": {"thread_id": thread_id},
            "hitl_override": {"enabled": use_hitl}
        }

        # Clone repositories with error handling
        try:
            local_repo_paths = [clone_if_remote(repo) for repo in [repo_path] + comparison_repo_paths]
            repo_path = local_repo_paths[0]
            comparison_repo_paths = local_repo_paths[1:]
        except Exception as e:
            logger.error(f"Failed to clone repositories: {str(e)}")
            session_store[session_id]["status"] = "failed"
            session_store[session_id]["error"] = f"Repository cloning failed: {str(e)}"
            return

        comparison_target_states = []
        for comparison_repo_path in comparison_repo_paths:
            try:
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
            except Exception as e:
                logger.error(f"Failed to analyze repository {comparison_repo_path}: {str(e)}")
                # Continue with other repositories, but log the failure
                comparison_target_states.append({
                    "repo_path": comparison_repo_path,
                    "analysis_result": f"Analysis failed: {str(e)}",
                    "aggregated_trends": []
                })

        # Run orchestration with error handling
        try:
            orchestrator = CrossPublicationInsightOrchestrator(user_query=user_query)

            results = []
            for comparison_target in comparison_target_states:
                try:
                    initial_state = {
                        "repo_path": repo_path,
                        "comparison_target": comparison_target,
                        "user_query": user_query.strip()
                    }
                    result = orchestrator.run(initial_state, config=config_override)
                    results.append({
                        "comparison_repo": comparison_target["repo_path"],
                        "analysis_result": result.get("analysis_result", "No analysis result found"),
                        "fact_check_result": result.get("fact_check_result", "No fact check result found."),
                        "aggregate_query_result": result.get("aggregate_query_result", "No aggregate query generated."),
                        "final_summary": result.get("final_summary", "No summary generated.")
                    })
                except Exception as e:
                    logger.error(f"Orchestration failed for comparison {comparison_target['repo_path']}: {str(e)}")
                    results.append({
                        "comparison_repo": comparison_target["repo_path"],
                        "analysis_result": f"Orchestration failed: {str(e)}",
                        "fact_check_result": "Skipped due to analysis failure",
                        "aggregate_query_result": "Skipped due to analysis failure",
                        "final_summary": "Analysis could not be completed due to errors"
                    })

            logger.info(f"Complete Analysis result: {results}")
            session_store[session_id] = {
                "status": "completed",
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Orchestration setup failed: {str(e)}")
            session_store[session_id] = {
                "status": "failed",
                "error": f"Orchestration failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    except Exception as e:
        logger.error(f"Unexpected error in orchestration: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        session_store[session_id] = {
            "status": "failed",
            "error": f"Unexpected error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


# Enhanced API endpoints with proper error handling
@app.post("/run-analysis/", response_model=AnalysisResponse)
async def run_analysis(request: RepoRequest, background_tasks: BackgroundTasks):
    """
    Start repository analysis with enhanced validation and error handling.
    """
    try:
        session_id = str(uuid4())
        session_store[session_id] = {
            "status": "processing", 
            "results": [],
            "timestamp": datetime.now().isoformat(),
            "request": request.model_dump()
        }
        
        background_tasks.add_task(
            run_orchestration, 
            session_id, 
            request.primary_repo, 
            request.comparison_repos, 
            request.user_query, 
            request.use_hitl
        )
        
        logger.info(f"Started analysis session {session_id}")
        
        return AnalysisResponse(
            session_id=session_id,
            status="processing",
            message="Analysis started successfully",
            timestamp=datetime.now().isoformat()
        )
        
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Validation failed",
                "message": "Invalid input data",
                "details": e.errors()
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error starting analysis: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": "Failed to start analysis",
                "details": str(e)
            }
        )


@app.get("/results/{session_id}", response_model=AnalysisResult)
async def get_results(session_id: str):
    """
    Get analysis results with enhanced error handling.
    """
    try:
        if session_id not in session_store:
            return AnalysisResult(
                session_id=session_id,
                status="not_found",
                error="Session not found",
                timestamp=datetime.now().isoformat()
            )
        
        session_data = session_store[session_id]
        
        return AnalysisResult(
            session_id=session_id,
            status=session_data.get("status", "unknown"),
            results=session_data.get("results"),
            error=session_data.get("error"),
            timestamp=session_data.get("timestamp", datetime.now().isoformat())
        )
        
    except Exception as e:
        logger.error(f"Error retrieving results for session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to retrieve results",
                "message": str(e)
            }
        )


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint with dependency status.
    """
    try:
        # Basic health checks
        dependencies = {
            "session_store": "healthy",
            "logging": "healthy"
        }
        
        # Could add more sophisticated checks here:
        # - Database connectivity
        # - LLM service status
        # - File system access
        
        return HealthCheckResponse(
            status="healthy",
            version="1.0.0",
            timestamp=datetime.now().isoformat(),
            dependencies=dependencies
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthCheckResponse(
            status="unhealthy",
            version="1.0.0",
            timestamp=datetime.now().isoformat(),
            dependencies={"error": str(e)}
        )


@app.get("/")
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "message": "Cross Publication Insight Assistant API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "timestamp": datetime.now().isoformat()
    }
