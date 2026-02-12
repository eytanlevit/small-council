"""Regression tests for configuration defaults and override precedence."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from small_council.config import ConfigError, load_config


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
                "openai/gpt-5.2-codex",
                "openai/gpt-5.2-pro",
                "google/gemini-3-pro-preview",
                "anthropic/claude-opus-4.6",
            ],
        )
        self.assertEqual(config.chairman_model, "anthropic/claude-opus-4.6")

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


if __name__ == "__main__":
    unittest.main()
