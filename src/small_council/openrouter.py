"""OpenRouter API client for making LLM requests."""

import asyncio
import httpx
from typing import List, Dict, Any, Optional


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    api_key: str,
    api_url: str = "https://openrouter.ai/api/v1/chat/completions",
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via OpenRouter API.

    Args:
        model: OpenRouter model identifier (e.g., "openai/gpt-5.2")
        messages: List of message dicts with 'role' and 'content'
        api_key: OpenRouter API key
        api_url: OpenRouter API endpoint
        timeout: Request timeout in seconds

    Returns:
        Response dict with 'content' and optional 'reasoning_details', or None if failed
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                api_url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            message = data['choices'][0]['message']

            return {
                'content': message.get('content'),
                'reasoning_details': message.get('reasoning_details')
            }

    except Exception as e:
        # Return None on failure for graceful degradation
        return None


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]],
    api_key: str,
    api_url: str = "https://openrouter.ai/api/v1/chat/completions"
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel.

    Args:
        models: List of OpenRouter model identifiers
        messages: List of message dicts to send to each model
        api_key: OpenRouter API key
        api_url: OpenRouter API endpoint

    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    tasks = [query_model(model, messages, api_key, api_url) for model in models]
    responses = await asyncio.gather(*tasks)
    return {model: response for model, response in zip(models, responses)}
