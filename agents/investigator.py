import json
from typing import Dict, Any

from .schemas import Incident, InvestigationResult
from .config import STRANDS_ENABLE_LLM
from .agent_factory import build_agent
from .prompts import INVESTIGATOR_PROMPT
from .mcp_tools import call_gateway_tool, list_gateway_tools, search_gateway_tools
from .tool_registry import resolve_tool_name
from .workflows import InvestigationStep, select_workflow


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


def _run_step(incident: Incident, step: InvestigationStep) -> Dict[str, Any]:
    ctx = incident.context.get(step.context_key, {}) if step.context_key else {}
    tool = _search_tool(step.tool_suffix, step.query)
    return call_gateway_tool(tool, ctx)


def _rule_based(incident: Incident, intent: str) -> InvestigationResult:
    workflow = select_workflow(intent, incident)
    evidence: Dict[str, Any] = {
        "intent": intent,
        "workflow_id": workflow.workflow_id,
        "service": workflow.service,
    }

    for step in workflow.investigation_steps:
        ctx = incident.context.get(step.context_key, {}) if step.context_key else {}
        if step.context_key and not ctx and step.optional:
            continue

        try:
            evidence[step.evidence_key] = _run_step(incident, step)
        except Exception as exc:
            evidence[step.evidence_key] = {"error": str(exc)}
            if not step.optional:
                evidence.setdefault("step_errors", []).append(step.evidence_key)

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
    payload["workflow_id"] = select_workflow(intent, incident).workflow_id
    result = agent(json.dumps(payload))
    return _parse_llm_result(result)


def investigate(incident: Incident, intent: str) -> InvestigationResult:
    if not STRANDS_ENABLE_LLM:
        return _rule_based(incident, intent)

    try:
        return _llm_investigate(incident, intent)
    except Exception:
        return _rule_based(incident, intent)
