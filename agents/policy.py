from typing import Dict, Any, List, Optional

from .schemas import PolicyDecision
from .service_policy_pack import enforce_service_policy

DECISIONS = ["auto_close", "auto_retry", "escalate", "human_review", "update_only"]

INTENT_OVERRIDES = {
    "access_denied": "escalate",
    "kafka_events_failed": "human_review",
}

RESTRICTIVENESS = {
    "auto_close": 0,
    "update_only": 1,
    "auto_retry": 2,
    "escalate": 3,
    "human_review": 4,
}


def _more_restrictive(left: str, right: str) -> str:
    return left if RESTRICTIVENESS.get(left, 4) >= RESTRICTIVENESS.get(right, 4) else right


def _base_decision(score: float) -> str:
    if score >= 0.8:
        return "auto_close"
    if score >= 0.6:
        return "auto_retry"
    if score >= 0.4:
        return "escalate"
    return "human_review"


def compute_policy_score(
    intent: str,
    evidence: Dict[str, Any],
    confidence: float,
    workflow_profile: Optional[Dict[str, Any]] = None,
    evaluation: Optional[Dict[str, Any]] = None,
) -> PolicyDecision:
    reasons: List[str] = []

    score = 0.0

    if confidence >= 0.8:
        score += 0.35
        reasons.append("High intent confidence")
    elif confidence >= 0.6:
        score += 0.2
        reasons.append("Medium intent confidence")
    else:
        reasons.append("Low intent confidence")

    if evidence:
        score += 0.25
        reasons.append("Evidence collected")

    if "source_check" in evidence:
        source_check = evidence.get("source_check", {})
        if isinstance(source_check, dict):
            status = source_check.get("status")
            if status in ("zero_data", "missing_data"):
                score += 0.2
                reasons.append(f"Source data status: {status}")

    if any(k in evidence for k in ("emr_logs", "glue_logs", "airflow_logs", "athena_query")):
        score += 0.1
        reasons.append("Primary diagnostics present")

    decision = _base_decision(min(score, 1.0))

    if intent in INTENT_OVERRIDES:
        decision = _more_restrictive(INTENT_OVERRIDES[intent], decision)
        reasons.append(f"Policy override for intent: {intent}")

    if workflow_profile:
        risk_tier = workflow_profile.get("risk_tier", "high")
        auto_retry_allowed = bool(workflow_profile.get("auto_retry_allowed", False))
        reasons.append(f"Workflow risk tier: {risk_tier}")

        if risk_tier == "high":
            score -= 0.1
        elif risk_tier == "low":
            score += 0.05

        if not auto_retry_allowed and decision == "auto_retry":
            decision = "escalate"
            reasons.append("Auto-retry blocked by workflow policy")

    if evaluation:
        evidence_coverage = float(evaluation.get("evidence_coverage", 0.0))
        action_coverage = float(evaluation.get("action_coverage", 0.0))
        recommended = evaluation.get("recommended_decision")
        hard_stop = bool(evaluation.get("hard_stop", False))

        score += 0.15 * evidence_coverage
        score += 0.1 * action_coverage
        reasons.append(f"Evidence coverage: {evidence_coverage:.2f}")
        reasons.append(f"Action coverage: {action_coverage:.2f}")

        if hard_stop:
            decision = "human_review"
            reasons.append("Evaluation hard-stop triggered")

        if isinstance(recommended, str) and recommended in RESTRICTIVENESS:
            restricted = _more_restrictive(recommended, decision)
            if restricted != decision:
                decision = restricted
                reasons.append(f"Evaluation recommendation enforced: {recommended}")

        for issue in evaluation.get("issues", [])[:3]:
            reasons.append(f"Eval issue: {issue}")

    if workflow_profile:
        decision, service_reasons = enforce_service_policy(
            decision=decision,
            confidence=confidence,
            evidence=evidence,
            workflow_profile=workflow_profile,
            evaluation=evaluation or {},
        )
        reasons.extend(service_reasons)

    score = max(0.0, min(score, 1.0))

    if decision not in RESTRICTIVENESS:
        decision = _base_decision(score)

    return PolicyDecision(
        intent=intent,
        confidence=confidence,
        policy_score=score,
        decision=decision,
        reasons=reasons,
    )
