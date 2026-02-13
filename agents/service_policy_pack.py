from typing import Any, Dict, List, Tuple

RESTRICTIVENESS = {
    "auto_close": 0,
    "update_only": 1,
    "auto_retry": 2,
    "escalate": 3,
    "human_review": 4,
}


def _more_restrictive(left: str, right: str) -> str:
    return left if RESTRICTIVENESS.get(left, 4) >= RESTRICTIVENESS.get(right, 4) else right


def _issues(evaluation: Dict[str, Any]) -> List[str]:
    raw = evaluation.get("issues", []) if isinstance(evaluation, dict) else []
    return [str(item).lower() for item in raw]


def _extract_status(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("status", "state", "query_state"):
            if key in value and value[key] is not None:
                return str(value[key]).upper()
        for nested in value.values():
            status = _extract_status(nested)
            if status:
                return status
    return ""


def _contains_access_denied(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_contains_access_denied(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_access_denied(v) for v in value)
    if isinstance(value, str):
        text = value.lower()
        return "access denied" in text or "not authorized" in text or "permission" in text
    return False


def enforce_service_policy(
    decision: str,
    confidence: float,
    evidence: Dict[str, Any],
    workflow_profile: Dict[str, Any],
    evaluation: Dict[str, Any],
) -> Tuple[str, List[str]]:
    reasons: List[str] = []
    service = str(workflow_profile.get("service", "unknown"))
    workflow_id = str(workflow_profile.get("workflow_id", "unknown"))
    evidence_coverage = float(evaluation.get("evidence_coverage", 0.0)) if isinstance(evaluation, dict) else 0.0
    action_coverage = float(evaluation.get("action_coverage", 0.0)) if isinstance(evaluation, dict) else 0.0
    issues = _issues(evaluation)

    if service == "kafka":
        decision = _more_restrictive("human_review", decision)
        reasons.append("Kafka policy: always require human review for data-loss safety")

    elif service == "emr":
        if workflow_id == "emr_spinup_failed":
            decision = _more_restrictive("escalate", decision)
            reasons.append("EMR spin-up policy: require escalation before remediation")
            if confidence < 0.85 or evidence_coverage < 1.0 or action_coverage < 1.0:
                decision = _more_restrictive("human_review", decision)
                reasons.append("EMR spin-up policy: confidence/coverage gate failed")
        if any("cluster_id" in issue for issue in issues):
            decision = _more_restrictive("human_review", decision)
            reasons.append("EMR policy: cluster identifier required")

    elif service == "glue":
        access_denied = workflow_id == "glue_access_denied" or any("access denied" in issue for issue in issues)
        if not access_denied:
            access_denied = _contains_access_denied(evidence.get("glue_logs", {}))

        if access_denied:
            decision = _more_restrictive("escalate", decision)
            reasons.append("Glue policy: access-denied incidents cannot auto-retry")
        if decision == "auto_close":
            decision = "auto_retry"
            reasons.append("Glue policy: disable auto-close for ETL failures")

    elif service == "mwaa_airflow":
        if evidence_coverage < 1.0 or action_coverage < 1.0:
            decision = _more_restrictive("escalate", decision)
            reasons.append("MWAA policy: require full log and retry coverage")
        if confidence < 0.7:
            decision = _more_restrictive("human_review", decision)
            reasons.append("MWAA policy: low confidence requires human review")

    elif service == "athena":
        status = _extract_status(evidence.get("athena_query", {}))
        retryable_states = {"FAILED", "CANCELLED", "TIMEOUT", "EXPIRED"}
        if decision in ("auto_retry", "auto_close") and status and status not in retryable_states:
            decision = _more_restrictive("human_review", decision)
            reasons.append(f"Athena policy: non-retryable query state {status}")
        if decision in ("auto_retry", "auto_close") and action_coverage < 1.0:
            decision = _more_restrictive("escalate", decision)
            reasons.append("Athena policy: retry path incomplete")

    return decision, reasons
