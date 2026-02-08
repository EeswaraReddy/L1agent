import boto3
from common import parse_event, response_ok, response_error


athena = boto3.client("athena")


def handler(event, _context):
    body = parse_event(event)
    query_execution_id = body.get("query_execution_id")

    if not query_execution_id:
        return response_error("query_execution_id is required", event=event)

    resp = athena.get_query_execution(QueryExecutionId=query_execution_id)
    exec_info = resp.get("QueryExecution", {})

    status = exec_info.get("Status", {})
    result = {
        "query_execution_id": query_execution_id,
        "state": status.get("State"),
        "state_change_reason": status.get("StateChangeReason"),
        "engine_version": exec_info.get("EngineVersion"),
        "statistics": exec_info.get("Statistics"),
        "result_conf": exec_info.get("ResultConfiguration"),
    }

    return response_ok(result, event=event)
