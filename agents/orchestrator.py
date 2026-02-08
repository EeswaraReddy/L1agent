from typing import Dict, Any
import json
import boto3
from .schemas import Incident, RCA
from .intent_classifier import classify_intent
from .investigator import investigate
from .action_agent import act
from .agent_tools import intent_classifier, investigator, action_agent
from .prompts import ORCHESTRATOR_PROMPT
from .config import RCA_BUCKET, RCA_PREFIX, STRANDS_ENABLE_LLM
from .agent_factory import build_agent
from .policy import compute_policy_score
from .servicenow import update_ticket
from .validation import validate_intent, validate_investigation, validate_action, validate_orchestrator


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


def _validate_outputs(intent_data: Dict[str, Any], investigation_data: Dict[str, Any], action_data: Dict[str, Any]) -> Dict[str, Any]:
    errors = {
        "intent": validate_intent(intent_data),
        "investigation": validate_investigation(investigation_data),
        "action": validate_action(action_data),
    }
    return errors


def handle_incident(payload: Dict[str, Any]) -> Dict[str, Any]:
    incident = Incident(**payload)

    if STRANDS_ENABLE_LLM:
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
    has_errors = any(validation_errors[k] for k in validation_errors)

    if has_errors:
        decision = compute_policy_score(
            intent="unknown",
            evidence={},
            confidence=0.0,
        )
        decision.decision = "human_review"
        decision.reasons.append("Schema validation failed")
    else:
        decision = compute_policy_score(
            intent=intent_data["intent"],
            evidence=investigation_data.get("evidence", {}),
            confidence=float(intent_data.get("confidence", 0.0)),
        )

    rca = RCA(
        incident_id=incident.incident_id,
        intent=intent_data.get("intent", "unknown"),
        summary=f"Incident classified as {intent_data.get('intent', 'unknown')}",
        root_cause=intent_data.get("rationale", ""),
        evidence=investigation_data.get("evidence", {}),
        actions_taken=action_data.get("actions", []),
        next_steps=["Review logs", "Validate downstream tables"],
        decision=decision,
    )

    _write_rca(incident.incident_id, rca)

    sn_context = incident.context.get("servicenow") if isinstance(incident.context, dict) else None
    sn_update = None
    if sn_context:
        rca_text = f"Decision: {decision.decision}\nScore: {decision.policy_score}\nReasons: {', '.join(decision.reasons)}"
        sn_update = update_ticket(sn_context, decision.decision, rca_text)

    output = {
        "incident_id": incident.incident_id,
        "intent": intent_data,
        "investigation": investigation_data,
        "actions": action_data,
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
