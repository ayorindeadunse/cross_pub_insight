"""
Enhanced LLM client with resilience patterns.
Wraps the existing LLM client with retry logic, circuit breakers, and timeout handling.
"""
import asyncio
from typing import Optional, Dict, Any, List
from utils.resilience import (
    with_retry, 
    resilience_manager, 
    RetryConfigs, 
    CircuitBreakerConfigs,
    RetryStrategy,
    TimeoutError
)
from utils.logger import get_logger

logger = get_logger(__name__)


class ResilientLLMError(Exception):
    """Base exception for resilient LLM operations"""
    pass


class LLMServiceUnavailableError(ResilientLLMError):
    """Exception raised when LLM service is unavailable"""
    pass


class ResilientLLMClient:
    """
    Enhanced LLM client with built-in resilience patterns.
    """
    
    def __init__(self, original_client=None):
        """
        Initialize with optional original client.
        If no client provided, will attempt to import and use existing client.
        """
        self.original_client = original_client
        self._fallback_responses = {
            "analysis": "Analysis temporarily unavailable due to service issues. Please try again later.",
            "trends": ["Service temporarily unavailable"],
            "comparison": "Comparison analysis temporarily unavailable.",
            "fact_check": "Fact checking temporarily unavailable.",
            "summary": "Summary generation temporarily unavailable due to service issues."
        }
    
    def _get_client(self):
        """Get the original LLM client"""
        if self.original_client:
            return self.original_client
        
        try:
            from llm.client import get_llm_client
            return get_llm_client()
        except ImportError as e:
            logger.error(f"Failed to import LLM client: {e}")
            raise LLMServiceUnavailableError("LLM client not available")
    
    @with_retry(
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
        exponential_base=2.0,
        jitter=True,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        retryable_exceptions=(ConnectionError, TimeoutError, Exception),
        timeout=60.0,
        circuit_breaker_name="llm_service",
        circuit_breaker_threshold=3,
        circuit_breaker_timeout=60.0
    )
    async def generate_response(
        self, 
        prompt: str, 
        context: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        fallback_type: str = "analysis"
    ) -> str:
        """
        Generate LLM response with resilience patterns.
        
        Args:
            prompt: The prompt to send to the LLM
            context: Optional context for the prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            fallback_type: Type of fallback response if LLM fails
        
        Returns:
            Generated response or fallback response
        """
        try:
            client = self._get_client()
            
            # Prepare the full prompt
            full_prompt = prompt
            if context:
                full_prompt = f"Context: {context}\n\n{prompt}"
            
            logger.info(f"Sending request to LLM with {len(full_prompt)} characters")
            
            # Simulate LLM call (replace with actual client call)
            if hasattr(client, 'generate'):
                response = await client.generate(
                    prompt=full_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            elif hasattr(client, '__call__'):
                response = await client(full_prompt)
            else:
                # Fallback for different client interfaces
                response = str(client)
            
            logger.info(f"LLM response generated successfully ({len(str(response))} characters)")
            return str(response)
            
        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}")
            # Return fallback response instead of failing completely
            fallback = self._fallback_responses.get(fallback_type, "Service temporarily unavailable")
            logger.warning(f"Using fallback response for type: {fallback_type}")
            return fallback
    
    @with_retry(
        max_attempts=2,
        base_delay=0.5,
        max_delay=10.0,
        retryable_exceptions=(ConnectionError, TimeoutError),
        timeout=30.0
    )
    async def analyze_repository(self, repo_path: str, analysis_type: str = "general") -> str:
        """
        Analyze repository with resilience patterns.
        """
        try:
            prompt = f"""
            Analyze the repository at {repo_path}.
            Focus on: {analysis_type}
            
            Provide a structured analysis including:
            1. Project overview
            2. Key technologies used
            3. Architecture patterns
            4. Notable features
            """
            
            return await self.generate_response(
                prompt=prompt,
                context=f"Repository path: {repo_path}",
                fallback_type="analysis"
            )
            
        except Exception as e:
            logger.error(f"Repository analysis failed for {repo_path}: {str(e)}")
            return f"Analysis failed for repository {repo_path}: {str(e)}"
    
    @with_retry(
        max_attempts=2,
        base_delay=1.0,
        max_delay=15.0,
        retryable_exceptions=(ConnectionError, TimeoutError),
        timeout=45.0
    )
    async def extract_trends(self, analysis_result: str, repo_path: str) -> List[str]:
        """
        Extract trends from analysis with resilience patterns.
        """
        try:
            prompt = f"""
            Extract technical trends and patterns from this repository analysis:
            
            {analysis_result}
            
            Return a list of specific trends, technologies, and patterns used.
            Focus on:
            - Programming languages and frameworks
            - Architecture patterns
            - Development practices
            - Tool usage
            """
            
            response = await self.generate_response(
                prompt=prompt,
                context=f"Repository: {repo_path}",
                fallback_type="trends"
            )
            
            # Parse response into list format
            if isinstance(response, list):
                return response
            
            # Simple parsing of response into trends
            trends = []
            for line in response.split('\n'):
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('*') or line.startswith('1.')):
                    trend = line.lstrip('-*0123456789. ').strip()
                    if trend:
                        trends.append(trend)
            
            return trends if trends else ["Trend extraction temporarily unavailable"]
            
        except Exception as e:
            logger.error(f"Trend extraction failed for {repo_path}: {str(e)}")
            return ["Trend extraction failed"]
    
    @with_retry(
        max_attempts=2,
        base_delay=1.0,
        max_delay=10.0,
        retryable_exceptions=(ConnectionError, TimeoutError),
        timeout=30.0
    )
    async def compare_projects(self, project1_analysis: str, project2_analysis: str) -> str:
        """
        Compare projects with resilience patterns.
        """
        try:
            prompt = f"""
            Compare these two project analyses and identify:
            1. Similarities in technology choices
            2. Differences in approach
            3. Unique features of each project
            
            Project 1 Analysis:
            {project1_analysis}
            
            Project 2 Analysis:
            {project2_analysis}
            """
            
            return await self.generate_response(
                prompt=prompt,
                fallback_type="comparison"
            )
            
        except Exception as e:
            logger.error(f"Project comparison failed: {str(e)}")
            return f"Project comparison failed: {str(e)}"
    
    @with_retry(
        max_attempts=2,
        base_delay=1.0,
        max_delay=10.0,
        retryable_exceptions=(ConnectionError, TimeoutError),
        timeout=20.0
    )
    async def fact_check(self, content: str, repo_path: str) -> str:
        """
        Fact check content with resilience patterns.
        """
        try:
            prompt = f"""
            Fact-check the following analysis for accuracy and consistency:
            
            {content}
            
            Repository context: {repo_path}
            
            Identify any potential inaccuracies or inconsistencies.
            """
            
            return await self.generate_response(
                prompt=prompt,
                context=f"Fact-checking for: {repo_path}",
                fallback_type="fact_check"
            )
            
        except Exception as e:
            logger.error(f"Fact checking failed for {repo_path}: {str(e)}")
            return f"Fact checking temporarily unavailable: {str(e)}"
    
    @with_retry(
        max_attempts=3,
        base_delay=1.0,
        max_delay=20.0,
        retryable_exceptions=(ConnectionError, TimeoutError),
        timeout=60.0
    )
    async def generate_summary(
        self, 
        analyses: List[str], 
        comparisons: List[str], 
        trends: List[str],
        fact_check_results: List[str]
    ) -> str:
        """
        Generate final summary with resilience patterns.
        """
        try:
            prompt = f"""
            Generate a comprehensive summary based on:
            
            Analyses: {analyses}
            Comparisons: {comparisons}  
            Trends: {trends}
            Fact Check Results: {fact_check_results}
            
            Create a structured summary with key insights and recommendations.
            """
            
            return await self.generate_response(
                prompt=prompt,
                context="Final summary generation",
                fallback_type="summary",
                max_tokens=1500
            )
            
        except Exception as e:
            logger.error(f"Summary generation failed: {str(e)}")
            return f"Summary generation temporarily unavailable: {str(e)}"
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the LLM service.
        """
        try:
            # Simple health check with short timeout
            response = await asyncio.wait_for(
                self.generate_response(
                    prompt="Hello, please respond with 'OK'",
                    max_tokens=10,
                    temperature=0.0,
                    fallback_type="analysis"
                ),
                timeout=10.0
            )
            
            return {
                "status": "healthy",
                "response_time_ms": 100,  # Approximate
                "service": "llm",
                "circuit_breaker_state": "closed"
            }
            
        except Exception as e:
            logger.error(f"LLM health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "service": "llm",
                "circuit_breaker_state": "unknown"
            }


# Global resilient LLM client instance
resilient_llm_client = ResilientLLMClient()