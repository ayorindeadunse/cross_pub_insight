import logging
import sys
from pathlib import Path
from utils.config_loader import load_config

def get_logger(name: str = "cross_pub_insight") -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.hasHandlers():
        return logger

    # Load logging configuration
    config = load_config()
    logging_config = config.get("Logging", {})

    log_level = getattr(logging, logging_config.get("level", "DEBUG").upper(), logging.DEBUG)
    log_file = logging_config.get("log_file", "output/project.log")

    logger.setLevel(log_level)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    log_file_path = Path(log_file)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
