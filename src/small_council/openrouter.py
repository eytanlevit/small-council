"""OpenRouter API client for making LLM requests."""

import asyncio
import sys
import httpx
from typing import List, Dict, Any, Optional


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    api_key: str,
    api_url: str = "https://openrouter.ai/api/v1/chat/completions",
    timeout: float = 3600.0,
    client: Optional[httpx.AsyncClient] = None,
    max_tokens: int = 32768,
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via OpenRouter API.

    Args:
        model: OpenRouter model identifier (e.g., "openai/gpt-5.4")
        messages: List of message dicts with 'role' and 'content'
        api_key: OpenRouter API key
        api_url: OpenRouter API endpoint
        timeout: Wall-clock timeout in seconds (enforced via asyncio.wait_for)
        client: Optional shared AsyncClient (creates one if not provided)

    Returns:
        Response dict with 'content' and optional 'reasoning_details', or None if failed
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = build_request_payload(model, messages, max_tokens=max_tokens)
    reasoning_effort = payload.get("reasoning", {}).get("effort", "default")
    print(
        f"[{model}] Request start: endpoint={api_url} timeout={timeout}s "
        f"messages={len(messages)} reasoning_effort={reasoning_effort}",
        file=sys.stderr,
    )

    async def do_request(c: httpx.AsyncClient) -> Dict[str, Any]:
        response = await c.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        message = data['choices'][0]['message']
        content = message.get('content') or ''
        reasoning_details = message.get('reasoning_details')
        print(
            f"[{model}] Request success: status={response.status_code} "
            f"content_chars={len(content)} "
            f"reasoning_details={'yes' if reasoning_details else 'no'}",
            file=sys.stderr,
        )
        return {
            'content': content,
            'reasoning_details': reasoning_details
        }

    try:
        if client:
            result = await asyncio.wait_for(do_request(client), timeout=timeout)
        else:
            # Use a generous read timeout but enforce wall-clock via wait_for
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=30.0)) as c:
                result = await asyncio.wait_for(do_request(c), timeout=timeout)
        return result
    except asyncio.TimeoutError:
        print(f"[{model}] Request TIMEOUT after {timeout}s — proceeding without this response", file=sys.stderr)
        return None
    except httpx.HTTPStatusError as e:
        print(f"[{model}] HTTP {e.response.status_code}: {e.response.text[:200]}", file=sys.stderr)
        return None
    except httpx.TimeoutException:
        print(f"[{model}] Request timed out (httpx)", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[{model}] Error: {type(e).__name__}: {e}", file=sys.stderr)
        return None


def model_requires_xhigh_reasoning(model: str) -> bool:
    """
    Return True when the model should be forced to maximum reasoning effort.

    Current policy: all OpenAI GPT-5.4 variants and all Anthropic Opus variants.
    """
    lower_model = model.lower()
    is_openai_gpt54 = lower_model.startswith("openai/") and "gpt-5.4" in lower_model
    is_anthropic_opus = lower_model.startswith("anthropic/claude-opus-")
    return is_openai_gpt54 or is_anthropic_opus


def build_request_payload(model: str, messages: List[Dict[str, str]], max_tokens: int = 32768) -> Dict[str, Any]:
    """
    Build OpenRouter chat completion payload with model-specific reasoning settings.
    """
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if model_requires_xhigh_reasoning(model):
        payload["reasoning"] = {"effort": "xhigh"}
    return payload


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]],
    api_key: str,
    api_url: str = "https://openrouter.ai/api/v1/chat/completions",
    timeout: float = 3600.0,
    model_timeouts: Optional[Dict[str, float]] = None,
    max_tokens: int = 32768,
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel using a shared connection pool.

    Args:
        models: List of OpenRouter model identifiers
        messages: List of message dicts to send to each model
        api_key: OpenRouter API key
        api_url: OpenRouter API endpoint
        timeout: Default wall-clock timeout in seconds
        model_timeouts: Optional per-model timeout overrides
        max_tokens: Maximum tokens for each response

    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    # Determine per-model timeouts
    timeouts = {}
    for model in models:
        if model_timeouts and model in model_timeouts:
            timeouts[model] = model_timeouts[model]
        else:
            timeouts[model] = timeout

    max_timeout = max(timeouts.values())

    print(
        f"[openrouter] Parallel request start: model_count={len(models)} "
        f"default_timeout={timeout}s max_timeout={max_timeout}s "
        f"models={models}",
        file=sys.stderr,
    )
    async with httpx.AsyncClient(timeout=httpx.Timeout(max_timeout, connect=30.0)) as client:
        tasks = [
            query_model(model, messages, api_key, api_url,
                       timeout=timeouts[model], client=client, max_tokens=max_tokens)
            for model in models
        ]
        responses = await asyncio.gather(*tasks)
    results = {model: response for model, response in zip(models, responses)}
    success_count = sum(1 for response in results.values() if response is not None)
    print(
        f"[openrouter] Parallel request complete: success={success_count}/{len(models)}",
        file=sys.stderr,
    )
    return results
