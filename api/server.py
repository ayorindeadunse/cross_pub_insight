from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from uuid import uuid4
from typing import List, Optional, Dict
import asyncio
from datetime import datetime
import traceback

from utils.logger import get_logger
from utils.structured_logger import get_structured_logger, LogContext, ComponentType, PerformanceMetrics
from utils.simple_monitoring import get_monitoring_system, HealthStatus
from orchestrator.orchestrator import CrossPublicationInsightOrchestrator
from agents.project_analyzer import ProjectAnalyzerAgent
from agents.trend_aggregator import run as aggregate_trends
from tools.repo_parser import parse_repository, condense_repo_summary
from utils.repo_utils import clone_if_remote

# Import our enhanced models and security
from api.models import (
    RepoRequest, AnalysisResponse, AnalysisResult, HealthCheckResponse,
    MonitoringHealthResponse, MonitoringMetricsResponse, MonitoringSummaryResponse
)
from api.security import setup_security_middleware

logger = get_logger(__name__)
structured_logger = get_structured_logger("api")
monitoring_system = get_monitoring_system()

session_store: Dict[str, Dict] = {}

# Initialize FastAPI app with enhanced configuration
app = FastAPI(
    title="Cross Publication Insight Assistant API",
    description="Multi-agent system for analyzing and comparing AI/ML repositories with production monitoring",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for Blazor frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "https://localhost:5001", "http://127.0.0.1:5000", "https://127.0.0.1:5001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


def run_orchestration_with_monitoring(session_id, repo_path, comparison_repo_paths, user_query="", use_hitl=False, request_session_id=None):
    """Enhanced orchestration with comprehensive monitoring and structured logging"""
    context = LogContext(
        session_id=request_session_id or session_id,
        component=ComponentType.ORCHESTRATOR,
        operation="run_orchestration",
        repo_path=repo_path
    )
    
    operation_start = datetime.now()
    
    try:
        with structured_logger.operation_context("run_orchestration", ComponentType.ORCHESTRATOR, context) as (op_context, metrics):
            structured_logger.info(
                f"Starting enhanced orchestration for session {session_id}",
                context=op_context,
                extra_data={
                    "repo_path": repo_path,
                    "comparison_repos_count": len(comparison_repo_paths),
                    "user_query_length": len(user_query),
                    "use_hitl": use_hitl
                }
            )
            
            # Run the existing orchestration logic but with monitoring
            run_orchestration(session_id, repo_path, comparison_repo_paths, user_query, use_hitl)
            
            # Calculate total duration
            total_duration = (datetime.now() - operation_start).total_seconds() * 1000
            
            # Check if session completed successfully
            session_data = session_store.get(session_id, {})
            success = session_data.get("status") == "completed"
            
            structured_logger.info(
                f"Orchestration {'completed' if success else 'failed'} for session {session_id}",
                context=op_context,
                extra_data={
                    "total_duration_ms": total_duration,
                    "session_status": session_data.get("status"),
                    "has_results": "results" in session_data
                }
            )
            
            # Record orchestration metrics
            monitoring_system.record_operation_metrics(
                "run_orchestration",
                "orchestrator",
                total_duration,
                success
            )
            
    except Exception as e:
        # Calculate duration even for failures
        total_duration = (datetime.now() - operation_start).total_seconds() * 1000
        
        structured_logger.error(
            f"Enhanced orchestration failed for session {session_id}",
            context=context,
            exception=e,
            extra_data={
                "total_duration_ms": total_duration,
                "repo_path": repo_path,
                "error_type": type(e).__name__
            }
        )
        
        # Record failed orchestration
        monitoring_system.record_operation_metrics(
            "run_orchestration",
            "orchestrator",
            total_duration,
            False
        )


# Enhanced API endpoints with proper error handling
@app.post("/run-analysis/", response_model=AnalysisResponse)
async def run_analysis(request: RepoRequest, background_tasks: BackgroundTasks):
    """
    Start repository analysis with enhanced validation, monitoring, and structured logging.
    """
    session_id = str(uuid4())
    request_context = LogContext(
        session_id=session_id,
        request_id=str(uuid4()),
        component=ComponentType.API,
        operation="run_analysis",
        repo_path=request.primary_repo
    )
    
    try:
        with structured_logger.operation_context("run_analysis", ComponentType.API, request_context) as (context, metrics):
            # Initialize session
            session_store[session_id] = {
                "status": "processing", 
                "results": [],
                "timestamp": datetime.now().isoformat(),
                "request": request.model_dump()
            }
            
            structured_logger.info(
                f"Starting analysis for session {session_id}",
                context=context,
                extra_data={
                    "primary_repo": request.primary_repo,
                    "comparison_repos_count": len(request.comparison_repos),
                    "has_user_query": bool(request.user_query),
                    "use_hitl": request.use_hitl
                }
            )
            
            # Add background task with monitoring
            background_tasks.add_task(
                run_orchestration_with_monitoring, 
                session_id, 
                request.primary_repo, 
                request.comparison_repos, 
                request.user_query, 
                request.use_hitl,
                context.session_id
            )
            
            # Record successful API call
            monitoring_system.record_operation_metrics(
                "run_analysis",
                "api",
                metrics.duration_ms or 0,
                True
            )
            
            return AnalysisResponse(
                session_id=session_id,
                status="processing",
                message="Analysis started successfully",
                timestamp=datetime.now().isoformat()
            )
        
    except ValidationError as e:
        structured_logger.error(
            "Validation error in analysis request",
            context=request_context,
            exception=e,
            extra_data={"validation_errors": e.errors()}
        )
        
        # Record failed API call
        monitoring_system.record_operation_metrics(
            "run_analysis",
            "api",
            0,
            False
        )
        
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Validation failed",
                "message": "Invalid input data",
                "details": e.errors(),
                "session_id": session_id
            }
        )
    except Exception as e:
        structured_logger.error(
            "Unexpected error starting analysis",
            context=request_context,
            exception=e
        )
        
        # Record failed API call
        monitoring_system.record_operation_metrics(
            "run_analysis",
            "api",
            0,
            False
        )
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": "Failed to start analysis",
                "details": str(e),
                "session_id": session_id
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
@app.get("/health/", response_model=HealthCheckResponse)
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


