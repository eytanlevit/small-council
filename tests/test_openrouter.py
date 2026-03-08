"""Regression tests for OpenRouter request payload construction and timeout behavior."""

import asyncio
import unittest

from small_council.openrouter import build_request_payload, model_requires_xhigh_reasoning, query_model


class OpenRouterPayloadTests(unittest.TestCase):
    """Ensure xhigh reasoning is enforced for required model families."""

    def setUp(self):
        self.messages = [{"role": "user", "content": "test"}]

    def test_gpt54_models_require_xhigh_reasoning(self):
        self.assertTrue(model_requires_xhigh_reasoning("openai/gpt-5.4"))
        self.assertTrue(model_requires_xhigh_reasoning("openai/gpt-5.4-pro"))

    def test_opus_models_require_xhigh_reasoning(self):
        self.assertTrue(model_requires_xhigh_reasoning("anthropic/claude-opus-4.6"))
        self.assertTrue(model_requires_xhigh_reasoning("anthropic/claude-opus-4.5"))

    def test_non_target_models_do_not_require_xhigh_reasoning(self):
        self.assertFalse(model_requires_xhigh_reasoning("openai/gpt-5.2-pro"))
        self.assertFalse(model_requires_xhigh_reasoning("google/gemini-3.1-pro-preview"))

    def test_payload_includes_reasoning_for_gpt54(self):
        payload = build_request_payload("openai/gpt-5.4", self.messages)
        self.assertEqual(payload["reasoning"]["effort"], "xhigh")

    def test_payload_includes_reasoning_for_opus(self):
        payload = build_request_payload("anthropic/claude-opus-4.6", self.messages)
        self.assertEqual(payload["reasoning"]["effort"], "xhigh")

    def test_payload_omits_reasoning_for_other_models(self):
        payload = build_request_payload("google/gemini-3.1-pro-preview", self.messages)
        self.assertNotIn("reasoning", payload)


class WallClockTimeoutTests(unittest.TestCase):
    """Verify asyncio.wait_for enforces wall-clock timeout."""

    def test_wall_clock_timeout_enforced(self):
        """query_model should return None when request exceeds wall-clock timeout."""
        import httpx

        async def slow_handler(request):
            await asyncio.sleep(5)
            return httpx.Response(200, json={
                "choices": [{"message": {"content": "ok"}}]
            })

        transport = httpx.MockTransport(slow_handler)
        client = httpx.AsyncClient(transport=transport, timeout=httpx.Timeout(10.0))

        async def run():
            result = await query_model(
                model="test/slow-model",
                messages=[{"role": "user", "content": "test"}],
                api_key="fake-key",
                timeout=0.5,  # 500ms wall-clock limit
                client=client,
            )
            await client.aclose()
            return result

        result = asyncio.run(run())
        self.assertIsNone(result)

    def test_fast_request_succeeds(self):
        """query_model should return response when request completes within timeout."""
        import httpx

        async def fast_handler(request):
            return httpx.Response(200, json={
                "choices": [{"message": {"content": "hello", "reasoning_details": None}}]
            })

        transport = httpx.MockTransport(fast_handler)
        client = httpx.AsyncClient(transport=transport, timeout=httpx.Timeout(10.0))

        async def run():
            result = await query_model(
                model="test/fast-model",
                messages=[{"role": "user", "content": "test"}],
                api_key="fake-key",
                timeout=5.0,
                client=client,
            )
            await client.aclose()
            return result

        result = asyncio.run(run())
        self.assertIsNotNone(result)
        self.assertEqual(result["content"], "hello")


if __name__ == "__main__":
    unittest.main()
