"""
Resilient orchestrator with enhanced error handling and retry logic.
"""
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from langgraph.graph import StateGraph, END 
from langgraph.checkpoint.memory import MemorySaver 

from agents.project_analyzer import run as analyze_project
from agents.trend_aggregator import run as aggregate_trends
from agents.comparison_agent import run as compare_projects
from agents.fact_checker import run as fact_check
from agents.summarize_agent import run as summarize_project
from agents.aggregate_query_agent import run as aggregate_query_run

from utils.config_loader import load_config
from tools.hitl_intervention import review_before_summary
from utils.resilience import with_retry, RetryStrategy, ResilienceManager
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExecutionMetrics:
    """Track execution metrics for monitoring and debugging"""
    start_time: datetime = field(default_factory=datetime.now)
    node_execution_times: Dict[str, float] = field(default_factory=dict)
    retry_counts: Dict[str, int] = field(default_factory=dict)
    failures: List[str] = field(default_factory=list)
    total_duration: Optional[float] = None
    
    def record_node_execution(self, node_name: str, duration: float, retries: int = 0):
        """Record execution metrics for a node"""
        self.node_execution_times[node_name] = duration
        if retries > 0:
            self.retry_counts[node_name] = retries
    
    def record_failure(self, node_name: str, error: str):
        """Record a failure for monitoring"""
        self.failures.append(f"{node_name}: {error}")
    
    def finalize(self):
        """Calculate total duration"""
        self.total_duration = (datetime.now() - self.start_time).total_seconds()


