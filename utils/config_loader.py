import yaml
from pathlib import Path

def load_config(config_file: str = "config/config.yaml") -> dict:
    config_path = Path(config_file)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found at {config_file}")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)