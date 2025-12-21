"""Configuration loading for Small Council."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml
from dotenv import load_dotenv


DEFAULT_COUNCIL_MODELS = [
    "openai/gpt-5.2",
    "openai/gpt-5.2-pro",
    "google/gemini-3-pro-preview",
    "anthropic/claude-sonnet-4",
    "x-ai/grok-4",
]

DEFAULT_CHAIRMAN_MODEL = "anthropic/claude-opus-4.5"
DEFAULT_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_TIMEOUT = 120.0


@dataclass
class CouncilConfig:
    """Configuration for the council."""
    api_key: str
    council_models: List[str] = field(default_factory=lambda: DEFAULT_COUNCIL_MODELS.copy())
    chairman_model: str = DEFAULT_CHAIRMAN_MODEL
    api_url: str = DEFAULT_API_URL
    timeout: float = DEFAULT_TIMEOUT


class ConfigError(Exception):
    """Configuration error."""
    pass


def load_config(
    config_path: Optional[Path] = None,
    models_override: Optional[List[str]] = None,
    chairman_override: Optional[str] = None,
) -> CouncilConfig:
    """
    Load configuration from YAML file and environment variables.

    Priority (highest to lowest):
    1. CLI flag overrides (models_override, chairman_override)
    2. Environment variables (OPENROUTER_API_KEY)
    3. Config file (~/.small-council.yaml)
    4. Built-in defaults

    Args:
        config_path: Path to config file (default: ~/.small-council.yaml)
        models_override: Override council models from CLI
        chairman_override: Override chairman model from CLI

    Returns:
        CouncilConfig instance

    Raises:
        ConfigError: If required configuration is missing
    """
    load_dotenv()

    if config_path is None:
        config_path = Path.home() / ".small-council.yaml"

    # Start with defaults
    api_key = None
    council_models = DEFAULT_COUNCIL_MODELS.copy()
    chairman_model = DEFAULT_CHAIRMAN_MODEL
    api_url = DEFAULT_API_URL
    timeout = DEFAULT_TIMEOUT

    # Load from config file if exists
    if config_path.exists():
        try:
            with open(config_path) as f:
                config_data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in {config_path}: {e}")

        if "api_key" in config_data:
            api_key = config_data["api_key"]
        if "council_models" in config_data:
            council_models = config_data["council_models"]
        if "chairman_model" in config_data:
            chairman_model = config_data["chairman_model"]
        if "api_url" in config_data:
            api_url = config_data["api_url"]
        if "timeout" in config_data:
            timeout = float(config_data["timeout"])

    # Environment variable overrides config file
    env_api_key = os.getenv("OPENROUTER_API_KEY")
    if env_api_key:
        api_key = env_api_key

    # CLI overrides everything
    if models_override:
        council_models = models_override
    if chairman_override:
        chairman_model = chairman_override

    # Validate
    if not api_key:
        raise ConfigError(
            "API key required. Set OPENROUTER_API_KEY environment variable "
            "or add api_key to ~/.small-council.yaml"
        )

    if not council_models:
        raise ConfigError("At least one council model is required.")

    if not chairman_model:
        raise ConfigError("Chairman model is required.")

    return CouncilConfig(
        api_key=api_key,
        council_models=council_models,
        chairman_model=chairman_model,
        api_url=api_url,
        timeout=timeout,
    )
