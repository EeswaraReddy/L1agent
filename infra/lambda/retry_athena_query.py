import boto3
from common import parse_event, response_ok, response_error


athena = boto3.client("athena")


def handler(event, _context):
    body = parse_event(event)
    query = body.get("query")
    database = body.get("database")
    output_location = body.get("output_location")
    workgroup = body.get("workgroup")

    if not query:
        return response_error("query is required", event=event)
    if not output_location:
        return response_error("output_location is required", event=event)

    kwargs = {
        "QueryString": query,
        "ResultConfiguration": {"OutputLocation": output_location},
    }
    if database:
        kwargs["QueryExecutionContext"] = {"Database": database}
    if workgroup:
        kwargs["WorkGroup"] = workgroup

    resp = athena.start_query_execution(**kwargs)
    return response_ok({"status": "submitted", "query_execution_id": resp.get("QueryExecutionId")}, event=event)
