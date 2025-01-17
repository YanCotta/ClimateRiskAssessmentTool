import json
from typing import Dict

def load_config(file_path: str) -> Dict:
    """Load configuration from a JSON file"""
    with open(file_path, 'r') as file:
        return json.load(file)

def save_config(config: Dict, file_path: str) -> None:
    """Save configuration to a JSON file"""
    with open(file_path, 'w') as file:
        json.dump(config, file, indent=4)
