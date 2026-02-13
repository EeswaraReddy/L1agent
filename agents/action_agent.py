import json
from typing import Dict, Any, List

from .schemas import Incident, ActionResult
from .config import STRANDS_ENABLE_LLM
from .agent_factory import build_agent
from .prompts import ACTION_PROMPT
from .mcp_tools import call_gateway_tool, list_gateway_tools
from .tool_registry import resolve_tool_name
from .workflows import ActionStep, select_workflow


def _action_result(intent: str, actions: List[Dict[str, Any]], status: str) -> ActionResult:
    return ActionResult(intent=intent, actions=actions, status=status)


def _run_action_step(incident: Incident, step: ActionStep) -> Dict[str, Any]:
    tool = resolve_tool_name(step.tool_suffix)
    ctx = incident.context.get(step.context_key, {}) if step.context_key else {}
    return call_gateway_tool(tool, ctx)


def _rule_based(incident: Incident, intent: str) -> ActionResult:
    workflow = select_workflow(intent, incident)
    actions: List[Dict[str, Any]] = []

    if not workflow.auto_retry_allowed and workflow.action_steps:
        actions.append(
            {
                "policy_block": (
                    f"Workflow {workflow.workflow_id} blocks automatic retries; escalate for manual approval"
                )
            }
        )
        return _action_result(intent, actions, status="blocked")

    for step in workflow.action_steps:
        ctx = incident.context.get(step.context_key, {}) if step.context_key else {}
        if step.context_key and not ctx and step.optional:
            continue

        try:
            action_result = _run_action_step(incident, step)
            actions.append({step.action_key: action_result})
        except Exception as exc:
            actions.append({step.action_key: {"error": str(exc)}})

    if not actions:
        actions.append({"noop": f"No automated action for workflow {workflow.workflow_id}"})

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
    payload["workflow_id"] = select_workflow(intent, incident).workflow_id
    result = agent(json.dumps(payload))
    return _parse_llm_result(result)


def act(incident: Incident, intent: str) -> ActionResult:
    if not STRANDS_ENABLE_LLM:
        return _rule_based(incident, intent)

    try:
        return _llm_act(incident, intent)
    except Exception:
        return _rule_based(incident, intent)
