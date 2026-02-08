import json
from typing import Dict, Any, List
from .schemas import Incident, ActionResult
from .config import STRANDS_ENABLE_LLM
from .agent_factory import build_agent
from .prompts import ACTION_PROMPT
from .mcp_tools import call_gateway_tool, list_gateway_tools
from .tool_registry import resolve_tool_name


def _action_result(intent: str, actions: List[Dict[str, Any]], status: str) -> ActionResult:
    return ActionResult(intent=intent, actions=actions, status=status)


def _rule_based(incident: Incident, intent: str) -> ActionResult:
    actions: List[Dict[str, Any]] = []

    if intent == "emr_failure":
        tool = resolve_tool_name("retry_emr")
        action = call_gateway_tool(tool, incident.context.get("emr_retry", {}))
        actions.append({"retry_emr": action})
    elif intent in ("dag_failure", "mwaa_failure", "dag_alarm"):
        tool = resolve_tool_name("retry_airflow_dag")
        action = call_gateway_tool(tool, incident.context.get("airflow_retry", {}))
        actions.append({"retry_airflow_dag": action})
    elif intent == "glue_etl_failure":
        tool = resolve_tool_name("retry_glue_job")
        action = call_gateway_tool(tool, incident.context.get("glue_retry", {}))
        actions.append({"retry_glue_job": action})
    elif intent == "athena_failure":
        tool = resolve_tool_name("retry_athena_query")
        action = call_gateway_tool(tool, incident.context.get("athena_retry", {}))
        actions.append({"retry_athena_query": action})
    elif intent == "kafka_events_failed":
        tool = resolve_tool_name("retry_kafka")
        action = call_gateway_tool(tool, incident.context.get("kafka_retry", {}))
        actions.append({"retry_kafka": action})
    elif intent in ("data_missing", "source_zero_data", "data_not_available"):
        tool = resolve_tool_name("verify_source_data")
        action = call_gateway_tool(tool, incident.context.get("source", {}))
        actions.append({"verify_source_data": action})
    else:
        actions.append({"noop": "No automated action for this intent"})

    return _action_result(intent, actions, status="completed")


def _parse_llm_result(result: Any) -> ActionResult:
    if isinstance(result, dict):
        return ActionResult(**result)
    data = json.loads(result)
    return ActionResult(**data)


def _llm_act(incident: Incident, intent: str) -> ActionResult:
    tools = list_gateway_tools()
    agent = build_agent(ACTION_PROMPT, tools=tools)
    payload = incident.model_dump()
    payload["intent"] = intent
    result = agent(json.dumps(payload))
    return _parse_llm_result(result)


def act(incident: Incident, intent: str) -> ActionResult:
    if not STRANDS_ENABLE_LLM:
        return _rule_based(incident, intent)

    try:
        return _llm_act(incident, intent)
    except Exception:
        return _rule_based(incident, intent)
