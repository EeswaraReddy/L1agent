from typing import Dict, Any, List
from jsonschema import Draft202012Validator


INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string"},
        "confidence": {"type": "number"},
        "rationale": {"type": "string"},
    },
    "required": ["intent", "confidence", "rationale"],
    "additionalProperties": True,
}

INVESTIGATION_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string"},
        "evidence": {"type": "object"},
    },
    "required": ["intent", "evidence"],
    "additionalProperties": True,
}

ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string"},
        "actions": {"type": "array"},
        "status": {"type": "string"},
    },
    "required": ["intent", "actions", "status"],
    "additionalProperties": True,
}

ORCHESTRATOR_SCHEMA = {
    "type": "object",
    "properties": {
        "incident_id": {"type": "string"},
        "intent": {"type": "object"},
        "investigation": {"type": "object"},
        "actions": {"type": "object"},
        "policy": {"type": "object"},
        "rca": {"type": "object"},
    },
    "required": ["incident_id", "intent", "investigation", "actions", "policy", "rca"],
    "additionalProperties": True,
}


def _errors(validator: Draft202012Validator, payload: Dict[str, Any]) -> List[str]:
    return [e.message for e in validator.iter_errors(payload)]


def validate_intent(payload: Dict[str, Any]) -> List[str]:
    return _errors(Draft202012Validator(INTENT_SCHEMA), payload)


def validate_investigation(payload: Dict[str, Any]) -> List[str]:
    return _errors(Draft202012Validator(INVESTIGATION_SCHEMA), payload)


def validate_action(payload: Dict[str, Any]) -> List[str]:
    return _errors(Draft202012Validator(ACTION_SCHEMA), payload)


def validate_orchestrator(payload: Dict[str, Any]) -> List[str]:
    return _errors(Draft202012Validator(ORCHESTRATOR_SCHEMA), payload)