@app.get("/monitoring/health", response_model=MonitoringHealthResponse)
async def detailed_health_check():
    """
    Comprehensive health check with system monitoring.
    """
    try:
        with structured_logger.operation_context("detailed_health_check", ComponentType.API) as (context, metrics):
            # Run comprehensive health checks
            health_results = await monitoring_system.run_health_checks()
            
            # Get system metrics
            system_metrics = await monitoring_system.get_system_metrics()
            
            # Determine overall status
            overall_status = HealthStatus.HEALTHY
            for result in health_results.values():
                if result.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                    break
                elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
            
            # Convert health results to proper dict format
            health_checks_dict = {}
            for name, result in health_results.items():
                health_checks_dict[name] = {
                    "status": result.status.value,
                    "component": result.component,
                    "response_time_ms": result.response_time_ms,
                    "timestamp": result.timestamp.isoformat(),
                    "details": result.details,
                    "error": result.error
                }
            
            response_data = MonitoringHealthResponse(
                status=overall_status.value,
                timestamp=datetime.now().isoformat(),
                version="1.0.0",
                health_checks=health_checks_dict,
                system_metrics=system_metrics,
                uptime_seconds=(datetime.utcnow() - monitoring_system.start_time).total_seconds()
            )
            
            # Record monitoring metrics
            monitoring_system.record_operation_metrics(
                "detailed_health_check",
                "api",
                metrics.duration_ms or 0,
                True
            )
            
            return response_data
    
    except Exception as e:
        structured_logger.error(
            "Detailed health check failed",
            context=LogContext(component=ComponentType.API, operation="detailed_health_check"),
            exception=e
        )
        # Return error response with proper model
        return MonitoringHealthResponse(
            status="unhealthy",
            timestamp=datetime.now().isoformat(),
            version="1.0.0",
            health_checks={},
            system_metrics={},
            uptime_seconds=0.0
        )