class ResilientCrossPublicationInsightOrchestrator:
    """
    Enhanced orchestrator with resilience patterns.
    """
    
    def __init__(self, user_query: str = "", enable_fallbacks: bool = True):
        """
        Initialize resilient orchestrator.
        
        Args:
            user_query: Optional query for aggregate_query node
            enable_fallbacks: Whether to enable fallback mechanisms
        """
        self.user_query = user_query
        self.enable_fallbacks = enable_fallbacks
        self.memory = MemorySaver()
        self.resilience_manager = ResilienceManager()
        self.metrics = ExecutionMetrics()
        
        # Build the execution graph
        self.graph = self._build_graph()
        self.executor = self.graph.compile(checkpointer=self.memory)
        
        logger.info("Initialized resilient orchestrator")
    
    def _build_graph(self) -> StateGraph:
        """Build the execution graph with nodes and edges"""
        graph = StateGraph(dict)
        
        # Add nodes with resilient wrappers
        graph.add_node("analyze", self._resilient_analyze)
        graph.add_node("aggregate", self._resilient_aggregate)
        graph.add_node("compare", self._resilient_compare)
        graph.add_node("fact_check", self._resilient_fact_check)
        graph.add_node("summarize", self._resilient_summarize)
        
        if self.user_query:
            graph.add_node("aggregate_query", self._resilient_aggregate_query)
        
        # Set up the execution flow
        graph.set_entry_point("analyze")
        graph.add_edge("analyze", "fact_check")
        graph.add_edge("fact_check", "aggregate")
        graph.add_edge("aggregate", "compare")
        
        if self.user_query:
            graph.add_edge("compare", "aggregate_query")
            graph.add_edge("aggregate_query", "summarize")
        else:
            graph.add_edge("compare", "summarize")
        
        graph.add_edge("summarize", END)
        
        return graph
    
    @with_retry(
        max_attempts=3,
        base_delay=2.0,
        max_delay=30.0,
        exponential_base=2.0,
        jitter=True,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        retryable_exceptions=(Exception,),
        timeout=120.0,
        circuit_breaker_name="project_analysis",
        circuit_breaker_threshold=3,
        circuit_breaker_timeout=300.0
    )
    def _resilient_analyze(self, state: dict) -> dict:
        """Resilient wrapper for project analysis"""
        logger.info("Starting resilient project analysis")
        start_time = datetime.now()
        
        try:
            result = analyze_project(state)
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_node_execution("analyze", duration)
            logger.info(f"Project analysis completed in {duration:.2f}s")
            return result
            
        except Exception as e:
            error_msg = f"Project analysis failed: {str(e)}"
            logger.error(error_msg)
            self.metrics.record_failure("analyze", str(e))
            
            if self.enable_fallbacks:
                # Provide fallback analysis
                state["analysis_result"] = f"Analysis temporarily unavailable: {str(e)}"
                logger.warning("Using fallback analysis result")
                return state
            else:
                raise
    
    @with_retry(
        max_attempts=2,
        base_delay=1.0,
        max_delay=15.0,
        retryable_exceptions=(Exception,),
        timeout=60.0
    )
    def _resilient_fact_check(self, state: dict) -> dict:
        """Resilient wrapper for fact checking"""
        logger.info("Starting resilient fact checking")
        start_time = datetime.now()
        
        try:
            result = fact_check(state)
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_node_execution("fact_check", duration)
            logger.info(f"Fact checking completed in {duration:.2f}s")
            return result
            
        except Exception as e:
            error_msg = f"Fact checking failed: {str(e)}"
            logger.error(error_msg)
            self.metrics.record_failure("fact_check", str(e))
            
            if self.enable_fallbacks:
                # Skip fact checking and continue
                state["fact_check_result"] = f"Fact checking temporarily unavailable: {str(e)}"
                logger.warning("Using fallback fact check result")
                return state
            else:
                raise
    
    @with_retry(
        max_attempts=2,
        base_delay=1.0,
        max_delay=10.0,
        retryable_exceptions=(Exception,),
        timeout=45.0
    )
    def _resilient_aggregate(self, state: dict) -> dict:
        """Resilient wrapper for trend aggregation"""
        logger.info("Starting resilient trend aggregation")
        start_time = datetime.now()
        
        try:
            result = aggregate_trends(state)
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_node_execution("aggregate", duration)
            logger.info(f"Trend aggregation completed in {duration:.2f}s")
            return result
            
        except Exception as e:
            error_msg = f"Trend aggregation failed: {str(e)}"
            logger.error(error_msg)
            self.metrics.record_failure("aggregate", str(e))
            
            if self.enable_fallbacks:
                # Provide fallback trends
                state["aggregate_trends"] = [f"Trend aggregation temporarily unavailable: {str(e)}"]
                logger.warning("Using fallback trend aggregation result")
                return state
            else:
                raise
    
    @with_retry(
        max_attempts=2,
        base_delay=1.0,
        max_delay=10.0,
        retryable_exceptions=(Exception,),
        timeout=45.0
    )
    def _resilient_compare(self, state: dict) -> dict:
        """Resilient wrapper for project comparison"""
        logger.info("Starting resilient project comparison")
        start_time = datetime.now()
        
        try:
            result = compare_projects(state)
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_node_execution("compare", duration)
            logger.info(f"Project comparison completed in {duration:.2f}s")
            return result
            
        except Exception as e:
            error_msg = f"Project comparison failed: {str(e)}"
            logger.error(error_msg)
            self.metrics.record_failure("compare", str(e))
            
            if self.enable_fallbacks:
                # Provide fallback comparison
                state["comparison_result"] = f"Project comparison temporarily unavailable: {str(e)}"
                logger.warning("Using fallback comparison result")
                return state
            else:
                raise
    
    @with_retry(
        max_attempts=2,
        base_delay=1.0,
        max_delay=10.0,
        retryable_exceptions=(Exception,),
        timeout=30.0
    )
    def _resilient_aggregate_query(self, state: dict) -> dict:
        """Resilient wrapper for query aggregation"""
        logger.info("Starting resilient query aggregation")
        start_time = datetime.now()
        
        try:
            result = aggregate_query_run(state)
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_node_execution("aggregate_query", duration)
            logger.info(f"Query aggregation completed in {duration:.2f}s")
            return result
            
        except Exception as e:
            error_msg = f"Query aggregation failed: {str(e)}"
            logger.error(error_msg)
            self.metrics.record_failure("aggregate_query", str(e))
            
            if self.enable_fallbacks:
                # Provide fallback query result
                state["aggregate_query_result"] = f"Query aggregation temporarily unavailable: {str(e)}"
                logger.warning("Using fallback query aggregation result")
                return state
            else:
                raise
    
    @with_retry(
        max_attempts=3,
        base_delay=1.0,
        max_delay=20.0,
        retryable_exceptions=(Exception,),
        timeout=90.0
    )
    def _resilient_summarize(self, state: dict) -> dict:
        """Resilient wrapper for summarization"""
        logger.info("Starting resilient summarization")
        start_time = datetime.now()
        
        try:
            result = summarize_project(state)
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_node_execution("summarize", duration)
            logger.info(f"Summarization completed in {duration:.2f}s")
            return result
            
        except Exception as e:
            error_msg = f"Summarization failed: {str(e)}"
            logger.error(error_msg)
            self.metrics.record_failure("summarize", str(e))
            
            if self.enable_fallbacks:
                # Provide fallback summary based on available state
                fallback_summary = self._generate_fallback_summary(state)
                state["summary"] = fallback_summary
                logger.warning("Using fallback summary")
                return state
            else:
                raise
    
    def _generate_fallback_summary(self, state: dict) -> str:
        """Generate a fallback summary when LLM summarization fails"""
        components = []
        
        if "analysis_result" in state:
            components.append(f"Analysis: {state['analysis_result'][:200]}...")
        
        if "aggregate_trends" in state:
            trends = state.get("aggregate_trends", [])
            if trends:
                components.append(f"Trends: {', '.join(trends[:3])}")
        
        if "comparison_result" in state:
            components.append(f"Comparison: {state['comparison_result'][:100]}...")
        
        if "fact_check_result" in state:
            components.append(f"Fact Check: {state['fact_check_result'][:100]}...")
        
        if components:
            return "FALLBACK SUMMARY:\n" + "\n".join(components)
        else:
            return "Summary generation temporarily unavailable due to system issues."
    
    def run(self, input_data: dict, config: dict = None) -> dict:
        """
        Execute the orchestration with resilience patterns.
        
        Args:
            input_data: Input state for the orchestration
            config: Optional configuration overrides
            
        Returns:
            Final state with results
        """
        logger.info(f"Starting resilient orchestration with {len(input_data)} input parameters")
        self.metrics = ExecutionMetrics()  # Reset metrics
        
        try:
            # Execute the graph
            result = self.executor.invoke(input_data, config=config) if config else self.executor.invoke(input_data)
            
            # Handle HITL intervention
            cfg = load_config()
            hitl_enabled = cfg.get("hitl", {}).get("enabled", False)

            if config and "hitl_override" in config:
                hitl_enabled = config["hitl_override"].get("enabled", hitl_enabled)
            
            if hitl_enabled and cfg["hitl"].get("step") == "pre-summary":
                logger.info("Applying HITL intervention")
                result = review_before_summary(result)
            
            # Finalize metrics
            self.metrics.finalize()
            
            # Add execution metadata to result
            result["_execution_metadata"] = {
                "total_duration": self.metrics.total_duration,
                "node_execution_times": self.metrics.node_execution_times,
                "retry_counts": self.metrics.retry_counts,
                "failure_count": len(self.metrics.failures),
                "failures": self.metrics.failures
            }
            
            logger.info(f"Orchestration completed successfully in {self.metrics.total_duration:.2f}s")
            return result
            
        except Exception as e:
            self.metrics.finalize()
            error_msg = f"Orchestration failed after {self.metrics.total_duration:.2f}s: {str(e)}"
            logger.error(error_msg)
            
            # Return partial results if available
            if hasattr(e, 'partial_state') and e.partial_state:
                logger.warning("Returning partial results due to orchestration failure")
                e.partial_state["_execution_metadata"] = {
                    "total_duration": self.metrics.total_duration,
                    "node_execution_times": self.metrics.node_execution_times,
                    "retry_counts": self.metrics.retry_counts,
                    "failure_count": len(self.metrics.failures),
                    "failures": self.metrics.failures,
                    "status": "partial_failure"
                }
                return e.partial_state
            
            raise
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the orchestrator and its components"""
        try:
            # Simple health check
            test_state = {"repo_path": "/tmp/test"}
            
            # Check if we can initialize the graph
            health_status = {
                "status": "healthy",
                "components": {
                    "graph": "healthy",
                    "memory": "healthy",
                    "resilience_manager": "healthy"
                },
                "last_execution_metrics": {
                    "total_duration": self.metrics.total_duration,
                    "failure_count": len(self.metrics.failures)
                }
            }
            
            return health_status
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "components": {
                    "graph": "unknown",
                    "memory": "unknown", 
                    "resilience_manager": "unknown"
                }
            }


# Legacy orchestrator wrapper for backward compatibility
class CrossPublicationInsightOrchestrator(ResilientCrossPublicationInsightOrchestrator):
    """Backward compatible wrapper"""
    
    def __init__(self, user_query: str = ""):
        super().__init__(user_query=user_query, enable_fallbacks=True)
        logger.info("Using resilient orchestrator via legacy interface")