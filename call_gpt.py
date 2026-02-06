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


def call_gpt_with_tools(
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    tool_executor: Any,
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: Optional[int] = 2048,
    max_tool_rounds: int = 5,
) -> Dict[str, Any]:
    """
    Call GPT with function/tool calling. Executes tools and loops until the model
    returns a final text response (or max_tool_rounds is reached).

    Args:
        messages: Chat messages in OpenAI format (role, content, optionally tool_calls).
        tools: List of tool definitions for OpenAI API, e.g.:
            [{"type": "function", "function": {"name": "foo", "description": "...", "parameters": {...}}}]
        tool_executor: Callable tool_executor(tool_name: str, arguments: dict) -> str
            that executes a tool and returns its output as a string (e.g. JSON).
        model, temperature, max_tokens: Passed to API.
        max_tool_rounds: Max iterations of tool calls before stopping.

    Returns:
        Dict with:
            - "content": final assistant text
            - "tool_calls": list of {"name", "arguments", "result"}
            - "usage": token usage
    """
    client = _get_client()
    model_name = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    api_tools = [{"type": "function", "function": t} if "type" not in t else t for t in tools]
    current_messages = [dict(m) for m in messages]
    all_tool_calls: List[Dict[str, Any]] = []
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    for _ in range(max_tool_rounds):
        response = client.chat.completions.create(
            model=model_name,
            messages=current_messages,
            tools=api_tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = response.choices[0]
        msg = choice.message

        if response.usage:
            total_usage["prompt_tokens"] += response.usage.prompt_tokens
            total_usage["completion_tokens"] += response.usage.completion_tokens
            total_usage["total_tokens"] += response.usage.total_tokens

        if msg.tool_calls:
            current_messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                }
            )

            import json as _json
            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = _json.loads(tc.function.arguments) if tc.function.arguments else {}
                except _json.JSONDecodeError:
                    args = {}

                result = tool_executor(name, args)
                if isinstance(result, dict):
                    result = _json.dumps(result)
                all_tool_calls.append({"name": name, "arguments": args, "result": result})

                current_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result if isinstance(result, str) else _json.dumps(result),
                    }
                )
        else:
            content = msg.content or ""
            return {
                "content": content,
                "tool_calls": all_tool_calls,
                "usage": total_usage,
            }

    return {
        "content": "",
        "tool_calls": all_tool_calls,
        "usage": total_usage,
        "error": "Max tool rounds reached without final response.",
    }
