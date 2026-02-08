from typing import Dict, Any, List
from .schemas import PolicyDecision


DECISIONS = ["auto_close", "auto_retry", "escalate", "human_review", "update_only"]

INTENT_OVERRIDES = {
    "access_denied": "escalate",
    "kafka_events_failed": "human_review",
}


def compute_policy_score(intent: str, evidence: Dict[str, Any], confidence: float) -> PolicyDecision:
    reasons: List[str] = []

    if intent in INTENT_OVERRIDES:
        decision = INTENT_OVERRIDES[intent]
        reasons.append(f"Policy override for intent: {intent}")
        return PolicyDecision(
            intent=intent,
            confidence=confidence,
            policy_score=1.0,
            decision=decision,
            reasons=reasons,
        )

    score = 0.0

    if confidence >= 0.8:
        score += 0.4
        reasons.append("High intent confidence")
    elif confidence >= 0.6:
        score += 0.2
        reasons.append("Medium intent confidence")
    else:
        reasons.append("Low intent confidence")

    if evidence:
        score += 0.3
        reasons.append("Evidence collected")

    if "source_check" in evidence:
        status = evidence["source_check"].get("status")
        if status in ("zero_data", "missing_data"):
            score += 0.2
            reasons.append(f"Source data status: {status}")

    if "emr_logs" in evidence or "glue_logs" in evidence or "airflow_logs" in evidence:
        score += 0.1
        reasons.append("Logs available")

    score = min(score, 1.0)

    if score >= 0.8:
        decision = "auto_close"
    elif score >= 0.6:
        decision = "auto_retry"
    elif score >= 0.4:
        decision = "escalate"
    else:
        decision = "human_review"

    return PolicyDecision(
        intent=intent,
        confidence=confidence,
        policy_score=score,
        decision=decision,
        reasons=reasons,
    )
