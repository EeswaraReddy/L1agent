# Design Diagram

```mermaid
flowchart LR
    A[ServiceNow Incident Payload] -->|Incident JSON| B[AgentCore Runtime App
agents/main.py]

    subgraph Multi-Agent Flow (Strands)
      B --> C[Intent Classifier Agent]
      C --> D[Investigator Agent]
      D --> E[Action Agent]
      E --> F[Policy Engine]
    end

    D -->|MCP Tool Search| G[AgentCore Gateway
(MCP + Cognito/JWT)]
    G --> T1[get_emr_logs Lambda]
    G --> T2[get_glue_logs Lambda]
    G --> T3[get_mwaa_logs Lambda]
    G --> T4[get_cloudwatch_alarm Lambda]
    G --> T5[verify_source_data Lambda]
    G --> T6[get_athena_query Lambda]
    G --> T7[retry_athena_query Lambda]
    G --> T8[retry_glue_job Lambda]
    G --> T9[retry_emr Lambda]
    G --> T10[retry_airflow_dag Lambda]
    G --> T11[update_servicenow_ticket Lambda]

    F -->|Decision + RCA| H[S3 RCA Bucket]
    F -->|Update ticket| T11

    B -->|Final Response| Z[ServiceNow Update / L1 Response]
```
