import json
import os
import sys
import types


def _install_stubs() -> None:
    strands_mod = types.ModuleType("strands")
    strands_models_mod = types.ModuleType("strands.models")
    strands_tools_mod = types.ModuleType("strands.tools")
    strands_tools_mcp_mod = types.ModuleType("strands.tools.mcp")

    class _DummyAgent:
        def __init__(self, *args, **kwargs):
            pass

        def __call__(self, payload: str):
            return payload

    class _DummyModel:
        def __init__(self, *args, **kwargs):
            pass

    class _ToolObj:
        def __init__(self, name: str):
            self.name = name

    class _DummyMCPClient:
        def __init__(self, *args, **kwargs):
            pass

        def list_tools_sync(self):
            names = [
                "mock__get_emr_logs",
                "mock__get_glue_logs",
                "mock__get_mwaa_logs",
                "mock__get_cloudwatch_alarm",
                "mock__get_athena_query",
                "mock__verify_source_data",
                "mock__get_s3_logs",
                "mock__get_kafka_status",
                "mock__retry_emr",
                "mock__retry_glue_job",
                "mock__retry_airflow_dag",
                "mock__retry_athena_query",
                "mock__retry_kafka",
                "mock__update_servicenow_ticket",
            ]
            return [_ToolObj(name) for name in names]

        def call_tool_sync(self, name: str, arguments: dict):
            if name == "x_amz_bedrock_agentcore_search":
                query = str(arguments.get("query", "")).lower()
                tool_name = "mock__get_cloudwatch_alarm"
                if "emr" in query:
                    tool_name = "mock__get_emr_logs"
                elif "glue" in query:
                    tool_name = "mock__get_glue_logs"
                elif "mwaa" in query or "airflow" in query or "dag" in query:
                    tool_name = "mock__get_mwaa_logs"
                elif "athena" in query:
                    tool_name = "mock__get_athena_query"
                elif "kafka" in query:
                    tool_name = "mock__get_kafka_status"
                elif "source" in query or "s3" in query:
                    tool_name = "mock__verify_source_data"
                return {"tools": [{"name": tool_name}]}

            if "retry" in name:
                return {"status": "started", "tool": name, "args": arguments}
            if "verify_source_data" in name:
                return {"status": "ok", "objects": 10, "bytes": 1024}
            if "get_athena_query" in name:
                return {"status": "FAILED", "error": "SYNTAX_ERROR"}
            if "get_kafka_status" in name:
                return {"status": "DEGRADED", "lag": 12345}
            return {"status": "ok", "tool": name, "args": arguments}

    def _tool_decorator(func):
        return func

    strands_mod.Agent = _DummyAgent
    strands_models_mod.BedrockModel = _DummyModel
    strands_tools_mod.tool = _tool_decorator
    strands_tools_mcp_mod.MCPClient = _DummyMCPClient

    sys.modules["strands"] = strands_mod
    sys.modules["strands.models"] = strands_models_mod
    sys.modules["strands.tools"] = strands_tools_mod
    sys.modules["strands.tools.mcp"] = strands_tools_mcp_mod

    sdk_client_mod = types.ModuleType("bedrock_agentcore_starter_toolkit.operations.gateway.client")

    class _GatewayClient:
        def __init__(self, *args, **kwargs):
            pass

    def _get_access_token_for_cognito(*args, **kwargs):
        return "dummy-token"

    sdk_client_mod.GatewayClient = _GatewayClient
    sdk_client_mod.get_access_token_for_cognito = _get_access_token_for_cognito

    sys.modules["bedrock_agentcore_starter_toolkit"] = types.ModuleType("bedrock_agentcore_starter_toolkit")
    sys.modules["bedrock_agentcore_starter_toolkit.operations"] = types.ModuleType(
        "bedrock_agentcore_starter_toolkit.operations"
    )
    sys.modules["bedrock_agentcore_starter_toolkit.operations.gateway"] = types.ModuleType(
        "bedrock_agentcore_starter_toolkit.operations.gateway"
    )
    sys.modules["bedrock_agentcore_starter_toolkit.operations.gateway.client"] = sdk_client_mod

    mcp_stream_mod = types.ModuleType("mcp.client.streamable_http")

    def _streamablehttp_client(*args, **kwargs):
        return object()

    mcp_stream_mod.streamablehttp_client = _streamablehttp_client
    sys.modules["mcp"] = types.ModuleType("mcp")
    sys.modules["mcp.client"] = types.ModuleType("mcp.client")
    sys.modules["mcp.client.streamable_http"] = mcp_stream_mod


_install_stubs()
os.environ.setdefault("STRANDS_ENABLE_LLM", "0")

from agents.orchestrator import handle_incident  # noqa: E402


def main() -> None:
    incidents = [
        {
            "incident_id": "DUMMY-EMR-1",
            "summary": "EMR cluster spin up failed during bootstrap",
            "details": "Provisioning timeout and node init failure",
            "context": {
                "emr": {"cluster_id": "j-111"},
                "emr_retry": {"cluster_id": "j-111"},
            },
        },
        {
            "incident_id": "DUMMY-GLUE-1",
            "summary": "Glue ETL failed with access denied",
            "details": "User not authorized glue:GetTable",
            "context": {
                "glue": {"job_name": "job-1"},
                "glue_retry": {"job_name": "job-1"},
            },
        },
    ]

    for payload in incidents:
        result = handle_incident(payload)
        print(
            json.dumps(
                {
                    "incident_id": result.get("incident_id"),
                    "workflow": result.get("workflow", {}).get("workflow_id"),
                    "decision": result.get("policy", {}).get("decision"),
                    "coverage": {
                        "evidence": result.get("evaluation", {}).get("evidence_coverage"),
                        "action": result.get("evaluation", {}).get("action_coverage"),
                    },
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
