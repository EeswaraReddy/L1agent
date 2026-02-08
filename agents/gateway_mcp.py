import json
from pathlib import Path
from typing import Dict, Tuple

from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient
from bedrock_agentcore_starter_toolkit.operations.gateway.client import (  # type: ignore
    get_access_token_for_cognito,
)
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient

from .config import GATEWAY_CONFIG_PATH, GATEWAY_URL, GATEWAY_REGION


def load_gateway_config() -> Dict[str, str]:
    path = Path(GATEWAY_CONFIG_PATH)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "gateway_url": GATEWAY_URL,
        "region": GATEWAY_REGION,
    }


def get_gateway_client(config: Dict[str, str]) -> GatewayClient:
    return GatewayClient(region=config.get("region", GATEWAY_REGION))


def get_gateway_auth(config: Dict[str, str]) -> Tuple[str, str]:
    gateway_url = config.get("gateway_url", "")
    if not gateway_url:
        raise ValueError("Gateway URL is required. Set GATEWAY_URL or gateway_config.json")

    client_info = config.get("client_info")
    if not client_info:
        raise ValueError("client_info is required in gateway_config.json for OAuth")

    client_info_obj = client_info if isinstance(client_info, dict) else json.loads(client_info)
    gateway_client = get_gateway_client(config)
    access_token = get_access_token_for_cognito(gateway_client, client_info_obj)
    return gateway_url, access_token


def get_mcp_client() -> MCPClient:
    config = load_gateway_config()
    gateway_url, access_token = get_gateway_auth(config)
    transport = streamablehttp_client(
        gateway_url,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    return MCPClient(transport)
