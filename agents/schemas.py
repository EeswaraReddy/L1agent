from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Incident(BaseModel):
    incident_id: str = Field(..., description="Unique incident identifier")
    summary: str
    details: Optional[str] = ""
    created_at: Optional[str] = None
    tags: List[str] = []
    context: Dict[str, Any] = {}


class IntentResult(BaseModel):
    intent: str
    confidence: float
    rationale: str


class InvestigationResult(BaseModel):
    intent: str
    evidence: Dict[str, Any]


class ActionResult(BaseModel):
    intent: str
    actions: List[Dict[str, Any]]
    status: str


class PolicyDecision(BaseModel):
    intent: str
    confidence: float
    policy_score: float
    decision: str
    reasons: List[str]


class RCA(BaseModel):
    incident_id: str
    intent: str
    summary: str
    root_cause: str
    evidence: Dict[str, Any]
    actions_taken: List[Dict[str, Any]]
    next_steps: List[str]
    decision: Optional[PolicyDecision] = None
