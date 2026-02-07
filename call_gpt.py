"""
OpenAI API client for calling GPT models.

Loads API key and model from environment variables (.env file).
"""

import os
import json
from typing import Any, Dict, List, Optional
from openai import OpenAI

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
    api_key = os.environ.get("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
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

            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    args = {}

                result = tool_executor(name, args)
                if isinstance(result, dict):
                    result = json.dumps(result)
                all_tool_calls.append({"name": name, "arguments": args, "result": result})

                current_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result if isinstance(result, str) else json.dumps(result),
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
