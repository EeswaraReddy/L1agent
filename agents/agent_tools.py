from typing import Dict, Any
from strands.tools import tool
from .schemas import Incident
from .intent_classifier import classify_intent
from .investigator import investigate
from .action_agent import act


@tool
def intent_classifier(payload: Dict[str, Any]) -> Dict[str, Any]:
    incident = Incident(**payload)
    return classify_intent(incident, force_rule_based=True).model_dump()


@tool
def investigator(payload: Dict[str, Any]) -> Dict[str, Any]:
    incident = Incident(**payload)
    intent = payload.get("intent") or "unknown"
    return investigate(incident, intent, force_rule_based=True).model_dump()


@tool
def action_agent(payload: Dict[str, Any]) -> Dict[str, Any]:
    incident = Incident(**payload)
    intent = payload.get("intent") or "unknown"
    return act(incident, intent, force_rule_based=True).model_dump()