@app.get("/monitoring/metrics", response_model=MonitoringMetricsResponse)
async def get_metrics():
    """
    Get operation and performance metrics.
    """
    try:
        with structured_logger.operation_context("get_metrics", ComponentType.API) as (context, metrics):
            operation_metrics = monitoring_system.get_operation_metrics()
            
            monitoring_system.record_operation_metrics(
                "get_metrics",
                "api", 
                metrics.duration_ms or 0,
                True
            )
            
            # Return properly structured response
            return MonitoringMetricsResponse(
                timestamp=datetime.now().isoformat(),
                memory_usage=operation_metrics.get("memory_usage", {}),
                operation_counts=operation_metrics.get("operation_counts", {}),
                response_times=operation_metrics.get("response_times", {}),
                error_rates=operation_metrics.get("error_rates", {})
            )
    
    except Exception as e:
        structured_logger.error(
            "Failed to get metrics",
            context=LogContext(component=ComponentType.API, operation="get_metrics"),
            exception=e
        )
        # Return error with proper model
        return MonitoringMetricsResponse(
            timestamp=datetime.now().isoformat(),
            memory_usage={},
            operation_counts={},
            response_times={},
            error_rates={"get_metrics": 1.0}
        )


@app.get("/monitoring/summary", response_model=MonitoringSummaryResponse)
async def get_monitoring_summary():
    """
    Get comprehensive monitoring summary including health, metrics, and alerts.
    """
    try:
        with structured_logger.operation_context("get_monitoring_summary", ComponentType.API) as (context, metrics):
            summary = await monitoring_system.get_monitoring_summary()
            
            monitoring_system.record_operation_metrics(
                "get_monitoring_summary",
                "api",
                metrics.duration_ms or 0,
                True
            )
            
            # Return properly structured response
            return MonitoringSummaryResponse(
                timestamp=datetime.now().isoformat(),
                overall_status=summary.get("overall_status", "unknown"),
                total_operations=summary.get("total_operations", 0),
                avg_response_time=summary.get("avg_response_time", 0.0),
                error_rate=summary.get("error_rate", 0.0),
                uptime_seconds=summary.get("uptime_seconds", 0.0),
                health_summary=summary.get("health_summary", {})
            )
    
    except Exception as e:
        structured_logger.error(
            "Failed to get monitoring summary",
            context=LogContext(component=ComponentType.API, operation="get_monitoring_summary"),
            exception=e
        )
        # Return error with proper model
        return MonitoringSummaryResponse(
            timestamp=datetime.now().isoformat(),
            overall_status="unhealthy",
            total_operations=0,
            avg_response_time=0.0,
            error_rate=1.0,
            uptime_seconds=0.0,
            health_summary={}
        )


@app.get("/monitoring/alerts")
async def get_alerts():
    """
    Get recent alerts and notifications.
    """
    try:
        with structured_logger.operation_context("get_alerts", ComponentType.API) as (context, metrics):
            alerts = list(monitoring_system.alerts)
            
            monitoring_system.record_operation_metrics(
                "get_alerts",
                "api",
                metrics.duration_ms or 0,
                True
            )
            
            return JSONResponse(content={
                "timestamp": datetime.now().isoformat(),
                "alerts": alerts,
                "total_alerts": len(alerts)
            })
    
    except Exception as e:
        structured_logger.error(
            "Failed to get alerts",
            context=LogContext(component=ComponentType.API, operation="get_alerts"),
            exception=e
        )
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
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
        "monitoring": {
            "detailed_health": "/monitoring/health",
            "metrics": "/monitoring/metrics", 
            "summary": "/monitoring/summary",
            "alerts": "/monitoring/alerts"
        },
        "timestamp": datetime.now().isoformat()
    }
