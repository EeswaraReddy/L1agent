import base64
import json
from typing import Any, Dict, Optional


def is_api_gateway_event(event: Dict[str, Any]) -> bool:
    return isinstance(event, dict) and "body" in event


def parse_event(event: Dict[str, Any]) -> Dict[str, Any]:
    if event is None:
        return {}

    # AgentCore Gateway invokes Lambda with the input args directly.
    if not is_api_gateway_event(event):
        if isinstance(event, dict):
            return event
        return {}

    body = event.get("body")
    if body is None:
        return {}
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    if isinstance(body, (bytes, bytearray)):
        body = body.decode("utf-8")
    if isinstance(body, str):
        body = body.strip()
        if not body:
            return {}
        return json.loads(body)
    if isinstance(body, dict):
        return body
    return {}


def get_tool_name(context: Any) -> Optional[str]:
    if context is None:
        return None
    client_ctx = getattr(context, "client_context", None)
    if client_ctx is None:
        return None
    custom = getattr(client_ctx, "custom", None) or {}
    tool_name = custom.get("bedrock_agentcore_tool_name")
    if tool_name and "__" in tool_name:
        return tool_name.split("__", 1)[1]
    return tool_name


def response_ok(payload: Dict[str, Any], event: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if event is not None and not is_api_gateway_event(event):
        return payload
    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(payload),
    }


def response_error(message: str, status_code: int = 400, event: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = {"error": message}
    if event is not None and not is_api_gateway_event(event):
        return payload
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(payload),
    }
