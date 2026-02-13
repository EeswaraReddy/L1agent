# Design Diagram

```mermaid
flowchart LR
    A[Incident Payload] --> B[AgentCore Runtime App\nagents/main.py]

    subgraph Orchestration
      B --> C[Intent Classifier]
      C --> D[Workflow Selector\nagents/workflows.py]
      D --> E[Investigator\nagents/investigator.py]
      E --> F[Action Agent\nagents/action_agent.py]
      F --> G[Workflow Evaluation\nagents/evaluation.py]
      G --> H[Policy Engine\nagents/policy.py]
      H --> I[Service Policy Pack\nagents/service_policy_pack.py]
      I --> J[AgentCore Governance (Optional)\nagents/agentcore_governance.py]
    end

    E -->|MCP tool search + call| K[AgentCore Gateway]
    F -->|MCP tool call| K

    K --> T1[get_emr_logs]
    K --> T2[get_glue_logs]
    K --> T3[get_mwaa_logs]
    K --> T4[get_cloudwatch_alarm]
    K --> T5[get_athena_query]
    K --> T6[verify_source_data]
    K --> T7[get_s3_logs]
    K --> T8[get_kafka_status]
    K --> T9[retry_emr]
    K --> T10[retry_glue_job]
    K --> T11[retry_airflow_dag]
    K --> T12[retry_athena_query]
    K --> T13[retry_kafka]
    K --> T14[update_servicenow_ticket]

    J -->|Decision + Reasons| L[Final Policy Decision]
    L --> M[RCA Object]
    M --> N[S3 RCA Bucket (Optional)]
    M --> O[ServiceNow Update (Optional)]
    M --> P[API/CLI Response]
```

## Decision Layers

1. Workflow evaluation checks confidence and step coverage.
2. Local policy scoring computes baseline decision.
3. Service policy pack applies strict per-service guardrails.
4. Optional AgentCore governance verifies policy engine/evaluator conditions.

## Workflow Coverage

- EMR: standard + spin-up failure specialization
- MWAA/Airflow: DAG failure/alarm workflows
- Glue: ETL failures + access-denied specialization
- Athena: query failure workflow
- Kafka: conservative human-review workflow
- Source/S3: missing or zero-data workflow
