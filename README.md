# Data Lake SRE Agent (AgentCore + Strands)

This project implements an enterprise-style incident handler for AWS data platform failures.

It combines:
- Workflow-based orchestration by issue type
- Strict per-service policy controls
- Optional Amazon Bedrock AgentCore policy/evaluation governance
- MCP tool execution through AgentCore Gateway

## What It Covers End-to-End

Supported domains:
- EMR failures (including cluster spin-up failures)
- MWAA/Airflow DAG failures and alarms
- Glue ETL failures and Glue access/permission incidents
- Athena query failures
- Kafka/MSK event pipeline failures
- Source data missing/zero-data scenarios (S3)

End-to-end lifecycle:
1. Receive incident payload
2. Classify intent
3. Select workflow from intent + context
4. Run investigation steps (logs/status/alarms/source checks)
5. Run action steps (retries or safe no-op)
6. Evaluate coverage and risk gates
7. Apply local policy + service policy pack
8. Optionally apply AgentCore governance (policy engine + online evaluation)
9. Build RCA, optionally update ServiceNow, optionally write RCA to S3

## Architecture and Design

Main runtime entry:
- `agents/main.py`

Orchestrator:
- `agents/orchestrator.py`

Core design modules:
- `agents/workflows.py`: workflow catalog + routing logic
- `agents/investigator.py`: workflow-driven evidence collection
- `agents/action_agent.py`: workflow-driven actions with safety blocks
- `agents/evaluation.py`: evidence/action coverage and hard-stop checks
- `agents/policy.py`: base policy scoring and decision composition
- `agents/service_policy_pack.py`: strict service-specific guardrails
- `agents/agentcore_governance.py`: optional AgentCore policy/evaluation enforcement

Detailed diagram:
- `docs/design_diagram.md`

## Workflow Model

Workflow selection is intent-aware and context-aware.

Examples:
- `emr_failure` + spin/bootstrap wording -> `emr_spinup_failed`
- `dag_failure`/`dag_alarm`/`mwaa_failure` -> `airflow_dag_failure`
- `access_denied` + Glue context -> `glue_access_denied`

Each workflow defines:
- Required investigation steps
- Required action steps
- Minimum confidence
- Risk tier
- Auto-retry allowance
- Required evidence/action keys

## Policy Model

Decision layering:
1. Base policy score (`agents/policy.py`)
2. Workflow-aware evaluation constraints (`agents/evaluation.py`)
3. Strict service policy pack (`agents/service_policy_pack.py`)
4. Optional AgentCore governance (`agents/agentcore_governance.py`)

Service policy pack behavior (strict):
- EMR spin-up failures: escalation/human-review gates when confidence or coverage is weak
- Glue access-denied: blocks auto-retry and forces escalation
- MWAA: requires full coverage; low confidence can force human review
- Athena: blocks retries on non-retryable query states
- Kafka: forces human review for safety

## AgentCore Governance Integration (Optional)

Supported APIs:
- `bedrock-agentcore-control`: policy engine/evaluator metadata checks
- `bedrock-agentcore`: runtime `Evaluate` calls

Environment flags:
- `AGENTCORE_POLICY_ENABLED`
- `AGENTCORE_POLICY_ENGINE_ID`
- `AGENTCORE_POLICY_STRICT`
- `AGENTCORE_EVALUATION_ENABLED`
- `AGENTCORE_EVALUATOR_ID`
- `AGENTCORE_EVALUATION_STRICT`
- `AGENTCORE_MIN_EVAL_SCORE`

If strict mode is enabled and governance is unavailable or failing, decision is pushed to `human_review`.

## Repository Structure

- `infra/`: CDK stack (tool Lambdas + RCA bucket)
- `agents/`: orchestration and policy modules
- `agentcore/`: runtime and gateway configs
- `scripts/`: deployment, gateway setup, regressions, smoke tests
- `examples/`: incident payloads and regression datasets
- `docs/`: diagrams and operations guidance

## Deployment

### 1) Deploy infrastructure

```powershell
cd infra
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cdk synth
cdk deploy
```

Or use helper script:

```powershell
powershell -File scripts\deploy.ps1
```

### 2) Configure AgentCore Gateway

1. Fill `agentcore/gateway_config.json`
2. Fill `agentcore/gateway_tools.json` with deployed Lambda ARNs
3. Run:

```powershell
python scripts\setup_gateway.py
```

### 3) Configure environment

```powershell
copy .env.example .env
```

Minimum required:
- `AWS_REGION`
- `BEDROCK_REGION`
- `MODEL_ID`
- `GATEWAY_CONFIG_PATH`
- `RCA_BUCKET` (if RCA persistence needed)

## Running

Local incident run:

```powershell
$env:PYTHONPATH='.'
python -m agents.main --input examples/incident.json
```

## Validation and Testing

Workflow regression:

```powershell
$env:PYTHONPATH='.'
python scripts\run_eval.py
```

Policy pack regression:

```powershell
$env:PYTHONPATH='.'
python scripts\run_policy_regression.py
```

AgentCore governance regression (offline logic):

```powershell
$env:PYTHONPATH='.'
python scripts\run_agentcore_governance_regression.py
```

Dummy E2E (stubbed dependencies, no live AWS required):

```powershell
$env:PYTHONPATH='.'
python scripts\run_dummy_e2e.py
```

Live AgentCore smoke:

```powershell
$env:PYTHONPATH='.'
python scripts\run_agentcore_live_smoke.py --region us-east-1 --policy-engine-id <id> --evaluator-id <id>
```

## Current Status

Implemented:
- Workflow orchestration by issue type
- Strict per-service policy pack
- AgentCore governance integration hooks
- Regression suites and dummy E2E runner

To run live governance end-to-end, configure valid AWS credentials plus real AgentCore Policy Engine/Evaluator IDs.
