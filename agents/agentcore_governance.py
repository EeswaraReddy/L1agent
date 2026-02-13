from typing import Any, Dict, List, Optional, Tuple

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from .config import (
    AGENTCORE_EVALUATION_ENABLED,
    AGENTCORE_EVALUATION_STRICT,
    AGENTCORE_EVALUATOR_ID,
    AGENTCORE_MIN_EVAL_SCORE,
    AGENTCORE_POLICY_ENABLED,
    AGENTCORE_POLICY_ENGINE_ID,
    AGENTCORE_POLICY_STRICT,
    AWS_REGION,
)

RESTRICTIVENESS = {
    "auto_close": 0,
    "update_only": 1,
    "auto_retry": 2,
    "escalate": 3,
    "human_review": 4,
}


def _more_restrictive(left: str, right: str) -> str:
    return left if RESTRICTIVENESS.get(left, 4) >= RESTRICTIVENESS.get(right, 4) else right


def _control_client():
    return boto3.client("bedrock-agentcore-control", region_name=AWS_REGION)


def _runtime_client():
    return boto3.client("bedrock-agentcore", region_name=AWS_REGION)


def _safe_error(exc: Exception) -> str:
    return f"{exc.__class__.__name__}: {exc}"


def fetch_policy_context() -> Dict[str, Any]:
    context: Dict[str, Any] = {
        "enabled": AGENTCORE_POLICY_ENABLED,
        "policy_engine_id": AGENTCORE_POLICY_ENGINE_ID,
    }

    if not AGENTCORE_POLICY_ENABLED:
        return context

    if not AGENTCORE_POLICY_ENGINE_ID:
        context["error"] = "AGENTCORE_POLICY_ENGINE_ID is required when AGENTCORE_POLICY_ENABLED=1"
        return context

    try:
        client = _control_client()
        engine = client.get_policy_engine(policyEngineId=AGENTCORE_POLICY_ENGINE_ID)
        policies = client.list_policies(policyEngineId=AGENTCORE_POLICY_ENGINE_ID, maxResults=20)
        policy_items = policies.get("policies", [])
        context.update(
            {
                "ok": True,
                "engine_status": engine.get("status", "UNKNOWN"),
                "engine_name": engine.get("name"),
                "policy_count": len(policy_items),
                "policy_statuses": [str(item.get("status", "UNKNOWN")) for item in policy_items],
            }
        )
        return context
    except (ClientError, BotoCoreError, Exception) as exc:
        context["error"] = _safe_error(exc)
        return context


def _extract_numeric_scores(value: Any) -> List[float]:
    scores: List[float] = []

    if isinstance(value, dict):
        for key, nested in value.items():
            if isinstance(nested, (int, float)) and "score" in str(key).lower():
                scores.append(float(nested))
            scores.extend(_extract_numeric_scores(nested))
    elif isinstance(value, list):
        for item in value:
            scores.extend(_extract_numeric_scores(item))

    return scores


def _build_evaluation_input(
    incident_id: str,
    intent: str,
    workflow_id: str,
    service: str,
    policy_decision: str,
    evidence_coverage: float,
    action_coverage: float,
) -> Dict[str, Any]:
    span_id = f"{incident_id}-{workflow_id}"
    return {
        "sessionSpans": [
            {
                "spanId": span_id,
                "traceId": incident_id,
                "name": "incident_policy_decision",
                "attributes": {
                    "intent": intent,
                    "service": service,
                    "workflow_id": workflow_id,
                    "policy_decision": policy_decision,
                    "evidence_coverage": evidence_coverage,
                    "action_coverage": action_coverage,
                },
            }
        ]
    }


