from typing import Dict, Any
import json

import boto3

from .schemas import Incident, RCA
from .intent_classifier import classify_intent, is_non_incident_access_request
from .investigator import investigate
from .action_agent import act
from .agent_tools import intent_classifier, investigator, action_agent
from .prompts import ORCHESTRATOR_PROMPT
from .config import RCA_BUCKET, RCA_PREFIX, STRANDS_ENABLE_LLM
from .agent_factory import build_agent
from .policy import compute_policy_score
from .servicenow import update_ticket
from .validation import validate_intent, validate_investigation, validate_action, validate_orchestrator
from .workflows import select_workflow, workflow_profile
from .evaluation import evaluate_workflow
from .agentcore_governance import apply_agentcore_governance

s3 = boto3.client("s3")


def _write_rca(incident_id: str, rca: RCA) -> None:
    if not RCA_BUCKET:
        return
    key = f"{RCA_PREFIX.rstrip('/')}/{incident_id}.json"
    s3.put_object(Bucket=RCA_BUCKET, Key=key, Body=rca.model_dump_json(indent=2).encode("utf-8"))


def _parse_llm_result(result: Any) -> Dict[str, Any]:
    if isinstance(result, dict):
        return result
    return json.loads(result)


def _run_llm(incident: Incident) -> Dict[str, Any]:
    tools = [intent_classifier, investigator, action_agent]
    agent = build_agent(ORCHESTRATOR_PROMPT, tools=tools)
    result = agent(json.dumps(incident.model_dump()))
    return _parse_llm_result(result)


def _validate_outputs(
    intent_data: Dict[str, Any],
    investigation_data: Dict[str, Any],
    action_data: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "intent": validate_intent(intent_data),
        "investigation": validate_investigation(investigation_data),
        "action": validate_action(action_data),
    }


def handle_incident(payload: Dict[str, Any]) -> Dict[str, Any]:
    incident = Incident(**payload)
    if is_non_incident_access_request(incident):
        intent_data = classify_intent(incident, force_rule_based=True).model_dump()
        investigation_data = {
            "intent": intent_data["intent"],
            "evidence": {
                "skipped": True,
                "reason": "Access request is not an incident investigation workflow",
                "required_process": "Use IAM/change-management access request process",
            },
        }
        action_data = {
            "intent": intent_data["intent"],
            "actions": [
                {
                    "policy_block": (
                        "Production access cannot be granted by incident automation. "
                        "Please submit IAM/change-management access request."
                    )
                }
            ],
            "status": "blocked",
        }

    elif STRANDS_ENABLE_LLM:
        try:
            outcome = _run_llm(incident)
            intent_data = outcome.get("intent", {})
            investigation_data = outcome.get("investigation", {})
            action_data = outcome.get("actions", {})
        except Exception:
            intent_data = classify_intent(incident).model_dump()
            investigation_data = investigate(incident, intent_data["intent"]).model_dump()
            action_data = act(incident, intent_data["intent"]).model_dump()
    else:
        intent_data = classify_intent(incident).model_dump()
        investigation_data = investigate(incident, intent_data["intent"]).model_dump()
        action_data = act(incident, intent_data["intent"]).model_dump()

    validation_errors = _validate_outputs(intent_data, investigation_data, action_data)
    selected_workflow = select_workflow(intent_data.get("intent", "unknown"), incident)
    profile = workflow_profile(selected_workflow)
    evaluation = evaluate_workflow(
        incident=incident,
        intent_data=intent_data,
        investigation_data=investigation_data,
        action_data=action_data,
        workflow=selected_workflow,
        validation_errors=validation_errors,
    )

    has_errors = any(validation_errors[k] for k in validation_errors)
    if has_errors:
        decision = compute_policy_score(
            intent="unknown",
            evidence={},
            confidence=0.0,
            workflow_profile=profile,
            evaluation=evaluation,
        )
        decision.decision = "human_review"
        decision.reasons.append("Schema validation failed")
    else:
        decision = compute_policy_score(
            intent=intent_data["intent"],
            evidence=investigation_data.get("evidence", {}),
            confidence=float(intent_data.get("confidence", 0.0)),
            workflow_profile=profile,
            evaluation=evaluation,
        )

    governance, governed_decision, governance_reasons = apply_agentcore_governance(
        incident_id=incident.incident_id,
        intent=intent_data.get("intent", "unknown"),
        workflow_profile=profile,
        decision=decision.decision,
        evaluation=evaluation,
    )
    decision.decision = governed_decision
    decision.reasons.extend(governance_reasons)

    next_steps = ["Review logs", "Validate downstream tables"]
    for issue in evaluation.get("issues", [])[:2]:
        next_steps.append(issue)

    rca = RCA(
        incident_id=incident.incident_id,
        intent=intent_data.get("intent", "unknown"),
        summary=(
            f"Incident classified as {intent_data.get('intent', 'unknown')} "
            f"using workflow {selected_workflow.workflow_id}"
        ),
        root_cause=intent_data.get("rationale", ""),
        evidence=investigation_data.get("evidence", {}),
        actions_taken=action_data.get("actions", []),
        next_steps=next_steps,
        decision=decision,
    )

    _write_rca(incident.incident_id, rca)

    sn_context = incident.context.get("servicenow") if isinstance(incident.context, dict) else None
    sn_update = None
    if sn_context:
        rca_text = (
            f"Decision: {decision.decision}\n"
            f"Score: {decision.policy_score}\n"
            f"Workflow: {selected_workflow.workflow_id}\n"
            f"Reasons: {', '.join(decision.reasons)}"
        )
        sn_update = update_ticket(sn_context, decision.decision, rca_text)

    output = {
        "incident_id": incident.incident_id,
        "intent": intent_data,
        "workflow": profile,
        "investigation": investigation_data,
        "actions": action_data,
        "evaluation": evaluation,
        "agentcore_governance": governance,
        "policy": decision.model_dump(),
        "validation": validation_errors,
        "servicenow": sn_update,
        "rca": rca.model_dump(),
    }

    output_errors = validate_orchestrator(output)
    if output_errors:
        output["validation"].setdefault("orchestrator", []).extend(output_errors)
        output["policy"]["decision"] = "human_review"
        output["policy"]["reasons"].append("Orchestrator output schema failed")

    return output
