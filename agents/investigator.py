import json
from typing import Dict, Any
from .schemas import Incident, InvestigationResult
from .config import STRANDS_ENABLE_LLM
from .agent_factory import build_agent
from .prompts import INVESTIGATOR_PROMPT
from .mcp_tools import call_gateway_tool, list_gateway_tools, search_gateway_tools
from .tool_registry import resolve_tool_name


def _search_tool(preferred_suffix: str, query: str) -> str:
    try:
        names = search_gateway_tools(query)
        for name in names:
            if preferred_suffix in name:
                return name
        if names:
            return names[0]
    except Exception:
        pass
    return resolve_tool_name(preferred_suffix)


def _rule_based(incident: Incident, intent: str) -> InvestigationResult:
    evidence: Dict[str, Any] = {"intent": intent}

    if intent == "emr_failure":
        tool = _search_tool("get_emr_logs", "emr logs")
        evidence["emr_logs"] = call_gateway_tool(tool, incident.context.get("emr", {}))
    elif intent in ("dag_failure", "mwaa_failure"):
        tool = _search_tool("get_mwaa_logs", "mwaa airflow logs")
        evidence["airflow_logs"] = call_gateway_tool(tool, incident.context.get("airflow", {}))
    elif intent == "dag_alarm":
        tool = _search_tool("get_cloudwatch_alarm", "cloudwatch alarm dag mwaa")
        alarm_ctx = incident.context.get("alarm", {})
        evidence["dag_alarm"] = call_gateway_tool(tool, alarm_ctx)
        if "airflow" in incident.context:
            tool = _search_tool("get_mwaa_logs", "mwaa airflow logs")
            evidence["airflow_logs"] = call_gateway_tool(tool, incident.context.get("airflow", {}))
    elif intent == "glue_etl_failure":
        tool = _search_tool("get_glue_logs", "glue logs")
        evidence["glue_logs"] = call_gateway_tool(tool, incident.context.get("glue", {}))
    elif intent == "athena_failure":
        tool = _search_tool("get_athena_query", "athena query execution error")
        evidence["athena_query"] = call_gateway_tool(tool, incident.context.get("athena_query", {}))
    elif intent in ("data_missing", "source_zero_data", "data_not_available"):
        tool = _search_tool("verify_source_data", "s3 source data validation")
        evidence["source_check"] = call_gateway_tool(tool, incident.context.get("source", {}))
        if "s3_logs" in incident.context:
            tool = _search_tool("get_s3_logs", "s3 logs")
            evidence["s3_logs"] = call_gateway_tool(tool, incident.context.get("s3_logs", {}))
    elif intent == "kafka_events_failed":
        tool = _search_tool("get_kafka_status", "kafka msk status")
        evidence["kafka_status"] = call_gateway_tool(tool, incident.context.get("kafka", {}))

    return InvestigationResult(intent=intent, evidence=evidence)


def _parse_llm_result(result: Any) -> InvestigationResult:
    if isinstance(result, dict):
        return InvestigationResult(**result)
    data = json.loads(result)
    return InvestigationResult(**data)


def _llm_investigate(incident: Incident, intent: str) -> InvestigationResult:
    tools = list_gateway_tools()
    agent = build_agent(INVESTIGATOR_PROMPT, tools=tools)
    payload = incident.model_dump()
    payload["intent"] = intent
    result = agent(json.dumps(payload))
    return _parse_llm_result(result)


def investigate(incident: Incident, intent: str) -> InvestigationResult:
    if not STRANDS_ENABLE_LLM:
        return _rule_based(incident, intent)

    try:
        return _llm_investigate(incident, intent)
    except Exception:
        return _rule_based(incident, intent)
