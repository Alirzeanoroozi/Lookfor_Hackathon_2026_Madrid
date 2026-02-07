from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol
import json
import os
from urllib import error, request

def _post_json(path: str, payload: Dict[str, Any], api_url: str | None = None) -> Dict[str, Any]:
    """
    Helper to call the hackathon API and normalize responses to the standard contract:
      - success: true | false
      - data: {...} (optional, on success)
      - error: string (on failure)
    """
    base = api_url or os.environ.get("API_URL")
    if not base:
        return {
            "success": False,
            "error": "API_URL is not configured. Set env var API_URL or pass api_url.",
        }

    url = base.rstrip("/") + path
    data = json.dumps(payload).encode("utf-8")

    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req) as resp:
            body = resp.read().decode("utf-8") or "{}"
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "Invalid JSON response from API.",
                    "body": body,
                }

            # API is expected to already follow the {success, data?, error?} contract.
            if isinstance(parsed, dict) and "success" in parsed:
                return parsed

            return {
                "success": False,
                "error": "Unexpected response format from API.",
                "body": parsed,
            }
    except error.HTTPError as e:
        body = e.read().decode("utf-8") if hasattr(e, "read") else ""
        return {
            "success": False,
            "error": f"HTTP error when calling API: {e}",
            "body": body,
        }
    except error.URLError as e:
        return {
            "success": False,
            "error": f"Network error when calling API: {e}",
        }


api_url = "https://lookfor-backend.ngrok.app/v1/api"
route = "/hackathon/get_order_details"
payload = {"orderId": "#1001"}

data = json.dumps(payload).encode("utf-8")

req = request.Request(
    api_url + route,
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with request.urlopen(req) as resp:
        print(resp.read().decode("utf-8"))
except error.HTTPError as e:
    body = e.read().decode("utf-8") if hasattr(e, "read") else ""
    print(f"HTTP {e.code}: {body}")
