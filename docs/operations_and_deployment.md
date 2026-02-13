# Operations and Deployment Guide

## 1) Prerequisites

- Python 3.10+ (runtime config uses Python 3.12)
- AWS credentials with access to:
  - CDK deployment
  - Lambda, IAM, S3
  - Bedrock AgentCore control/runtime APIs
- CDK installed and bootstrapped in target account

## 2) Deploy Infrastructure

```powershell
powershell -File scripts\deploy.ps1
```

This deploys tool Lambdas and RCA bucket.

## 3) Configure Gateway

Populate:
- `agentcore/gateway_config.json`
- `agentcore/gateway_tools.json`

Then run:

```powershell
python scripts\setup_gateway.py
```

## 4) Configure Runtime Environment

Copy and fill:

```powershell
copy .env.example .env
```

Core flags:
- `STRANDS_ENABLE_LLM=0|1`

Optional AgentCore governance flags:
- `AGENTCORE_POLICY_ENABLED=0|1`
- `AGENTCORE_POLICY_ENGINE_ID=<policy engine id>`
- `AGENTCORE_POLICY_STRICT=0|1`
- `AGENTCORE_EVALUATION_ENABLED=0|1`
- `AGENTCORE_EVALUATOR_ID=<evaluator id>`
- `AGENTCORE_EVALUATION_STRICT=0|1`
- `AGENTCORE_MIN_EVAL_SCORE=0.7`

## 5) Rollout Recommendation

1. Start with governance disabled.
2. Enable `AGENTCORE_POLICY_ENABLED=1` with `AGENTCORE_POLICY_STRICT=0`.
3. Enable evaluation with strict mode off.
4. Observe outcomes and tune thresholds.
5. Enable strict modes only after stability.

## 6) Verification Commands

Compile check:

```powershell
python -m compileall agents scripts
```

Workflow regression:

```powershell
$env:PYTHONPATH='.'
python scripts\run_eval.py
```

Service policy regression:

```powershell
$env:PYTHONPATH='.'
python scripts\run_policy_regression.py
```

AgentCore governance regression:

```powershell
$env:PYTHONPATH='.'
python scripts\run_agentcore_governance_regression.py
```

Dummy E2E:

```powershell
$env:PYTHONPATH='.'
python scripts\run_dummy_e2e.py
```

Live AgentCore smoke:

```powershell
$env:PYTHONPATH='.'
python scripts\run_agentcore_live_smoke.py --region us-east-1 --policy-engine-id <id> --evaluator-id <id>
```

## 7) Operational Notes

- If gateway/tool calls fail, orchestration still returns a controlled output with validation/evaluation signals.
- High-risk workflows and strict policy rules intentionally bias toward `escalate` or `human_review`.
- Governance strict mode can force `human_review` when policy/evaluation dependencies are unavailable.
