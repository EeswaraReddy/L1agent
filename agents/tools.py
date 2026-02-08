from typing import Any, Dict
from .config import GATEWAY_URL
from .gateway_client import AgentcoreGatewayClient


_client = None


def _get_client() -> AgentcoreGatewayClient:
    global _client
    if _client is None:
        _client = AgentcoreGatewayClient(GATEWAY_URL)
    return _client


def call_tool(tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return _get_client().call_tool(tool_name, payload)
