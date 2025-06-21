import logging
import sys
from pathlib import Path

def get_logger(name: str = "cross_pub_insight", log_file: str = "output/project.log") -> logging.Logger:
    logger = logging.getLogger(name)

    # Avoid adding multiple handlers in environments where get_logger might be called repeatedly
    if logger.hasHandlers():
        return logger
    
    logger.setLevel(logging.DEBUG)

    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    # Console Handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
    file_handler = logging.FileHandler(log_path, encoding='utf-8')  
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.info(f"Logger initialized. Logs will be saved to {log_path}")
    return logger    