from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from .schemas import Incident


@dataclass(frozen=True)
class InvestigationStep:
    tool_suffix: str
    context_key: Optional[str]
    evidence_key: str
    query: str
    optional: bool = False


@dataclass(frozen=True)
class ActionStep:
    tool_suffix: str
    context_key: Optional[str]
    action_key: str
    optional: bool = False


@dataclass(frozen=True)
class WorkflowSpec:
    workflow_id: str
    service: str
    intents: List[str]
    risk_tier: str
    min_confidence: float
    auto_retry_allowed: bool
    investigation_steps: List[InvestigationStep]
    action_steps: List[ActionStep]
    required_evidence_keys: List[str]
    required_action_keys: List[str]


def _text(incident: Incident) -> str:
    return f"{incident.summary} {incident.details or ''}".lower()


def _contains_any(text: str, values: List[str]) -> bool:
    return any(v in text for v in values)


WORKFLOWS: Dict[str, WorkflowSpec] = {
    "emr_failure": WorkflowSpec(
        workflow_id="emr_failure",
        service="emr",
        intents=["emr_failure"],
        risk_tier="medium",
        min_confidence=0.6,
        auto_retry_allowed=True,
        investigation_steps=[
            InvestigationStep("get_emr_logs", "emr", "emr_logs", "emr logs"),
            InvestigationStep("get_cloudwatch_alarm", "alarm", "alarm", "cloudwatch emr alarm", optional=True),
        ],
        action_steps=[ActionStep("retry_emr", "emr_retry", "retry_emr")],
        required_evidence_keys=["emr_logs"],
        required_action_keys=["retry_emr"],
    ),
    "emr_spinup_failed": WorkflowSpec(
        workflow_id="emr_spinup_failed",
        service="emr",
        intents=["emr_failure"],
        risk_tier="high",
        min_confidence=0.7,
        auto_retry_allowed=True,
        investigation_steps=[
            InvestigationStep("get_emr_logs", "emr", "emr_logs", "emr bootstrap provisioning logs"),
            InvestigationStep("get_cloudwatch_alarm", "alarm", "alarm", "cloudwatch emr capacity alarm", optional=True),
        ],
        action_steps=[ActionStep("retry_emr", "emr_retry", "retry_emr")],
        required_evidence_keys=["emr_logs"],
        required_action_keys=["retry_emr"],
    ),
    "airflow_dag_failure": WorkflowSpec(
        workflow_id="airflow_dag_failure",
        service="mwaa_airflow",
        intents=["dag_failure", "mwaa_failure", "dag_alarm"],
        risk_tier="medium",
        min_confidence=0.6,
        auto_retry_allowed=True,
        investigation_steps=[
            InvestigationStep("get_mwaa_logs", "airflow", "airflow_logs", "mwaa airflow dag logs"),
            InvestigationStep("get_cloudwatch_alarm", "alarm", "dag_alarm", "cloudwatch alarm dag mwaa", optional=True),
        ],
        action_steps=[ActionStep("retry_airflow_dag", "airflow_retry", "retry_airflow_dag")],
        required_evidence_keys=["airflow_logs"],
        required_action_keys=["retry_airflow_dag"],
    ),
    "glue_etl_failure": WorkflowSpec(
        workflow_id="glue_etl_failure",
        service="glue",
        intents=["glue_etl_failure"],
        risk_tier="medium",
        min_confidence=0.6,
        auto_retry_allowed=True,
        investigation_steps=[
            InvestigationStep("get_glue_logs", "glue", "glue_logs", "glue etl logs"),
            InvestigationStep("verify_source_data", "source", "source_check", "s3 source data validation", optional=True),
        ],
        action_steps=[ActionStep("retry_glue_job", "glue_retry", "retry_glue_job")],
        required_evidence_keys=["glue_logs"],
        required_action_keys=["retry_glue_job"],
    ),
    "glue_access_denied": WorkflowSpec(
        workflow_id="glue_access_denied",
        service="glue",
        intents=["access_denied", "glue_etl_failure"],
        risk_tier="high",
        min_confidence=0.7,
        auto_retry_allowed=False,
        investigation_steps=[
            InvestigationStep("get_glue_logs", "glue", "glue_logs", "glue access denied logs"),
        ],
        action_steps=[],
        required_evidence_keys=["glue_logs"],
        required_action_keys=[],
    ),
    "athena_failure": WorkflowSpec(
        workflow_id="athena_failure",
        service="athena",
        intents=["athena_failure"],
        risk_tier="medium",
        min_confidence=0.6,
        auto_retry_allowed=True,
        investigation_steps=[
            InvestigationStep("get_athena_query", "athena_query", "athena_query", "athena query execution error"),
        ],
        action_steps=[ActionStep("retry_athena_query", "athena_retry", "retry_athena_query")],
        required_evidence_keys=["athena_query"],
        required_action_keys=["retry_athena_query"],
    ),
    "kafka_failure": WorkflowSpec(
        workflow_id="kafka_failure",
        service="kafka",
        intents=["kafka_events_failed"],
        risk_tier="high",
        min_confidence=0.7,
        auto_retry_allowed=False,
        investigation_steps=[
            InvestigationStep("get_kafka_status", "kafka", "kafka_status", "kafka msk status"),
        ],
        action_steps=[],
        required_evidence_keys=["kafka_status"],
        required_action_keys=[],
    ),
    "source_data_failure": WorkflowSpec(
        workflow_id="source_data_failure",
        service="s3_source",
        intents=["data_missing", "source_zero_data", "data_not_available"],
        risk_tier="low",
        min_confidence=0.6,
        auto_retry_allowed=False,
        investigation_steps=[
            InvestigationStep("verify_source_data", "source", "source_check", "s3 source data validation"),
            InvestigationStep("get_s3_logs", "s3_logs", "s3_logs", "s3 logs", optional=True),
        ],
        action_steps=[ActionStep("verify_source_data", "source", "verify_source_data")],
        required_evidence_keys=["source_check"],
        required_action_keys=[],
    ),
    "generic_access_denied": WorkflowSpec(
        workflow_id="generic_access_denied",
        service="iam_permissions",
        intents=["access_denied"],
        risk_tier="high",
        min_confidence=0.7,
        auto_retry_allowed=False,
        investigation_steps=[],
        action_steps=[],
        required_evidence_keys=[],
        required_action_keys=[],
    ),
    "unknown": WorkflowSpec(
        workflow_id="unknown",
        service="unknown",
        intents=["unknown", "batch_auto_recovery_failed"],
        risk_tier="high",
        min_confidence=0.8,
        auto_retry_allowed=False,
        investigation_steps=[],
        action_steps=[],
        required_evidence_keys=[],
        required_action_keys=[],
    ),
}


