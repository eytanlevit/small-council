"""Regression tests for configuration defaults and override precedence."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from small_council.config import ConfigError, DEFAULT_TIMEOUT, load_config


class ConfigTests(unittest.TestCase):
    """Validate model defaults and config precedence rules."""

    def test_default_models_updated(self):
        """Defaults should match the latest configured council lineup."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "missing.yaml"
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}, clear=True):
                config = load_config(config_path=config_path)

        self.assertEqual(
            config.council_models,
            [
                "openai/gpt-5.4",
                "openai/gpt-5.4-pro",
                "google/gemini-3.1-pro-preview",
                "anthropic/claude-opus-4.6",
            ],
        )
        self.assertEqual(config.chairman_model, "anthropic/claude-opus-4.6")
        self.assertEqual(DEFAULT_TIMEOUT, 3600.0)
        self.assertEqual(config.timeout, 3600.0)
        self.assertEqual(config.model_timeouts, {})

    def test_config_file_values_respected_when_no_cli_override(self):
        """User config values should be respected when CLI overrides are absent."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.yaml"
            config_path.write_text(
                yaml.safe_dump(
                    {
                        "api_key": "file-key",
                        "council_models": ["custom/model-a", "custom/model-b"],
                        "chairman_model": "custom/chair",
                    }
                )
            )

            with patch.dict(os.environ, {}, clear=True):
                config = load_config(config_path=config_path)

        self.assertEqual(config.api_key, "file-key")
        self.assertEqual(config.council_models, ["custom/model-a", "custom/model-b"])
        self.assertEqual(config.chairman_model, "custom/chair")

    def test_cli_overrides_take_priority(self):
        """CLI model overrides must beat config file values."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.yaml"
            config_path.write_text(
                yaml.safe_dump(
                    {
                        "api_key": "file-key",
                        "council_models": ["custom/model-from-file"],
                        "chairman_model": "custom/chair-from-file",
                    }
                )
            )

            with patch.dict(os.environ, {"OPENROUTER_API_KEY": "env-key"}, clear=True):
                config = load_config(
                    config_path=config_path,
                    models_override=["cli/model-a", "cli/model-b"],
                    chairman_override="cli/chair",
                )

        self.assertEqual(config.api_key, "env-key")
        self.assertEqual(config.council_models, ["cli/model-a", "cli/model-b"])
        self.assertEqual(config.chairman_model, "cli/chair")

    def test_missing_api_key_raises(self):
        """Missing API key should fail fast with ConfigError."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "missing.yaml"
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(ConfigError):
                    load_config(config_path=config_path)

    def test_per_model_timeout_config(self):
        """Mixed model format with per-model timeouts should parse correctly."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.yaml"
            config_path.write_text(
                yaml.safe_dump(
                    {
                        "api_key": "test-key",
                        "council_models": [
                            {"model": "openai/gpt-5.4", "timeout": 300},
                            {"model": "openai/gpt-5.4-pro", "timeout": 3600},
                            "google/gemini-3.1-pro-preview",
                        ],
                    }
                )
            )

            with patch.dict(os.environ, {}, clear=True):
                config = load_config(config_path=config_path)

        self.assertEqual(
            config.council_models,
            ["openai/gpt-5.4", "openai/gpt-5.4-pro", "google/gemini-3.1-pro-preview"],
        )
        self.assertEqual(
            config.model_timeouts,
            {"openai/gpt-5.4": 300.0, "openai/gpt-5.4-pro": 3600.0},
        )

    def test_simple_model_list_no_timeouts(self):
        """Simple string model list should produce empty model_timeouts."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.yaml"
            config_path.write_text(
                yaml.safe_dump(
                    {
                        "api_key": "test-key",
                        "council_models": ["model/a", "model/b"],
                    }
                )
            )

            with patch.dict(os.environ, {}, clear=True):
                config = load_config(config_path=config_path)

        self.assertEqual(config.council_models, ["model/a", "model/b"])
        self.assertEqual(config.model_timeouts, {})


if __name__ == "__main__":
    unittest.main()
