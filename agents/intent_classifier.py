import json
from typing import Any
from .schemas import Incident, IntentResult
from .config import STRANDS_ENABLE_LLM
from .agent_factory import build_agent
from .prompts import INTENT_CLASSIFIER_PROMPT


INTENTS = [
    "dag_failure",
    "dag_alarm",
    "mwaa_failure",
    "glue_etl_failure",
    "athena_failure",
    "emr_failure",
    "kafka_events_failed",
    "data_missing",
    "source_zero_data",
    "data_not_available",
    "batch_auto_recovery_failed",
    "access_denied",
    "unknown",
]


def is_non_incident_access_request(incident: Incident) -> bool:
    text = f"{incident.summary} {incident.details or ''}".lower()
    access_terms = (
        "access to prod",
        "production access",
        "prod access",
        "grant access",
        "request access",
        "need access",
        "prod credentials",
        "permission to prod",
    )
    request_terms = (
        "request",
        "grant",
        "need",
        "please provide",
        "please give",
    )
    return any(term in text for term in access_terms) or (
        ("prod" in text or "production" in text) and any(term in text for term in request_terms) and "access" in text
    )


def _rule_based_intent(text: str) -> IntentResult:
    t = text.lower()
    if "alarm" in t and ("dag" in t or "mwaa" in t or "airflow" in t):
        return IntentResult(intent="dag_alarm", confidence=0.6, rationale="Matched alarm for dag/mwaa")
    if "mwaa" in t or "airflow" in t or "dag" in t:
        return IntentResult(intent="mwaa_failure", confidence=0.6, rationale="Matched keyword dag/mwaa/airflow")
    if "glue" in t or "etl" in t:
        return IntentResult(intent="glue_etl_failure", confidence=0.6, rationale="Matched keyword glue/etl")
    if "athena" in t:
        return IntentResult(intent="athena_failure", confidence=0.6, rationale="Matched keyword athena")
    if "emr" in t:
        return IntentResult(intent="emr_failure", confidence=0.6, rationale="Matched keyword emr")
    if "kafka" in t or "msk" in t:
        return IntentResult(intent="kafka_events_failed", confidence=0.6, rationale="Matched keyword kafka/msk")
    if "access denied" in t or "permission" in t:
        return IntentResult(intent="access_denied", confidence=0.6, rationale="Matched access denied")
    if "zero" in t or "no data" in t:
        return IntentResult(intent="source_zero_data", confidence=0.6, rationale="Matched zero/no data")
    if "missing" in t or "not available" in t or "cmcm" in t:
        return IntentResult(intent="data_missing", confidence=0.6, rationale="Matched missing data")
    if "recovery" in t or "auto recover" in t:
        return IntentResult(intent="batch_auto_recovery_failed", confidence=0.6, rationale="Matched recovery failure")
    return IntentResult(intent="unknown", confidence=0.3, rationale="No match")


def _parse_llm_result(result: Any) -> IntentResult:
    if isinstance(result, dict):
        return IntentResult(**result)
    data = json.loads(result)
    return IntentResult(**data)


def _llm_intent(text: str) -> IntentResult:
    agent = build_agent(INTENT_CLASSIFIER_PROMPT)
    result = agent(text)
    return _parse_llm_result(result)


def classify_intent(incident: Incident, force_rule_based: bool = False) -> IntentResult:
    text = f"{incident.summary} {incident.details or ''}".strip()
    if is_non_incident_access_request(incident):
        return IntentResult(
            intent="access_denied",
            confidence=0.95,
            rationale="Access-to-production request detected; follow IAM/change-management access process",
        )

    if force_rule_based or not STRANDS_ENABLE_LLM:
        return _rule_based_intent(text)

    try:
        return _llm_intent(text)
    except Exception:
        return _rule_based_intent(text)
