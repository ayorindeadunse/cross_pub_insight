"""
Enhanced Pydantic models for API validation and security.
"""
from pydantic import BaseModel, Field, field_validator, HttpUrl
from typing import List, Optional
import re
from urllib.parse import urlparse


class GitHubRepoUrl(BaseModel):
    """Validated GitHub repository URL"""
    url: str = Field(..., description="GitHub repository URL")
    
    @field_validator('url')
    @classmethod
    def validate_github_url(cls, v):
        """Validate that the URL is a legitimate GitHub repository URL"""
        if not isinstance(v, str):
            raise ValueError('URL must be a string')
        
        # Remove any potential malicious characters
        cleaned_url = v.strip()
        
        # Basic GitHub URL pattern validation
        github_pattern = re.compile(
            r'^https://github\.com/[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+/?$'
        )
        
        if not github_pattern.match(cleaned_url):
            # Also allow local paths for testing
            if not (cleaned_url.startswith('/') or cleaned_url.startswith('./')):
                raise ValueError(
                    'URL must be a valid GitHub repository URL '
                    '(https://github.com/owner/repo) or local path'
                )
        
        # Additional security checks
        dangerous_patterns = [
            r'\.\./', '///', '<script', 'javascript:', 'data:',
            '&lt;', '&gt;', '%3C', '%3E'
        ]
        
        for pattern in dangerous_patterns:
            if pattern.lower() in cleaned_url.lower():
                raise ValueError(f'URL contains potentially dangerous content: {pattern}')
        
        return cleaned_url


class RepoRequest(BaseModel):
    """Enhanced repository analysis request with validation"""
    
    primary_repo: str = Field(
        ..., 
        description="Primary repository URL or path",
        min_length=1,
        max_length=500
    )
    
    comparison_repos: List[str] = Field(
        default=[],
        description="List of comparison repository URLs or paths",
        max_length=10  # Reasonable limit to prevent abuse
    )
    
    user_query: Optional[str] = Field(
        default="",
        description="Optional user query for cross-repository analysis",
        max_length=1000  # Prevent extremely long queries
    )
    
    use_hitl: Optional[bool] = Field(
        default=True,
        description="Whether to use human-in-the-loop intervention"
    )
    
    @field_validator('primary_repo')
    @classmethod
    def validate_primary_repo(cls, v):
        """Validate primary repository URL/path"""
        return GitHubRepoUrl(url=v).url
    
    @field_validator('comparison_repos')
    @classmethod
    def validate_comparison_repos(cls, v):
        """Validate comparison repository URLs/paths"""
        validated_repos = []
        for repo in v:
            validated_repos.append(GitHubRepoUrl(url=repo).url)
        return validated_repos
    
    @field_validator('user_query')
    @classmethod
    def validate_user_query(cls, v):
        """Sanitize and validate user query"""
        if not v:
            return ""
        
        # Remove potential script injections and dangerous content
        dangerous_patterns = [
            '<script', '</script', 'javascript:', 'data:',
            'vbscript:', 'onload=', 'onerror=', '<?php', '<%',
            'eval(', 'exec(', '__import__', 'subprocess'
        ]
        
        cleaned_query = v.strip()
        
        for pattern in dangerous_patterns:
            if pattern.lower() in cleaned_query.lower():
                raise ValueError(f'Query contains potentially dangerous content: {pattern}')
        
        # Remove excessive whitespace and control characters
        cleaned_query = re.sub(r'\s+', ' ', cleaned_query)
        cleaned_query = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', cleaned_query)
        
        return cleaned_query


class AnalysisResponse(BaseModel):
    """Standardized response for analysis requests"""
    
    session_id: str = Field(..., description="Unique session identifier")
    status: str = Field(..., description="Request status (processing, completed, failed)")
    message: Optional[str] = Field(None, description="Optional status message")
    timestamp: Optional[str] = Field(None, description="Response timestamp")


class AnalysisResult(BaseModel):
    """Complete analysis results"""
    
    session_id: str = Field(..., description="Session identifier")
    status: str = Field(..., description="Analysis status")
    results: Optional[List[dict]] = Field(None, description="Analysis results if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    timestamp: Optional[str] = Field(None, description="Completion timestamp")


class HealthCheckResponse(BaseModel):
    """Health check response model"""
    
    status: str = Field(..., description="Service health status")
    version: str = Field(..., description="API version")
    timestamp: str = Field(..., description="Check timestamp")
    dependencies: Optional[dict] = Field(None, description="Dependency status")