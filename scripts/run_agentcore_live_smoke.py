import argparse
import json
import os
from typing import Any, Dict

import boto3
from botocore.exceptions import BotoCoreError, ClientError


def _safe_error(exc: Exception) -> str:
    return f"{exc.__class__.__name__}: {exc}"


def _control_client(region: str):
    return boto3.client("bedrock-agentcore-control", region_name=region)


def _runtime_client(region: str):
    return boto3.client("bedrock-agentcore", region_name=region)


def _policy_engine_check(region: str, policy_engine_id: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {"policy_engine_id": policy_engine_id}
    try:
        client = _control_client(region)
        engine = client.get_policy_engine(policyEngineId=policy_engine_id)
        policies = client.list_policies(policyEngineId=policy_engine_id, maxResults=20)
        result.update(
            {
                "ok": True,
                "engine_status": engine.get("status"),
                "engine_name": engine.get("name"),
                "policy_count": len(policies.get("policies", [])),
            }
        )
    except (ClientError, BotoCoreError, Exception) as exc:
        result.update({"ok": False, "error": _safe_error(exc)})
    return result


def _evaluator_check(region: str, evaluator_id: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {"evaluator_id": evaluator_id}
    try:
        client = _control_client(region)
        evaluator = client.get_evaluator(evaluatorId=evaluator_id)
        result.update(
            {
                "ok": True,
                "status": evaluator.get("status"),
                "name": evaluator.get("evaluatorName"),
                "level": evaluator.get("level"),
            }
        )
    except (ClientError, BotoCoreError, Exception) as exc:
        result.update({"ok": False, "error": _safe_error(exc)})
    return result


def _evaluate_smoke(region: str, evaluator_id: str, incident_id: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {"evaluator_id": evaluator_id, "incident_id": incident_id}
    payload = {
        "sessionSpans": [
            {
                "spanId": f"span-{incident_id}",
                "traceId": incident_id,
                "name": "agentcore_live_smoke",
                "attributes": {
                    "intent": "emr_failure",
                    "service": "emr",
                    "workflow_id": "emr_failure",
                    "policy_decision": "escalate",
                    "evidence_coverage": 1.0,
                    "action_coverage": 1.0,
                },
            }
        ]
    }

    try:
        client = _runtime_client(region)
        response = client.evaluate(
            evaluatorId=evaluator_id,
            evaluationInput=payload,
            evaluationTarget={},
        )
        result.update({"ok": True, "evaluation_results": response.get("evaluationResults", [])})
    except (ClientError, BotoCoreError, Exception) as exc:
        result.update({"ok": False, "error": _safe_error(exc)})
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="AgentCore live smoke test for policy/evaluation")
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "us-east-1"))
    parser.add_argument("--policy-engine-id", default=os.getenv("AGENTCORE_POLICY_ENGINE_ID", ""))
    parser.add_argument("--evaluator-id", default=os.getenv("AGENTCORE_EVALUATOR_ID", ""))
    parser.add_argument("--incident-id", default="SMOKE-INC-001")
    args = parser.parse_args()

    output: Dict[str, Any] = {
        "region": args.region,
        "policy": {"ok": False, "skipped": True, "reason": "policy engine id not provided"},
        "evaluator": {"ok": False, "skipped": True, "reason": "evaluator id not provided"},
        "evaluate_call": {"ok": False, "skipped": True, "reason": "evaluator id not provided"},
    }

    if args.policy_engine_id:
        output["policy"] = _policy_engine_check(args.region, args.policy_engine_id)

    if args.evaluator_id:
        output["evaluator"] = _evaluator_check(args.region, args.evaluator_id)
        output["evaluate_call"] = _evaluate_smoke(args.region, args.evaluator_id, args.incident_id)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
