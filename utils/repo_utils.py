import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional

from utils.resilience import with_retry, RetryStrategy
from utils.logger import get_logger

logger = get_logger(__name__)


class RepositoryError(Exception):
    """Base exception for repository operations"""
    pass


class CloneError(RepositoryError):
    """Exception raised when repository cloning fails"""
    pass


@with_retry(
    max_attempts=3,
    base_delay=2.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    retryable_exceptions=(subprocess.CalledProcessError, ConnectionError, OSError),
    timeout=300.0,  # 5 minutes for cloning
    circuit_breaker_name="repository_cloning",
    circuit_breaker_threshold=5,
    circuit_breaker_timeout=300.0
)
def clone_if_remote(repo_input: str, base_clone_dir: str = "~/projects") -> str:
    """
    Clones a repo if it's a GitHub URL; otherwise returns the local path.
    Enhanced with retry logic and error handling.
    
    Args:
        repo_input: Either a full URL or a local path.
        base_clone_dir: Where to clone if needed.

    Returns:
        Local path to the repo.
        
    Raises:
        CloneError: If cloning fails after all retries
        RepositoryError: If repository path is invalid
    """
    repo_input = repo_input.strip()
    
    if not repo_input:
        raise RepositoryError("Repository input cannot be empty")
    
    logger.info(f"Processing repository input: {repo_input}")
    
    if repo_input.startswith("http://") or repo_input.startswith("https://"):
        try:
            parsed = urlparse(repo_input)
            if not parsed.netloc or not parsed.path:
                raise RepositoryError(f"Invalid repository URL: {repo_input}")
            
            repo_name = Path(parsed.path).stem  # e.g., 'gemini-cli-main' from URL
            if not repo_name:
                repo_name = "repository"
            
            clone_path = os.path.expanduser(f"{base_clone_dir}/{repo_name}")
            
            # Check if repo already exists
            if Path(clone_path).exists():
                logger.info(f"Repository already exists locally: {clone_path}")
                return clone_path
            
            # Create base directory if it doesn't exist
            os.makedirs(os.path.dirname(clone_path), exist_ok=True)
            
            logger.info(f"Cloning repository from {repo_input} to {clone_path}...")
            
            # Use git clone with timeout and error handling
            result = subprocess.run(
                ["git", "clone", repo_input, clone_path],
                check=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            logger.info(f"Successfully cloned repository to {clone_path}")
            return clone_path
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Git clone failed: {e.stderr if e.stderr else str(e)}"
            logger.error(error_msg)
            raise CloneError(error_msg) from e
            
        except subprocess.TimeoutExpired as e:
            error_msg = f"Git clone timed out after 5 minutes: {repo_input}"
            logger.error(error_msg)
            raise CloneError(error_msg) from e
            
        except OSError as e:
            error_msg = f"System error during clone: {str(e)}"
            logger.error(error_msg)
            raise CloneError(error_msg) from e
            
    else:
        # Assume it's already a local path
        expanded_path = os.path.expanduser(repo_input)
        
        if not os.path.exists(expanded_path):
            raise RepositoryError(f"Local repository path does not exist: {expanded_path}")
        
        if not os.path.isdir(expanded_path):
            raise RepositoryError(f"Repository path is not a directory: {expanded_path}")
        
        logger.info(f"Using local repository: {expanded_path}")
        return expanded_path

