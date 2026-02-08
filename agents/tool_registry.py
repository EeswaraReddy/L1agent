from typing import Dict, List
from .mcp_tools import list_gateway_tools


_TOOL_CACHE: Dict[str, str] = {}


def _build_cache() -> None:
    tools = list_gateway_tools()
    for tool in tools:
        name = tool.name
        _TOOL_CACHE[name] = name
        if "__" in name:
            suffix = name.split("__", 1)[1]
            _TOOL_CACHE[suffix] = name


def resolve_tool_name(name: str) -> str:
    if not _TOOL_CACHE:
        _build_cache()
    if name not in _TOOL_CACHE:
        raise KeyError(f"Tool not found: {name}")
    return _TOOL_CACHE[name]