def run_online_evaluation(
    evaluator_id: str,
    evaluation_input: Dict[str, Any],
    evaluation_target: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    try:
        client = _runtime_client()
        response = client.evaluate(
            evaluatorId=evaluator_id,
            evaluationInput=evaluation_input,
            evaluationTarget=evaluation_target or {},
        )
        scores = _extract_numeric_scores(response.get("evaluationResults", []))
        return {
            "ok": True,
            "evaluator_id": evaluator_id,
            "raw": response,
            "min_score": min(scores) if scores else None,
            "score_count": len(scores),
        }
    except (ClientError, BotoCoreError, Exception) as exc:
        return {
            "ok": False,
            "evaluator_id": evaluator_id,
            "error": _safe_error(exc),
        }


def enforce_governance_outcome(
    decision: str,
    policy_context: Dict[str, Any],
    evaluation_context: Dict[str, Any],
) -> Tuple[str, List[str]]:
    reasons: List[str] = []
    updated = decision

    if AGENTCORE_POLICY_ENABLED:
        if not policy_context.get("ok"):
            reasons.append("AgentCore policy context unavailable")
            if AGENTCORE_POLICY_STRICT:
                updated = _more_restrictive("human_review", updated)
                reasons.append("AgentCore policy strict mode enforced")
        elif str(policy_context.get("engine_status", "UNKNOWN")).upper() != "ACTIVE":
            reasons.append(f"AgentCore policy engine status: {policy_context.get('engine_status')}")
            if AGENTCORE_POLICY_STRICT:
                updated = _more_restrictive("human_review", updated)
                reasons.append("AgentCore policy strict mode enforced")

    if AGENTCORE_EVALUATION_ENABLED:
        if not evaluation_context.get("ok"):
            reasons.append("AgentCore evaluation unavailable")
            if AGENTCORE_EVALUATION_STRICT:
                updated = _more_restrictive("human_review", updated)
                reasons.append("AgentCore evaluation strict mode enforced")
        else:
            min_score = evaluation_context.get("min_score")
            if isinstance(min_score, (int, float)) and float(min_score) < AGENTCORE_MIN_EVAL_SCORE:
                updated = _more_restrictive("human_review", updated)
                reasons.append(
                    f"AgentCore evaluation score {float(min_score):.2f} below threshold {AGENTCORE_MIN_EVAL_SCORE:.2f}"
                )

    return updated, reasons


def apply_agentcore_governance(
    incident_id: str,
    intent: str,
    workflow_profile: Dict[str, Any],
    decision: str,
    evaluation: Dict[str, Any],
) -> Tuple[Dict[str, Any], str, List[str]]:
    governance: Dict[str, Any] = {}

    policy_context = fetch_policy_context()
    governance["policy"] = policy_context

    evaluation_context: Dict[str, Any] = {
        "enabled": AGENTCORE_EVALUATION_ENABLED,
        "evaluator_id": AGENTCORE_EVALUATOR_ID,
    }

    if AGENTCORE_EVALUATION_ENABLED:
        if not AGENTCORE_EVALUATOR_ID:
            evaluation_context["ok"] = False
            evaluation_context["error"] = "AGENTCORE_EVALUATOR_ID is required when AGENTCORE_EVALUATION_ENABLED=1"
        else:
            eval_input = _build_evaluation_input(
                incident_id=incident_id,
                intent=intent,
                workflow_id=str(workflow_profile.get("workflow_id", "unknown")),
                service=str(workflow_profile.get("service", "unknown")),
                policy_decision=decision,
                evidence_coverage=float(evaluation.get("evidence_coverage", 0.0)),
                action_coverage=float(evaluation.get("action_coverage", 0.0)),
            )
            evaluation_context = run_online_evaluation(
                evaluator_id=AGENTCORE_EVALUATOR_ID,
                evaluation_input=eval_input,
            )
            evaluation_context["enabled"] = True

    governance["evaluation"] = evaluation_context

    updated_decision, reasons = enforce_governance_outcome(
        decision=decision,
        policy_context=policy_context,
        evaluation_context=evaluation_context,
    )

    return governance, updated_decision, reasons
