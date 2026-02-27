"""Regression tests for OpenRouter request payload construction."""

import unittest

from small_council.openrouter import build_request_payload, model_requires_xhigh_reasoning


class OpenRouterPayloadTests(unittest.TestCase):
    """Ensure xhigh reasoning is enforced for required model families."""

    def setUp(self):
        self.messages = [{"role": "user", "content": "test"}]

    def test_codex_models_require_xhigh_reasoning(self):
        self.assertTrue(model_requires_xhigh_reasoning("openai/gpt-5.3-codex"))
        self.assertTrue(model_requires_xhigh_reasoning("openai/gpt-5-codex"))

    def test_opus_models_require_xhigh_reasoning(self):
        self.assertTrue(model_requires_xhigh_reasoning("anthropic/claude-opus-4.6"))
        self.assertTrue(model_requires_xhigh_reasoning("anthropic/claude-opus-4.5"))

    def test_non_target_models_do_not_require_xhigh_reasoning(self):
        self.assertFalse(model_requires_xhigh_reasoning("openai/gpt-5.2-pro"))
        self.assertFalse(model_requires_xhigh_reasoning("google/gemini-3.1-pro-preview"))

    def test_payload_includes_reasoning_for_codex(self):
        payload = build_request_payload("openai/gpt-5.3-codex", self.messages)
        self.assertEqual(payload["reasoning"]["effort"], "xhigh")

    def test_payload_includes_reasoning_for_opus(self):
        payload = build_request_payload("anthropic/claude-opus-4.6", self.messages)
        self.assertEqual(payload["reasoning"]["effort"], "xhigh")

    def test_payload_omits_reasoning_for_other_models(self):
        payload = build_request_payload("google/gemini-3.1-pro-preview", self.messages)
        self.assertNotIn("reasoning", payload)


if __name__ == "__main__":
    unittest.main()
