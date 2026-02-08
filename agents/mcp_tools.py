import json
from typing import Any, Dict, List
from strands.tools.mcp import MCPClient
from .gateway_mcp import get_mcp_client


_mcp_client = None


def _client() -> MCPClient:
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = get_mcp_client()
    return _mcp_client


def _normalize_tool_result(result: Any) -> Any:
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if hasattr(result, "content"):
        return {
            "content": [getattr(item, "text", str(item)) for item in result.content],
            "is_error": getattr(result, "is_error", False),
        }
    return result


def _extract_tools(result: Any) -> List[Any]:
    if isinstance(result, dict):
        base = result.get("result", result)
        if isinstance(base, dict):
            if "structuredContent" in base:
                return base.get("structuredContent", {}).get("tools", [])
            if "tools" in base:
                return base.get("tools", [])
        return []
    if hasattr(result, "structuredContent"):
        return getattr(result, "structuredContent", {}).get("tools", [])
    if hasattr(result, "content"):
        try:
            content_text = "".join(getattr(item, "text", "") for item in result.content)
            data = json.loads(content_text)
            return data.get("tools", [])
        except Exception:
            return []
    return []


def list_gateway_tools():
    return _client().list_tools_sync()


def search_gateway_tools(query: str, limit: int = 3) -> List[str]:
    result = _client().call_tool_sync("x_amz_bedrock_agentcore_search", {"query": query})
    tools = _extract_tools(result)
    names: List[str] = []
    for tool in tools:
        if isinstance(tool, dict):
            name = tool.get("name")
        else:
            name = getattr(tool, "name", None) or str(tool)
        if name:
            names.append(name)
    return names[:limit]


def call_gateway_tool(name: str, arguments: Dict[str, Any]):
    result = _client().call_tool_sync(name, arguments)
    return _normalize_tool_result(result)
