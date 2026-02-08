import os
import boto3
from common import parse_event, response_ok, response_error


logs_client = boto3.client("logs")


def handler(event, _context):
    body = parse_event(event)
    env_name = body.get("env_name") or os.environ.get("MWAA_ENV_NAME")
    log_group = body.get("log_group")
    start_time = body.get("start_time")
    end_time = body.get("end_time")

    if not log_group:
        if not env_name:
            return response_error("log_group or env_name is required", event=event)
        log_group = f"/aws/mwaa/{env_name}/task"

    kwargs = {"logGroupName": log_group}
    if start_time:
        kwargs["startTime"] = int(start_time)
    if end_time:
        kwargs["endTime"] = int(end_time)

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
