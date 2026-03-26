"""
config_loader.py
----------------
Loads and exposes the project configuration from config/config.json.
"""

import json
import os


def load_config(config_path: str = None) -> dict:
    """
    Load config.json. Defaults to <project_root>/config/config.json
    resolved relative to this file's location.
    """
    if config_path is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base, "config", "config.json")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    print(f"[ConfigLoader] Loaded config from: {config_path}")
    return config
