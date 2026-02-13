from typing import Any, Dict, List

from .schemas import Incident
from .workflows import WorkflowSpec


def _coverage(required: List[str], actual: List[str]) -> float:
    if not required:
        return 1.0
    matched = sum(1 for item in required if item in actual)
    return matched / float(len(required))


def _recommendation(
    risk_tier: str,
    auto_retry_allowed: bool,
    evidence_coverage: float,
    action_coverage: float,
    confidence: float,
) -> str:
    if evidence_coverage < 0.5:
        return "human_review"
    if risk_tier == "high" and confidence < 0.8:
        return "escalate"
    if not auto_retry_allowed:
        return "escalate"
    if action_coverage < 0.5:
        return "escalate"
    return "auto_retry"


def evaluate_workflow(
    incident: Incident,
    intent_data: Dict[str, Any],
    investigation_data: Dict[str, Any],
    action_data: Dict[str, Any],
    workflow: WorkflowSpec,
    validation_errors: Dict[str, List[str]],
) -> Dict[str, Any]:
    confidence = float(intent_data.get("confidence", 0.0))
    evidence = investigation_data.get("evidence", {}) if isinstance(investigation_data, dict) else {}
    actions = action_data.get("actions", []) if isinstance(action_data, dict) else []

    evidence_keys = list(evidence.keys()) if isinstance(evidence, dict) else []
    action_keys: List[str] = []
    for action in actions:
        if isinstance(action, dict):
            action_keys.extend(action.keys())

    evidence_coverage = _coverage(workflow.required_evidence_keys, evidence_keys)
    action_coverage = _coverage(workflow.required_action_keys, action_keys)

    issues: List[str] = []
    if confidence < workflow.min_confidence:
        issues.append(
            f"Intent confidence {confidence:.2f} below workflow threshold {workflow.min_confidence:.2f}"
        )
    if evidence_coverage < 1.0:
        missing = [k for k in workflow.required_evidence_keys if k not in evidence_keys]
        if missing:
            issues.append(f"Missing required evidence: {', '.join(missing)}")
    if workflow.required_action_keys and action_coverage < 1.0:
        missing_actions = [k for k in workflow.required_action_keys if k not in action_keys]
        if missing_actions:
            issues.append(f"Missing required actions: {', '.join(missing_actions)}")

    text = f"{incident.summary} {incident.details or ''}".lower()
    if workflow.workflow_id == "emr_spinup_failed":
        emr_ctx = incident.context.get("emr", {}) if isinstance(incident.context, dict) else {}
        if not emr_ctx.get("cluster_id"):
            issues.append("EMR spin-up issue missing context.emr.cluster_id")
    if "access denied" in text and workflow.auto_retry_allowed:
        issues.append("Access-denied pattern detected; avoid automatic retries")

    has_validation_errors = any(validation_errors.get(k) for k in validation_errors)
    hard_stop = has_validation_errors or confidence < (workflow.min_confidence - 0.25)

    recommended_decision = _recommendation(
        workflow.risk_tier,
        workflow.auto_retry_allowed,
        evidence_coverage,
        action_coverage,
        confidence,
    )

    if "access denied" in text:
        recommended_decision = "escalate"

    return {
        "workflow_id": workflow.workflow_id,
        "service": workflow.service,
        "risk_tier": workflow.risk_tier,
        "intent_confidence": confidence,
        "evidence_coverage": round(evidence_coverage, 2),
        "action_coverage": round(action_coverage, 2),
        "hard_stop": hard_stop,
        "recommended_decision": recommended_decision,
        "issues": issues,
    }
