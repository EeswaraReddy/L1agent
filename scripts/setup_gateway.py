import json
from pathlib import Path
from typing import Dict, Any

import boto3


def load_json(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> None:
    config = load_json("agentcore/gateway_config.json")
    tools = load_json("agentcore/gateway_tools.json")

    region = config.get("region", "us-east-1")
    client = boto3.client("bedrock-agentcore-control", region_name=region)

    gateway_id = config.get("gateway_id")
    if not gateway_id:
        authorizer_type = config.get("authorizer_type", "CUSTOM_JWT")
        authorizer_config = config.get("authorizer_config")
        if not authorizer_config:
            raise RuntimeError("authorizer_config is required to create a gateway")

        create_args: Dict[str, Any] = {
            "name": config.get("gateway_name", "datalake-sre-gateway"),
            "protocolType": "MCP",
            "protocolConfiguration": {
                "mcp": {
                    "supportedVersions": ["2024-11-05"],
                    "instructions": "Datalake SRE tools",
                    "searchType": "SEMANTIC",
                }
            },
            "authorizerType": authorizer_type,
            "authorizerConfiguration": authorizer_config,
        }

        if config.get("role_arn"):
            create_args["roleArn"] = config["role_arn"]

        gateway = client.create_gateway(**create_args)
        gateway_id = gateway["gatewayId"]
        config["gateway_id"] = gateway_id
        config["gateway_url"] = gateway.get("gatewayUrl", "")
        Path("agentcore/gateway_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
        print(f"Created gateway: {gateway_id}")

    for tool in tools:
        lambda_arn = tool.get("lambda_arn")
        if not lambda_arn:
            raise RuntimeError(f"Missing lambda_arn for tool {tool['name']}")

        target_config = {
            "mcp": {
                "lambda": {
                    "lambdaArn": lambda_arn,
                    "toolSchema": {"inlinePayload": [tool["schema"]]},
                }
            }
        }

        resp = client.create_gateway_target(
            gatewayIdentifier=gateway_id,
            name=tool["name"],
            targetConfiguration=target_config,
            credentialProvider=[{"credentialProviderType": "GATEWAY_IAM_ROLE"}],
        )
        print(f"Created target for {tool['name']}: {resp['targetId']}")


if __name__ == "__main__":
    main()
