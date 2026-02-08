import os
import boto3
from common import parse_event, response_ok, response_error


logs_client = boto3.client("logs")


def handler(event, _context):
    body = parse_event(event)
    log_group = body.get("log_group") or os.environ.get("GLUE_LOG_GROUP")
    start_time = body.get("start_time")
    end_time = body.get("end_time")
    filter_pattern = body.get("filter", "")

    if not log_group:
        return response_error("log_group is required", event=event)

    kwargs = {"logGroupName": log_group}
    if start_time:
        kwargs["startTime"] = int(start_time)
    if end_time:
        kwargs["endTime"] = int(end_time)
    if filter_pattern:
        kwargs["filterPattern"] = filter_pattern

    resp = logs_client.filter_log_events(**kwargs)
    events = [
        {
            "timestamp": e.get("timestamp"),
            "message": e.get("message"),
            "log_stream": e.get("logStreamName"),
        }
        for e in resp.get("events", [])
    ]

    return response_ok({"log_group": log_group, "events": events}, event=event)