def select_workflow(intent: str, incident: Incident) -> WorkflowSpec:
    text = _text(incident)

    if intent == "emr_failure" and _contains_any(text, ["spin", "bootstrap", "provision", "cluster launch"]):
        return WORKFLOWS["emr_spinup_failed"]

    if intent in ("dag_failure", "mwaa_failure", "dag_alarm"):
        return WORKFLOWS["airflow_dag_failure"]

    if intent in ("data_missing", "source_zero_data", "data_not_available"):
        return WORKFLOWS["source_data_failure"]

    if intent == "access_denied":
        if "glue" in text or "glue" in incident.context:
            return WORKFLOWS["glue_access_denied"]
        return WORKFLOWS["generic_access_denied"]

    if intent == "kafka_events_failed":
        return WORKFLOWS["kafka_failure"]

    if intent in WORKFLOWS:
        return WORKFLOWS[intent]

    for workflow in WORKFLOWS.values():
        if intent in workflow.intents:
            return workflow

    return WORKFLOWS["unknown"]


def workflow_profile(spec: WorkflowSpec) -> Dict[str, Any]:
    return {
        "workflow_id": spec.workflow_id,
        "service": spec.service,
        "risk_tier": spec.risk_tier,
        "min_confidence": spec.min_confidence,
        "auto_retry_allowed": spec.auto_retry_allowed,
        "required_evidence_keys": list(spec.required_evidence_keys),
        "required_action_keys": list(spec.required_action_keys),
    }


def step_to_dict(step: InvestigationStep | ActionStep) -> Dict[str, Any]:
    return asdict(step)
