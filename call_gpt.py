"""
OpenAI API client for calling GPT models.

Loads API key and model from environment variables (.env file).
"""

import os
from typing import Any, Dict, List, Optional

try:
    from openai import OpenAI
except ImportError:
    raise ImportError(
        "openai package is required. Install with: pip install openai"
    )


def _get_client() -> OpenAI:
    """Get OpenAI client with API key from environment."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not found in environment. Set it in .env file."
        )
    return OpenAI(api_key=api_key)


def call_gpt(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Call OpenAI GPT model with a list of messages.

    Args:
        messages: List of message dicts with "role" and "content" keys.
                 Example: [{"role": "user", "content": "Hello!"}]
        model: Model name (defaults to OPENAI_MODEL env var, or "gpt-4o-mini").
        temperature: Sampling temperature (0-2), default 0.7.
        max_tokens: Maximum tokens to generate (optional).
        **kwargs: Additional arguments passed to OpenAI API.

    Returns:
        Dict with:
            - "content": str (the assistant's response text)
            - "role": str ("assistant")
            - "model": str (model used)
            - "usage": dict (token usage stats)
            - "raw_response": dict (full API response)

    Raises:
        RuntimeError: If API key is missing or API call fails.
    """
    client = _get_client()
    model_name = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        choice = response.choices[0]
        message = choice.message

        return {
            "content": message.content or "",
            "role": message.role or "assistant",
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
            "raw_response": response.model_dump() if hasattr(response, "model_dump") else {},
        }
    except Exception as e:
        raise RuntimeError(f"OpenAI API call failed: {e}") from e


def call_gpt_simple(prompt: str, **kwargs: Any) -> str:
    """
    Simple wrapper: call GPT with a single user prompt and return just the text.

    Args:
        prompt: User message string.
        **kwargs: Passed to call_gpt (model, temperature, etc.).

    Returns:
        Assistant's response text as a string.
    """
    messages = [{"role": "user", "content": prompt}]
    result = call_gpt(messages, **kwargs)
    return result["content"]
