# Data Lake SRE Agent (AgentCore + Strands)

This scaffold implements a multi-agent incident handler for AWS data lake failures (EMR, Glue, MWAA/Airflow, S3 source data, Kafka/MSK). It follows the Amazon Bedrock AgentCore pattern of a runtime + MCP gateway for tools and uses Strands Agents for orchestration.

## Design
- AgentCore Runtime executes `agents/main.py` using `BedrockAgentCoreApp`.
- AgentCore Gateway exposes Lambda tools via MCP with Cognito/JWT auth.
- Intent → investigate → action → policy flow with strict schema validation.
- RCA artifacts are written to S3.

Design diagram: `docs/design_diagram.md`

## Repo Structure
- `infra/` CDK stack for tool Lambdas + S3 RCA bucket
- `agents/` Strands-based multi-agent workflow (intent -> investigate -> action -> policy)
- `agentcore/` AgentCore runtime + gateway configs
- `scripts/` Gateway setup + evaluation scripts
- `docs/` Design diagram

## End-to-End Flow
1. Incident payload arrives at the orchestrator.
2. **Intent Classifier** assigns intent from short description.
3. **Investigator** uses AgentCore Gateway semantic tool search + MCP calls.
4. **Action Agent** performs safe retries or validations when allowed.
5. **Policy Engine** scores confidence + evidence and selects a decision.
6. **ServiceNow Update** is executed (if credentials provided).
7. RCA is written to S3 and returned to the caller.

## Quick Start

### 1) Deploy Lambdas + RCA Bucket

```
cd infra
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cdk synth
cdk deploy
```

Outputs:
- `RcaBucketName`
- Lambda ARNs for each tool

### 2) Configure AgentCore Gateway

1. Update `agentcore/gateway_config.json` with Gateway + Cognito config.
2. Update `agentcore/gateway_tools.json` with the Lambda ARNs from CDK outputs.
3. Create gateway + targets:

```
python scripts/setup_gateway.py
```

### 3) Configure Environment

```
copy .env.example .env
```

Set at minimum:
- `AWS_REGION`
- `BEDROCK_REGION`
- `MODEL_ID`
- `GATEWAY_CONFIG_PATH`
- `RCA_BUCKET`

Optional for ServiceNow updates:
- `SERVICENOW_INSTANCE_URL`
- `SERVICENOW_USERNAME`
- `SERVICENOW_PASSWORD`

### 4) Run the Agent Locally

```
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python -m agents.main --input examples/incident.json
```

### 5) End-to-End Verification (Manual)
1. Confirm gateway targets exist and are healthy.
2. Run `python -m agents.main --input examples/incident.json`.
3. Verify an RCA JSON file was created under `s3://<RCA_BUCKET>/<RCA_PREFIX>/`.

### 6) Policy Evaluation

```
python scripts/run_eval.py
```

## Intent Taxonomy (Current)
- `dag_failure`
- `dag_alarm`
- `mwaa_failure`
- `glue_etl_failure`
- `athena_failure`
- `emr_failure`
- `kafka_events_failed`
- `data_missing`
- `source_zero_data`
- `data_not_available`
- `batch_auto_recovery_failed`
- `access_denied`
- `unknown`

## Tools (Gateway Targets)
- `get_emr_logs`
- `get_glue_logs`
- `get_mwaa_logs`
- `get_cloudwatch_alarm`
- `get_athena_query`
- `verify_source_data`
- `get_s3_logs`
- `retry_emr`
- `retry_glue_job`
- `retry_airflow_dag`
- `retry_athena_query`
- `retry_kafka`
- `update_servicenow_ticket`

## Testing Status
- End-to-end flow has **not** been executed in this environment.
- Use the manual verification and evaluation steps above to validate in your AWS account.
